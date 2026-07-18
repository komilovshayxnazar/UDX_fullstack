// Command memdb wires the sharded engine, WAL, and TCP server together.
package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/komilovshayxnazar/memdb/server"
	"github.com/komilovshayxnazar/memdb/storage"
	"github.com/komilovshayxnazar/memdb/wal"
)

func main() {
	addr := flag.String("addr", ":5455", "TCP listen address")
	dataDir := flag.String("data", "./data", "data directory (WAL + snapshot)")
	syncMode := flag.String("sync", "interval", "fsync mode: always | interval | never")
	syncEvery := flag.Duration("sync-every", 200*time.Millisecond, "background fsync period when --sync=interval")
	idle := flag.Duration("idle", 5*time.Minute, "connection idle timeout")
	autoSnapshot := flag.Duration("auto-snapshot", 0, "if >0, take a snapshot every N (e.g. 5m)")
	flag.Parse()

	engine := storage.New()

	mode := wal.SyncInterval
	switch *syncMode {
	case "always":
		mode = wal.SyncAlways
	case "never":
		mode = wal.SyncNever
	case "interval":
		mode = wal.SyncInterval
	default:
		log.Fatalf("memdb: unknown --sync mode %q", *syncMode)
	}

	w, err := wal.Open(wal.Config{Dir: *dataDir, SyncMode: mode, SyncEvery: *syncEvery}, engine)
	if err != nil {
		log.Fatalf("memdb: open wal: %v", err)
	}
	log.Printf("memdb: recovered %d keys from %s", engine.Len(), *dataDir)

	srv := server.New(server.Config{
		Addr:        *addr,
		IdleTimeout: *idle,
	}, engine, w)

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	// Optional periodic snapshotting so long-running processes don't grow
	// an unbounded WAL.
	if *autoSnapshot > 0 {
		go func() {
			t := time.NewTicker(*autoSnapshot)
			defer t.Stop()
			for {
				select {
				case <-ctx.Done():
					return
				case <-t.C:
					if err := w.Snapshot(engine); err != nil {
						log.Printf("memdb: auto-snapshot: %v", err)
					}
				}
			}
		}()
	}

	errCh := make(chan error, 1)
	go func() { errCh <- srv.Serve(ctx) }()

	select {
	case <-ctx.Done():
		log.Printf("memdb: shutting down")
	case err := <-errCh:
		if err != nil {
			log.Printf("memdb: serve: %v", err)
		}
	}

	// Graceful shutdown: drain the WAL buffer + fsync before exit.
	if err := w.Close(); err != nil {
		log.Printf("memdb: close wal: %v", err)
	}
}
