// Package transport hosts the gRPC service implementations and the helpers
// for dialing / listening. The agent uses the client side; the central
// server uses the server side.
package transport

import (
	"fmt"
	"net"

	"google.golang.org/grpc"
)

// DefaultAddr is the gRPC listen / dial address used by the skeleton.
const DefaultAddr = "localhost:50051"

// Listen returns a *grpc.Server already bound to addr. The caller is
// responsible for grpc.Server.Serve on the returned listener.
func Listen(addr string) (net.Listener, *grpc.Server, error) {
	l, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, nil, fmt.Errorf("transport: listen %s: %w", addr, err)
	}
	s := grpc.NewServer()
	return l, s, nil
}

// Dial constructs a gRPC client connection. The caller is responsible for
// closing it. Insecure is intentional for the local skeleton; a production
// build would use TLS or at least an authenticated interceptor.
func Dial(addr string) (*grpc.ClientConn, error) {
	cc, err := grpc.Dial(addr, grpc.WithInsecure())
	if err != nil {
		return nil, fmt.Errorf("transport: dial %s: %w", addr, err)
	}
	return cc, nil
}
