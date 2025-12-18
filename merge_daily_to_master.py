import os
import json
from datetime import datetime, timedelta, timezone
from glob import glob

# =========================
# 設定
# =========================

DAILY_DIR = os.environ.get(
    "DAILY_JSON_DIR",
    "daily_videos"
)

MASTER_JSON_PATH = os.environ.get(
    "MASTER_JSON_PATH",
    "public/videos_master.json"
)

KEEP_DAYS = int(os.environ.get("KEEP_DAYS", "7"))

# =========================
# ユーティリティ
# =========================

def parse_iso(dt_str: str) -> datetime:
    """ISO8601文字列を datetime に変換"""
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# メイン処理
# =========================

def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=KEEP_DAYS)

    videos_by_id = {}

    # 既存 master を読み込み（あれば）
    if os.path.exists(MASTER_JSON_PATH):
        master = load_json(MASTER_JSON_PATH)

        if isinstance(master, list):
            master_videos = master
        else:
            master_videos = master.get("videos", [])

        for v in master_videos:
            if not isinstance(v, dict):
                continue
            vid = v.get("id")
            if not vid:
                continue
            videos_by_id[vid] = v



    # daily json を全読み込み
    daily_files = sorted(
        glob(os.path.join(DAILY_DIR, "videos_*.json"))
    )

    for path in daily_files:
        daily = load_json(path)
        if isinstance(daily, list):
            daily_videos = daily
        else:
            daily_videos = daily.get("videos", [])

        for v in daily_videos:
            if not isinstance(v, dict):
                continue
            vid = v.get("id")
            if not vid:
                continue
            videos_by_id[vid] = v


    # publish_at でフィルタ（直近 KEEP_DAYS のみ）
    filtered_videos = []
    for v in videos_by_id.values():
        try:
            published_at = parse_iso(v["publish_at"])
            if published_at >= cutoff:
                filtered_videos.append(v)
        except Exception:
            # publish_at が壊れているものは除外
            continue

    # 新しい順にソート
    filtered_videos.sort(
        key=lambda v: parse_iso(v["publish_at"]),
        reverse=True
    )

    # master json 構築
    master_output = {
        "updated_at": now.strftime("%Y-%m-%d"),
        "days": KEEP_DAYS,
        "count": len(filtered_videos),
        "videos": filtered_videos
    }

    save_json(MASTER_JSON_PATH, master_output)

    print(f"[OK] master updated: {MASTER_JSON_PATH}")
    print(f"[INFO] videos count: {len(filtered_videos)}")


if __name__ == "__main__":
    main()
