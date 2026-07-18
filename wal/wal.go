// Package wal implements the Write-Ahead Log (Component 2) and the
// snapshot compaction path (Component 4).
//
// Wire format per record (all integers little-endian):
//
//	byte  0        : op (SET=0x01, DEL=0x02)
//	bytes 1..4     : uint32 keyLen
//	bytes 5..8     : uint32 valLen  (0 for DEL)
//	bytes 9..     : key bytes  (keyLen)
//	bytes ...     : value bytes (valLen)
//
// Files under the data directory:
//
//	snapshot.bin    : durable point-in-time snapshot (records of op=SET)
//	wal.log         : active append-only log of every mutation since the
//	                  last successful snapshot
//
// Recovery order: replay snapshot.bin (if present), then wal.log.
package wal

import (
	"bufio"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"

	"github.com/komilovshayxnazar/memdb/storage"
)

// Op is the WAL record type.
type Op byte

const (
	OpSet Op = 0x01
	OpDel Op = 0x02
)

// Cap on a single record to protect the replay path from allocating an
// insane buffer against a corrupt/truncated tail.
const maxRecordBytes = 64 * 1024 * 1024

// SyncMode selects the disk-sync strategy.
type SyncMode int

const (
	// SyncAlways calls fsync after every Append. Highest durability, worst
	// throughput.
	SyncAlways SyncMode = iota
	// SyncInterval fsyncs on a background timer (see WAL.SyncEvery).
	SyncInterval
	// SyncNever leaves durability up to the OS. Highest throughput; a crash
	// can lose recently buffered records.
	SyncNever
)

// Config bundles the WAL knobs.
type Config struct {
	Dir       string
	SyncMode  SyncMode
	SyncEvery time.Duration // used when SyncMode == SyncInterval
}

// WAL is the durable log. All exported methods are safe for concurrent use.
type WAL struct {
	dir       string
	mode      SyncMode
	syncEvery time.Duration

	mu sync.Mutex // guards f/bw and the rotation swap
	f  *os.File
	bw *bufio.Writer

	// snapMu serializes snapshot operations so two calls can't race.
	snapMu sync.Mutex

	stopBg chan struct{}
	bgWg   sync.WaitGroup

	closed atomic.Bool
}

// Open initializes the WAL directory, replays snapshot + WAL into engine,
// and returns the ready-to-write WAL. If the directory does not exist yet
// it is created.
func Open(cfg Config, engine *storage.Engine) (*WAL, error) {
	if cfg.Dir == "" {
		return nil, errors.New("wal: Dir is required")
	}
	if err := os.MkdirAll(cfg.Dir, 0o755); err != nil {
		return nil, fmt.Errorf("wal: mkdir: %w", err)
	}
	if cfg.SyncEvery <= 0 {
		cfg.SyncEvery = 200 * time.Millisecond
	}

	w := &WAL{
		dir:       cfg.Dir,
		mode:      cfg.SyncMode,
		syncEvery: cfg.SyncEvery,
	}

	if err := replay(cfg.Dir, engine); err != nil {
		return nil, err
	}

	f, err := os.OpenFile(w.walPath(), os.O_RDWR|os.O_CREATE|os.O_APPEND, 0o644)
	if err != nil {
		return nil, fmt.Errorf("wal: open log: %w", err)
	}
	w.f = f
	w.bw = bufio.NewWriterSize(f, 64*1024)

	if w.mode == SyncInterval {
		w.stopBg = make(chan struct{})
		w.bgWg.Add(1)
		go w.backgroundSync()
	}
	return w, nil
}

func (w *WAL) walPath() string      { return filepath.Join(w.dir, "wal.log") }
func (w *WAL) snapshotPath() string { return filepath.Join(w.dir, "snapshot.bin") }
func (w *WAL) snapshotTmp() string  { return filepath.Join(w.dir, "snapshot.new") }
func (w *WAL) walOldPath() string   { return filepath.Join(w.dir, "wal.old") }

// AppendSet writes a SET record.
func (w *WAL) AppendSet(key string, value []byte) error {
	return w.append(OpSet, key, value)
}

// AppendDel writes a DEL record.
func (w *WAL) AppendDel(key string) error {
	return w.append(OpDel, key, nil)
}

