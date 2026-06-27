// WYGENEROWANE Z contracts.json — NIE EDYTUJ RĘCZNIE. Przegeneruj: `make gen-go`.
package handlers

import "fmt"

var _ = fmt.Errorf // fmt używane w szkieletach poniżej

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
