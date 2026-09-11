import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createWriteStream } from "node:fs";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import process from "node:process";

const QUEUE = "https://queue.fal.run";
const REST = "https://rest.fal.ai";

const MODELS = {
  omnihuman: {
    endpoint: "fal-ai/bytedance/omnihuman/v1.5",
    price: 0.16,
    kind: "image",
    note: "identity winner in our tests, 1080p, <30s/gen",
  },
  "omnihuman-1.0": {
    endpoint: "fal-ai/bytedance/omnihuman",
    price: 0.14,
    kind: "image",
    note: "previous generation",
  },
  kling: {
    endpoint: "fal-ai/kling-video/v1/pro/ai-avatar",
    price: 0.115,
    kind: "image",
    note: "expressive/alive, can read theatrical",
  },
  "kling-v2": {
    endpoint: "fal-ai/kling-video/ai-avatar/v2/pro",
    price: 0.115,
    kind: "image",
    note: "expressive/alive, can read theatrical",
  },
  aurora: {
    endpoint: "fal-ai/creatify/aurora",
    price: 0.14,
    kind: "image",
    note: "720p; outputs yuv444p — use --reencode",
  },
  infinitetalk: {
    endpoint: "fal-ai/infinitetalk",
    price: 0.1,
    kind: "image",
    note: "weakest on identity in our tests, 720p",
  },
  sync2: {
    endpoint: "fal-ai/sync-lipsync/v2",
    price: 0.0,
    kind: "video",
    note: "lipsync ONTO real footage (price varies — check the model page)",
  },
};

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const key = a.slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) out[key] = true;
    else {
      out[key] = next;
      i++;
    }
  }
  return out;
}

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");

async function loadEnvKey(name) {
  let text;
  try {
    text = await readFile(path.join(repoRoot, ".env"), "utf8");
  } catch {
    die(`no .env at ${path.join(repoRoot, ".env")}`);
  }
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (t.startsWith(name + "=")) {
      const v = t.slice(name.length + 1).trim().replace(/^["']|["']$/g, "");
      if (v) return v;
    }
  }
  return die(`${name} not found in .env  (add it: ${name}=...)`);
}

function die(msg) {
  console.error(msg);
  process.exit(1);
}

const MIME = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".m4a": "audio/mp4",
  ".aac": "audio/aac",
  ".mp4": "video/mp4",
  ".mov": "video/quicktime",
};

async function uploadToFal(headers, file) {
  const abs = path.resolve(file);
  const ext = path.extname(abs).toLowerCase();
  const contentType = MIME[ext] || "application/octet-stream";
  const bytes = await readFile(abs).catch(() => die(`no such file: ${abs}`));

  const initiate = await fetch(
    `${REST}/storage/upload/initiate?storage_type=fal-cdn-v3`,
    {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ content_type: contentType, file_name: path.basename(abs) }),
    },
  );
  if (!initiate.ok) die(`upload initiate failed HTTP ${initiate.status}: ${(await initiate.text()).slice(0, 800)}`);
  const { upload_url, file_url } = await initiate.json();

  const put = await fetch(upload_url, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: bytes,
  });
  if (!put.ok) die(`upload PUT failed HTTP ${put.status}: ${(await put.text()).slice(0, 800)}`);

  console.log(`  uploaded ${path.basename(abs)} (${Math.round(bytes.length / 1024)} KB)`);
  return file_url;
}

