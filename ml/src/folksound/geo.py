"""geo.py — 地理距離(F-12 / SPEC §5.5)。

球近似の大円距離(haversine)を使う。楕円体(Vincenty / geodesic)にしないのは、
**こちらの座標がそもそも国の代表点**だからである。粒度が国単位なのに
距離だけ数十メートルの精度で出しても、その精度は嘘になる(SPEC §5.5)。
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0  # 平均半径(IUGG)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """2 点間の大円距離を km で返す。

    `asin` の引数は丸め誤差で 1 をわずかに超えうるので、必ずクランプする
    (超えると定義域外で NaN になり、**非有限が黙って伝播する**)。
    """
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    a = min(1.0, max(0.0, a))
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
