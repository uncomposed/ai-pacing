// Run Epoch's compiled GATE solver under Node, without a browser.
//
// Usage: node run_official.mjs <gate.js> <out.json> [jobs.json]
//
// <gate.js> is the playground bundle https://epoch.ai/generated/gate.js, fetched and
// hash-checked by fetch_bundle.sh (not vendored). It contains the GATE model as C++
// compiled to WebAssembly inside an inline Web Worker. This script extracts:
//   * the worker source (emscripten module, embedded wasm, and the small wrapper that
//     calls runSimulation / runSimulationChecks), and runs it unchanged in a vm context
//     with a minimal worker-global shim;
//   * `cache_default`, the playground's precomputed runs of its three presets, which the
//     rerun of an unmodified preset is compared against.
// A job is {name, preset, modelParams?: {"dotted.path": value}, solverArgs?: {...}}:
// the preset's exact cached arguments with the given overrides. Without jobs.json the
// three presets are run.
import fs from "node:fs";
import vm from "node:vm";

const [bundlePath, outPath, jobsPath] = process.argv.slice(2);
if (!bundlePath || !outPath) {
  console.error("usage: node run_official.mjs <gate.js> <out.json> [jobs.json]");
  process.exit(2);
}
const src = fs.readFileSync(bundlePath, "utf8");

// --- cache_default: one line holding a JSON-compatible literal ---
const cacheLine = src.split("\n").find((l) => l.trim().startsWith("var cache_default = "));
if (!cacheLine) throw new Error("cache_default not found in bundle");
const cache = JSON.parse(cacheLine.trim().slice("var cache_default = ".length).replace(/;$/, ""));

// --- worker source: the single-quoted literal passed to inlineWorker() in Worker2 ---
const marker = "function Worker2() {\n    return inlineWorker(";
const i0 = src.indexOf(marker);
if (i0 < 0) throw new Error("Worker2 not found in bundle");
const litStart = i0 + marker.length;
const litEnd = src.indexOf(");\n  }", litStart);
// Evaluate only the string literal, in an empty context.
const workerSrc = vm.runInNewContext(src.slice(litStart, litEnd), Object.create(null));
if (typeof workerSrc !== "string") throw new Error("worker literal did not evaluate to a string");

let onMessage = null;
let pending = null;
const sandbox = {
  console, atob, setTimeout, clearTimeout, setInterval, clearInterval,
  WebAssembly, TextDecoder, TextEncoder, URL,
  addEventListener: (type, fn) => { if (type === "message") onMessage = fn; },
  postMessage: (data) => { const p = pending; pending = null; p(data); },
};
sandbox.self = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
// The solver prints progress lines to stdout; send them to stderr so stdout stays clean.
sandbox.console = { ...console, log: (...a) => console.error(...a) };
vm.runInContext(workerSrc, sandbox, { filename: "gate.worker.js" });
if (!onMessage) throw new Error("worker did not register a message handler");

function solve(args) {
  return new Promise((resolve) => {
    pending = resolve;
    onMessage({ data: JSON.parse(JSON.stringify(args)) });
  });
}

// The playground's reshaping (gate-api.ts, convertRunToFrontEnd), reproduced.
function toFrontEnd(run) {
  const out = {
    automation_schedule_x: run.automation_schedule_x,
    automation_schedule_y: run.automation_schedule_y,
    objective_path: run.objective_path,
    allocation_grid: run.allocation_grid,
    states: [],
  };
  for (let i = 0; i < run.timesteps.length; i++) {
    const s = { time: run.timesteps[i] };
    for (const k of Object.keys(run)) {
      if (k.endsWith("_path") && k !== "objective_path") s[k.slice(0, -5)] = run[k][i];
    }
    s.chip_fabrication_scale_up =
      run.compute_path[i] / run.hardware_path[i] / (run.compute_path[0] / run.hardware_path[0]);
    out.states.push(s);
  }
  return out;
}

function setPath(obj, dotted, value) {
  const keys = dotted.split(".");
  let o = obj;
  for (const k of keys.slice(0, -1)) {
    if (!(k in o)) throw new Error(`unknown parameter path ${dotted}`);
    o = o[k];
  }
  if (!(keys.at(-1) in o)) throw new Error(`unknown parameter path ${dotted}`);
  o[keys.at(-1)] = value;
}

const jobs = jobsPath
  ? JSON.parse(fs.readFileSync(jobsPath, "utf8"))
  : cache.map((_, k) => ({ name: `preset_${k}`, preset: k }));

const results = [];
for (const job of jobs) {
  const args = JSON.parse(JSON.stringify(cache[job.preset].args));
  for (const [p, v] of Object.entries(job.modelParams ?? {})) setPath(args.modelParams, p, v);
  Object.assign(args.solverArgs, job.solverArgs ?? {});
  const unmodified = !job.modelParams && !job.solverArgs;
  const t0 = Date.now();
  const raw = await solve(args);
  const seconds = (Date.now() - t0) / 1000;
  results.push({
    job, args, seconds,
    rerun: { ...raw, world_path: toFrontEnd(raw.world_path) },
    cached: unmodified ? cache[job.preset].run : null,
  });
  console.error(`${job.name}: ${seconds.toFixed(1)} s, objective ${raw.objective}`);
}
fs.writeFileSync(outPath, JSON.stringify({ node: process.version, results }));
