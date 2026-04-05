"""
01_fetch_news.py
チェンマイのローカルニュースをRSSフィードから収集し、JSONに保存する
"""
import json
import sys
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from config import NEWS_SOURCES, TEMP_DIR

JST = timezone(timedelta(hours=9))
FETCH_HOURS = 24  # 過去24時間のニュースを収集


def fetch_rss(source: dict) -> list[dict]:
    """RSSフィードを取得してニュース記事リストを返す"""
    articles = []
    try:
        # HTTPステータスコードとレスポンス先頭200文字をデバッグ出力
        try:
            resp = requests.get(source["url"], timeout=10)
            print(f"[DEBUG]   HTTP {resp.status_code} - {source['url']}")
            print(f"[DEBUG]   Response preview: {resp.text[:200]!r}")
        except Exception as req_err:
            print(f"[DEBUG]   HTTP request failed: {req_err}")

        feed = feedparser.parse(source["url"])
        print(f"[DEBUG]   feedparser entries: {len(feed.entries)}")
        cutoff = datetime.now(tz=JST) - timedelta(hours=FETCH_HOURS)

        for entry in feed.entries:
            # 公開日時を取得
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(JST)
            else:
                published = datetime.now(tz=JST)

            if published < cutoff:
                continue

            # キーワードフィルタ（Bangkok Postなど）
            if "filter_keyword" in source:
                kw = source["filter_keyword"].lower()
                text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
                if kw not in text:
                    continue

            # 本文を取得（summary or content）
            summary = entry.get("summary", "")
            if hasattr(entry, "content"):
                summary = entry.content[0].get("value", summary)

            # HTMLタグを除去
            soup = BeautifulSoup(summary, "lxml")
            clean_text = soup.get_text(separator=" ").strip()

            articles.append({
                "source": source["name"],
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "summary": clean_text[:800],
                "published": published.isoformat(),
            })

    except Exception as e:
        print(f"[WARN] {source['name']} の取得に失敗: {e}")

    return articles


def fetch_all_news() -> list[dict]:
    """全ソースからニュースを収集する"""
    all_articles = []
    for source in NEWS_SOURCES:
        print(f"[INFO] 取得中: {source['name']}")
        articles = fetch_rss(source)
        print(f"[INFO]   → {len(articles)} 件取得")
        all_articles.extend(articles)

    # 重複排除（タイトルで簡易判定）
    seen_titles = set()
    unique = []
    for a in all_articles:
        if a["title"] not in seen_titles:
            seen_titles.add(a["title"])
            unique.append(a)

    # 最新順にソート
    unique.sort(key=lambda x: x["published"], reverse=True)
    return unique[:15]  # 最大15件


def main():
    print("[START] ニュース収集開始")
    articles = fetch_all_news()

    if not articles:
        print("[ERROR] ニュースが取得できませんでした")
        sys.exit(1)

    output_path = TEMP_DIR / "news.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"[DONE] {len(articles)} 件のニュースを {output_path} に保存")


if __name__ == "__main__":
    main()
