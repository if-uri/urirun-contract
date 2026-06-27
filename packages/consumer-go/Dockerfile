FROM golang:1.22-alpine AS builder
WORKDIR /build
COPY packages/consumer-go/go.mod .
COPY packages/consumer-go/service.go .
RUN go build -o service .

FROM scratch
COPY --from=builder /build/service /service
COPY contracts.json /contracts.json
ENV CONTRACTS=/contracts.json PORT=8803
EXPOSE 8803
HEALTHCHECK --interval=3s --timeout=2s --retries=10 \
  CMD ["/service", "-health"]
CMD ["/service"]
