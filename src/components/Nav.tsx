import Link from "next/link";

const ITEMS: { href: string; label: string }[] = [
  { href: "/", label: "ホーム" },
  { href: "/map/", label: "世界地図" },
  { href: "/space/", label: "音響空間" },
  { href: "/distance/", label: "地理と音響" },
  { href: "/models/", label: "モデル" },
  { href: "/about/", label: "この地図帳について" },
];

export default function Nav({ current }: { current: string }) {
  return (
    <nav className="nav" aria-label="主ナビゲーション">
      <div className="nav__inner">
        {ITEMS.map((it) => {
          const active = it.href === current;
          return (
            <Link
              key={it.href}
              href={it.href}
              aria-current={active ? "page" : undefined}
            >
              {it.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
