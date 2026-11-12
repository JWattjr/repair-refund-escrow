// Read-only: complete the final view readbacks for the recorded live run (no writes, no keys needed beyond a client).
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const cliRoot = "C:/Users/User/AppData/Roaming/npm/node_modules/genlayer/node_modules";
const { createClient } = await import(pathToFileURL(`${cliRoot}/genlayer-js/dist/index.js`).href);
const { studionet } = await import(pathToFileURL(`${cliRoot}/genlayer-js/dist/chains/index.js`).href);
const file = path.join(root, "deployments", "studionet-live-run.json");
const result = JSON.parse(fs.readFileSync(file, "utf8"));
const addr = result.contract_address;
const client = createClient({ chain: studionet });
const big = (_, v) => (typeof v === "bigint" ? v.toString() : v);

async function read(fn, args = []) {
  for (let i = 1; i <= 8; i++) {
    try { return JSON.parse(JSON.stringify(await client.readContract({ address: addr, functionName: fn, args }), big)); }
    catch (e) { process.stdout.write(`${fn} attempt ${i} failed\n`); await new Promise((r) => setTimeout(r, 3000)); }
  }
  throw new Error(`${fn} unreadable`);
}
result.final = {
  terms: await read("get_terms"), submission_1: await read("get_submission", [1]), submission_2: await read("get_submission", [2]),
  claims: await read("get_claims"), cutoff: await read("get_criterion_state", ["cutoff"]), contact: await read("get_criterion_state", ["contact"]),
  judgment_1_1: await read("get_judgment", [1, 1]), judgment_2_1: await read("get_judgment", [2, 1]), accounting: await read("get_accounting"),
};
const local = execFileSync("git", ["show", `${result.source_commit}:contracts/repair_refund_escrow.py`], { cwd: root, maxBuffer: 1 << 24 });
for (let i = 1; i <= 8 && result.onchain_source_matches_local === undefined; i++) {
  try {
    const code = await client.getContractCode?.(addr);
    if (typeof code === "string") result.onchain_source_matches_local = crypto.createHash("sha256").update(code, "utf8").digest("hex") === result.source_sha256;
    else break;
  } catch (e) { await new Promise((r) => setTimeout(r, 3000)); }
}
result.readback_utc = new Date().toISOString();
fs.writeFileSync(file, JSON.stringify(result, null, 2) + "\n");
process.stdout.write(`accounting ${JSON.stringify(result.final.accounting)}\nsource_match ${result.onchain_source_matches_local}\n`);
