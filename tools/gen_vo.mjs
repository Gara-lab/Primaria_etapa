import { readFile, writeFile, mkdir } from "node:fs/promises";
import { execFile } from "node:child_process";
import path from "node:path";
import process from "node:process";

const VOICE_ID = "BTq6sz7H4zXMYN9OUp1X";
const MODEL_ID = "eleven_multilingual_v2";
const SETTINGS = { stability: 0.55, similarity_boost: 0.8, style: 0.3, speed: 0.95 };

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) out[a.slice(2)] = true;
    else { out[a.slice(2)] = next; i++; }
  }
  return out;
}

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");

function die(msg) { console.error(msg); process.exit(1); }

async function loadEnvKey(name) {
  let text;
  try { text = await readFile(path.join(repoRoot, ".env"), "utf8"); }
  catch { die(`no .env at ${path.join(repoRoot, ".env")}`); }
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (t.startsWith(name + "=")) {
      const v = t.slice(name.length + 1).trim().replace(/^["']|["']$/g, "");
      if (v) return v;
    }
  }
  return die(`${name} not found in .env`);
}

function probeDuration(file) {
  return new Promise((resolve) => {
    execFile("ffprobe", ["-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", file],
      (err, stdout) => resolve(err ? null : parseFloat(stdout.trim()) || null));
  });
}

async function _elevenlabsTts({ id, key, voiceId, modelId, settings, text, previousRequestIds }) {
  const body = { text, model_id: modelId, voice_settings: settings };
  if (previousRequestIds.length) body.previous_request_ids = previousRequestIds.slice(-3);

  const r = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}?output_format=mp3_44100_192`, {
    method: "POST",
    headers: { "xi-api-key": key, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) die(`${id}: HTTP ${r.status}: ${(await r.text()).slice(0, 800)}`);
  const requestId = r.headers.get("request-id");
  const buffer = Buffer.from(await r.arrayBuffer());
  return { buffer, requestId };
}

const PROVIDERS = { elevenlabs: _elevenlabsTts };

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.beats || !args["out-dir"]) die("usage: node tools/gen_vo.mjs --beats <beats.json> --out-dir <dir>");

  const beats = JSON.parse(await readFile(path.resolve(args.beats), "utf8"));
  const outDir = path.resolve(args["out-dir"]);
  await mkdir(outDir, { recursive: true });
  const key = await loadEnvKey("ELEVENLABS_API_KEY");

  const providerName = process.env.TTS_PROVIDER || "elevenlabs";
  const ttsFn = PROVIDERS[providerName];
  if (!ttsFn) die(`Unknown TTS_PROVIDER '${providerName}'. Implement a function with the same signature as _elevenlabsTts({ id, key, voiceId, modelId, settings, text, previousRequestIds }) returning { buffer, requestId }, and add it to PROVIDERS in tools/gen_vo.mjs.`);

  const manifest = { voice_id: VOICE_ID, model_id: MODEL_ID, settings: SETTINGS, recipe: "#18", beats: {} };
  const prevIds = [];

  for (const [id, text] of Object.entries(beats)) {
    console.log(`${id}: "${text.slice(0, 60)}${text.length > 60 ? "…" : ""}"`);
    const { buffer, requestId } = await ttsFn({
      id, key, voiceId: VOICE_ID, modelId: MODEL_ID, settings: SETTINGS, text, previousRequestIds: prevIds,
    });
    if (requestId) prevIds.push(requestId);

    const outFile = path.join(outDir, `${id}.mp3`);
    await writeFile(outFile, buffer);
    const dur = await probeDuration(outFile);
    manifest.beats[id] = { text, file: `${id}.mp3`, duration_s: dur, request_id: requestId };
    console.log(`  wrote ${path.relative(repoRoot, outFile)}${dur ? `  (${dur.toFixed(2)}s)` : ""}`);
  }

  const manifestFile = path.join(outDir, "vo-manifest.json");
  await writeFile(manifestFile, JSON.stringify(manifest, null, 2), "utf8");
  console.log(`wrote ${path.relative(repoRoot, manifestFile)}`);
}

main();
