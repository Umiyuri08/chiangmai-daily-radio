"""
02_generate_script.py
収集したニュースをClaude APIで日本語ポッドキャスト台本に変換する
"""
import json
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
以下のチェンマイの英語ニュース記事を元に、日本人リスナー向けの自然な日本語ポッドキャスト台本を生成してください。

## 要件
- 放送日: {date_str}
- 全体の長さ: 読み上げ時間が15〜20分程度（約4,500〜6,000文字）
- セグメント構成: 8〜12個のセグメントで構成する
- 各ニュースセグメントのテキスト: 200〜400文字（ひとつのニュースを丁寧に掘り下げて解説する）
- 音楽コーナー: 2〜3個含める。「♪ 〜〜 ♪」のような形式で挿入し、チェンマイらしいタイ音楽や現地の雰囲気に合う曲を紹介する
- トーン: 親しみやすく、明るい朝のラジオ風
- 冒頭: 「おはようございます！チェンマイ・デイリー・ラジオです。」で始める
- 各ニュースを自然な流れで日本語にまとめ、現地の雰囲気・背景・リスナーへの影響を丁寧に伝える
- 固有名詞（地名・人名）はカタカナ表記を優先
- ニュースとニュースの間に自然なつなぎ・コメントを入れる
- 締めくくり: 「今日も素敵なチェンマイの一日をお過ごしください。チェンマイ・デイリー・ラジオでした！」で終わる
- 台本のみ出力する（説明文・マークダウン不要）

## 今日のニュース
{news_text}
"""


def generate_script(articles: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    date_str = datetime.now(tz=JST).strftime("%Y年%m月%d日")

    print(f"[INFO] Claude ({CLAUDE_MODEL}) で台本生成中...")
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        messages=[
            {"role": "user", "content": build_prompt(articles, date_str)}
        ],
    )

    return message.content[0].text


def main():
    news_path = TEMP_DIR / "news.json"
    if not news_path.exists():
        print("[ERROR] news.json が見つかりません。01_fetch_news.py を先に実行してください")
        sys.exit(1)

    with open(news_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    script = generate_script(articles)

    output_path = TEMP_DIR / "script.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script)

    print(f"[DONE] 台本を {output_path} に保存 ({len(script)} 文字)")


if __name__ == "__main__":
    main()
