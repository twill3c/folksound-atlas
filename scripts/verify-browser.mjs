/**
 * verify-browser.mjs — 実ブラウザ検品(T-023 / T-024 / G-12)。
 *
 * 静的検査では緑のまま通る欠陥を捕まえるためのもの。とくに:
 *   - 図が本当に描かれているか(要素数だけでなく **幾何** を見る — HC-138)
 *   - 横に溢れていないか / 縦に伸びすぎていないか(HC-078 の代理指標)
 *   - 複数の画面幅で見る(1 つの幅だけでは列の潰れが出ない)
 *
 * **この検品器自身が壊れていないか**も疑う(HC-080)。
 * `--self-test` を付けると、わざと壊した頁を作って検査に当て、
 * 検査が実際に落ちることを確かめる。落ちないなら検品器が働いていない。
 *
 * 使い方:
 *   node scripts/verify-browser.mjs [--base http://localhost:3000] [--self-test]
 */

import { chromium } from "playwright";

const args = process.argv.slice(2);
const baseIdx = args.indexOf("--base");
const BASE = baseIdx >= 0 ? args[baseIdx + 1] : "http://localhost:3000";
const SELF_TEST = args.includes("--self-test");

const WIDTHS = [1280, 900, 480];
const MAX_PAGE_HEIGHT = 16000; // HC-078: これを超えたら、まず表の潰れを疑う

const failures = [];
const notes = [];

function fail(msg) {
  failures.push(msg);
  console.error(`  ✗ ${msg}`);
}
function ok(msg) {
  console.log(`  ✓ ${msg}`);
}

/** 取得そのものが失敗したら、それは「異常なし」ではない(HC-041)。 */
async function goto(page, path) {
  const url = `${BASE}${path}`;
  const res = await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
  if (!res || !res.ok()) {
    throw new Error(`取得に失敗: ${url} (${res ? res.status() : "no response"})`);
  }
  return res;
}

async function checkOverflow(page, label) {
  const r = await page.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
    scrollH: document.documentElement.scrollHeight,
  }));
  // 1px の丸めは許す
  if (r.scrollW > r.clientW + 1) {
    fail(`${label}: 横に溢れている (scrollWidth ${r.scrollW} > clientWidth ${r.clientW})`);
  } else {
    ok(`${label}: 横溢れなし`);
  }
  if (r.scrollH > MAX_PAGE_HEIGHT) {
    fail(`${label}: 縦に伸びすぎ (${r.scrollH}px > ${MAX_PAGE_HEIGHT}px)`);
  }
}

/** 図の中身が viewBox に収まっているかを測る(HC-159 / T-022)。 */
async function checkSvgGeometry(page, selector, label) {
  const info = await page.evaluate((sel) => {
    const svg = document.querySelector(sel);
    if (!svg) return null;
    const vb = svg.viewBox.baseVal;
    const out = [];
    for (const el of svg.querySelectorAll("text, path, rect, circle")) {
      let b;
      try {
        b = el.getBBox();
      } catch {
        continue;
      }
      if (b.width === 0 && b.height === 0) continue;
      const overflow =
        b.x < vb.x - 0.5 ||
        b.y < vb.y - 0.5 ||
        b.x + b.width > vb.x + vb.width + 0.5 ||
        b.y + b.height > vb.y + vb.height + 0.5;
      if (overflow) {
        out.push({
          tag: el.tagName,
          text: (el.textContent || "").slice(0, 24),
          x: Math.round(b.x),
          y: Math.round(b.y),
          w: Math.round(b.width),
          h: Math.round(b.height),
        });
      }
    }
    return { vb: { x: vb.x, y: vb.y, w: vb.width, h: vb.height }, out };
  }, selector);

  if (!info) {
    fail(`${label}: ${selector} が無い`);
    return;
  }
  if (info.out.length > 0) {
    for (const o of info.out.slice(0, 5)) {
      fail(
        `${label}: viewBox からはみ出し <${o.tag}> "${o.text}" ` +
          `at (${o.x},${o.y}) ${o.w}x${o.h} / viewBox ${info.vb.w}x${info.vb.h}`,
      );
    }
  } else {
    ok(`${label}: 図の要素は viewBox に収まっている`);
  }
}

/** 「在る」ではなく「重なっていない・意味のある位置にある」を見る(HC-138)。 */
async function checkScatterGeometry(page, label) {
  const r = await page.evaluate(() => {
    const svg = document.querySelector(".soundspace__svg");
    if (!svg) return null;
    const pts = [...svg.querySelectorAll("circle")];
    if (pts.length === 0) return { n: 0 };
    const xs = pts.map((c) => +c.getAttribute("cx"));
    const ys = pts.map((c) => +c.getAttribute("cy"));
    const uniq = new Set(pts.map((c) => `${c.getAttribute("cx")},${c.getAttribute("cy")}`));
    return {
      n: pts.length,
      distinct: uniq.size,
      spanX: Math.max(...xs) - Math.min(...xs),
      spanY: Math.max(...ys) - Math.min(...ys),
    };
  });
  if (!r) {
    fail(`${label}: 散布図が無い`);
    return;
  }
  if (r.n === 0) {
    fail(`${label}: 点が 0 個`);
    return;
  }
  // 全部同じ場所に描かれる故障は、要素数では捕まらない
  if (r.distinct < r.n * 0.5) {
    fail(`${label}: 点が重なりすぎ(${r.n} 個中 ${r.distinct} 座標しかない)`);
  } else if (r.spanX < 50 || r.spanY < 50) {
    fail(`${label}: 点が一箇所に潰れている(広がり ${Math.round(r.spanX)}x${Math.round(r.spanY)})`);
  } else {
    ok(`${label}: 点 ${r.n} 個 / 異なる座標 ${r.distinct} / 広がり ${Math.round(r.spanX)}x${Math.round(r.spanY)}`);
  }
}

