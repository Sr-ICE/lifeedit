# 4.5room サイト管理画面（ローカル専用）

サイトの中身を HTML から切り離して `_dir/content/*.json` に置き、そこをブラウザから編集する仕組み。
HTML を開かずに、持ちものの入れ替え・文面の書き換え・数値の更新・公開までできる。

対象は試作の `_dir/e-rooms.html` と `_dir/e-work.html`。
本番の `index.html` / `carry.html` / `about.html` は触らない。

**`_dir/bags/` は管理画面の対象外**（下の「かばんの中身ページ」を参照）。

---

## 起動

| 方法 | 手順 |
|---|---|
| コントロールパネル | `~/AIタスク/コントロールパネル/` を開き「4.5room サイト管理画面」を起動（ポート 8792）※パネル自体を一度再起動すると項目が出る |
| Claude Code | `.claude/launch.json` の `4.5room-admin` |
| 手動 | `python3 ~/AIタスク/個人用/4.5room-hp/_dir/admin/server.py` |

- 管理画面 … http://127.0.0.1:8792/
- 編集結果の確認 … http://127.0.0.1:8792/_dir/e-rooms.html ／ http://127.0.0.1:8792/_dir/e-work.html

`127.0.0.1` にだけ待ち受ける。外からは見えない。

---

## 3つのボタン

| ボタン | すること | 失敗したとき |
|---|---|---|
| **保存** | 編集した `carry.json` と `site.json` を書き出す。書き込む前に `content/.backup/<名前>.<日時>.json` へ退避する | 何も書かずに理由を出す（分類名や名前が空のときは断る） |
| **最新を取得** | YouTube Data API と note の RSS を取りに行き、`channel.json` / `lab.json` / `notes.json` を作り直す。`measured_at` に実行日を書く | **古い値で上書きしない**。取れなかったファイルは前のまま残し、画面に「× ファイル名: 理由」を出す |
| **公開** | `git add _dir` → `git commit` → `git push`。押す前に確認ダイアログが1回出る | 差分がなければ「変更なし」。push だけ失敗したときは「コミットはできましたが push に失敗しました」と出る |

「最新を取得」は本編の全動画の再生数を数えるので10秒前後かかる。

APIキーは `~/AIタスク/個人用/.secrets/youtube_api_key.txt` を実行時に読むだけ。
JSON・HTML・ログ・リポジトリのどこにも書き出さない。

---

## JSON の構造

`_dir/content/` に5つ。**手で書くもの2つ**と**自動で入るもの3つ**に分かれている。

### 手で書くもの（管理画面から編集する）

**`carry.json`** — 持ちもの

```json
{ "groups": [ { "name": "かばんまわり",
  "items": [ { "brand": "StandardProducts", "name": "スマホショルダー（BL）",
               "changed": "本を持って出るのに、かばんを選ばなくなった。",
               "since": "2026-05", "url": "https://…", "shop": "公式" } ] } ] }
```

- `since` は `YYYY-MM`。サイトでは `2026.05〜` と出る
- `shop` は `Amazon` か `公式`。リンクの読み上げ用の説明（aria-label）が変わる
- 点数と分類は数え直されるので、**間取り 05 の「16点」も自動で追従する**

**`site.json`** — 文面

| キー | 中身 |
|---|---|
| `hero.fact` | 表札の1行 |
| `rooms[]` | 各室（01〜06）の `name` / `summary` / `url`。06 だけ `items[]`（室に並ぶ行）を持つ |
| `carry` | 持ちものセクションの `heading` / `lead` / `notes[]`（※の注記） |
| `work` | お仕事ページ。`bio` `lab_line` `stats_note` `media[]` `accept[]` `ask` `ask_4` `mail{}` |
| `colophon` | 奥付の `copyright` と `links[]`。`only` が `rooms` ならトップだけ、`work` ならお仕事ページだけに出る |

`summary` などに書ける差し込みは次のものだけ。**値が1つでも取れないと、その行は HTML の直書きのまま残る**。

