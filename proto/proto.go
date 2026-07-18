// Package proto defines the on-the-wire framing used by the TCP server.
//
// Command grammar (text, line-oriented, values are length-prefixed and
// binary-safe):
//
//	GET  <key>\r\n
//	DEL  <key>\r\n
//	PING\r\n
//	STATS\r\n
//	SNAPSHOT\r\n
//	SET  <key> <valueLen>\r\n<value bytes>\r\n
//
// Reply framing (Redis RESP-flavored):
//
//	+OK\r\n              simple string
//	+PONG\r\n
//	$<n>\r\n<n bytes>\r\n   bulk value
//	$-1\r\n                 null (miss)
//	:<int>\r\n              integer
//	-ERR <message>\r\n      error
//
// Keys are ASCII with no whitespace / CRLF.
package proto

import (
	"bufio"
	"bytes"
	"errors"
	"io"
	"strconv"
)

// CmdKind is a lightweight tag identifying the parsed command.
type CmdKind int

const (
	CmdUnknown CmdKind = iota
	CmdGet
	CmdSet
	CmdDel
	CmdPing
	CmdStats
	CmdSnapshot
)

// Cmd is the parsed form of one client request. Key is a fresh string;
// Value is either nil or an owned []byte (already read off the wire).
type Cmd struct {
	Kind  CmdKind
	Key   string
	Value []byte
}

// ErrClosed is returned when the peer half-closed the connection cleanly.
var ErrClosed = io.EOF

// MaxLineBytes caps the length of the command line to protect us from
// pathological clients that never send \n.
const MaxLineBytes = 64 * 1024

// MaxValueBytes caps a single SET value.
const MaxValueBytes = 64 * 1024 * 1024

// ReadCmd parses one command from r. It uses bufio.Reader.ReadSlice on the
// command line to avoid allocating a per-command byte slice; the returned
// Cmd only allocates for Key and Value, which have to escape the parser.
func ReadCmd(r *bufio.Reader) (Cmd, error) {
	line, err := readLine(r)
	if err != nil {
		return Cmd{}, err
	}
	if len(line) == 0 {
		return Cmd{Kind: CmdUnknown}, errors.New("proto: empty command")
	}

	verb, rest := splitFirst(line)
	switch {
	case bytesEqualCI(verb, "PING"):
		return Cmd{Kind: CmdPing}, nil
	case bytesEqualCI(verb, "STATS"):
		return Cmd{Kind: CmdStats}, nil
	case bytesEqualCI(verb, "SNAPSHOT"):
		return Cmd{Kind: CmdSnapshot}, nil
	case bytesEqualCI(verb, "GET"):
		if len(rest) == 0 {
			return Cmd{}, errors.New("proto: GET requires key")
		}
		return Cmd{Kind: CmdGet, Key: string(rest)}, nil
	case bytesEqualCI(verb, "DEL"):
		if len(rest) == 0 {
			return Cmd{}, errors.New("proto: DEL requires key")
		}
		return Cmd{Kind: CmdDel, Key: string(rest)}, nil
	case bytesEqualCI(verb, "SET"):
		key, lenBytes := splitFirst(rest)
		if len(key) == 0 || len(lenBytes) == 0 {
			return Cmd{}, errors.New("proto: SET requires key and length")
		}
		vLen, err := strconv.Atoi(string(lenBytes))
		if err != nil || vLen < 0 {
			return Cmd{}, errors.New("proto: SET length must be non-negative int")
		}
		if vLen > MaxValueBytes {
			return Cmd{}, errors.New("proto: SET value too large")
		}
		val := make([]byte, vLen)
		if vLen > 0 {
			if _, err := io.ReadFull(r, val); err != nil {
				return Cmd{}, err
			}
		}
		// Consume trailing CRLF after the raw value.
		if err := expectCRLF(r); err != nil {
			return Cmd{}, err
		}
		return Cmd{Kind: CmdSet, Key: string(key), Value: val}, nil
	}
	return Cmd{}, errors.New("proto: unknown command")
}

