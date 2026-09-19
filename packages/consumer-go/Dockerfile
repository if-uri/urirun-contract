FROM golang:1.22-alpine@sha256:4eb607b9efd29f7ecd2d5a5214592b2c012d8194e6e9b89cfe15e65e9226a745 AS builder
WORKDIR /build
COPY packages/consumer-go/go.mod .
COPY packages/consumer-go/service.go .
RUN go build -o service .

FROM scratch
COPY --from=builder /build/service /service
COPY examples/windowpair/contracts.json /contracts.json
ENV CONTRACTS=/contracts.json PORT=8803
EXPOSE 8803
HEALTHCHECK --interval=3s --timeout=2s --retries=10 \
  CMD ["/service", "-health"]
CMD ["/service"]
