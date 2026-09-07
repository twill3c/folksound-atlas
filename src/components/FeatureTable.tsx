import type { FeatureRow } from "@/lib/types";

/**
 * 従来型音響特徴量の表。
 * **単位と意味を書く。** 数だけ並べても読めないし、
 * 読めない数に良し悪しの色を付けてはならない(HC-079)。
 */
const ROWS: {
  key: keyof FeatureRow;
  label: string;
  unit: string;
  what: string;
  digits: number;
}[] = [
  { key: "rms", label: "実効値 (RMS)", unit: "", what: "全体の強さ", digits: 4 },
  { key: "zcr", label: "ゼロ交差率", unit: "/サンプル", what: "高い音・雑音ほど大きい", digits: 4 },
  { key: "spectral_centroid", label: "スペクトル重心", unit: "Hz", what: "音の明るさの目安", digits: 1 },
  { key: "spectral_bandwidth", label: "スペクトル帯域幅", unit: "Hz", what: "重心まわりの広がり", digits: 1 },
  { key: "spectral_rolloff", label: "ロールオフ", unit: "Hz", what: "エネルギーの 85% が収まる上限", digits: 1 },
  { key: "tempo", label: "推定テンポ", unit: "BPM", what: "拍の速さの推定値", digits: 1 },
];

export default function FeatureTable({ f }: { f: FeatureRow }) {
  return (
    <div className="scrollx">
      <table className="ftable">
        <thead>
          <tr>
            <th>特徴量</th>
            <th className="num">値</th>
            <th>単位</th>
            <th>何を見ているか</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((r) => {
            const v = f[r.key];
            return (
              <tr key={String(r.key)}>
                <td>{r.label}</td>
                <td className="num">
                  {typeof v === "number" ? v.toFixed(r.digits) : "—"}
                </td>
                <td>{r.unit || "—"}</td>
                <td>{r.what}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
