"""共通設定モジュール"""
import json
import os
from pathlib import Path

# プロジェクトルート
ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "podcast_config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _cfg = json.load(f)

# ポッドキャスト設定
PODCAST = _cfg["podcast"]
AUDIO = _cfg["audio"]
NEWS_SOURCES = _cfg["news_sources"]
R2 = _cfg["r2"]
RSS = _cfg["rss"]

# 環境変数
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]

# Claude モデル
CLAUDE_MODEL = "claude-sonnet-4-6"

# ディレクトリ
SCRIPTS_DIR = ROOT_DIR / "scripts"
DOCS_DIR = ROOT_DIR / "docs"
TEMP_DIR = ROOT_DIR / ".tmp"
TEMP_DIR.mkdir(exist_ok=True)
