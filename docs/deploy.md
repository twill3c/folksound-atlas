# デプロイ手順

## 構成

```
GitHub → Vercel → Next.js build (output: "export") → 静的配信
```

- **サーバー関数 0 / cron 0 / DB 0。** 課金経路を持たない(SPEC N-01)
- 学習・特徴量抽出・UMAP はすべて手元で行い、その結果の JSON だけを配る(SPEC N-02)
- **音源は配らない。** 再生は Wikimedia Commons の原本を `<audio src>` で直接指す

## ETL の順序

`public/data/` の中身は、次の順に作る。前の出力が次の入力になるので順序は動かせない。

```bash
.venv/Scripts/python.exe ml/scripts/01_discover.py --max-depth 2
.venv/Scripts/python.exe ml/scripts/02_fetch_metadata.py
.venv/Scripts/python.exe ml/scripts/02b_rights_summary.py
.venv/Scripts/python.exe ml/scripts/03_select_and_download.py \
    --per-country 20 --min-per-country 1 --max-bytes 12000000
.venv/Scripts/python.exe ml/scripts/04_geocode.py
.venv/Scripts/python.exe ml/scripts/05_preprocess_features.py --workers 6
.venv/Scripts/python.exe ml/scripts/06_train.py --epochs-ae 8 --epochs-clf 8
.venv/Scripts/python.exe ml/scripts/07_embeddings.py
.venv/Scripts/python.exe ml/scripts/08_project_and_similar.py
.venv/Scripts/python.exe ml/scripts/09_analysis.py
.venv/Scripts/python.exe ml/scripts/11_prepare_map.py
.venv/Scripts/python.exe ml/scripts/10_export.py
```

### 外部サービスの癖(実測 2026-09-07〜08)

- **`upload.wikimedia.org` は User-Agent を見る。** 連絡先が実在の URL でない UA だと
  数件で HTTP 429 になり、600 秒待てと言われる。**間隔を空けても直らない。**
  `ml/scripts/*.py` の `UA` にはリポジトリの URL を入れてある。ここを空にしない
- **`commons.wikimedia.org/w/api.php` と `upload.wikimedia.org` は別枠**で、
  後者のほうが厳しい
- **Wikidata Query Service は障害時に 1 req/min まで絞る。**
  `04_geocode.py` は一括クエリ 1 回で済むように書いてある。ループで叩かない
- **`www.loc.gov` は使えない**(Cloudflare のチャレンジ配下・JSON API は 403)

## 手元での確認

```bash
.venv/Scripts/python.exe -m pytest -q     # 単体 + 出荷物の検証
python harness/text_hygiene.py            # 字種・制御文字(G-10)
npm run typecheck
npm run build                             # out/ に静的サイトができる
npx serve out -l 3000 &                   # 配られる木そのものを立てる
npm run verify:browser -- --self-test     # 実ブラウザ検品(G-12)
```

**`npm run build` が通ることと、テストが緑であることは別である**(HC-062)。
検証段では必ずビルドまで通す。

## Vercel

**本番: https://folksound-atlas.vercel.app**

```bash
vercel deploy --prod --yes          # 通常はこれでよい(リモートでビルドされる)
```

- Framework Preset: Next.js / Output Directory: `out` / 環境変数: 不要
- GitHub 連携済み。`main` への push でも本番が更新される

### 除外設定は **先頭 `/` で固定して書く**(実測 2026-09-08〜09)

`.vercelignore` の無印パターンは `.gitignore` と同じ意味で**どの階層にも当たる**。
`data/` と書くと `public/data/` まで消える。`public/data/*.json` は画面が読む本体で、
`generateStaticParams()` も `songs.json` を読むので、消えると

```
Page "/song/[id]" is missing "generateStaticParams()"
```

で落ちる。**Next は「ファイルが無い」ではなく「関数が無い」と言う**ので、
コードの誤りに見える点に注意。真因はデータが届いていないことだった。

音源(`data/raw/audio/` 881MB)と `.venv` を送ると `Upload aborted` になるので、
除外設定そのものは最初のデプロイ前に必要である。**消しすぎず、消し漏らさず。**

### prebuilt デプロイ(必要なときだけ)

```bash
vercel build --prod --yes
vercel deploy --prebuilt --prod --yes
```

手元で検品した木をそのまま配れる利点はあるが、`.vercel/output` が 35MB / 1000 ファイルを
超えたあたりから `Upload aborted` が出やすい(実測 2026-09-09)。
**常用しない。** リモートビルドが通らないときの逃げ道として置いておく。

> **注意:** 2026-09-08 の時点では「角括弧を含む動的ルートが転送側で落ちる」と診断して
> prebuilt を常用にしていたが、**これは誤診だった**(HC-229 の訂正を参照)。
> 回避策が効いたことを診断の裏づけにしてはならない。

## 本番に対する検品

`out/` を見て緑でも、本番で同じとは限らない。**本番の URL に対しても検品を回す。**

```bash
node scripts/verify-browser.mjs --base https://folksound-atlas.vercel.app --self-test
```

`public/data/` は Git に入っているので、Vercel 側で ETL は走らない。
**データを更新したいときは、手元で ETL を回して `public/data/` を commit する。**

## 更新するとき

音源の追加・入れ替えをしたら、`01` から順に通し直す。
`03_select_and_download.py` は既にある音源を再取得しないので、途中から流しても安全。
ただし **`--seed` を変えると選抜が変わる**ので、比較を続けたいときは固定したままにする。
