"""
02_generate_script.py
収集したニュースをClaude APIで日本語ポッドキャスト台本（JSON）に変換する
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone

import anthropic

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, PODCAST, TEMP_DIR

JST = timezone(timedelta(hours=9))


def build_prompt(articles: list[dict], date_str: str) -> str:
    news_text = ""
    for i, a in enumerate(articles, 1):
        news_text += f"\n【ニュース{i}】{a['source']}\nタイトル: {a['title']}\n内容: {a['summary']}\n"

    return f"""あなたはタイ・チェンマイ在住の日本語ポッドキャストパーソナリティです。
以下のチェンマイの英語ニュース記事を元に、日本人リスナー向けの自然な日本語ポッドキャスト台本をJSON形式で生成してください。

## 要件
- 放送日: {date_str}
- 全体の文字数（text フィールドの合計）: 6,000〜8,000文字
- セグメント数: 10〜14個
- 各ニュースセグメントのテキスト: 300〜500文字（ひとつのニュースを丁寧に掘り下げて解説する）
- 音楽コーナー: 必ず3個含める。チェンマイの伝統音楽、ライブハウス情報、アーティスト紹介をそれぞれ1個ずつ
- トーン: 親しみやすく、明るい朝のラジオ風。ユキとケンの掛け合いで進行
- 冒頭セグメント（type: "opening"）: 「おはようございます！チェンマイ・デイリー・ラジオです。」で始め、今日の見どころを紹介
- 締めくくりセグメント（type: "ending"）: 「今日も素敵なチェンマイの一日をお過ごしください。チェンマイ・デイリー・ラジオでした！」で終わる
- 固有名詞（地名・人名）はカタカナ表記を優先
- ニュースとニュースの間に自然なつなぎ・コメントを入れる

## 出力形式
以下のJSON配列のみを出力してください（説明文・マークダウン・コードブロック不要）。

[
  {{
    "type": "opening",
    "speaker": "ユキ",
    "text": "おはようございます！..."
  }},
  {{
    "type": "news",
    "speaker": "ケン",
    "text": "今日のニュースは..."
  }},
  {{
    "type": "music",
    "speaker": "ユキ",
    "text": "♪ それでは音楽コーナーです... ♪"
  }},
  {{
    "type": "ending",
    "speaker": "ユキ",
    "text": "今日も素敵な..."
  }}
]

- type: "opening"（オープニング）/ "news"（ニュース）/ "music"（音楽コーナー）/ "ending"（エンディング）
- speaker: "ユキ"（女性）または "ケン"（男性）
- ニュースセグメントはユキとケンが交互に担当

## 今日のニュース
{news_text}
"""


def extract_json(raw: str) -> list[dict]:
    """Claude応答からJSON配列を抽出してパース"""
    # コードブロック除去
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    # 最初の [ から最後の ] までを抽出
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"JSON配列が見つかりません: {raw[:200]}")
    return json.loads(raw[start : end + 1])


def generate_script(articles: list[dict]) -> list[dict]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    date_str = datetime.now(tz=JST).strftime("%Y年%m月%d日")

    print(f"[INFO] Claude ({CLAUDE_MODEL}) で台本生成中...")
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=12000,
        messages=[
            {"role": "user", "content": build_prompt(articles, date_str)}
        ],
    )

    raw = message.content[0].text
    segments = extract_json(raw)

    total_chars = sum(len(s.get("text", "")) for s in segments)
    print(f"[INFO] セグメント数: {len(segments)}, 合計文字数: {total_chars}")
    return segments


def main():
    news_path = TEMP_DIR / "news.json"
    if not news_path.exists():
        print("[ERROR] news.json が見つかりません。01_fetch_news.py を先に実行してください")
        sys.exit(1)

    with open(news_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    segments = generate_script(articles)

    output_path = TEMP_DIR / "script.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    total_chars = sum(len(s.get("text", "")) for s in segments)
    print(f"[DONE] 台本を {output_path} に保存 ({len(segments)} セグメント, {total_chars} 文字)")


if __name__ == "__main__":
    main()