`{subscribers}` `{views}` `{videos}` `{first_upload}` `{measured_at}` `{opened}` `{count}`

### 自動で入るもの（「最新を取得」でだけ書き換わる／手で編集しない）

| ファイル | 取得元 | 中身 |
|---|---|---|
| `channel.json` | YouTube Data API（`UCdxzGFZI8g1MT3vUCprx_vw`） | `subscribers` `views` `videos` `first_upload` `latest[3]` `top[3]` `measured_at` |
| `lab.json` | YouTube Data API（`UCtpqTOuTy5gK_2UZzgikizQ`） | `subscribers` `videos` `opened` `latest[3]` `measured_at` |
| `notes.json` | note RSS（`https://note.com/4_5room/rss`） | `items[4]`（`title` / `date` / `url`）`measured_at` |

---

## かばんの中身ページ（`_dir/bags/`）

持ちものの上に置いた「かばん」の行から飛ぶ先。**回ごとの記録なので JSON にはしていない**
（15点の持ちものと違って、後から中身が入れ替わることがないため）。素のHTMLを直接編集する。

| ファイル | かばん | 出典動画 |
|---|---|---|
| `backpack-t77.html` | tomtoc アーバンEX T77 | `szskMWWj2b4`（2026-08-02）※製品提供 |
| `sling-t21.html` | tomtoc Explorer T21 | `BOpgKhPvgfA`（2026-07-31） |
| `ipadmini.html` | StandardProducts 2wayバッグ｜iPad mini編 | `l301qoGagvk`（2026-05-24） |
| `dokusho-2.html` | 読書かばん その２ | `1slz-DYE6l4`（2026-05-17） |
| `dokusho.html` | 読書かばん | `rylwwKJMskw`（2026-04-19） |

`bag.css` と `bag.js` は5ページ共通。書体は `_dir/fonts/` を見にいく。

**かばんを1本足すとき**

1. いちばん近いページをコピーして `_dir/bags/<名前>.html` を作る
2. 品名・リンク・もくじを、その回のYouTube概要欄「🛒紹介したもの」から写す
3. 冒頭のコメント（出典の動画ID・公開日・取得日）を書き換える
4. `e-rooms.html` の `.bags` に1行足す
5. 既存5ページの「ほかのかばん」にも1行ずつ足す

**守ること**

- 購入リンクは概要欄の `amzn.to/…` をそのまま使う（差し替えるときは `href` だけ）
- アフィリエイト表記（`.note-s`）は消さない。製品提供を受けた回はPR表記も残す
- 再生数などの変動値はこのページに書かない（本番READMEの「数値の扱い」と同じ）
- 期限のあるクーポンを載せたら、コメントに終了日を書いて期限後に消す

---

## 失敗したときの見え方

**サイト側** — `content/*.json` が読めなくても真っ白にならない。
HTML には現在の内容が直書きで残してあり、JSON が取れたときだけ上書きする（プログレッシブエンハンスメント）。
JSON の一部だけ欠けている場合も、欠けたブロックだけ直書きのまま残る。

**管理画面側**

- 保存 … 中身の形が変なら1文字も書かずに断る。上書き前のものは `content/.backup/` に残る（削除はしない）
- 最新を取得 … 取れなかったチャンネル／RSS のファイルは前の値のまま。古い数値を新しい実測日で塗り替えることはしない
- 公開 … `git` が失敗したらその出力をそのまま画面に出す

---

## API

| メソッド | パス | 動作 |
|---|---|---|
| GET | `/` | 管理画面 |
| GET | `/api/content` | `content/` の JSON と、各ファイルの更新日時・git の状態 |
| POST | `/api/save` | `{ "carry": …, "site": … }` を書き出す |
| POST | `/api/refresh` | 取得しに行く。取得元と取得日時を返す |
| POST | `/api/publish` | git add / commit / push |
| GET | `/api/status` | git のブランチと未コミット差分 |

Python は標準ライブラリだけで動く（外部パッケージを入れる必要はない）。
通信は `curl` に任せている（macOS の python は証明書が未設定なことがあるため）。
