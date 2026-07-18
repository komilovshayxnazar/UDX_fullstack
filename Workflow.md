Here is the operational workflow for the **Dynamic Rate Limiter & Reverse Proxy API Gateway** system, structured to reflect a high-performance production engineering environment.

---

## System Architecture Workflow

```
[ Client Request (HTTP) ]
          │
          ▼
[ API Gateway (Go Listener) ]
          │
          ├──> [ 1. Reverse Proxy Layer ] (Intercepts request, parses headers/IP)
          │
          ├──> [ 2. Dynamic Rate Limiting Engine ]
          │         ├── Lockless Token Bucket Check (In-Memory)
          │         └── Syncs with Redis (for distributed nodes)
          │
          │         * If Limit Exceeded: Returns HTTP 429 Too Many Requests
          │         * If Safe: Proceeds
          │
          ├──> [ 3. Circuit Breaker Layer ] (Tracks downstream health status)
          │         * If Closed: Normal Routing
          │         * If Open: Fast-fails, returns HTTP 503 Service Unavailable
          │
          ▼ 
[ 4. Upstream Routing ] ──(Forwards request)──> [ Downstream FastAPI / Microservices ]
          │                                                         │
          └──<──(Captures metrics & performance stats)<─────────────┘

```

---

## The 4-Stage Operational Lifecycle

### 1. Request Interception & Identification (Reverse Proxy Layer)

* The API Gateway acts as the single entry point for all client traffic, listening on public ports (e.g., `:80` or `:443`) using Go's highly optimized `net/http` package.
* When a request arrives, the proxy intercepts it before it hits any internal microservice.
* It extracts identifying criteria to apply rate limits, such as the client's IP address (`X-Forwarded-For`), an API Key/JWT token from the authorization header, or the specific URL path target.

### 2. Lockless Rate Evaluation (Rate Limiting Engine)

* The gateway runs the **Token Bucket** or **Leaky Bucket** algorithm entirely in memory using standard Go structures to evaluate whether the client has exceeded their allowed quota.
* **Performance Optimization:** Instead of global `sync.Mutex` locks that create a massive bottleneck when thousands of concurrent requests arrive, the system can use fine-grained, per-IP sharded mutexes or low-level `sync/atomic` counters to keep the check overhead under 1 millisecond.
* **Evaluation Verdict:**
* **Quota Violated:** If the client's bucket is empty, the gateway halts the execution flow immediately, dropping the request and returning an `HTTP 429 Too Many Requests` status along with standard `Retry-After` headers.
* **Quota Allowed:** If tokens are available, the gateway decrements the counter and seamlessly forwards the request to the next security boundary.



### 3. Resiliency Check (Circuit Breaker Layer)

* Before passing the request deeper into the network, the gateway passes it through a **Circuit Breaker** state machine that manages target microservice availability.
* **State Machine Logic:**
* **Closed State (Healthy):** The gateway routes traffic normally. It tracks the percentage of response failures (e.g., HTTP 5xx codes or timeouts) from the downstream service.
* **Open State (Tripped):** If the failure rate crosses a configured threshold (e.g., 50% failures within 10 seconds), the circuit trips open. The gateway immediately stops sending traffic to the broken service and returns `HTTP 503 Service Unavailable` to protect the ecosystem from cascading failures.
* **Half-Open State (Recovery):** After a cooldown period, the gateway cautiously lets a small percentage of requests through to check if the downstream service has recovered.



### 4. Dynamic Upstream Routing & Metrics Capture

* If both the rate limit and the circuit breaker pass, Go's custom standard library proxy (`httpx/httputil.ReverseProxy`) alters the request headers, updates the host target, and forwards the payload to the actual upstream server (like your FastAPI app) via an internal, low-latency network interface.
* Once the downstream app finishes processing and responds, the gateway intercepts the response on its way back to the client.
* It records critical real-time execution statistics—such as Request Per Second (RPS), round-trip response latency, and status code counts—pushing them to an internal metric engine without adding overhead to the client's response cycle.