async function submit(headers, endpoint, payload) {
  const r = await fetch(`${QUEUE}/${endpoint}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) die(`submit failed HTTP ${r.status}: ${(await r.text()).slice(0, 1500)}`);
  return r.json();
}

async function poll(headers, statusUrl, responseUrl, timeoutS) {
  const t0 = Date.now();
  let last = null;
  while ((Date.now() - t0) / 1000 < timeoutS) {
    const r = await fetch(statusUrl, { headers });
    if (!r.ok) die(`status failed HTTP ${r.status}: ${(await r.text()).slice(0, 800)}`);
    const st = await r.json();
    if (st.status !== last) {
      const q = st.queue_position != null ? ` (queue position ${st.queue_position})` : "";
      console.log(`  ${st.status}${q}`);
      last = st.status;
    }
    if (st.status === "COMPLETED") {
      const rr = await fetch(responseUrl, { headers });
      if (!rr.ok) die(`response failed HTTP ${rr.status}: ${(await rr.text()).slice(0, 800)}`);
      return rr.json();
    }
    if (["FAILED", "CANCELLED", "ERROR"].includes(st.status)) {
      die(`job ${st.status}: ${JSON.stringify(st).slice(0, 1500)}`);
    }
    await new Promise((res) => setTimeout(res, 3000));
  }
  die(`timed out after ${timeoutS}s (job may still finish; re-poll ${statusUrl})`);
}

async function download(url, out) {
  await mkdir(path.dirname(out), { recursive: true });
  const r = await fetch(url);
  if (!r.ok) die(`download failed HTTP ${r.status}`);
  await pipeline(Readable.fromWeb(r.body), createWriteStream(out));
}

async function reencode(file, ffmpegBin) {
  const tmp = file.replace(/\.mp4$/, ".yuv420.mp4");
  await new Promise((resolve, reject) => {
    const p = spawn(ffmpegBin, [
      "-y", "-i", file,
      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "medium",
      "-c:a", "aac", "-b:a", "192k", tmp,
    ], { stdio: ["ignore", "ignore", "inherit"] });
    p.on("error", reject);
    p.on("close", (code) => (code === 0 ? resolve() : reject(new Error(`ffmpeg exited ${code}`))));
  });
  const { rename, unlink } = await import("node:fs/promises");
  await unlink(file);
  await rename(tmp, file);
  console.log("  re-encoded to yuv420p");
}

async function _falGenerateAvatar(model, args, out) {
  const headers = { Authorization: "Key " + (await loadEnvKey("FAL_KEY")) };

  console.log(`model: ${model.endpoint}`);
  const audioUrl = await uploadToFal(headers, args.audio);
  const payload = { audio_url: audioUrl };
  if (model.kind === "video") payload.video_url = await uploadToFal(headers, args.video);
  else payload.image_url = await uploadToFal(headers, args.image);
  if (args.prompt) payload.prompt = args.prompt;
  if (args.resolution) payload.resolution = args.resolution;

  const job = await submit(headers, model.endpoint, payload);
  console.log(`submitted ${job.request_id}`);
  const result = await poll(headers, job.status_url, job.response_url, Number(args.timeout || 900));

  const videoUrl = result?.video?.url || result?.video_url || result?.output?.url;
  if (!videoUrl) die(`no video in response: ${JSON.stringify(result).slice(0, 1500)}`);

  await download(videoUrl, out);
  return { job, result };
}

const PROVIDERS = {
  fal: _falGenerateAvatar,
};

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args["list-models"]) {
    for (const [alias, m] of Object.entries(MODELS)) {
      const price = m.price ? `$${m.price.toFixed(3)}/s` : "see page";
      console.log(`  ${alias.padEnd(14)} ${price.padEnd(11)} [${m.kind}]  ${m.endpoint}\n${" ".repeat(16)}${m.note}`);
    }
    return;
  }

  const alias = args.model || "omnihuman";
  const model = MODELS[alias] || { endpoint: alias, price: null, kind: args.video ? "video" : "image", note: "" };
  if (!args.out) die("--out is required");
  if (!args.audio) die("--audio is required");
  if (model.kind === "video" && !args.video) die(`--video is required for ${alias} (lipsync onto real footage)`);
  if (model.kind === "image" && !args.image) die(`--image is required for ${alias}`);

  const providerName = process.env.AVATAR_PROVIDER || "fal";
  const generate = PROVIDERS[providerName];
  if (!generate) {
    die(`unknown AVATAR_PROVIDER '${providerName}': implement a function with the same signature as _falGenerateAvatar(model, args, out) and add it to PROVIDERS in this file`);
  }

  const out = path.resolve(args.out);
  const { job, result } = await generate(model, args, out);

  if (args.reencode) {
    const ff = typeof args.reencode === "string" ? args.reencode : (process.env.FFMPEG || "ffmpeg");
    await reencode(out, ff);
  }
  const { stat } = await import("node:fs/promises");
  console.log(`wrote ${args.out}  (${((await stat(out)).size / 1e6).toFixed(1)} MB)`);

  const js = out.replace(/\.mp4$/, "") + ".fal.json";
  await writeFile(js, JSON.stringify({
    request_id: job.request_id,
    endpoint: model.endpoint,
    alias,
    inputs: { image: args.image || null, video: args.video || null, audio: args.audio },
    prompt: args.prompt || null,
    result,
  }, null, 1), "utf8");
  console.log(`wrote ${path.relative(repoRoot, js)}`);
}

main();
