import { chromium } from "playwright";
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const baseUrl = process.env.DEMO_BASE_URL || "http://localhost:3000";
const outputDir = path.resolve("docs/assets");
const tmpDir = path.resolve("tmp/gif-captures");

const targets = [
  { name: "demo-dashboard", url: `${baseUrl}/dashboard`, wait: 3000 },
  { name: "demo-agent-builder", url: `${baseUrl}/agents`, wait: 3000 },
  { name: "demo-workflow-builder", url: `${baseUrl}/workflows`, wait: 3000 },
];

const ensureDir = (dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
};

const run = async () => {
  ensureDir(outputDir);
  ensureDir(tmpDir);

  const browser = await chromium.launch();
  for (const target of targets) {
    const videoDir = path.join(tmpDir, target.name);
    ensureDir(videoDir);

    const context = await browser.newContext({
      recordVideo: { dir: videoDir, size: { width: 1280, height: 720 } },
    });
    const page = await context.newPage();
    await page.goto(target.url, { waitUntil: "networkidle" });
    await page.waitForTimeout(target.wait);
    await context.close();

    const files = fs.readdirSync(videoDir).filter((file) => file.endsWith(".webm"));
    if (!files.length) {
      throw new Error(`No video capture found for ${target.name}`);
    }
    const videoPath = path.join(videoDir, files[0]);
    const gifPath = path.join(outputDir, `${target.name}.gif`);

    execSync(
      `ffmpeg -y -i "${videoPath}" -vf "fps=12,scale=960:-1:flags=lanczos" -loop 0 "${gifPath}"`,
      { stdio: "inherit" }
    );
  }

  await browser.close();
  console.log("GIF captures written to docs/assets");
};

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
