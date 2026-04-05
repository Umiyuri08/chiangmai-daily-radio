"""
03_synthesize_audio.py
台本テキストをSSMLに変換してGoogle Cloud TTSでMP3音声に変換する
"""
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.cloud import texttospeech

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from config import AUDIO, TEMP_DIR

JST = timezone(timedelta(hours=9))
MAX_SSML_BYTES = 4500  # <speak>ラッパー込みで5000バイト以内に収まるよう余裕を持たせた値


def _process_sentences(text: str) -> str:
    """文単位でSSMLインライン要素（break/emphasis/prosody）を適用する"""
    result = ""
    for sentence in re.split(r"(?<=[。！？])", text):
        if not sentence:
            continue
        stripped = sentence.rstrip()
        if stripped.endswith("？"):
            inner = stripped[:-1].replace("。", '<break time="300ms"/>。')
            result += f'<prosody pitch="+1st">{inner}？</prosody>'
        elif stripped.endswith("！"):
            inner = stripped[:-1].replace("。", '<break time="300ms"/>。')
            result += f'<emphasis level="strong">{inner}！</emphasis>'
        else:
            result += sentence.replace("。", '<break time="300ms"/>。')
    return result


def convert_to_ssml_body(text: str) -> str:
    """台本テキスト全体をSSMLボディ（<speak>タグなし）に変換する"""
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            lines.append("")
            continue

        # 見出し判定: 40文字未満で文末句読点を含まない行、または♪で始まる行
        is_heading = (
            len(line) < 40 and not any(c in line for c in "。！？")
        ) or line.startswith("♪")

        if is_heading:
            processed = _process_sentences(line)
            lines.append(f'<prosody rate="slow" pitch="-1st">{processed}</prosody>')
        else:
            lines.append(_process_sentences(line))

    return "\n".join(lines)


def split_ssml(ssml_body: str) -> list[str]:
    """SSMLボディを行単位でチャンク分割し、各チャンクを<speak>で包む"""
    chunks = []
    current = ""
    for line in ssml_body.split("\n"):
        candidate = (current + "\n" + line).strip() if current else line
        if len(f"<speak>{candidate}</speak>".encode("utf-8")) > MAX_SSML_BYTES:
            if current:
                chunks.append(f"<speak>{current}</speak>")
            current = line
        else:
            current = candidate
    if current:
        chunks.append(f"<speak>{current}</speak>")
    return chunks


def synthesize(text: str, output_path: Path) -> None:
    client = texttospeech.TextToSpeechClient()

    voice = texttospeech.VoiceSelectionParams(
        language_code=AUDIO["language_code"],
        name=AUDIO["voice_name"],
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=AUDIO["speaking_rate"],
        pitch=AUDIO["pitch"],
        sample_rate_hertz=AUDIO["sample_rate_hertz"],
    )

    ssml_body = convert_to_ssml_body(text)
    chunks = split_ssml(ssml_body)
    print(f"[INFO] SSMLを {len(chunks)} チャンクに分割して合成")

    audio_parts = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[INFO]   チャンク {i}/{len(chunks)} を合成中...")
        synthesis_input = texttospeech.SynthesisInput(ssml=chunk)
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        audio_parts.append(response.audio_content)

    # MP3バイナリを結合して保存
    with open(output_path, "wb") as f:
        for part in audio_parts:
            f.write(part)

    size_kb = output_path.stat().st_size // 1024
    print(f"[DONE] 音声ファイル生成: {output_path} ({size_kb} KB)")


def main():
    script_path = TEMP_DIR / "script.txt"
    if not script_path.exists():
        print("[ERROR] script.txt が見つかりません。02_generate_script.py を先に実行してください")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        script = f.read()

    date_str = datetime.now(tz=JST).strftime("%Y%m%d")
    output_path = TEMP_DIR / f"episode_{date_str}.mp3"

    synthesize(script, output_path)

    # 後続スクリプトが参照できるようファイル名を記録
    ref_path = TEMP_DIR / "audio_filename.txt"
    with open(ref_path, "w") as f:
        f.write(output_path.name)


if __name__ == "__main__":
    main()
