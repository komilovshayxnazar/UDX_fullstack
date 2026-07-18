// Command query runs a structured query against the local chunk store.

package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"regexp"
	"syscall"
	"time"

	"github.com/shayxnazar/logagg/internal/chunk"
	"github.com/shayxnazar/logagg/internal/index"
	"github.com/shayxnazar/logagg/internal/query"
)

func main() {
	expr := flag.String("q", "", "query expression, e.g. `service=api AND level=ERROR` (positional arg also accepted)")
	dataDir := flag.String("data", "./data", "data directory")
	regex := flag.String("regex", "", "optional regex applied to the message field")
	since := flag.String("since", "", "RFC3339 lower bound on timestamp")
	until := flag.String("until", "", "RFC3339 upper bound on timestamp")
	flag.Parse()

	if *expr == "" && flag.NArg() > 0 {
		*expr = flag.Arg(0)
	}
	if *expr == "" {
		fmt.Fprintln(os.Stderr, "query: -q (or positional) is required")
		os.Exit(2)
	}

	q, err := query.Parse(*expr)
	if err != nil {
		log.Fatalf("query: parse: %v", err)
	}

	store, err := chunk.NewStore(*dataDir)
	if err != nil {
		log.Fatalf("query: open store: %v", err)
	}

	idx := index.New()
	if err := idx.Rebuild(store); err != nil {
		log.Fatalf("query: rebuild index: %v", err)
	}

	r := query.Range{}
	if *since != "" {
		t, err := time.Parse(time.RFC3339, *since)
		if err != nil {
			log.Fatalf("query: parse --since: %v", err)
		}
		r.Since = t
	}
	if *until != "" {
		t, err := time.Parse(time.RFC3339, *until)
		if err != nil {
			log.Fatalf("query: parse --until: %v", err)
		}
		r.Until = t
	}

	var msgRegex *regexp.Regexp
	if *regex != "" {
		msgRegex, err = regexp.Compile(*regex)
		if err != nil {
			log.Fatalf("query: compile --regex: %v", err)
		}
	}

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	eng := &query.Engine{Store: store, Index: idx}
	matches, err := eng.Run(ctx, q, r, msgRegex)
	if err != nil {
		log.Fatalf("query: run: %v", err)
	}
	if err := query.Print(os.Stdout, matches); err != nil {
		log.Fatalf("query: print: %v", err)
	}
	query.Summarize(os.Stderr, len(matches))
}
