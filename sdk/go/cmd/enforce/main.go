// Part of the ifURI solution — CLI parytetu: czyta kopertę z stdin, zwraca naruszenie.
//
//	go run ./cmd/enforce <contracts.json> <route>      # koperta z stdin
//	  "OK" (exit 0)  albo  "VIOLATION <msg>" (exit 1)
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	"github.com/if-uri/urirun-contract/sdk/go/contract"
)

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintln(os.Stderr, "użycie: enforce <contracts.json> <route>")
		os.Exit(2)
	}
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, "brak contracts.json:", err)
		os.Exit(2)
	}
	var doc map[string]interface{}
	if err := json.Unmarshal(raw, &doc); err != nil {
		fmt.Fprintln(os.Stderr, "zły JSON kontraktu:", err)
		os.Exit(2)
	}
	cs, _ := doc["contracts"].(map[string]interface{})
	c, ok := cs[os.Args[2]].(map[string]interface{})
	if !ok {
		fmt.Fprintln(os.Stderr, "brak trasy:", os.Args[2])
		os.Exit(2)
	}
	input, _ := io.ReadAll(os.Stdin)
	var env map[string]interface{}
	if err := json.Unmarshal(input, &env); err != nil {
		fmt.Fprintln(os.Stderr, "zła koperta JSON:", err)
		os.Exit(2)
	}
	if v := contract.EnvelopeViolation(c, env); v != "" {
		fmt.Println("VIOLATION " + v)
		os.Exit(1)
	}
	fmt.Println("OK")
}
