// WYGENEROWANE Z contracts.json — NIE EDYTUJ RĘCZNIE. Przegeneruj: `make gen-js`.
import { check } from "./contract.mjs";
const _OUT = {"window/command/close": {"action": "const:window-close", "reversible": "const:true", "snapshot": "obj", "inverse": {"path": "const:window/command/restore", "args": {"snapshot": "obj"}}}, "window/command/restore": {"action": "const:window-restore", "reversible": "const:true", "inverse": {"path": "const:window/command/close", "args": {"id": "?str"}}}};
// self-guard: koperta walidowana out-schematem kontraktu PRZED zwrotem
export const ok = (route, fields) => {
  const env = { ok: true, ...fields };
  check(_OUT[route], env, `${route}.out`);
  return env;
};

// WYGENEROWANE Z KONTRAKTU v1 — kształt z contracts.json, nie edytuj ręcznie
export function close({ id = "" } = {}) {
  throw new Error("ciało window/command/close");          // uzupełnij logikę, potem:
  return ok("window/command/close", { action: "window-close", reversible: true, snapshot: {}, inverse: {path: "window/command/restore", args: {snapshot: {}}} });
}

// WYGENEROWANE Z KONTRAKTU v1 — kształt z contracts.json, nie edytuj ręcznie
export function restore({ snapshot = null } = {}) {
  throw new Error("ciało window/command/restore");          // uzupełnij logikę, potem:
  return ok("window/command/restore", { action: "window-restore", reversible: true, inverse: {path: "window/command/close", args: {id: ""}} });
}
