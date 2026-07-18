BIN := bin
GO  := go

.PHONY: all build test vet tidy clean run

all: build

build:
	mkdir -p $(BIN)
	$(GO) build -o $(BIN)/memdb ./

test:
	$(GO) test ./...

vet:
	$(GO) vet ./...

tidy:
	$(GO) mod tidy

clean:
	rm -rf $(BIN) data

run: build
	$(BIN)/memdb --addr :5455 --data ./data
