"""
05_generate_rss.py
エピソードメタデータをfeed.xmlに追記してSpotify用RSSフィードを更新する
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from config import DOCS_DIR, PODCAST, RSS, ROOT_DIR, TEMP_DIR

JST = timezone(timedelta(hours=9))
FEED_PATH = ROOT_DIR / RSS["feed_path"]
MAX_EPISODES = RSS["max_episodes"]

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"


def load_feed() -> ET.ElementTree:
    ET.register_namespace("itunes", ITUNES_NS)
    ET.register_namespace("content", CONTENT_NS)
    if FEED_PATH.exists():
        return ET.parse(FEED_PATH)
    return None


def build_initial_feed() -> ET.Element:
    p = PODCAST
    rss = ET.Element("rss", {
        "version": "2.0",
        "xmlns:itunes": ITUNES_NS,
        "xmlns:content": CONTENT_NS,
    })
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = p["title"]
    ET.SubElement(channel, "link").text = p["website"]
    ET.SubElement(channel, "description").text = p["description"]
    ET.SubElement(channel, "language").text = p["language"]
    ET.SubElement(channel, "copyright").text = p["copyright"]
    ET.SubElement(channel, "lastBuildDate").text = datetime.now(tz=JST).strftime("%a, %d %b %Y %H:%M:%S %z")
    ET.SubElement(channel, f"{{{ITUNES_NS}}}author").text = p["author"]
    ET.SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "false"
    image = ET.SubElement(channel, f"{{{ITUNES_NS}}}image")
    image.set("href", p["image_url"])
    owner = ET.SubElement(channel, f"{{{ITUNES_NS}}}owner")
    ET.SubElement(owner, f"{{{ITUNES_NS}}}name").text = p["author"]
    ET.SubElement(owner, f"{{{ITUNES_NS}}}email").text = p["email"]
    category = ET.SubElement(channel, f"{{{ITUNES_NS}}}category")
    category.set("text", p["category"])
    return rss


def build_item(meta: dict, script: str) -> ET.Element:
    date_label = datetime.strptime(meta["date"], "%Y%m%d").strftime("%Y年%m月%d日")
    item = ET.Element("item")
    ET.SubElement(item, "title").text = f"{PODCAST['title']} - {date_label}"
    ET.SubElement(item, "description").text = f"チェンマイの最新ニュースをお届けします。{date_label}放送分。"
    ET.SubElement(item, f"{{{CONTENT_NS}}}encoded").text = f"<![CDATA[{script}]]>"
    ET.SubElement(item, "pubDate").text = meta["pub_date"]
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = meta["filename"]
   # URLがフルURLでない場合はpublic_url_baseから組み立て
    url = meta.get("url", "")
    if not url.startswith("http"):
        from config import R2
        url = f"{R2['public_url_base']}/episodes/{meta['filename']}"
    enclosure = ET.SubElement(item, "enclosure")
    enclosure.set("url", url)
    enclosure.set("length", str(meta["size_bytes"]))
    enclosure.set("type", "audio/mpeg")
    ET.SubElement(item, f"{{{ITUNES_NS}}}duration").text = "00:06:00"  # 概算
    ET.SubElement(item, f"{{{ITUNES_NS}}}explicit").text = "false"
    return item


def update_feed(meta: dict, script: str) -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    tree = load_feed()

    if tree is None:
        rss = build_initial_feed()
        channel = rss.find("channel")
    else:
        rss = tree.getroot()
        channel = rss.find("channel")

    # 同日エピソードが既にあれば上書き
    existing_items = channel.findall("item")
    for existing in existing_items:
        guid = existing.findtext("guid")
        if guid == meta["filename"]:
            channel.remove(existing)
            break

    # 新エピソードを先頭に挿入
    new_item = build_item(meta, script)
    first_item_index = None
    for i, child in enumerate(list(channel)):
        if child.tag == "item":
            first_item_index = i
            break

    if first_item_index is not None:
        channel.insert(first_item_index, new_item)
    else:
        channel.append(new_item)

    # 最大件数を超えた古いエピソードを削除
    items = channel.findall("item")
    for old in items[MAX_EPISODES:]:
        channel.remove(old)

    # lastBuildDate を更新
    lbd = channel.find("lastBuildDate")
    if lbd is not None:
        lbd.text = datetime.now(tz=JST).strftime("%a, %d %b %Y %H:%M:%S %z")

    tree_out = ET.ElementTree(rss)
    ET.indent(tree_out, space="  ")
    with open(FEED_PATH, "wb") as f:
        tree_out.write(f, encoding="utf-8", xml_declaration=True)

    print(f"[DONE] RSSフィード更新: {FEED_PATH} (エピソード数: {len(channel.findall('item'))})")


def main():
    meta_path = TEMP_DIR / "episode_meta.json"
    script_path = TEMP_DIR / "script.json"

    for p in [meta_path, script_path]:
        if not p.exists():
            print(f"[ERROR] {p} が見つかりません")
            sys.exit(1)

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    script = script_path.read_text(encoding="utf-8")

    update_feed(meta, script)


if __name__ == "__main__":
    main()
