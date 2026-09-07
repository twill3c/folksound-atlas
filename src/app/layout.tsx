import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FolkSound Atlas — 世界の民謡を音の構造から眺める",
  description:
    "権利を一件ずつ確かめた世界の民謡を、波形・スペクトログラム・音響特徴量・深層学習 Embedding で並べ直す。「地理的に近い音楽は音響的にも近いのか」を、測って、答えが何であれ画面に出す。",
};

// フリート共通のフッタ規約(koho-lens が正本)。
// MIT License ・ © ・ GitHub ・ 歩き方 ・ 設計図 ・ App Menu をこの並びで、下部固定で出す。
// **並びと項目数を揃えるのであって、文言は各アプリのものを残す。**
const FOOTER = {
  license: "https://github.com/twill3c/folksound-atlas/blob/main/LICENSE",
  repository: "https://github.com/twill3c/folksound-atlas",
  appMenu: "https://app-menu-amber.vercel.app/",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Zen+Old+Mincho:wght@400;700&family=IBM+Plex+Sans+JP:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
        />
      </head>
      <body>
        {children}
        {/* fleet: fixed footer */}
        <footer className="site-footer">
          <div className="site-footer__inner">
            <a href={FOOTER.license}>MIT License</a>
            <span className="site-footer__copy">© 2026 坂田哲朗</span>
            <span className="fsep">・</span>
            <a href={FOOTER.repository}>GitHub</a>
            <span className="fsep">・</span>
            <a href={FOOTER.appMenu}>App Menu</a>
          </div>
        </footer>
      </body>
    </html>
  );
}
