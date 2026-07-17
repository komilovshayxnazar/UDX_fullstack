# Distributed Log Aggregator — Makefile
#
# Targets:
#   make build       compile server, agent, query into ./bin
#   make proto       regenerate gRPC stubs (requires protoc + plugins)
#   make test        run unit tests
#   make tidy        go mod tidy
#   make clean       remove bin/ and data/

BIN     := bin
GO      := go
PROTOC  := protoc

.PHONY: all build proto test tidy clean run-server run-agent run-query

all: build

build:
	mkdir -p $(BIN)
	$(GO) build -o $(BIN)/server ./cmd/server
	$(GO) build -o $(BIN)/agent  ./cmd/agent
	$(GO) build -o $(BIN)/query  ./cmd/query

proto:
	@command -v $(PROTOC) >/dev/null || (echo "protoc not found" && exit 1)
	$(PROTOC) --go_out=. --go_opt=module=github.com/shayxnazar/logagg \
	          --go-grpc_out=. --go-grpc_opt=module=github.com/shayxnazar/logagg \
	          -I proto proto/logagg.proto

test:
	$(GO) test ./...

tidy:
	$(GO) mod tidy

clean:
	rm -rf $(BIN) data

run-server: build
	$(BIN)/server

run-agent: build
	$(BIN)/agent

run-query: build
	$(BIN)/query
