#!/usr/bin/env bash
#
# assets/stats.json を YouTube Data API の実測値で更新する。
#
#   使い方:  ./scripts/update_stats.sh
#
# サイト上の登録者数・再生数・動画本数はすべてこの JSON 経由で表示している。
# HTML に数値を直書きしない（古い数字が残るのを防ぐため）。
#
# APIキーはリポジトリの外（~/AIタスク/個人用/.secrets/）に置く。コミットしないこと。
# 環境変数 YT_API_KEY があればそちらを優先する。
#
set -euo pipefail

CHANNEL_ID="UCdxzGFZI8g1MT3vUCprx_vw"
KEY_FILE="${HOME}/AIタスク/個人用/.secrets/youtube_api_key.txt"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/assets/stats.json"

API_KEY="${YT_API_KEY:-}"
if [ -z "${API_KEY}" ]; then
  if [ ! -f "${KEY_FILE}" ]; then
    echo "エラー: APIキーが見つかりません: ${KEY_FILE}" >&2
    echo "       環境変数 YT_API_KEY でも指定できます。" >&2
    exit 1
  fi
  API_KEY="$(tr -d '\n\r' < "${KEY_FILE}")"
fi

export API_KEY CHANNEL_ID OUT

python3 - <<'PY'
import json, os, subprocess, sys, urllib.parse
from datetime import datetime, timezone, timedelta

API = "https://www.googleapis.com/youtube/v3/"
KEY = os.environ["API_KEY"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
OUT = os.environ["OUT"]


def get(endpoint, **params):
    """通信は curl に任せる（macOS の python は証明書が未設定なことがあるため）。"""
    params["key"] = KEY
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    res = subprocess.run(["curl", "-fsS", "--max-time", "30", url],
                         capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"取得失敗: {endpoint} — {res.stderr.strip()}")
    return json.loads(res.stdout)


# --- チャンネル本体 -------------------------------------------------------
ch = get("channels", part="snippet,statistics,contentDetails", id=CHANNEL_ID)
items = ch.get("items") or []
if not items:
    sys.exit("取得失敗: チャンネルが取得できませんでした（IDまたはAPIキーを確認）")
c = items[0]
stats = c["statistics"]
uploads = c["contentDetails"]["relatedPlaylists"]["uploads"]

# --- アップロード一覧（全件）---------------------------------------------
uploads_list, token = [], None
while True:
    page = get("playlistItems", part="contentDetails,snippet",
               playlistId=uploads, maxResults=50,
               **({"pageToken": token} if token else {}))
    for it in page.get("items", []):
        cd = it["contentDetails"]
        published = cd.get("videoPublishedAt")
        if not published:          # 非公開・削除済みはスキップ
            continue
        uploads_list.append({
            "id": cd["videoId"],
            "title": it["snippet"]["title"],
            "published": published,
        })
    token = page.get("nextPageToken")
    if not token:
        break

uploads_list.sort(key=lambda v: v["published"], reverse=True)

now = datetime.now(timezone.utc)
since_90 = now - timedelta(days=90)


def dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


recent_90 = [v for v in uploads_list if dt(v["published"]) >= since_90]

# --- 全動画の再生数（50件ずつ）--------------------------------------------
views = {}
ids = [v["id"] for v in uploads_list]
for i in range(0, len(ids), 50):
    res = get("videos", part="statistics", id=",".join(ids[i:i + 50]))
    for it in res.get("items", []):
        views[it["id"]] = int(it["statistics"].get("viewCount", 0))

top = sorted(uploads_list, key=lambda v: views.get(v["id"], 0), reverse=True)[:5]

latest = [{
    "id": v["id"],
    "title": v["title"],
    "published": v["published"][:10],
    "views": views.get(v["id"]),
} for v in uploads_list[:12]]

first = uploads_list[-1] if uploads_list else None

data = {
    "_comment": "YouTube Data API の実測値。scripts/update_stats.sh で再生成する。手で編集しない。",
    "measured_at": now.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"),
    "channel": {
        "id": CHANNEL_ID,
        "title": c["snippet"]["title"],
        "url": "https://www.youtube.com/@4.5room",
        "subscribers": int(stats["subscriberCount"]),
        "views_total": int(stats["viewCount"]),
        "videos": int(stats["videoCount"]),
        "first_video_published": first["published"][:10] if first else None,
    },
    # 注: YouTube Analytics（Studio）の「直近90日の総再生数」は OAuth が必要なため
    #     Data API では取得できない。ここは「直近90日に公開した動画の再生数合計」。
    #     ラベルもその通りに表示すること。
    "recent_90d": {
        "since": since_90.strftime("%Y-%m-%d"),
        "video_count": len(recent_90),
        "views_sum": sum(views.get(v["id"], 0) for v in recent_90),
    },
    "latest_videos": latest,
    "top_videos": [{
        "id": v["id"],
        "title": v["title"],
        "published": v["published"][:10],
        "views": views.get(v["id"]),
    } for v in top],
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"更新しました: {OUT}")
print(f"  実測日        : {data['measured_at']}")
print(f"  登録者        : {data['channel']['subscribers']:,}")
print(f"  総再生         : {data['channel']['views_total']:,}")
print(f"  動画本数       : {data['channel']['videos']:,}")
print(f"  初投稿         : {data['channel']['first_video_published']}")
print(f"  直近90日公開分 : {data['recent_90d']['video_count']}本 / "
      f"{data['recent_90d']['views_sum']:,} 回")
print("  よく見られた動画:")
for v in data["top_videos"][:3]:
    print(f"    {v['views']:>9,}  {v['title'][:38]}")
PY