func (w *WAL) append(op Op, key string, value []byte) error {
	if w.closed.Load() {
		return errors.New("wal: closed")
	}
	if len(key) == 0 {
		return errors.New("wal: empty key")
	}
	if len(key) > maxRecordBytes || len(value) > maxRecordBytes {
		return errors.New("wal: record too large")
	}

	var hdr [9]byte
	hdr[0] = byte(op)
	binary.LittleEndian.PutUint32(hdr[1:5], uint32(len(key)))
	binary.LittleEndian.PutUint32(hdr[5:9], uint32(len(value)))

	w.mu.Lock()
	defer w.mu.Unlock()

	if _, err := w.bw.Write(hdr[:]); err != nil {
		return fmt.Errorf("wal: write header: %w", err)
	}
	if _, err := w.bw.WriteString(key); err != nil {
		return fmt.Errorf("wal: write key: %w", err)
	}
	if len(value) > 0 {
		if _, err := w.bw.Write(value); err != nil {
			return fmt.Errorf("wal: write value: %w", err)
		}
	}

	if w.mode == SyncAlways {
		if err := w.bw.Flush(); err != nil {
			return fmt.Errorf("wal: flush: %w", err)
		}
		if err := w.f.Sync(); err != nil {
			return fmt.Errorf("wal: fsync: %w", err)
		}
	}
	return nil
}

// Flush drains the buffered writer to the file. It does not fsync.
func (w *WAL) Flush() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.bw == nil {
		return nil
	}
	return w.bw.Flush()
}

// Sync flushes and fsyncs the WAL to disk.
func (w *WAL) Sync() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.bw == nil {
		return nil
	}
	if err := w.bw.Flush(); err != nil {
		return err
	}
	return w.f.Sync()
}

// Close flushes, fsyncs, closes the file, and stops the background sync
// goroutine if any.
func (w *WAL) Close() error {
	if !w.closed.CompareAndSwap(false, true) {
		return nil
	}
	if w.stopBg != nil {
		close(w.stopBg)
		w.bgWg.Wait()
	}
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.bw != nil {
		_ = w.bw.Flush()
	}
	if w.f != nil {
		_ = w.f.Sync()
		return w.f.Close()
	}
	return nil
}

func (w *WAL) backgroundSync() {
	defer w.bgWg.Done()
	t := time.NewTicker(w.syncEvery)
	defer t.Stop()
	for {
		select {
		case <-w.stopBg:
			return
		case <-t.C:
			_ = w.Sync()
		}
	}
}

// -----------------------------------------------------------------------
// Snapshot compaction (Component 4)
// -----------------------------------------------------------------------

// Snapshot serializes engine's current state into snapshot.bin and
// truncates the WAL. Reads on engine are not blocked; writers are only
// briefly serialized while the log file is rotated. The heavy disk I/O
// happens outside all shard locks.
func (w *WAL) Snapshot(engine *storage.Engine) error {
	w.snapMu.Lock()
	defer w.snapMu.Unlock()

	if w.closed.Load() {
		return errors.New("wal: closed")
	}

	// Step 1: rotate the active WAL. Fresh writes from now on land in a
	// brand-new empty wal.log; the old one is preserved as wal.old until
	// we're certain the snapshot is durable.
	if err := w.rotate(); err != nil {
		return err
	}

	// Step 2: take a point-in-time snapshot of the engine. This iterates
	// each shard under RLock — writers to other shards continue.
	entries := engine.Snapshot()

	// Step 3: write snapshot.new atomically.
	tmp, err := os.OpenFile(w.snapshotTmp(), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0o644)
	if err != nil {
		return fmt.Errorf("wal: snapshot open: %w", err)
	}
	bw := bufio.NewWriterSize(tmp, 256*1024)
	for _, e := range entries {
		if err := writeRecord(bw, OpSet, e.Key, e.Value); err != nil {
			_ = tmp.Close()
			return err
		}
	}
	if err := bw.Flush(); err != nil {
		_ = tmp.Close()
		return err
	}
	if err := tmp.Sync(); err != nil {
		_ = tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}

	// Step 4: atomic rename → snapshot.bin. This is the commit point.
	if err := os.Rename(w.snapshotTmp(), w.snapshotPath()); err != nil {
		return fmt.Errorf("wal: snapshot rename: %w", err)
	}

	// Step 5: the old WAL is now redundant.
	if err := os.Remove(w.walOldPath()); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("wal: remove old wal: %w", err)
	}
	return nil
}

// rotate flushes the current wal.log, renames it to wal.old, and opens a
// fresh empty wal.log for subsequent appends. Only writers are briefly
// blocked (via w.mu).
func (w *WAL) rotate() error {
	w.mu.Lock()
	defer w.mu.Unlock()

	if err := w.bw.Flush(); err != nil {
		return fmt.Errorf("wal: pre-rotate flush: %w", err)
	}
	if err := w.f.Sync(); err != nil {
		return fmt.Errorf("wal: pre-rotate fsync: %w", err)
	}
	if err := w.f.Close(); err != nil {
		return fmt.Errorf("wal: pre-rotate close: %w", err)
	}

	// If a previous snapshot crashed after rotate but before finish, an
	// existing wal.old means we'd be about to lose data. Refuse.
	if _, err := os.Stat(w.walOldPath()); err == nil {
		return errors.New("wal: refuse to rotate — stale wal.old present, run recovery")
	}
	if err := os.Rename(w.walPath(), w.walOldPath()); err != nil {
		return fmt.Errorf("wal: rotate: %w", err)
	}

	f, err := os.OpenFile(w.walPath(), os.O_RDWR|os.O_CREATE|os.O_APPEND, 0o644)
	if err != nil {
		return fmt.Errorf("wal: reopen: %w", err)
	}
	w.f = f
	w.bw = bufio.NewWriterSize(f, 64*1024)
	return nil
}

