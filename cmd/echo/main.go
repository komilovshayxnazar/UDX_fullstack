// Command echo is a tiny demo upstream used to exercise the gateway. It
// echoes the request path and can be poked into failing so the circuit
// breaker becomes observable.
//
//   GET /            -> 200 "hello from echo"
//   GET /fail        -> 500 "boom"
//   GET /toggle-fail -> flips a global switch: while set, all requests 500
//   GET /slow?ms=NN  -> sleeps NN ms before responding
//
package main

import (
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"sync/atomic"
	"time"
)

func main() {
	addr := flag.String("addr", ":9000", "listen address")
	flag.Parse()

	var forceFail atomic.Bool
	mux := http.NewServeMux()

	mux.HandleFunc("/toggle-fail", func(w http.ResponseWriter, _ *http.Request) {
		next := !forceFail.Load()
		forceFail.Store(next)
		fmt.Fprintf(w, "forceFail=%v\n", next)
	})

	mux.HandleFunc("/fail", func(w http.ResponseWriter, _ *http.Request) {
		http.Error(w, "boom", http.StatusInternalServerError)
	})

	mux.HandleFunc("/slow", func(w http.ResponseWriter, r *http.Request) {
		ms, _ := strconv.Atoi(r.URL.Query().Get("ms"))
		time.Sleep(time.Duration(ms) * time.Millisecond)
		fmt.Fprintf(w, "slept %dms\n", ms)
	})

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if forceFail.Load() {
			http.Error(w, "forced failure", http.StatusInternalServerError)
			return
		}
		fmt.Fprintf(w, "hello from echo: %s\n", r.URL.Path)
	})

	srv := &http.Server{Addr: *addr, Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	log.Printf("echo: listen=%s", *addr)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
