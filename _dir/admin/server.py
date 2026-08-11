#!/usr/bin/env python3
"""4.5room サイトの中身を編集する管理画面（ローカル専用）

  http://127.0.0.1:8792/            管理画面
  http://127.0.0.1:8792/_dir/e-rooms.html   編集結果の確認（同じサーバーが配信する）

  GET  /api/content   _dir/content/ の JSON をまとめて返す
  POST /api/save      carry.json と site.json を書き出す（書き込み前に .backup/ へ退避）
  POST /api/refresh   YouTube API と note RSS から channel/lab/notes.json を作り直す
  POST /api/publish   git add _dir && git commit && git push
  GET  /api/status    git のブランチと未コミット差分

127.0.0.1 にだけ待ち受ける（外部には出さない）。
APIキーは ~/AIタスク/個人用/.secrets/ から実行時に読むだけで、
JSON・HTML・ログ・リポジトリのどこにも書き出さない。
取得に失敗したときは古い値で上書きせず、エラーを返して既存のJSONをそのまま残す。
ファイルの削除は行わない（上書き前の退避のみ）。
"""

import http.server
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # _dir/admin
DIR = HERE.parent                               # _dir
ROOT = DIR.parent                               # 4.5room-hp（git リポジトリ）
CONTENT = DIR / "content"
BACKUP = CONTENT / ".backup"

HOST = "127.0.0.1"
PORT = int(os.environ.get("ADMIN_PORT", "8792"))

KEY_FILE = Path.home() / "AIタスク" / "個人用" / ".secrets" / "youtube_api_key.txt"
CHANNEL_ID = "UCdxzGFZI8g1MT3vUCprx_vw"          # 本編
LAB_ID = "UCtpqTOuTy5gK_2UZzgikizQ"              # Lab
NOTE_RSS = "https://note.com/4_5room/rss"
NOTE_URL = "https://note.com/4_5room/"
YT_API = "https://www.googleapis.com/youtube/v3/"

FILES = ["site", "carry", "channel", "lab", "notes"]   # 読み出す対象
EDITABLE = ["site", "carry"]                            # 管理画面から書き換える対象
JST = timezone(timedelta(hours=9))


def now_jst():
    return datetime.now(timezone.utc).astimezone(JST)


# ── JSON の読み書き ────────────────────────────────────

def read_json(name):
    path = CONTENT / f"{name}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{name}.json が壊れています（{e}）")


def file_meta(name):
    path = CONTENT / f"{name}.json"
    if not path.is_file():
        return {"exists": False}
    stamp = datetime.fromtimestamp(path.stat().st_mtime, JST)
    return {"exists": True, "modified": stamp.strftime("%Y-%m-%d %H:%M")}


def write_json(name, data):
    """上書き前に .backup/<name>.<timestamp>.json へ退避してから書く。"""
    path = CONTENT / f"{name}.json"
    CONTENT.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        stamp = now_jst().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, BACKUP / f"{name}.{stamp}.json")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    return str(path)


# ── 取得（YouTube Data API / note RSS）─────────────────

def api_key():
    if os.environ.get("YT_API_KEY"):
        return os.environ["YT_API_KEY"].strip()
    if not KEY_FILE.is_file():
        raise RuntimeError(f"APIキーが見つかりません（{KEY_FILE}）")
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("APIキーが空です")
    return key


def scrub(text, key):
    """エラー文にキーが混ざらないようにする。"""
    return text.replace(key, "***") if key else text


