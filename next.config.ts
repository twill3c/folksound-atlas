import type { NextConfig } from "next";

// 静的書き出しのみ。サーバ関数も cron も一つも持たない(SPEC N-01 / N-02 / F-16)。
// 学習・特徴量抽出・UMAP はすべて手元で行い、その結果の JSON だけを配る。
// **next build は外部へ取りに行かない** — 行けばビルドが外部の生死に依存する。
const nextConfig: NextConfig = {
  output: "export",
  reactStrictMode: true,
  trailingSlash: true,
};

export default nextConfig;
