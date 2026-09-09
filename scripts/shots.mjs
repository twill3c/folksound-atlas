/**
 * shots.mjs — 目視検品のための画面撮影。
 *
 * **fullPage で撮らない。** この機では固定フッタが途中に焼き込まれ、
 * 「無い欠陥」が写る(HC-194)。ビューポートのまま撮り、
 * 長い頁は位置をずらして複数枚に分ける。
 */
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.argv[2] ?? "http://localhost:3000";
const OUT = "shots";
fs.mkdirSync(OUT, { recursive: true });

const TARGETS = [
  ["/", "home", [0, 700]],
  ["/map/", "map", [0, 620]],
  ["/space/", "space", [0, 640]],
  ["/distance/", "distance", [0, 620, 1240, 1900]],
  ["/network/", "network", [0, 400]],
  ["/models/", "models", [0, 700, 1400]],
  ["/about/", "about", [0, 900]],
  ["/song/folk_000001/", "song", [0, 700, 1400]],
];

const browser = await chromium.launch();
for (const width of [1280, 480]) {
  const ctx = await browser.newContext({ viewport: { width, height: 860 } });
  const page = await ctx.newPage();
  for (const [path, name, offsets] of TARGETS) {
    await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(700);
    for (const y of offsets) {
      await page.evaluate((v) => window.scrollTo(0, v), y);
      await page.waitForTimeout(200);
      const f = `${OUT}/${name}-${width}-${y}.png`;
      await page.screenshot({ path: f });
      console.log(f);
    }
  }
  await ctx.close();
}
await browser.close();
