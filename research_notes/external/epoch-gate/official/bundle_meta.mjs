// Extract the parts of a GATE playground bundle that a redeploy check compares (issue #33).
//
// Usage: node bundle_meta.mjs <gate.js> <out.json>
//
// Writes {sha256, bytes, parameter_table, presets}: the SHA-256 of the file, the
// playground's parameter table (`input_default2`; the long "Definition" and "Reasoning"
// texts are replaced by their SHA-256 so a change still shows), and the three preset
// argument sets from `cache_default` (modelParams, solverArgs, simulationArgs; the cached
// runs themselves are left out). `cache_default` is parsed as JSON. `input_default2` uses
// single quotes, so that one line is evaluated as an expression in an empty vm context
// with a timeout. vm is not a security boundary; this script is meant for the CI runner
// (or a throwaway directory), where a redeployed bundle is downloaded but not trusted.
import crypto from "node:crypto";
import fs from "node:fs";
import vm from "node:vm";

const [bundlePath, outPath] = process.argv.slice(2);
if (!bundlePath || !outPath) {
  console.error("usage: node bundle_meta.mjs <gate.js> <out.json>");
  process.exit(2);
}
const buf = fs.readFileSync(bundlePath);
const src = buf.toString("utf8");
const sha = (s) => crypto.createHash("sha256").update(s).digest("hex");

function literalAfter(prefix, json) {
  const line = src.split("\n").find((l) => l.trim().startsWith(prefix));
  if (!line) return null;
  const lit = line.trim().slice(prefix.length).replace(/;$/, "");
  if (json) return JSON.parse(lit);
  // Parentheses make an object or array literal an expression; empty context, no globals.
  return vm.runInNewContext(`(${lit})`, Object.create(null), { timeout: 5000 });
}

const out = { sha256: sha(buf), bytes: buf.length, parameter_table: null, presets: null, errors: [] };
try {
  const table = literalAfter("var input_default2 = ", false);
  out.parameter_table = table && table.map((row) => {
    const r = {};
    for (const [k, v] of Object.entries(row)) {
      r[k] = k === "Definition" || k === "Reasoning" ? `sha256:${sha(String(v))}` : v;
    }
    return r;
  });
  if (!table) out.errors.push("input_default2 not found");
} catch (e) {
  out.errors.push(`parameter table: ${e.message}`);
}
try {
  const cache = literalAfter("var cache_default = ", true);
  out.presets = cache && cache.map((c) => c.args);
  if (!cache) out.errors.push("cache_default not found");
} catch (e) {
  out.errors.push(`presets: ${e.message}`);
}
fs.writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
console.error(`${bundlePath}: sha256 ${out.sha256}, ${out.bytes} bytes, ${out.errors.length} extraction errors`);