async function run() {
  const browser = await chromium.launch();
  try {
    for (const width of WIDTHS) {
      console.log(`\n=== 幅 ${width}px ===`);
      const ctx = await browser.newContext({ viewport: { width, height: 900 } });
      const page = await ctx.newPage();

      // 自分の落ち度と、外部サービスの機嫌を分ける。
      // 本文の書体は fonts.googleapis.com から来るので、そこが遅いと
      // ERR_TIMED_OUT が出るが、**それは本アプリの欠陥ではない**
      // (書体が来なくても代替書体で読める)。いっぽう同一オリジンの取得失敗は
      // こちらの欠陥なので、必ず落とす。
      const THIRD_PARTY = ["fonts.googleapis.com", "fonts.gstatic.com"];
      const errors = [];
      const thirdParty = [];
      const bucket = (text) =>
        THIRD_PARTY.some((h) => text.includes(h)) ? thirdParty : errors;

      page.on("pageerror", (e) => bucket(String(e)).push(String(e)));
      page.on("console", (m) => {
        if (m.type() === "error") bucket(m.text()).push(m.text());
      });
      page.on("requestfailed", (r) => {
        const text = `${r.url()} ${r.failure()?.errorText ?? ""}`;
        bucket(text).push(text);
      });

      for (const [path, label] of [
        ["/", "ホーム"],
        ["/map/", "世界地図"],
        ["/space/", "音響空間"],
        ["/models/", "モデル"],
        ["/about/", "About"],
      ]) {
        await goto(page, path);
        await checkOverflow(page, `${label}@${width}`);

        if (path === "/map/") {
          await page.waitForTimeout(900); // world.geojson の読み込みを待つ
          const pins = await page.locator(".worldmap__pin").count();
          if (pins === 0) fail(`世界地図@${width}: 国の点が 0 個`);
          else ok(`世界地図@${width}: 国の点 ${pins} 個`);
          const land = await page.locator(".worldmap__land").count();
          if (land === 0) fail(`世界地図@${width}: 陸地が描かれていない`);
          else ok(`世界地図@${width}: 陸地 ${land} 面`);
          await checkSvgGeometry(page, ".worldmap__svg", `世界地図@${width}`);
        }

        if (path === "/space/") {
          await page.waitForTimeout(500);
          await checkScatterGeometry(page, `音響空間@${width}`);
          await checkSvgGeometry(page, ".soundspace__svg", `音響空間@${width}`);
        }

        // フッタは常に見えていること(フリート共通規約)
        const footer = await page.locator(".site-footer").count();
        if (footer !== 1) fail(`${label}@${width}: フッタが ${footer} 個`);
      }

      if (errors.length) {
        for (const e of errors.slice(0, 5)) fail(`JS エラー@${width}: ${e.slice(0, 160)}`);
      } else {
        ok(`幅 ${width}: 自分側の JS / 取得エラーなし`);
      }
      if (thirdParty.length) {
        // 落とさないが、黙らせもしない。外部が落ちていたことは記録に残す
        notes.push(
          `  ! 幅 ${width}: 外部資源の失敗 ${thirdParty.length} 件` +
            `(書体など。本アプリの欠陥ではないが、参考に残す)`,
        );
      }

      await ctx.close();
    }

    // --- 検品器の陽性対照(T-024 / HC-080)---------------------------------
    if (SELF_TEST) {
      console.log("\n=== 検品器の陽性対照 ===");
      const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
      const page = await ctx.newPage();
      await page.setContent(`
        <style>body{margin:0}</style>
        <div style="width:3000px;height:40px">わざと横に溢れさせた頁</div>
        <svg class="soundspace__svg" viewBox="0 0 100 100" width="400" height="400">
          <text x="180" y="50">はみ出したラベル</text>
          <circle cx="50" cy="50" r="3"></circle>
          <circle cx="50" cy="50" r="3"></circle>
        </svg>
      `);
      const before = failures.length;
      await checkOverflow(page, "対照");
      await checkSvgGeometry(page, ".soundspace__svg", "対照");
      await checkScatterGeometry(page, "対照");
      const caught = failures.length - before;
      // 対照で出た失敗は本物の失敗ではないので取り除く
      failures.length = before;
      if (caught >= 3) {
        ok(`陽性対照: 壊した頁を ${caught} 件で捕まえた(検品器は働いている)`);
      } else {
        fail(`陽性対照: 壊した頁を ${caught} 件しか捕まえなかった。検品器が働いていない`);
      }
      await ctx.close();
    }
  } finally {
    await browser.close();
  }

  console.log("\n" + "=".repeat(56));
  for (const n of notes) console.log(n);
  if (failures.length) {
    console.error(`検品 NG: ${failures.length} 件`);
    process.exit(1);
  }
  console.log("検品 OK");
}

run().catch((e) => {
  // 道具が転んだときに「異常なし」を返さない(HC-041)
  console.error("検品器が失敗しました:", e);
  process.exit(2);
});
