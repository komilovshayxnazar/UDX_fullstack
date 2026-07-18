// Command server runs the central ingestion server: gRPC on :50051, a WAL
// for durability, a 1-hour chunk store, and an in-memory inverted index.

package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	pb "github.com/shayxnazar/logagg/gen/logagg/v1"
	"github.com/shayxnazar/logagg/internal/chunk"
	"github.com/shayxnazar/logagg/internal/index"
	"github.com/shayxnazar/logagg/internal/logline"
	"github.com/shayxnazar/logagg/internal/server"
	"github.com/shayxnazar/logagg/internal/transport"
	"github.com/shayxnazar/logagg/internal/wal"
)

func main() {
	addr := flag.String("addr", transport.DefaultAddr, "gRPC listen address")
	dataDir := flag.String("data", "./data", "data directory (WAL + chunks live here)")
	workers := flag.Int("workers", 0, "ingest worker count (0 = NumCPU*2)")
	flag.Parse()

	if err := os.MkdirAll(*dataDir, 0o755); err != nil {
		log.Fatalf("server: mkdir data: %v", err)
	}

	store, err := chunk.NewStore(*dataDir)
	if err != nil {
		log.Fatalf("server: open chunk store: %v", err)
	}

	idx := index.New()
	if err := idx.Rebuild(store); err != nil {
		log.Fatalf("server: rebuild index: %v", err)
	}

	walPath := filepath.Join(*dataDir, "wal", "active.wal")
	w, err := wal.Open(walPath, replayConsumer(store))
	if err != nil {
		log.Fatalf("server: open wal: %v", err)
	}
	defer w.Close()

	sink := &walSink{wal: w, store: store, idx: idx}
	ingest := server.NewWithWorkers(sink, *workers, 65536)
	defer ingest.Close()

	lis, gs, err := transport.Listen(*addr)
	if err != nil {
		log.Fatalf("server: listen: %v", err)
	}
	pb.RegisterIngestServiceServer(gs, ingest)

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	go func() {
		log.Printf("server: listening on %s, data=%s", *addr, *dataDir)
		if err := gs.Serve(lis); err != nil {
			log.Printf("server: grpc serve: %v", err)
		}
	}()

	go rotateLoop(ctx, store, idx)

	<-ctx.Done()
	log.Printf("server: shutting down")
	if err := store.Rotate(); err != nil {
		log.Printf("server: rotate on shutdown: %v", err)
	}
	gs.GracefulStop()
}

type walSink struct {
	wal   *wal.WAL
	store *chunk.Store
	idx   *index.Index
}

func (s *walSink) Append(ctx context.Context, lines []logline.LogLine) error {
	if err := s.wal.Append(lines); err != nil {
		return err
	}
	return s.store.Append(lines)
}

func replayConsumer(store *chunk.Store) func([]logline.LogLine) error {
	return func(lines []logline.LogLine) error {
		// Replay re-populates the chunk store. The index is rebuilt from
		// disk before the WAL is opened, so we don't update it here.
		return store.Append(lines)
	}
}

func rotateLoop(ctx context.Context, store *chunk.Store, idx *index.Index) {
	t := time.NewTicker(5 * time.Minute)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			before := len(store.Rotated())
			if err := store.Rotate(); err != nil {
				log.Printf("server: rotate: %v", err)
				continue
			}
			after := len(store.Rotated())
			for _, ref := range store.Rotated()[before:after] {
				addRefToIndex(idx, ref)
			}
		}
	}
}

// addRefToIndex reads a freshly-rotated chunk and registers its (field,
// value) pairs in the inverted index. Done out-of-band so the rotate loop
// is decoupled from the index's main path.
func addRefToIndex(idx *index.Index, ref chunk.Ref) {
	lines, err := chunk.ReadLines(ref.Path)
	if err != nil {
		log.Printf("server: index add read %s: %v", ref.Path, err)
		return
	}
	for _, l := range lines {
		for _, field := range []string{index.FieldService, index.FieldLevel, index.FieldTraceID} {
			if v := index.ExtractField(l, field); v != "" {
				idx.Add(field, v, ref)
			}
		}
	}
}