// -----------------------------------------------------------------------
// Reply writers
// -----------------------------------------------------------------------

// WriteOK writes "+OK\r\n".
func WriteOK(w *bufio.Writer) error {
	_, err := w.WriteString("+OK\r\n")
	return err
}

// WritePong writes "+PONG\r\n".
func WritePong(w *bufio.Writer) error {
	_, err := w.WriteString("+PONG\r\n")
	return err
}

// WriteBulk writes a bulk value (or the null variant when value == nil and
// hit == false).
func WriteBulk(w *bufio.Writer, value []byte, hit bool) error {
	if !hit {
		_, err := w.WriteString("$-1\r\n")
		return err
	}
	if err := writeByte(w, '$'); err != nil {
		return err
	}
	if _, err := w.WriteString(strconv.Itoa(len(value))); err != nil {
		return err
	}
	if _, err := w.WriteString("\r\n"); err != nil {
		return err
	}
	if len(value) > 0 {
		if _, err := w.Write(value); err != nil {
			return err
		}
	}
	_, err := w.WriteString("\r\n")
	return err
}

// WriteInt writes ":<n>\r\n".
func WriteInt(w *bufio.Writer, n int64) error {
	if err := writeByte(w, ':'); err != nil {
		return err
	}
	if _, err := w.WriteString(strconv.FormatInt(n, 10)); err != nil {
		return err
	}
	_, err := w.WriteString("\r\n")
	return err
}

// WriteError writes "-ERR <msg>\r\n".
func WriteError(w *bufio.Writer, msg string) error {
	if _, err := w.WriteString("-ERR "); err != nil {
		return err
	}
	if _, err := w.WriteString(msg); err != nil {
		return err
	}
	_, err := w.WriteString("\r\n")
	return err
}

// -----------------------------------------------------------------------
// helpers
// -----------------------------------------------------------------------

// readLine reads a single \r\n-terminated line and returns the line
// without the terminator. The returned slice is copied so the caller can
// hold it across further reads.
func readLine(r *bufio.Reader) ([]byte, error) {
	// ReadSlice avoids the allocation ReadBytes performs; we only copy the
	// slice bytes that survive parsing.
	slice, err := r.ReadSlice('\n')
	if err != nil {
		if errors.Is(err, bufio.ErrBufferFull) {
			return nil, errors.New("proto: command line too long")
		}
		return nil, err
	}
	if len(slice) > MaxLineBytes {
		return nil, errors.New("proto: command line too long")
	}
	// Strip trailing \r\n or just \n.
	end := len(slice)
	if end > 0 && slice[end-1] == '\n' {
		end--
	}
	if end > 0 && slice[end-1] == '\r' {
		end--
	}
	// Copy because the ReadSlice buffer may be recycled on the next call.
	out := make([]byte, end)
	copy(out, slice[:end])
	return out, nil
}

func splitFirst(b []byte) (head, rest []byte) {
	i := bytes.IndexByte(b, ' ')
	if i < 0 {
		return b, nil
	}
	return b[:i], b[i+1:]
}

func bytesEqualCI(b []byte, s string) bool {
	if len(b) != len(s) {
		return false
	}
	for i := 0; i < len(b); i++ {
		bb := b[i]
		if bb >= 'a' && bb <= 'z' {
			bb -= 'a' - 'A'
		}
		ss := s[i]
		if ss >= 'a' && ss <= 'z' {
			ss -= 'a' - 'A'
		}
		if bb != ss {
			return false
		}
	}
	return true
}

func expectCRLF(r *bufio.Reader) error {
	var buf [2]byte
	if _, err := io.ReadFull(r, buf[:]); err != nil {
		return err
	}
	if buf[0] != '\r' || buf[1] != '\n' {
		return errors.New("proto: missing CRLF after SET value")
	}
	return nil
}

func writeByte(w *bufio.Writer, b byte) error { return w.WriteByte(b) }