def curl(url, key="", timeout=40):
    """通信は curl に任せる（macOS の python は証明書が未設定なことがあるため）。"""
    res = subprocess.run(
        ["curl", "-fsS", "--max-time", str(timeout), url],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(scrub(res.stderr.strip() or f"取得失敗（curl {res.returncode}）", key))
    return res.stdout


def yt(endpoint, key, **params):
    params["key"] = key
    url = YT_API + endpoint + "?" + urllib.parse.urlencode(params)
    try:
        return json.loads(curl(url, key))
    except json.JSONDecodeError:
        raise RuntimeError(f"YouTube API の応答が読めませんでした（{endpoint}）")


def uploads_of(channel, key):
    """アップロード一覧（新しい順）"""
    playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    out, token = [], None
    while True:
        extra = {"pageToken": token} if token else {}
        page = yt("playlistItems", key, part="contentDetails,snippet",
                  playlistId=playlist, maxResults=50, **extra)
        for it in page.get("items", []):
            published = it["contentDetails"].get("videoPublishedAt")
            if not published:            # 非公開・削除済みはスキップ
                continue
            out.append({
                "id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "published": published,
            })
        token = page.get("nextPageToken")
        if not token:
            break
    out.sort(key=lambda v: v["published"], reverse=True)
    return out


def channel_of(cid, key):
    res = yt("channels", key, part="snippet,statistics,contentDetails", id=cid)
    items = res.get("items") or []
    if not items:
        raise RuntimeError(f"チャンネルが取得できませんでした（{cid}）")
    return items[0]


def refresh_channel(key):
    """本編。登録者・総再生・本数・初投稿・最新3本・よく見られている3本。"""
    c = channel_of(CHANNEL_ID, key)
    stats = c["statistics"]
    ups = uploads_of(c, key)
    if not ups:
        raise RuntimeError("アップロード一覧が空でした")

    views = {}
    ids = [v["id"] for v in ups]
    for i in range(0, len(ids), 50):
        res = yt("videos", key, part="statistics", id=",".join(ids[i:i + 50]))
        for it in res.get("items", []):
            views[it["id"]] = int(it["statistics"].get("viewCount", 0))

    top = sorted(ups, key=lambda v: views.get(v["id"], 0), reverse=True)[:3]

    return {
        "_comment": "YouTube Data API の実測値。管理画面の「最新を取得」で再生成する。手で編集しない。",
        "measured_at": now_jst().strftime("%Y-%m-%d"),
        "id": CHANNEL_ID,
        "title": c["snippet"]["title"],
        "url": "https://www.youtube.com/@4.5room",
        "subscribers": int(stats["subscriberCount"]),
        "views": int(stats["viewCount"]),
        "videos": int(stats["videoCount"]),
        "first_upload": ups[-1]["published"][:10],
        "latest": [{"id": v["id"], "title": v["title"], "published": v["published"][:10]} for v in ups[:3]],
        "top": [{"id": v["id"], "title": v["title"], "published": v["published"][:10],
                 "views": views.get(v["id"])} for v in top],
    }


def refresh_lab(key):
    c = channel_of(LAB_ID, key)
    stats = c["statistics"]
    ups = uploads_of(c, key)
    return {
        "_comment": "YouTube Data API の実測値（Lab）。管理画面の「最新を取得」で再生成する。手で編集しない。",
        "measured_at": now_jst().strftime("%Y-%m-%d"),
        "id": LAB_ID,
        "title": c["snippet"]["title"],
        "url": f"https://www.youtube.com/channel/{LAB_ID}",
        "subscribers": int(stats["subscriberCount"]),
        "videos": int(stats["videoCount"]),
        "opened": c["snippet"]["publishedAt"][:7],
        "latest": [{"id": v["id"], "title": v["title"], "published": v["published"][:10]} for v in ups[:3]],
    }


def refresh_notes():
    xml = curl(NOTE_RSS)
    try:
        tree = ET.fromstring(xml)
    except ET.ParseError as e:
        raise RuntimeError(f"note の RSS が読めませんでした（{e}）")
    items = tree.findall(".//item")
    if not items:
        raise RuntimeError("note の RSS に記事がありませんでした")

    out = []
    for it in items[:4]:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        if not (title and link and pub):
            raise RuntimeError("note の RSS に欠けている項目がありました")
        date = parsedate_to_datetime(pub).astimezone(JST).strftime("%Y-%m-%d")
        out.append({"title": title, "date": date, "url": link})

    return {
        "_comment": f"note の RSS（{NOTE_RSS}）から上位4本。管理画面の「最新を取得」で再生成する。手で編集しない。",
        "measured_at": now_jst().strftime("%Y-%m-%d"),
        "url": NOTE_URL,
        "items": out,
    }, len(items)


def do_refresh():
    """取れたものだけ書き、取れなかったものは既存JSONをそのまま残す。"""
    stamp = now_jst().strftime("%Y-%m-%d %H:%M")
    sources, errors = [], []

    try:
        key = api_key()
    except RuntimeError as e:
        key = None
        errors.append(f"YouTube: {e}")

    if key:
        for name, fn, label in (("channel", refresh_channel, "YouTube Data API（本編）"),
                                ("lab", refresh_lab, "YouTube Data API（Lab）")):
            try:
                data = fn(key)
                write_json(name, data)
                sources.append({
                    "file": f"{name}.json", "from": label, "at": stamp,
                    "values": {k: data[k] for k in ("subscribers", "videos") if k in data},
                })
            except Exception as e:                       # noqa: BLE001
                errors.append(f"{name}.json: {scrub(str(e), key)}")

    try:
        data, total = refresh_notes()
        write_json("notes", data)
        sources.append({"file": "notes.json", "from": f"note RSS（{NOTE_RSS}／{total}本中4本）",
                        "at": stamp, "values": {"items": len(data["items"])}})
    except Exception as e:                               # noqa: BLE001
        errors.append(f"notes.json: {e}")

    return {
        "ok": not errors,
        "measured_at": now_jst().strftime("%Y-%m-%d"),
        "sources": sources,
        "errors": errors,
        "msg": ("最新を取得しました" if not errors else
                "取得できなかったものがあります（そのファイルは前の値のままです）"),
    }


# ── git ────────────────────────────────────────────────

def git(*args, timeout=120):
    return subprocess.run(["git"] + list(args), cwd=str(ROOT),
                          capture_output=True, text=True, timeout=timeout)


def git_status():
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    res = git("status", "--porcelain", "--", "_dir")
    changes = [line[3:] for line in res.stdout.splitlines() if line.strip()]
    return {"branch": branch, "dirty": bool(changes), "changes": changes[:50]}


def git_publish():
    add = git("add", "--", "_dir")
    if add.returncode:
        return {"ok": False, "error": (add.stderr or add.stdout).strip()}

    staged = git("diff", "--cached", "--name-only", "--", "_dir").stdout.strip()
    if not staged:
        return {"ok": True, "changed": False, "msg": "変更なし（公開するものがありません）"}

    msg = "content: サイトの中身を更新（管理画面 " + now_jst().strftime("%Y-%m-%d %H:%M") + "）"
    com = git("commit", "-m", msg, "--", "_dir")
    if com.returncode:
        return {"ok": False, "error": (com.stdout + com.stderr).strip()}

    push = git("push")
    if push.returncode:
        return {"ok": False, "committed": True,
                "error": "コミットはできましたが push に失敗しました：" + (push.stderr or push.stdout).strip()}

    return {"ok": True, "changed": True, "msg": "公開しました",
            "commit": msg, "files": staged.splitlines()}


# ── HTTP ───────────────────────────────────────────────

class Handler(http.server.SimpleHTTPRequestHandler):
    """静的配信はリポジトリ全体（編集結果をそのまま確認できるように）。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def guess_type(self, path):
        ctype = super().guess_type(path)
        if ctype.startswith("text/") and "charset=" not in ctype:
            return ctype + "; charset=utf-8"
        if ctype == "application/json":
            return "application/json; charset=utf-8"
        return ctype

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.partition("?")[0]

        if path in ("/", "/index.html", "/admin", "/admin/"):
            page = HERE / "index.html"
            if not page.is_file():
                self.send_error(404, "admin/index.html がありません")
                return
            body = page.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/content":
            try:
                content = {name: read_json(name) for name in FILES}
            except RuntimeError as e:
                self._json({"ok": False, "error": str(e)}, 500)
                return
            self._json({
                "ok": True,
                "content": content,
                "meta": {name: file_meta(name) for name in FILES},
                "editable": EDITABLE,
                "git": git_status(),
            })
            return

        if path == "/api/status":
            self._json({"ok": True, "git": git_status(),
                        "meta": {name: file_meta(name) for name in FILES}})
            return

        if path.startswith("/api/"):
            self._json({"ok": False, "error": "不明なエンドポイントです"}, 404)
            return

        super().do_GET()

    def do_POST(self):
        path = self.path.partition("?")[0]
        if path not in ("/api/save", "/api/refresh", "/api/publish"):
            self._json({"ok": False, "error": "不明なエンドポイントです"}, 404)
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "JSONが不正です"}, 400)
            return

        try:
            if path == "/api/save":
                result = do_save(body)
            elif path == "/api/refresh":
                result = do_refresh()
            else:
                result = git_publish()
        except Exception as e:                           # noqa: BLE001 — 理由をそのまま画面に返す
            result = {"ok": False, "error": str(e)}

        result["git"] = git_status()
        result["meta"] = {name: file_meta(name) for name in FILES}
        self._json(result)

    def log_message(self, fmt, *args):
        if args and "/api/" in str(args[0]):
            sys.stderr.write("  %s\n" % (fmt % args))


def do_save(body):
    """carry.json と site.json を書き出す。中身の形だけ最低限確かめる。"""
    written, skipped = [], []
    for name in EDITABLE:
        if name not in body:
            skipped.append(name)
            continue
        data = body[name]
        if not isinstance(data, dict):
            return {"ok": False, "error": f"{name}.json の形が違います（オブジェクトではありません）"}
        if name == "carry":
            groups = data.get("groups")
            if not isinstance(groups, list) or not groups:
                return {"ok": False, "error": "持ちものの分類が空です。1つ以上必要です"}
            for g in groups:
                if not isinstance(g, dict) or not str(g.get("name", "")).strip():
                    return {"ok": False, "error": "分類名が空の分類があります"}
                if not isinstance(g.get("items"), list):
                    return {"ok": False, "error": f"「{g.get('name')}」の中身が読めません"}
                for it in g["items"]:
                    if not str(it.get("name", "")).strip():
                        return {"ok": False, "error": f"「{g.get('name')}」に名前が空の項目があります"}
        if name == "site":
            if not isinstance(data.get("rooms"), list):
                return {"ok": False, "error": "site.json の rooms が読めません"}
        written.append(write_json(name, data))

    if not written:
        return {"ok": False, "error": "保存するものがありませんでした"}
    return {"ok": True, "msg": "保存しました", "written": written, "skipped": skipped}


def main():
    if not CONTENT.is_dir():
        print(f"content フォルダがありません: {CONTENT}", file=sys.stderr)
        return 1
    try:
        server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        print(f"ポート {PORT} は既に使われています。起動済みのウィンドウをご確認ください。")
        return 1

    print(f"  4.5room 管理画面 : http://{HOST}:{PORT}/")
    print(f"  サイトの確認     : http://{HOST}:{PORT}/_dir/e-rooms.html")
    print(f"  content          : {CONTENT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
