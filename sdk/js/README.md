# urirun-contract (JS SDK)

Runtime envelope guard for [urirun](https://urirun.com) connectors written in JavaScript —
a 1:1 port of the Python kernel `urirun_contract.gate` (`check` + `envelopeViolation`).

The contract (output shape, effect class, reversibility, error taxonomy) lives in a neutral,
language-agnostic `contracts.json`. This SDK validates a connector's envelope against it **at the
boundary**, so a JS connector can't silently drift from the declared shape. Golden examples in the
contract double as a cross-language conformance corpus (Python · JS · Go all agree).

## Install

```bash
npm install urirun-contract
```

## Use in a connector

```js
import { envelopeViolation, loadContracts } from "urirun-contract";
import contractsDoc from "./contracts.json" assert { type: "json" };

const contracts = loadContracts(contractsDoc);

function close({ id = "" } = {}) {
  const env = { ok: true, action: "window-close", reversible: true, snapshot: snap, inverse };
  const violation = envelopeViolation(contracts["window/command/close"], env);
  if (violation) throw new Error(`kontrakt: ${violation}`);
  return env;
}
```

`check(schema, value, where)` throws on the first violation; `envelopeViolation(contract, env)`
returns a message or `null`. `loadContracts(doc)` reads a neutral `contracts.json`.

## CLI (conformance parity)

```bash
echo '{"ok":true,...}' | npx urirun-contract-enforce contracts.json window/command/close
# -> "OK"  (exit 0)  |  "VIOLATION <msg>"  (exit 1)
```

Apache-2.0 · part of the ifURI solution.
