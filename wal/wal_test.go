package wal

import (
	"bytes"
	"path/filepath"
	"strconv"
	"testing"

	"github.com/komilovshayxnazar/memdb/storage"
)

func TestReplayAfterRestart(t *testing.T) {
	dir := t.TempDir()
	cfg := Config{Dir: dir, SyncMode: SyncAlways}

	// First run: write some data.
	{
		eng := storage.New()
		w, err := Open(cfg, eng)
		if err != nil {
			t.Fatal(err)
		}
		if err := w.AppendSet("a", []byte("1")); err != nil {
			t.Fatal(err)
		}
		eng.Set("a", []byte("1"))
		if err := w.AppendSet("b", []byte("two")); err != nil {
			t.Fatal(err)
		}
		eng.Set("b", []byte("two"))
		if err := w.AppendDel("a"); err != nil {
			t.Fatal(err)
		}
		eng.Delete("a")
		if err := w.Close(); err != nil {
			t.Fatal(err)
		}
	}
	// Second run: replay and verify state.
	eng := storage.New()
	w, err := Open(cfg, eng)
	if err != nil {
		t.Fatal(err)
	}
	defer w.Close()

	if v, ok := eng.Get("b"); !ok || !bytes.Equal(v, []byte("two")) {
		t.Fatalf("replay: get b -> %q ok=%v", v, ok)
	}
	if _, ok := eng.Get("a"); ok {
		t.Fatal("replay: a should have been deleted")
	}
}

func TestSnapshotShrinksWAL(t *testing.T) {
	dir := t.TempDir()
	cfg := Config{Dir: dir, SyncMode: SyncAlways}
	eng := storage.New()
	w, err := Open(cfg, eng)
	if err != nil {
		t.Fatal(err)
	}
	// Write a bunch of records so wal.log has real bytes on disk.
	for i := 0; i < 100; i++ {
		k := "k" + strconv.Itoa(i)
		v := []byte("value-" + strconv.Itoa(i))
		if err := w.AppendSet(k, v); err != nil {
			t.Fatal(err)
		}
		eng.Set(k, v)
	}
	if err := w.Snapshot(eng); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	// wal.log must exist and be empty; snapshot.bin must exist and be
	// non-empty; wal.old must be gone.
	fi, err := statSize(filepath.Join(dir, "wal.log"))
	if err != nil || fi != 0 {
		t.Fatalf("wal.log size=%d err=%v (want 0)", fi, err)
	}
	if sz, err := statSize(filepath.Join(dir, "snapshot.bin")); err != nil || sz == 0 {
		t.Fatalf("snapshot.bin size=%d err=%v (want >0)", sz, err)
	}
	if _, err := statSize(filepath.Join(dir, "wal.old")); err == nil {
		t.Fatal("wal.old should have been removed")
	}

	// Restart: state must be intact.
	eng2 := storage.New()
	w2, err := Open(cfg, eng2)
	if err != nil {
		t.Fatal(err)
	}
	defer w2.Close()
	if eng2.Len() != 100 {
		t.Fatalf("restart len=%d want 100", eng2.Len())
	}
	if v, ok := eng2.Get("k42"); !ok || string(v) != "value-42" {
		t.Fatalf("restart get k42 -> %q ok=%v", v, ok)
	}
}

func statSize(p string) (int64, error) {
	fi, err := osStat(p)
	if err != nil {
		return 0, err
	}
	return fi.Size(), nil
}
