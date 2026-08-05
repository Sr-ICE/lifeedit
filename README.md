# 4.5room 公式サイト（4-5room.com）

YouTubeチャンネル **4.5room** の公式サイト。素のHTML/CSSのみ。ビルド不要。
GitHub Pages（`Sr-ICE/lifeedit` の `main` ブランチ / ルート）で配信する。

記事メディアではなく、**機能特化のミニサイト**として作っている。

| 役割 | 置き場所 |
|------|---------|
| ① 案件交渉用の実績・問い合わせ | `about.html` |
| ② アフィリエイトリンクの終着点 | `carry.html` / `videos/*.html` |
| ③ いま持ち歩いている物の一覧 | `carry.html` |
| 読みもの | note の記事へ外部リンクするだけ（トップの「読みもの」欄） |

---

## ファイル構成

```
index.html            トップ（ヒーロー／持ち物抜粋／読みもの／動画／about／問い合わせ）
carry.html            いま持ち歩いているもの 全一覧（16点）
about.html            実績・メディア掲載・お受けできること・お仕事のご相談
videos/template.html  「この動画に登場した物」ページの雛形
                      （読書かばんその２ = 1slz-DYE6l4 の実データ版サンプル）
assets/
  site.css            全ページ共通スタイル
  site.js             stats.json の流し込み／経過月数の計算／動画リスト生成
  stats.json          YouTube実測値（自動生成。手で編集しない）
  photos/             写真（_mock/photos からコピー）
  logo-4.5room.png
scripts/
  update_stats.sh     stats.json を YouTube Data API で更新する
CNAME                 4-5room.com
.nojekyll             _ で始まるディレクトリも配信するため
_mock/                デザイン検討用のモック（本組みのベースは f-time.html）
_concepts/            初期コンセプト案
_old/index.html       旧トップページ（退避。削除していない）
```

---

## デザインの決めごと（崩さないこと）

モックF「使い込んだ時間が主役」の静けさを保つための取り決め。

1. **YouTubeのサムネイルを並べない。**
   サムネには「安いのに高性能すぎる」「※売り切れ必至」のような大きな煽り文字が
   焼き込まれている。グレースケールにしても文字は消えないので、トップ・about・
   動画ページの動画一覧はすべて**タイトル＋日付（＋再生数）だけの行**にしている。
   動画ページの埋め込みプレイヤーだけは例外（動画そのものなので）。
2. **空の灰色ボックスを並べない。**
   写真のない品は写真枠を置かず、整然としたリスト行で見せる（`carry.html` の
   `.things`）。写真は「その品を写したもの」がある場合だけ使う。
3. **実績数値を誇示しない。**
   トップでは小さな1行、about.html でも `.facts` の静かな行で置く。
   「〜突破」「!」などの煽り表現は使わない。
4. アクセントカラーはティール（`--accent`）1色だけ。影・グラデーション・角丸は使わない。
   構造は1pxのヘアラインと余白で作る。
5. トーンは常体（〜だ／〜している）。ただし**企業向けの文面（about.html の
   「お受けできること」「お仕事のご相談」、注意書き）は敬体**にしている。

### 表示と実体を一致させる

トップの「常用しているもの **16** 点」は `carry.html` に載っている品数と同じ数字。
**carry.html の品を増減したら、index.html の数字も必ず直すこと。**
（この数値だけはAPIで測れないため直書きしている）

---

## 数値の扱い（重要なルール）

**登録者数・再生数・本数などの変動値をHTMLに直書きしないこと。**

すべて `assets/stats.json` に入れ、各ページは `data-stat="..."` の属性で読み込んでいる。
数値を更新したいときは次を実行するだけでよい。

```bash
./scripts/update_stats.sh
git add assets/stats.json && git commit -m "Update stats" && git push
```

- APIキーは `~/AIタスク/個人用/.secrets/youtube_api_key.txt` を読む（リポジトリには入れない）。
  環境変数 `YT_API_KEY` でも指定できる。
- `stats.json` には実測日（`measured_at`）が必ず入り、about.html に表示される。
- 取得に失敗した場合、ページは数値を「—」のままにする（古い数値を出さないため）。

### 「直近90日の再生数」について

`recent_90d.views_sum` は **「直近90日に公開した動画の再生数の合計」**。
YouTube Studio の「直近90日の総再生回数」とは別物（あちらは OAuth が必要な
YouTube Analytics API でしか取れない）。about.html のラベルもその通りに書いてある。
言い換えないこと。

---

## 本人がやる残作業

### 1. Cloudflare に DNS レコードを2つ追加

