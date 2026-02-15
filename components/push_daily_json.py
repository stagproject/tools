import os
import json
import subprocess
from datetime import datetime, timezone

# ============================================================
# 設定（絶対パス）
# ============================================================

YOUTUBE_DAILY_DIR = r"C:\AGS\youtube-auto\data\daily_videos"
TOOLS_DIR = r"C:\AGS\tools"
TOOLS_DAILY_DIR = os.path.join(TOOLS_DIR, "daily_videos")

TARGET_BRANCH = "daily-input"

# ============================================================
# utils
# ============================================================

def run_git(cmd: list[str]):
    subprocess.run(
        ["git"] + cmd,
        cwd=TOOLS_DIR,
        check=True
    )


def git_has_staged_changes() -> bool:
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=TOOLS_DIR,
        capture_output=True,
        text=True
    )
    return bool(r.stdout.strip())


def today_filename() -> str:
    return f"videos_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"


def load_json_safe(path: str):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_videos_by_id(existing: list, new: list) -> list:
    merged = {v["id"]: v for v in existing if "id" in v}
    for v in new:
        vid = v.get("id")
        if vid:
            merged[vid] = v
    return list(merged.values())

# ============================================================
# main
# ============================================================

def main():
    filename = today_filename()

    src = os.path.join(YOUTUBE_DAILY_DIR, filename)
    dst = os.path.join(TOOLS_DAILY_DIR, filename)

    if not os.path.exists(src):
        print(f"[SKIP] source not found: {src}")
        return

    os.makedirs(TOOLS_DAILY_DIR, exist_ok=True)

    # --- 作業ブランチを触る前に clean な状態を保証 ---
    run_git(["fetch", "origin"])
    run_git(["checkout", TARGET_BRANCH])
    run_git(["reset", "--hard", f"origin/{TARGET_BRANCH}"])

    # --- JSON 読み込み ---
    new_payload = load_json_safe(src)
    new_videos = new_payload if isinstance(new_payload, list) else new_payload.get("videos", [])

    existing_payload = load_json_safe(dst)
    existing_videos = (
        existing_payload if isinstance(existing_payload, list)
        else existing_payload.get("videos", [])
    )

    # --- マージ ---
    merged_videos = merge_videos_by_id(existing_videos, new_videos)

    days = existing_payload.get("days", 1) if isinstance(existing_payload, dict) else 1

    merged_payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "days": days,
        "count": len(merged_videos),
        "videos": merged_videos,
    }

    save_json(dst, merged_payload)
    print(f"[OK] merged & saved: {filename} (count={len(merged_videos)})")

    # --- commit ---
    run_git(["add", f"daily_videos/{filename}"])

    if not git_has_staged_changes():
        print("[INFO] no staged git changes")
        return

    run_git(["commit", "-m", f"update daily videos json: {filename}"])
    run_git(["push", "origin", TARGET_BRANCH])

    print("[OK] daily json pushed to daily-input branch")


if __name__ == "__main__":
    main()
