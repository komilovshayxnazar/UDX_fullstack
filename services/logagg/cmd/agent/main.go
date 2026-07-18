// Command agent tails a JSON-line log file and streams compressed batches
// of LogLine records to the central server over gRPC.

package main

import (
	"context"
	"errors"
	"flag"
	"io"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	pb "github.com/shayxnazar/logagg/gen/logagg/v1"
	"github.com/shayxnazar/logagg/internal/batch"
	"github.com/shayxnazar/logagg/internal/compress"
	"github.com/shayxnazar/logagg/internal/logline"
	"github.com/shayxnazar/logagg/internal/tailer"
	"github.com/shayxnazar/logagg/internal/transport"
)

func main() {
	file := flag.String("file", "/var/log/fastapi/app.log", "log file to tail")
	addr := flag.String("server", transport.DefaultAddr, "central server gRPC address")
	host, _ := os.Hostname()
	source := flag.String("source", host, "agent identifier (sent in LogBatch.source)")
	flag.Parse()

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	// wire: tailer -> batcher -> gRPC stream. The tailer pushes to lines; a
	// small pump forwards lines into the batcher; sealed batches are sent
	// on the gRPC stream. All three are driven by a single supervisor
	// goroutine that retries the gRPC connection on failure.
	lines := make(chan logline.LogLine, 4096)
	t := tailer.New(*file, lines, 250*time.Millisecond)

	batches := make(chan batch.Batch, 64)
	asm := batch.NewAssembler(ctx, batches)
	defer asm.Close()

	// tailer pump
	go func() {
		if err := t.Run(ctx); err != nil && !errors.Is(err, context.Canceled) {
			log.Printf("agent: tailer: %v", err)
		}
		close(lines)
	}()
	// line pump: tailer -> batcher
	var pumpWG sync.WaitGroup
	pumpWG.Add(1)
	go func() {
		defer pumpWG.Done()
		for l := range lines {
			asm.Push(l)
		}
	}()

	// stream loop
	for {
		if err := ctx.Err(); err != nil {
			break
		}
		if err := streamOnce(ctx, *addr, *source, batches); err != nil {
			if errors.Is(err, context.Canceled) {
				break
			}
			log.Printf("agent: stream: %v (retry in 1s)", err)
			select {
			case <-ctx.Done():
			case <-time.After(time.Second):
			}
			continue
		}
	}

	pumpWG.Wait()
	log.Printf("agent: shutting down (skipped %d bad lines)", t.Skipped())
}

func streamOnce(ctx context.Context, addr, source string, batches <-chan batch.Batch) error {
	cc, err := transport.Dial(addr)
	if err != nil {
		return err
	}
	defer cc.Close()
	client := pb.NewIngestServiceClient(cc)
	stream, err := client.Stream(ctx)
	if err != nil {
		return err
	}
	for {
		select {
		case <-ctx.Done():
			_, _ = stream.CloseAndRecv()
			return ctx.Err()
		case b, ok := <-batches:
			if !ok {
				_, err := stream.CloseAndRecv()
				return err
			}
			payload, err := encode(b.Lines)
			if err != nil {
				return err
			}
			if err := stream.Send(&pb.LogBatch{
				Payload:        payload,
				Count:          uint32(len(b.Lines)),
				Source:         source,
				SealedAtUnixNs: b.SealedAt.UnixNano(),
			}); err != nil {
				if errors.Is(err, io.EOF) {
					return nil
				}
				return err
			}
		}
	}
}

func encode(lines []logline.LogLine) ([]byte, error) {
	raw, err := logline.EncodeBatch(lines)
	if err != nil {
		return nil, err
	}
	return compress.Compress(raw)
}
