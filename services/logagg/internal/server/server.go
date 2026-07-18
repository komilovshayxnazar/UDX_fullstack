// Package server hosts the gRPC IngestService implementation and the
// worker pool that fans compressed batches out to storage. The structure
// follows the workflow's stage 3:
//
//   - sync.Pool recycles the per-batch decompressed byte buffers
//   - a fixed worker pool decompresses and decodes incoming LogBatches
//   - a single internal channel feeds the storage engine
package server

import (
	"context"
	"io"
	"log"
	"runtime"
	"sync"

	pb "github.com/shayxnazar/logagg/gen/logagg/v1"
	"github.com/shayxnazar/logagg/internal/compress"
	"github.com/shayxnazar/logagg/internal/logline"
)

// Sink is the contract between the gRPC handler and the storage engine. The
// server doesn't know about WAL, chunks, or index — it just hands decoded
// log lines to whatever Sink the caller provides. This keeps the package
// unit-testable and the dependency graph one-way.
type Sink interface {
	Append(ctx context.Context, lines []logline.LogLine) error
}

// IngestService implements pb.IngestServiceServer.
type IngestService struct {
	pb.UnimplementedIngestServiceServer

	sink     Sink
	workers  int
	incoming chan []logline.LogLine
	recvPool sync.Pool // for reused byte slices during decompression
	wg       sync.WaitGroup
}

// New constructs an IngestService and starts its worker pool. The worker
// count defaults to NumCPU*2 and the internal channel is buffered to absorb
// bursty ingest.
func New(sink Sink) *IngestService {
	return NewWithWorkers(sink, runtime.NumCPU()*2, 65536)
}

// NewWithWorkers lets the caller pin the pool size and channel capacity.
func NewWithWorkers(sink Sink, workers, channelCap int) *IngestService {
	if workers <= 0 {
		workers = 1
	}
	if channelCap <= 0 {
		channelCap = 1024
	}
	s := &IngestService{
		sink:     sink,
		workers:  workers,
		incoming: make(chan []logline.LogLine, channelCap),
		recvPool: sync.Pool{New: func() any { b := make([]byte, 0, 64*1024); return &b }},
	}
	for i := 0; i < workers; i++ {
		s.wg.Add(1)
		go s.worker()
	}
	return s
}

// Close drains the worker pool. The gRPC server is shut down by the caller
// before Close is called.
func (s *IngestService) Close() {
	close(s.incoming)
	s.wg.Wait()
}

// Stream is the client-streaming RPC entry point. Each Recv pulls a
// compressed batch, decompresses it, and forwards the decoded lines to the
// worker pool. The first error returns the Ack with the error string.
func (s *IngestService) Stream(stream pb.IngestService_StreamServer) error {
	var total uint64
	ctx := stream.Context()
	for {
		batch, err := stream.Recv()
		if err == io.EOF {
			return stream.SendAndClose(&pb.Ack{Received: total})
		}
		if err != nil {
			return stream.SendAndClose(&pb.Ack{Received: total, Error: err.Error()})
		}
		if len(batch.Payload) == 0 {
			continue
		}
		// Stage 3: decompress inside a pool to avoid per-batch allocation.
		bufPtr := s.recvPool.Get().(*[]byte)
		*bufPtr = (*bufPtr)[:0]
		decoded, err := compress.Decompress(batch.Payload)
		if err != nil {
			s.recvPool.Put(bufPtr)
			return stream.SendAndClose(&pb.Ack{Received: total, Error: "decompress: " + err.Error()})
		}
		*bufPtr = decoded
		s.recvPool.Put(bufPtr)

		lines, err := logline.DecodeBatch(decoded)
		if err != nil {
			return stream.SendAndClose(&pb.Ack{Received: total, Error: "decode: " + err.Error()})
		}
		total += uint64(len(lines))

		// Hand the batch to the worker pool via the internal channel.
		// Backpressure naturally throttles the gRPC handler.
		select {
		case s.incoming <- lines:
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

func (s *IngestService) worker() {
	defer s.wg.Done()
	for lines := range s.incoming {
		ctx := context.Background()
		if err := s.sink.Append(ctx, lines); err != nil {
			log.Printf("ingest: sink append: %v", err)
		}
	}
}
