// Package query implements the offline query engine. It reads the chunk
// store directly from disk (no gRPC) and uses the in-memory inverted index
// for fast lookups. The query DSL is intentionally tiny:
//
//	service=fastapi AND level=ERROR AND trace_id=abc123
//
// Every constraint is ANDed. The engine intersects the chunk sets returned
// by the index, then scans the surviving chunks line by line. A regex on
// the message field is applied as a final post-filter.
package query

import (
	"fmt"
	"strings"
	"unicode"
)

// Constraint is a single equality predicate.
type Constraint struct {
	Field string
	Value string
}

// Query is the parsed form of a query expression.
type Query struct {
	Constraints []Constraint
}

// String returns the canonical form (re-emitted for logging / debugging).
func (q Query) String() string {
	parts := make([]string, 0, len(q.Constraints))
	for _, c := range q.Constraints {
		parts = append(parts, fmt.Sprintf("%s=%s", c.Field, c.Value))
	}
	return strings.Join(parts, " AND ")
}

// tokenKind is a small enum for the lexer.
type tokenKind int

const (
	tkIdent tokenKind = iota
	tkEq
	tkAnd
	tkEOF
)

type token struct {
	kind  tokenKind
	value string
}

// Parse takes a query expression like `service=api AND level=ERROR` and
// returns a Query. Whitespace is ignored. The parser is recursive-descent
// over a strict two-level grammar: Term (AND Term)*.
func Parse(src string) (Query, error) {
	toks, err := tokenize(src)
	if err != nil {
		return Query{}, err
	}
	p := &parser{toks: toks}
	q, err := p.parseQuery()
	if err != nil {
		return Query{}, err
	}
	if p.peek().kind != tkEOF {
		return Query{}, fmt.Errorf("query: unexpected %q", p.peek().value)
	}
	if len(q.Constraints) == 0 {
		return Query{}, fmt.Errorf("query: empty expression")
	}
	return q, nil
}

type parser struct {
	toks []token
	pos  int
}

func (p *parser) peek() token { return p.toks[p.pos] }
func (p *parser) next() token { t := p.toks[p.pos]; p.pos++; return t }

func (p *parser) parseQuery() (Query, error) {
	c, err := p.parseConstraint()
	if err != nil {
		return Query{}, err
	}
	q := Query{Constraints: []Constraint{c}}
	for p.peek().kind == tkAnd {
		p.next()
		c, err = p.parseConstraint()
		if err != nil {
			return Query{}, err
		}
		q.Constraints = append(q.Constraints, c)
	}
	return q, nil
}

func (p *parser) parseConstraint() (Constraint, error) {
	field := p.next()
	if field.kind != tkIdent {
		return Constraint{}, fmt.Errorf("query: expected field name, got %q", field.value)
	}
	eq := p.next()
	if eq.kind != tkEq {
		return Constraint{}, fmt.Errorf("query: expected '=' after %q", field.value)
	}
	val := p.next()
	if val.kind != tkIdent {
		return Constraint{}, fmt.Errorf("query: expected value after %q=", field.value)
	}
	return Constraint{Field: strings.ToLower(field.value), Value: val.value}, nil
}

func tokenize(src string) ([]token, error) {
	var toks []token
	i := 0
	for i < len(src) {
		r := rune(src[i])
		if unicode.IsSpace(r) {
			i++
			continue
		}
		switch {
		case r == '=':
			toks = append(toks, token{kind: tkEq, value: "="})
			i++
		case isIdentStart(r):
			j := i
			for j < len(src) && isIdentCont(rune(src[j])) {
				j++
			}
			word := src[i:j]
			if strings.EqualFold(word, "AND") {
				toks = append(toks, token{kind: tkAnd, value: word})
			} else {
				toks = append(toks, token{kind: tkIdent, value: word})
			}
			i = j
		default:
			return nil, fmt.Errorf("query: unexpected character %q at offset %d", r, i)
		}
	}
	toks = append(toks, token{kind: tkEOF})
	return toks, nil
}

func isIdentStart(r rune) bool {
	return unicode.IsLetter(r) || r == '_'
}
func isIdentCont(r rune) bool {
	return unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' || r == '.'
}
