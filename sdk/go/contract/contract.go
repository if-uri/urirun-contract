// Author: Tom Sapletta · https://tom.sapletta.com
// Part of the ifURI solution.
//
// Package contract: runtime guard koperty dla connectorów Go — port 1:1 kernela
// urirun_contract.gate. Connector woła EnvelopeViolation(contract, env) przed zwróceniem
// koperty; jeśli kształt rozjedzie się z kontraktem, dostaje komunikat zamiast cichego dryfu.
// Ten sam neutralny contracts.json + złote przykłady co Python/JS → walidator neutralny.
//
// Tarcie Go: JSON liczby dekodują się do float64 (int = sprawdź całkowitość); brak-vs-zero
// zachowany przez walidację map[string]interface{} (obecność klucza), nie struct.
package contract

import (
	"fmt"
	"math"
	"strconv"
	"strings"
)

func parseConst(tok string) interface{} {
	switch tok {
	case "true":
		return true
	case "false":
		return false
	}
	if i, err := strconv.Atoi(tok); err == nil {
		return i
	}
	return tok
}

func constEqual(exp, v interface{}) bool {
	if ei, ok := exp.(int); ok { // const liczbowy: JSON daje float64
		if vf, ok := v.(float64); ok {
			return float64(ei) == vf
		}
		return false
	}
	return exp == v
}

func leafOK(tok string, v interface{}) bool {
	if strings.HasPrefix(tok, "?") {
		return v == nil || leafOK(tok[1:], v)
	}
	if strings.HasPrefix(tok, "const:") {
		return constEqual(parseConst(tok[6:]), v)
	}
	if strings.HasPrefix(tok, "enum:") {
		s, ok := v.(string)
		if !ok {
			return false
		}
		for _, a := range strings.Split(tok[5:], "|") {
			if a == s {
				return true
			}
		}
		return false
	}
	switch tok {
	case "str":
		_, ok := v.(string)
		return ok
	case "int":
		f, ok := v.(float64)
		return ok && f == math.Trunc(f)
	case "num":
		_, ok := v.(float64)
		return ok
	case "bool":
		_, ok := v.(bool)
		return ok
	case "obj":
		_, ok := v.(map[string]interface{})
		return ok
	case "list":
		_, ok := v.([]interface{})
		return ok
	case "any":
		return true
	}
	return false
}

// Check zwraca błąd z umiejscowionym komunikatem, gdy value nie spełnia schema (jak kernel `check`).
func Check(schema, value interface{}, where string) error {
	if m, ok := schema.(map[string]interface{}); ok {
		if alts, has := m["oneOf"]; has {
			var errs []string
			for i, alt := range alts.([]interface{}) {
				if e := Check(alt, value, fmt.Sprintf("%s|oneOf[%d]", where, i)); e == nil {
					return nil
				} else {
					errs = append(errs, e.Error())
				}
			}
			return fmt.Errorf("%s: matched none of oneOf -> %v", where, errs)
		}
		vm, ok := value.(map[string]interface{})
		if !ok {
			return fmt.Errorf("%s: expected object", where)
		}
		for key, sub := range m {
			subStr, isStr := sub.(string)
			if isStr && strings.HasPrefix(subStr, "?") {
				if _, present := vm[key]; !present {
					continue
				}
			}
			val, present := vm[key]
			if !present {
				return fmt.Errorf("%s: missing required key %q", where, key)
			}
			if e := Check(sub, val, fmt.Sprintf("%s.%s", where, key)); e != nil {
				return e
			}
		}
		return nil
	}
	if tok, ok := schema.(string); ok {
		if !leafOK(tok, value) {
			return fmt.Errorf("%s: %v does not satisfy %s", where, value, tok)
		}
		return nil
	}
	if arr, ok := schema.([]interface{}); ok && len(arr) > 0 {
		va, ok := value.([]interface{})
		if !ok {
			return fmt.Errorf("%s: expected list", where)
		}
		for i, it := range va {
			if e := Check(arr[0], it, fmt.Sprintf("%s[%d]", where, i)); e != nil {
				return e
			}
		}
		return nil
	}
	return nil
}

// EnvelopeViolation zwraca komunikat naruszenia albo "" (jak kernel `envelope_violation`).
func EnvelopeViolation(c map[string]interface{}, env map[string]interface{}) string {
	if ok, _ := env["ok"].(bool); ok {
		if out, ok := c["out"].(map[string]interface{}); ok && len(out) > 0 {
			if e := Check(out, env, "out"); e != nil {
				return e.Error()
			}
		}
		return ""
	}
	var cls interface{}
	if rem, ok := env["remediation"].(map[string]interface{}); ok {
		cls = rem["class"]
	}
	if cls == nil {
		if errm, ok := env["error"].(map[string]interface{}); ok {
			cls = errm["remediationClass"]
		}
	}
	if errors, ok := c["errors"].([]interface{}); ok && len(errors) > 0 && cls != nil {
		for _, e := range errors {
			if e == cls {
				return ""
			}
		}
		return fmt.Sprintf("error class %v not in declared %v", cls, errors)
	}
	return ""
}