Cloudflare ダッシュボード → `4-5room.com` → DNS → レコードを追加。

| Type | Name | Target | Proxy | TTL |
|------|------|--------|-------|-----|
| CNAME | `@` | `sr-ice.github.io` | **DNS only（グレーの雲）** | Auto |
| CNAME | `www` | `sr-ice.github.io` | **DNS only（グレーの雲）** | Auto |

- apex（`@`）に CNAME を置けるのは Cloudflare が CNAME フラットニングに対応しているため。
- **最初は必ず DNS only（グレー雲）にする。** オレンジ雲（プロキシ）のままだと
  GitHub が Let's Encrypt 証明書を発行できず、HTTPSが有効にならない。
  証明書が出たあとにプロキシへ切り替えたい場合は、SSL/TLS の暗号化モードを
  **Full** 以上にしてから行うこと（Flexible はリダイレクトループになる）。
- 反映確認：

  ```bash
  dig +short 4-5room.com
  dig +short www.4-5room.com
  ```

### 2. GitHub Pages 側のカスタムドメイン設定

`CNAME` ファイル（中身 `4-5room.com`）を push した時点で、GitHub が自動的に
カスタムドメインを設定する。**通常は追加の操作は不要。**

反映されたかの確認：

```bash
gh api repos/Sr-ICE/lifeedit/pages --jq '{cname,status,https_enforced,html_url}'
```

`cname` が `4-5room.com` になっていれば設定済み。
なっていない場合だけ、次のどちらかで設定する。

- 画面から：GitHub → `Sr-ICE/lifeedit` → Settings → Pages → Custom domain に
  `4-5room.com` を入れて Save
- コマンドから：

  ```bash
  gh api -X PUT repos/Sr-ICE/lifeedit/pages -f cname='4-5room.com'
  ```

### 3. HTTPS を有効にする

DNSが通ると GitHub が証明書を発行する（数分〜最大24時間）。
発行後、Settings → Pages の **Enforce HTTPS** にチェックを入れる。
コマンドなら：

```bash
gh api -X PUT repos/Sr-ICE/lifeedit/pages -F https_enforced=true
```

証明書の発行前にチェックするとエラーになるので、その場合は時間をおいて再実行する。

### 4.（任意）Cloudflare Email Routing

`info@4-5room.com` のような独自ドメインのアドレスを作って Gmail に転送できる。
Cloudflare → Email → Email Routing から設定（MX と TXT が自動で追加される）。
現状サイトに載せている連絡先は `4.5roomsrice@gmail.com` なので、
切り替える場合は `index.html` と `about.html` の `mailto:` も直すこと。

### 5.（任意）持ち物の「使用期間」を実際の日付に直す

`carry.html` などの `data-since="2026-05"` は、**その道具を動画で紹介した月**を入れている
（各ページにもその旨を明記している）。実際に使い始めた月に書き換えれば、
そのまま「使い込んだ期間」の表示になる。JSが自動で経過月数を計算する。

---

## ローカルで確認する

`stats.json` を `fetch` で読むため、**ファイルを直接ダブルクリックで開くと数値が出ない**
（file:// は CORS で弾かれる）。簡易サーバーを立てて確認すること。

```bash
cd ~/AIタスク/個人用/4.5room-hp
python3 -m http.server 8765
# → http://localhost:8765/
```

同じ理由で、`videos/template.html` を `file://` で開くと YouTube の埋め込みが
**エラー153**（Referer が送られないため埋め込み拒否）になる。
埋め込みコード自体は正しいので、ローカルサーバー経由（`http://localhost:8765/...`）でも
本番（`https://4-5room.com/...`）でも正常に再生される。確認済み。

---

## アフィリエイトリンクについて

- `carry.html` / `videos/template.html` の購入リンクは、**YouTube概要欄に載っている
  Amazonアソシエイトの短縮リンク（amzn.to/...）をそのまま使っている。**
- ASP（レントラックス等）のリンクに差し替える場合は、`<a class="buy">` の `href` だけを
  置き換えればよい。差し替え箇所は各ファイル冒頭のコメントに書いてある。
- **アフィリエイト表記（`.disclosure` のブロック）は消さないこと**（ステマ規制対応）。

---

## Phase 2 以降

- `videos/template.html` を雛形に、動画1本 = 1ページを自動生成する。
  生成元データは `~/AIタスク/個人用/yt-to-article/out/<video_id>/meta.json`
  （概要欄・Amazonリンク・PR判定を保持している）。
- 過去の上位20〜30本を在庫としてページ化する。
- 10月のプライム感謝祭前にセールまとめページ。
