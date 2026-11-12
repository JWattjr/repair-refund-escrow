// Live StudioNet run for repair-refund-escrow. Stops at the first unexpected result; never retries a write.
// Private keys stay in memory (OS keychain via the GenLayer CLI); nothing secret is printed or saved.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const cliRoot = "C:/Users/User/AppData/Roaming/npm/node_modules/genlayer/node_modules";
const { createAccount, createClient } = await import(pathToFileURL(`${cliRoot}/genlayer-js/dist/index.js`).href);
const { studionet } = await import(pathToFileURL(`${cliRoot}/genlayer-js/dist/chains/index.js`).href);
const keytar = (await import(pathToFileURL(`${cliRoot}/keytar/lib/keytar.js`).href)).default;

const EV = "https://raw.githubusercontent.com/JWattjr/repair-refund-escrow-evidence";
const V1 = `${EV}/3286314dd6492df572823a454e8a777640f9026f/handover.md`;
const V2 = `${EV}/50bbb9ebb65ed37394f84f8ed60c4351f19b381c/handover.md`;
const CRITERIA = [
  { criterion_id: "cutoff", description: "The handover states a low-water cutoff of at least 15 cm.", allocation_units: 60 },
  { criterion_id: "contact", description: "The handover states an emergency contact phone number.", allocation_units: 40 },
];
const CLAIMS = [
  { criterion_id: "cutoff", allegation: "The stated low-water cutoff is 5 cm, below the required 15 cm.", quoted_line: "Low-water cutoff: 5 cm" },
  { criterion_id: "contact", allegation: "No emergency contact phone number is given; the field says TBD.", quoted_line: "Emergency contact: TBD" },
];
const out = path.join(root, "deployments", "studionet-live-run.json");
const big = (_, v) => (typeof v === "bigint" ? v.toString() : v);

const source = execFileSync("git", ["show", "HEAD:contracts/repair_refund_escrow.py"], { cwd: root, maxBuffer: 1 << 24 });
const blob = execFileSync("git", ["rev-parse", "HEAD:contracts/repair_refund_escrow.py"], { cwd: root }).toString().trim();
const commit = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root }).toString().trim();
if (execFileSync("git", ["status", "--porcelain", "--", "contracts"], { cwd: root }).toString().trim()) throw new Error("contracts/ is dirty");

async function who(alias) {
  const key = await keytar.getPassword("genlayer-cli", `account:${alias}`);
  if (!key) throw new Error(`account ${alias} unavailable`);
  const account = createAccount(key);
  return { account, client: createClient({ chain: studionet, account }) };
}
const buyer = await who("moment-grid-studionet");
const supplier = await who("portal-five-release");
const result = {
  network: "GenLayer StudioNet", chain_id: 61999, source_commit: commit, source_git_blob_sha1: blob,
  source_bytes: source.length, source_sha256: crypto.createHash("sha256").update(source).digest("hex"),
  buyer: buyer.account.address, supplier: supplier.account.address,
  evidence: { v1_url: V1, v2_url: V2 }, started_utc: new Date().toISOString(), steps: [],
};
const save = () => fs.writeFileSync(out, JSON.stringify(result, big, 2) + "\n");

