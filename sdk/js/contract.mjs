#!/usr/bin/env node
// Author: Tom Sapletta · https://tom.sapletta.com
// Part of the ifURI solution.
//
// Runtime guard koperty dla connectorów JS — port 1:1 kernela urirun_contract.gate.
// Connector woła `envelopeViolation(contract, env)` PRZED zwróceniem koperty: jeśli kształt
// rozjedzie się z kontraktem, dostaje komunikat (nie cichy dryf). Ten sam contracts.json,
// te same złote przykłady co Python/Go → walidator jest językowo-neutralny.
//
// CLI (do testów parytetu): node contract.mjs <contracts.json> <route>   # koperta z stdin
//   wypisuje "OK" (exit 0) albo "VIOLATION <msg>" (exit 1).

const parseConst = (tok) =>
  tok === "true" ? true : tok === "false" ? false
  : /^-?\d+$/.test(tok) ? parseInt(tok, 10) : tok;

function leafOk(token, value) {
  if (token.startsWith("?")) return value === null || value === undefined || leafOk(token.slice(1), value);
  if (token.startsWith("const:")) return value === parseConst(token.slice(6));
  if (token.startsWith("enum:")) return token.slice(5).split("|").includes(value);
  switch (token) {
    case "str": return typeof value === "string";
    case "int": return typeof value === "number" && Number.isInteger(value);
    case "num": return typeof value === "number";
    case "bool": return typeof value === "boolean";
    case "obj": return value !== null && typeof value === "object" && !Array.isArray(value);
    case "list": return Array.isArray(value);
    case "any": return true;
  }
  return false;
}

// Rzuca Error z umiejscowionym komunikatem (jak kernel `check`).
export function check(schema, value, where) {
  if (schema && typeof schema === "object" && !Array.isArray(schema)) {
    if ("oneOf" in schema) {
      const errs = [];
      for (let i = 0; i < schema.oneOf.length; i++) {
        try { check(schema.oneOf[i], value, `${where}|oneOf[${i}]`); return; }
        catch (e) { errs.push(e.message); }
      }
      throw new Error(`${where}: matched none of oneOf -> ${errs}`);
    }
    if (value === null || typeof value !== "object" || Array.isArray(value))
      throw new Error(`${where}: expected object`);
    for (const [key, spec] of Object.entries(schema)) {
      if (!(key in value)) {
        if (typeof spec === "string" && spec.startsWith("?")) continue;
        throw new Error(`${where}: missing required key '${key}'`);
      }
      check(spec, value[key], `${where}.${key}`);
    }
    return;
  }
  if (Array.isArray(schema)) {
    if (!Array.isArray(value)) throw new Error(`${where}: expected list`);
    if (schema.length) value.forEach((it, i) => check(schema[0], it, `${where}[${i}]`));
    return;
  }
  if (!leafOk(schema, value))
    throw new Error(`${where}: ${JSON.stringify(value)} does not satisfy ${schema}`);
}

// Zwraca komunikat naruszenia albo null (jak kernel `envelope_violation`).
export function envelopeViolation(contract, env) {
  try {
    if (env && env.ok) {
      if (contract.out && Object.keys(contract.out).length) check(contract.out, env, "out");
      return null;
    }
    let cls = null;
    const rem = env && env.remediation;
    if (rem && typeof rem === "object") cls = rem.class;
    if (cls == null) {
      const err = env && env.error;
      if (err && typeof err === "object") cls = err.remediationClass;
    }
    const errors = contract.errors || [];
    if (errors.length && cls != null && !errors.includes(cls))
      return `error class '${cls}' not in declared ${JSON.stringify(errors)}`;
  } catch (e) { return e.message; }
  return null;
}

// Neutralny contracts.json → {route: contract} (te same pola co kernel).
export function loadContracts(doc) {
  const out = {};
  for (const [route, c] of Object.entries(doc.contracts || {})) {
    out[route] = {
      version: c.version || "v1", effect: c.effect || "query",
      reversible: !!c.reversible, inverseRoute: c.inverseRoute || "",
      inp: c.inp || {}, out: c.out || {}, errors: c.errors || [], examples: c.examples || [],
    };
  }
  return out;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const fs = await import("node:fs");
  const [, , contractsPath, route] = process.argv;
  const contracts = loadContracts(JSON.parse(fs.readFileSync(contractsPath, "utf8")));
  let input = "";
  for await (const chunk of process.stdin) input += chunk;
  const violation = envelopeViolation(contracts[route], JSON.parse(input));
  if (violation) { console.log("VIOLATION " + violation); process.exit(1); }
  console.log("OK");
}
