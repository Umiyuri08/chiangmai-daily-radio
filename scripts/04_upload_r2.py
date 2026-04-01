"""
04_upload_r2.py
生成したMP3をCloudflare R2バケットにアップロードする
"""
import sys
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from config import R2, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, TEMP_DIR

JST = timezone(timedelta(hours=9))


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_mp3(local_path, filename: str) -> str:
    """MP3をR2にアップロードしてパブリックURLを返す"""
    client = get_r2_client()
    bucket = R2["bucket"]
    key = f"episodes/{filename}"

    print(f"[INFO] R2へアップロード中: s3://{bucket}/{key}")
    with open(local_path, "rb") as f:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=f,
            ContentType="audio/mpeg",
        )

    public_url = f"{R2['public_url_base']}/{key}"
    print(f"[DONE] アップロード完了: {public_url}")
    return public_url


def main():
    ref_path = TEMP_DIR / "audio_filename.txt"
    if not ref_path.exists():
        print("[ERROR] audio_filename.txt が見つかりません。03_synthesize_audio.py を先に実行してください")
        sys.exit(1)

    filename = ref_path.read_text().strip()
    local_path = TEMP_DIR / filename

    if not local_path.exists():
        print(f"[ERROR] 音声ファイルが見つかりません: {local_path}")
        sys.exit(1)

    public_url = upload_mp3(local_path, filename)

    # 後続スクリプト用にURLを保存
    url_path = TEMP_DIR / "audio_url.txt"
    url_path.write_text(public_url)

    # エピソードメタデータを保存
    date_str = datetime.now(tz=JST).strftime("%Y%m%d")
    pub_date = datetime.now(tz=JST).strftime("%a, %d %b %Y 07:00:00 +0900")
    size_bytes = local_path.stat().st_size

    import json
    meta = {
        "filename": filename,
        "url": public_url,
        "date": date_str,
        "pub_date": pub_date,
        "size_bytes": size_bytes,
    }
    meta_path = TEMP_DIR / "episode_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[INFO] メタデータを {meta_path} に保存")


if __name__ == "__main__":
    main()
