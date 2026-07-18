// Package server exposes the sharded engine + WAL over a lightweight
// text TCP protocol (see package proto). Each connection runs in its own
// goroutine and is torn down on client EOF, protocol error, or Shutdown.
package server

import (
	"bufio"
	"context"
	"errors"
	"io"
	"log"
	"net"
	"sync"
	"sync/atomic"
	"time"

	"github.com/komilovshayxnazar/memdb/proto"
	"github.com/komilovshayxnazar/memdb/storage"
	"github.com/komilovshayxnazar/memdb/wal"
)

// Config bundles the TCP server tunables.
type Config struct {
	Addr        string
	IdleTimeout time.Duration
	Logger      *log.Logger
}

// Server owns the listener + connection lifecycle.
type Server struct {
	cfg    Config
	engine *storage.Engine
	wal    *wal.WAL

	listener net.Listener
	wg       sync.WaitGroup

	shuttingDown atomic.Bool
}

// New returns a Server bound to engine and w. Call Serve to enter the
// accept loop.
func New(cfg Config, engine *storage.Engine, w *wal.WAL) *Server {
	if cfg.IdleTimeout <= 0 {
		cfg.IdleTimeout = 5 * time.Minute
	}
	if cfg.Logger == nil {
		cfg.Logger = log.Default()
	}
	return &Server{cfg: cfg, engine: engine, wal: w}
}

// Serve listens on cfg.Addr and blocks accepting connections. It returns
// when ctx is cancelled or the listener fails.
func (s *Server) Serve(ctx context.Context) error {
	l, err := net.Listen("tcp", s.cfg.Addr)
	if err != nil {
		return err
	}
	s.listener = l
	s.cfg.Logger.Printf("memdb: listening on %s", s.cfg.Addr)

	// Close listener on shutdown so Accept returns.
	go func() {
		<-ctx.Done()
		s.shuttingDown.Store(true)
		_ = l.Close()
	}()

	for {
		conn, err := l.Accept()
		if err != nil {
			if s.shuttingDown.Load() {
				break
			}
			var ne net.Error
			if errors.As(err, &ne) && ne.Timeout() {
				continue
			}
			return err
		}
		s.wg.Add(1)
		go s.handle(conn)
	}
	s.wg.Wait()
	return nil
}

// handle is the per-connection loop.
func (s *Server) handle(conn net.Conn) {
	defer s.wg.Done()
	defer conn.Close()

	br := bufio.NewReaderSize(conn, 32*1024)
	bw := bufio.NewWriterSize(conn, 32*1024)

	for {
		if s.cfg.IdleTimeout > 0 {
			_ = conn.SetReadDeadline(time.Now().Add(s.cfg.IdleTimeout))
		}
		cmd, err := proto.ReadCmd(br)
		if err != nil {
			if err == io.EOF {
				return
			}
			// On protocol errors we send an error frame then close.
			_ = proto.WriteError(bw, err.Error())
			_ = bw.Flush()
			return
		}
		if err := s.dispatch(cmd, bw); err != nil {
			s.cfg.Logger.Printf("memdb: dispatch: %v", err)
			return
		}
		if err := bw.Flush(); err != nil {
			return
		}
	}
}

func (s *Server) dispatch(cmd proto.Cmd, bw *bufio.Writer) error {
	switch cmd.Kind {
	case proto.CmdPing:
		return proto.WritePong(bw)

	case proto.CmdStats:
		return proto.WriteInt(bw, int64(s.engine.Len()))

	case proto.CmdGet:
		v, ok := s.engine.Get(cmd.Key)
		return proto.WriteBulk(bw, v, ok)

	case proto.CmdSet:
		// WAL first, then in-memory (Component 2 requirement).
		if err := s.wal.AppendSet(cmd.Key, cmd.Value); err != nil {
			return proto.WriteError(bw, err.Error())
		}
		s.engine.Set(cmd.Key, cmd.Value)
		return proto.WriteOK(bw)

	case proto.CmdDel:
		if err := s.wal.AppendDel(cmd.Key); err != nil {
			return proto.WriteError(bw, err.Error())
		}
		existed := s.engine.Delete(cmd.Key)
		if existed {
			return proto.WriteInt(bw, 1)
		}
		return proto.WriteInt(bw, 0)

	case proto.CmdSnapshot:
		// Snapshotting runs in a background goroutine so the caller doesn't
		// pay the disk-write latency inline. Reads continue unblocked;
		// writers are briefly serialized during log rotation only.
		go func() {
			if err := s.wal.Snapshot(s.engine); err != nil {
				s.cfg.Logger.Printf("memdb: snapshot: %v", err)
			}
		}()
		return proto.WriteOK(bw)
	}
	return proto.WriteError(bw, "unknown command")
}
