package storage

import (
	"bytes"
	"strconv"
	"sync"
	"testing"
)

func TestSetGetDelete(t *testing.T) {
	e := New()
	e.Set("k", []byte("v1"))
	got, ok := e.Get("k")
	if !ok || !bytes.Equal(got, []byte("v1")) {
		t.Fatalf("get after set: got=%q ok=%v", got, ok)
	}
	e.Set("k", []byte("v2"))
	got, _ = e.Get("k")
	if !bytes.Equal(got, []byte("v2")) {
		t.Fatalf("overwrite: got=%q", got)
	}
	if !e.Delete("k") {
		t.Fatal("delete existing key should return true")
	}
	if e.Delete("k") {
		t.Fatal("delete missing key should return false")
	}
	if _, ok := e.Get("k"); ok {
		t.Fatal("get after delete should miss")
	}
}

func TestValueCopyIsolation(t *testing.T) {
	e := New()
	buf := []byte("hello")
	e.Set("k", buf)
	buf[0] = 'X' // mutate caller's buffer after write
	got, _ := e.Get("k")
	if !bytes.Equal(got, []byte("hello")) {
		t.Fatalf("engine stored aliased buffer: got=%q", got)
	}
	got[0] = 'Y' // mutate the returned slice
	got2, _ := e.Get("k")
	if !bytes.Equal(got2, []byte("hello")) {
		t.Fatalf("engine returned aliased buffer: got2=%q", got2)
	}
}

func TestSnapshotContainsAll(t *testing.T) {
	e := New()
	for i := 0; i < 200; i++ {
		e.Set("k"+strconv.Itoa(i), []byte(strconv.Itoa(i)))
	}
	snap := e.Snapshot()
	if len(snap) != 200 {
		t.Fatalf("snap len=%d want 200", len(snap))
	}
	seen := make(map[string]string, 200)
	for _, en := range snap {
		seen[en.Key] = string(en.Value)
	}
	for i := 0; i < 200; i++ {
		if seen["k"+strconv.Itoa(i)] != strconv.Itoa(i) {
			t.Fatalf("missing key %d", i)
		}
	}
}

func TestConcurrentSafety(t *testing.T) {
	e := New()
	var wg sync.WaitGroup
	for w := 0; w < 8; w++ {
		wg.Add(1)
		go func(base int) {
			defer wg.Done()
			for i := 0; i < 1000; i++ {
				k := "k" + strconv.Itoa((base*1000+i)%200)
				e.Set(k, []byte(strconv.Itoa(i)))
				e.Get(k)
				if i%17 == 0 {
					e.Delete(k)
				}
			}
		}(w)
	}
	wg.Wait()
	// Test just needs to complete without a data race under -race.
}
