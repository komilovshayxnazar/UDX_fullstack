BIN := bin
GO  := go

.PHONY: all build test tidy vet clean run-gateway run-echo

all: build

build:
	mkdir -p $(BIN)
	$(GO) build -o $(BIN)/gateway ./cmd/gateway
	$(GO) build -o $(BIN)/echo    ./cmd/echo

test:
	$(GO) test ./...

vet:
	$(GO) vet ./...

tidy:
	$(GO) mod tidy

clean:
	rm -rf $(BIN)

run-gateway: build
	$(BIN)/gateway

run-echo: build
	$(BIN)/echo
