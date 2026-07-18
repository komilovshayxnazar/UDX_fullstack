package proto

import (
	"bufio"
	"bytes"
	"strings"
	"testing"
)

func TestReadCmd(t *testing.T) {
	cases := []struct {
		in   string
		want CmdKind
		key  string
		val  string
	}{
		{"PING\r\n", CmdPing, "", ""},
		{"STATS\r\n", CmdStats, "", ""},
		{"SNAPSHOT\r\n", CmdSnapshot, "", ""},
		{"GET foo\r\n", CmdGet, "foo", ""},
		{"DEL foo\r\n", CmdDel, "foo", ""},
		{"SET foo 5\r\nhello\r\n", CmdSet, "foo", "hello"},
		{"set foo 0\r\n\r\n", CmdSet, "foo", ""}, // empty value + case-insensitive verb
	}
	for _, c := range cases {
		r := bufio.NewReader(strings.NewReader(c.in))
		got, err := ReadCmd(r)
		if err != nil {
			t.Fatalf("%q: %v", c.in, err)
		}
		if got.Kind != c.want {
			t.Fatalf("%q: kind=%v want %v", c.in, got.Kind, c.want)
		}
		if got.Key != c.key {
			t.Fatalf("%q: key=%q want %q", c.in, got.Key, c.key)
		}
		if string(got.Value) != c.val {
			t.Fatalf("%q: val=%q want %q", c.in, got.Value, c.val)
		}
	}
}

func TestWriters(t *testing.T) {
	var buf bytes.Buffer
	w := bufio.NewWriter(&buf)
	WriteOK(w)
	WritePong(w)
	WriteBulk(w, nil, false)
	WriteBulk(w, []byte("hi"), true)
	WriteInt(w, 42)
	WriteError(w, "bad")
	w.Flush()
	want := "+OK\r\n+PONG\r\n$-1\r\n$2\r\nhi\r\n:42\r\n-ERR bad\r\n"
	if buf.String() != want {
		t.Fatalf("got %q\nwant %q", buf.String(), want)
	}
}
