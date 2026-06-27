// WYGENEROWANE Z contracts.json — NIE EDYTUJ RĘCZNIE. Przegeneruj: `make gen-js`.
// `ok(fields)` (koperta {ok:true,...}) dostarcza pakiet connectora — zaimportuj go:
//   import { ok } from './conn.mjs'
const ok = (fields) => ({ ok: true, ...fields });  // domyślny; nadpisz importem

// WYGENEROWANE Z KONTRAKTU v1 — kształt z contracts.json, nie edytuj ręcznie
export function close({ id = "" } = {}) {
  throw new Error("ciało window/command/close");          // uzupełnij logikę, potem:
  return ok({ action: "window-close", reversible: true, snapshot: {}, inverse: {path: "window/command/restore", args: {snapshot: {}}} });
}

// WYGENEROWANE Z KONTRAKTU v1 — kształt z contracts.json, nie edytuj ręcznie
export function restore({ snapshot = null } = {}) {
  throw new Error("ciało window/command/restore");          // uzupełnij logikę, potem:
  return ok({ action: "window-restore", reversible: true, inverse: {path: "window/command/close", args: {id: ""}} });
}