// -----------------------------------------------------------------------
// Recovery
// -----------------------------------------------------------------------

// replay reads snapshot.bin (if present) then wal.log and applies both to
// engine. wal.old is treated as a leftover from a crashed snapshot: if
// snapshot.bin is missing it is replayed first, otherwise it is deleted.
func replay(dir string, engine *storage.Engine) error {
	snapPath := filepath.Join(dir, "snapshot.bin")
	tmpPath := filepath.Join(dir, "snapshot.new")
	walPath := filepath.Join(dir, "wal.log")
	walOld := filepath.Join(dir, "wal.old")

	// Case: previous snapshot wrote snapshot.new but crashed before rename.
	// snapshot.new is only fully written+synced before rename, so keep it
	// only if snapshot.bin is absent.
	if _, err := os.Stat(tmpPath); err == nil {
		if _, err := os.Stat(snapPath); err != nil && os.IsNotExist(err) {
			// Adopt the new snapshot.
			if err := os.Rename(tmpPath, snapPath); err != nil {
				return fmt.Errorf("wal: adopt snapshot.new: %w", err)
			}
		} else {
			// snapshot.bin already exists → snapshot.new is stale.
			_ = os.Remove(tmpPath)
		}
	}

	// If wal.old is present, replay it first: it holds the writes captured
	// in the last snapshot attempt that never got compacted.
	if _, err := os.Stat(walOld); err == nil {
		if err := replayFile(walOld, engine); err != nil {
			return err
		}
	}

	// Snapshot next.
	if _, err := os.Stat(snapPath); err == nil {
		if err := replayFile(snapPath, engine); err != nil {
			return err
		}
	}

	// Active WAL.
	if _, err := os.Stat(walPath); err == nil {
		if err := replayFile(walPath, engine); err != nil {
			return err
		}
	}

	// Both walOld and snapshot successfully processed — clean up.
	_ = os.Remove(walOld)
	return nil
}

func replayFile(path string, engine *storage.Engine) error {
	f, err := os.Open(path)
	if err != nil {
		return fmt.Errorf("wal: open %s: %w", path, err)
	}
	defer f.Close()
	br := bufio.NewReaderSize(f, 64*1024)

	for {
		var hdr [9]byte
		if _, err := io.ReadFull(br, hdr[:]); err != nil {
			if err == io.EOF {
				return nil
			}
			if err == io.ErrUnexpectedEOF {
				// truncated tail record — treat as clean end.
				return nil
			}
			return fmt.Errorf("wal: read hdr: %w", err)
		}
		op := Op(hdr[0])
		if op != OpSet && op != OpDel {
			// unknown opcode → assume torn write, stop.
			return nil
		}
		keyLen := binary.LittleEndian.Uint32(hdr[1:5])
		valLen := binary.LittleEndian.Uint32(hdr[5:9])
		if keyLen == 0 || keyLen > maxRecordBytes || valLen > maxRecordBytes {
			return nil
		}
		key := make([]byte, keyLen)
		if _, err := io.ReadFull(br, key); err != nil {
			return nil
		}
		var val []byte
		if valLen > 0 {
			val = make([]byte, valLen)
			if _, err := io.ReadFull(br, val); err != nil {
				return nil
			}
		}
		switch op {
		case OpSet:
			engine.Set(string(key), val)
		case OpDel:
			engine.Delete(string(key))
		}
	}
}

// writeRecord serializes one record to bw using the same wire format as
// Append. Used by the snapshotter.
func writeRecord(bw *bufio.Writer, op Op, key string, value []byte) error {
	var hdr [9]byte
	hdr[0] = byte(op)
	binary.LittleEndian.PutUint32(hdr[1:5], uint32(len(key)))
	binary.LittleEndian.PutUint32(hdr[5:9], uint32(len(value)))
	if _, err := bw.Write(hdr[:]); err != nil {
		return err
	}
	if _, err := bw.WriteString(key); err != nil {
		return err
	}
	if len(value) > 0 {
		if _, err := bw.Write(value); err != nil {
			return err
		}
	}
	return nil
}
