// WYGENEROWANE Z contracts.json — NIE EDYTUJ RĘCZNIE. Przegeneruj: `make gen-go`.
package handlers

import (
	"encoding/json"
	"fmt"

	contract "uriruncontract/contract"
)

const _outJSON = `{"window/command/close": {"action": "const:window-close", "reversible": "const:true", "snapshot": "obj", "inverse": {"path": "const:window/command/restore", "args": {"snapshot": "obj"}}}, "window/command/restore": {"action": "const:window-restore", "reversible": "const:true", "inverse": {"path": "const:window/command/close", "args": {"id": "?str"}}}}`

var _out map[string]interface{}

func init() {
	if err := json.Unmarshal([]byte(_outJSON), &_out); err != nil {
		panic(err)
	}
}

// Guard: zwaliduj kopertę out-schematem kontraktu PRZED zwrotem (opakuj nim ciało).
func Guard(route string, env map[string]interface{}) (map[string]interface{}, error) {
	if err := contract.Check(_out[route], env, route+".out"); err != nil {
		return nil, fmt.Errorf("kontrakt %s: %w", route, err)
	}
	return env, nil
}

// WYGENEROWANE Z KONTRAKTU v1 — kształt z contracts.json, nie edytuj ręcznie
type CloseIn struct {
	Id string `json:"id"`
}

func Close(in CloseIn) (map[string]any, error) {
	return nil, fmt.Errorf("ciało window/command/close niezaimplementowane")
	// po implementacji zwróć kopertę zgodną z out-schematem kontraktu
}

// WYGENEROWANE Z KONTRAKTU v1 — kształt z contracts.json, nie edytuj ręcznie
type RestoreIn struct {
	Snapshot map[string]any `json:"snapshot"`
}

func Restore(in RestoreIn) (map[string]any, error) {
	return nil, fmt.Errorf("ciało window/command/restore niezaimplementowane")
	// po implementacji zwróć kopertę zgodną z out-schematem kontraktu
}
