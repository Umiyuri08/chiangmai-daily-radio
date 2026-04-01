"""
03_synthesize_audio.py
台本テキストをGoogle Cloud TTSでMP3音声に変換する
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.cloud import texttospeech

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from config import AUDIO, TEMP_DIR

JST = timezone(timedelta(hours=9))
MAX_BYTES = 4800  # Google TTS の1リクエスト上限（5000バイト）に余裕を持たせた値


def split_text(text: str) -> list[str]:
    """テキストをTTSリクエスト単位に分割する"""
    chunks = []
    current = ""
    for sentence in text.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n"):
        sentence = sentence.strip()
        if not sentence:
            continue
        encoded = (current + sentence).encode("utf-8")
        if len(encoded) > MAX_BYTES:
            if current:
                chunks.append(current)
            current = sentence
        else:
            current += sentence
    if current:
        chunks.append(current)
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

    chunks = split_text(text)
    print(f"[INFO] テキストを {len(chunks)} チャンクに分割して合成")

    audio_parts = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[INFO]   チャンク {i}/{len(chunks)} を合成中...")
        synthesis_input = texttospeech.SynthesisInput(text=chunk)
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
