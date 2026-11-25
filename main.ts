// The World in One Day — Tuesday 24 November 2026.
// Entry image for the make.fun news-image-20261124 bounty.
//
// This file does exactly one thing: it copies the pre-rendered entry.png
// (drawn at build time by draw.py) into the output directory. It never
// renders, draws, or executes anything else. The grader runs this file
// read-only, so nothing here writes into the repository.
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = path.join(HERE, "entry.png");

async function main(): Promise<void> {
  const outDir = process.env.OUTPUT_DIR ?? "/output";
  const target = path.posix.join(outDir, "entry.png");
  await fs.promises.mkdir(outDir, { recursive: true });
  await fs.promises.copyFile(SOURCE, target);
  const bytes = (await fs.promises.stat(target)).size;
  console.log(`copied entry.png (${bytes} bytes) -> ${target}`);
}

main().catch((err: unknown) => {
  console.error("main.ts failed:", err);
  process.exit(1);
});