function summarize(receipt) {
  const c = receipt.consensus_data ?? {};
  const leader = c.leader_receipt ?? [];
  const votes = c.votes ?? {};
  const counts = {};
  for (const v of Object.values(votes)) counts[String(v)] = (counts[String(v)] ?? 0) + 1;
  return {
    status: receipt.status_name ?? receipt.status, consensus_result: receipt.result_name ?? receipt.result,
    leader_execution: leader[0]?.execution_result ?? receipt.tx_execution_result_name ?? null,
    rounds: receipt.consensus_history?.consensus_results?.length ?? null, votes: counts,
  };
}
async function wait(client, hash) {
  for (let i = 0; i < 40; i++) {
    try { return await client.waitForTransactionReceipt({ hash, status: "FINALIZED", interval: 4000, retries: 90 }); }
    catch (e) { process.stdout.write(`  poll ${i + 1} failed; retrying\n`); }
  }
  throw new Error(`no finalized receipt for ${hash}`);
}
async function step(label, actor, fn, { expectFailure = false } = {}) {
  const row = { label, actor: actor.account.address, submitted_utc: new Date().toISOString(), expected_failure: expectFailure };
  result.steps.push(row);
  try { row.hash = await fn(actor.client); }
  catch (e) {
    row.submit_error = String(e.message ?? e).slice(0, 300); save();
    if (expectFailure) { process.stdout.write(`${label}: rejected at submit (expected)\n`); return row; }
    throw e;
  }
  const receipt = await wait(actor.client, row.hash);
  Object.assign(row, summarize(receipt));
  row.contract_address = receipt.data?.contract_address ?? undefined;
  save();
  process.stdout.write(`${label}: ${row.hash} ${row.status} ${row.consensus_result} leader=${row.leader_execution} votes=${JSON.stringify(row.votes)}\n`);
  const good = row.leader_execution === "SUCCESS" || row.leader_execution === "FINISHED_WITH_RETURN";
  const bad = !good || ["MAJORITY_DISAGREE", "UNDETERMINED", "DISAGREE"].includes(row.consensus_result);
  if (expectFailure ? good : bad) throw new Error(`${label}: unexpected outcome ${JSON.stringify(summarize(receipt))}`);
  return row;
}
const write = (address, fn, args) => (c) => c.writeContract({ address, functionName: fn, args, leaderOnly: false });
const read = async (address, fn, args = []) => {
  const v = await buyer.client.readContract({ address, functionName: fn, args });
  return JSON.parse(JSON.stringify(v, big));
};

const deadlines = ["2030-01-05T00:00:00Z", "2030-01-10T00:00:00Z", "2030-01-15T00:00:00Z", "2030-01-20T00:00:00Z", "2030-01-25T00:00:00Z"];
const ctor = [supplier.account.address, "Deliver a fictional pump controller handover note meeting the agreed criteria.", JSON.stringify(CRITERIA), 100, ...deadlines];
result.constructor_args = ctor;
const d = await step("deploy", buyer, (c) => c.deployContract({ code: source.toString("utf8"), args: ctor, leaderOnly: false }));
const addr = d.contract_address ?? (await buyer.client.getTransaction({ hash: d.hash })).data?.contract_address;
result.contract_address = addr;
result.explorer_url = `https://explorer-studio.genlayer.com/address/${addr}`;
save();
process.stdout.write(`address ${addr}\n`);

const terms = await read(addr, "get_terms");
result.terms_before_acceptance = terms;
save();
await step("accept_terms", supplier, write(addr, "accept_terms", [terms.terms_digest]));
await step("submit_delivery_v1", supplier, write(addr, "submit_delivery", [V1, "Version one of the fictional handover note."]));
await step("file_claims", buyer, write(addr, "file_claims", [JSON.stringify(CLAIMS)]));
await step("judge_defects_round1", buyer, write(addr, "judge_defects", []));
result.after_round1 = {
  cutoff: await read(addr, "get_criterion_state", ["cutoff"]), contact: await read(addr, "get_criterion_state", ["contact"]),
  judgment: await read(addr, "get_judgment", [1, 1]), accounting: await read(addr, "get_accounting"),
};
save();
await step("submit_repair_v2", supplier, write(addr, "submit_repair", [V2, "Raised the cutoff in version two."]));
await step("judge_repair_round2", buyer, write(addr, "judge_repair", []));
await step("expected_failure_new_claims_after_round1", buyer, write(addr, "file_claims", [JSON.stringify(CLAIMS)]), { expectFailure: true });
await step("expected_failure_finalize_after_settlement", supplier, write(addr, "finalize", []), { expectFailure: true });

result.final = {
  terms: await read(addr, "get_terms"), submission_1: await read(addr, "get_submission", [1]), submission_2: await read(addr, "get_submission", [2]),
  claims: await read(addr, "get_claims"), cutoff: await read(addr, "get_criterion_state", ["cutoff"]), contact: await read(addr, "get_criterion_state", ["contact"]),
  judgment_1_1: await read(addr, "get_judgment", [1, 1]), judgment_2_1: await read(addr, "get_judgment", [2, 1]), accounting: await read(addr, "get_accounting"),
};
result.finished_utc = new Date().toISOString();
save();
process.stdout.write(`final accounting ${JSON.stringify(result.final.accounting)}\n`);
