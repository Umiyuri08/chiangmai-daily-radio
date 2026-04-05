"""
03_synthesize_audio.py
台本JSONをVOICEVOXで音声合成してMP3に変換する（BGM・ジングル付き）
"""
import io
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from pydub import AudioSegment
from pydub.generators import Sine

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from config import TEMP_DIR

JST = timezone(timedelta(hours=9))
VOICEVOX_URL = "http://localhost:50021"

# 話者マッピング: ユキ=四国めたん・ノーマル, ケン=青山龍星
SPEAKER_MAP = {"ユキ": 0, "ケン": 13}
DEFAULT_SPEAKER = 0

CREDIT_TEXT = "VOICEVOX、四国めたん、VOICEVOX、青山龍星"


# ─────────────────────────────────────────
# VOICEVOX ユーティリティ
# ─────────────────────────────────────────

def wait_for_voicevox(timeout: int = 180) -> None:
    """VOICEVOXエンジンが起動するまで待機"""
    print("[INFO] VOICEVOXエンジンの起動を待機中...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{VOICEVOX_URL}/version", timeout=5)
            if r.status_code == 200:
                print(f"[INFO] VOICEVOXエンジン起動確認 (version: {r.text.strip()})")
                return
        except requests.exceptions.ConnectionError:
            pass
        print("[INFO]   待機中...")
        time.sleep(5)
    raise RuntimeError("VOICEVOXエンジンの起動タイムアウト（180秒）")


def synthesize_segment(text: str, speaker_id: int) -> AudioSegment:
    """テキストをVOICEVOXで合成してAudioSegmentとして返す"""
    # Step 1: audio_query を取得
    r = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": speaker_id},
        timeout=60,
    )
    r.raise_for_status()
    audio_query = r.json()

    # 読み上げ速度を少し上げる（デフォルト1.0 → 1.1）
    audio_query["speedScale"] = 1.1

    # Step 2: synthesis で WAV を取得
    r = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": speaker_id},
        json=audio_query,
        timeout=120,
    )
    r.raise_for_status()

    return AudioSegment.from_wav(io.BytesIO(r.content))


# ─────────────────────────────────────────
# ジングル生成（外部ファイル不要）
# ─────────────────────────────────────────

def _tone(freq: float, duration_ms: int, volume_db: float = -10.0) -> AudioSegment:
    """指定周波数・長さのサイン波トーンを生成（フェード付き）"""
    fade_ms = min(50, duration_ms // 4)
    return (
        Sine(freq)
        .to_audio_segment(duration=duration_ms)
        .fade_in(fade_ms)
        .fade_out(fade_ms)
        + volume_db
    )


def make_opening_jingle() -> AudioSegment:
    """オープニングジングル: 約2秒、明るい上昇アルペジオ"""
    gap = AudioSegment.silent(duration=60)
    return (
        _tone(523.25, 350, -8.0) + gap   # C5
        + _tone(659.25, 350, -8.0) + gap  # E5
        + _tone(783.99, 350, -8.0) + gap  # G5
        + _tone(1046.50, 900, -6.0)       # C6（余韻）
    )


def make_news_jingle() -> AudioSegment:
    """ニュース転換音: 0.5秒、短いチャイム"""
    return _tone(880.0, 500, -12.0)


def make_music_jingle() -> AudioSegment:
    """音楽コーナー転換音: 約1秒、明るい2音"""
    return (
        _tone(523.25, 450, -10.0)
        + _tone(659.25, 550, -10.0)
    )


def make_ending_jingle() -> AudioSegment:
    """エンディングジングル: 約3秒、下降アルペジオ"""
    gap = AudioSegment.silent(duration=60)
    return (
        _tone(523.25, 450, -8.0) + gap   # C5
        + _tone(392.00, 450, -8.0) + gap  # G4
        + _tone(329.63, 450, -8.0) + gap  # E4
        + _tone(261.63, 1400, -6.0)       # C4（余韻）
    )


SILENCE = AudioSegment.silent(duration=500)


# ─────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────

def main():
    script_path = TEMP_DIR / "script.json"
    if not script_path.exists():
        print("[ERROR] script.json が見つかりません。02_generate_script.py を先に実行してください")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    wait_for_voicevox()

    # オープニングジングル
    final = make_opening_jingle() + SILENCE

    prev_type: str | None = None

    for i, seg in enumerate(segments):
        seg_type = seg.get("type", "news")
        speaker_name = seg.get("speaker", "ユキ")
        text = seg.get("text", "").strip()

        if not text:
            continue

        speaker_id = SPEAKER_MAP.get(speaker_name, DEFAULT_SPEAKER)

        # セグメント間の転換ジングル
        if prev_type is not None:
            if seg_type == "music":
                final += make_music_jingle()
            else:
                final += make_news_jingle()
            final += SILENCE

        preview = text[:40].replace("\n", " ")
        print(f"[INFO] [{i+1}/{len(segments)}] {seg_type} / {speaker_name}(speaker={speaker_id}): {preview}...")
        audio = synthesize_segment(text, speaker_id)
        final += audio
        prev_type = seg_type

    # クレジット読み上げ
    final += SILENCE
    final += make_news_jingle()
    final += SILENCE
    print(f"[INFO] クレジット読み上げ中...")
    final += synthesize_segment(CREDIT_TEXT, DEFAULT_SPEAKER)

    # エンディングジングル
    final += SILENCE
    final += make_ending_jingle()

    # MP3 出力
    date_str = datetime.now(tz=JST).strftime("%Y%m%d")
    output_path = TEMP_DIR / f"episode_{date_str}.mp3"
    final.export(output_path, format="mp3", bitrate="128k")

    size_kb = output_path.stat().st_size // 1024
    duration_min = len(final) / 1000 / 60
    print(f"[DONE] 音声ファイル生成: {output_path} ({size_kb} KB, {duration_min:.1f}分)")

    ref_path = TEMP_DIR / "audio_filename.txt"
    with open(ref_path, "w") as f:
        f.write(output_path.name)


if __name__ == "__main__":
    main()
