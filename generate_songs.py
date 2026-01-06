import os
import re
import csv
import io
import urllib.request
from datetime import datetime
from typing import List, Dict

# 元スクリから必要部分を引き継ぎ（URLは独立管理）
SONGS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=0#gid=0"
OUTPUT_DIR = "songs"

def build_csv_url(edit_url: str) -> str:
    parts = edit_url.split("/d/")
    if len(parts) < 2:
        return ""
    sheet_id = parts[1].split("/")[0]
    gid = "0"
    if "gid=" in edit_url:
        try:
            gid = edit_url.split("gid=")[1].split("&")[0].split("#")[0]
        except:
            gid = "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

def fetch_csv_rows(edit_url: str) -> List[Dict]:
    rows: List[Dict] = []
    try:
        csv_url = build_csv_url(edit_url)
        if not csv_url:
            return rows
        with urllib.request.urlopen(csv_url, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(data))
        rows = [r for r in reader]
    except Exception as e:
        print(f"CSV取得に失敗: {e}")
    return rows

def to_iso_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except:
            pass
    m = re.search(r"(\d{4})[./-]?(\d{1,2})(?:[./-]?(\d{1,2}))?", s)
    if m:
        y, mo, da = m.group(1), m.group(2).zfill(2), (m.group(3) or "01").zfill(2)
        return f"{y}-{mo}-{da}"
    return ""

def to_int(val: str) -> int:
    s = (val or "").replace(",", "").replace("回", "").replace(" ", "")
    try:
        return int(s)
    except:
        return 0

def make_song_slug(name: str, sheet_id: int) -> str:
    base = (name or "").strip()
    base = re.sub(r'[\\/:*?"<>|]', '', base)
    base = re.sub(r'\s+', '_', base)
    return f"{sheet_id}-{base}" if sheet_id and sheet_id > 0 else base

def make_cd_slug(name: str) -> str:
    """CDページ用の安全なファイル名を生成（generate.pyと同等）"""
    base = (name or "").strip()
    base = re.sub(r'[\\/:*?"<>|]', '', base)
    base = re.sub(r'\s+', '_', base)
    return base or "untitled"

def kind_code(raw_kind: str) -> str:
    k = (raw_kind or "").strip().lower()
    if ("オリ" in raw_kind) or ("original" in k) or k.startswith("ori"):
        return "original"
    if ("カバ" in raw_kind) or ("cover" in k):
        return "cover"
    return "other"

def parse_singer_flags(s_raw: str) -> Dict[str, int]:
    s = (s_raw or "").strip()
    sl = s.lower()
    unit = 1 if ("はのこと" in s or "ハコリリ" in s or "ハコニワリリィ" in s or "hakoniwa" in sl or "hakoniwalily" in sl) else 0
    hanon = 1 if ("hanon" in sl) else 0
    kotoha = 1 if ("kotoha" in sl) else 0
    return {"unit": unit, "hanon": hanon, "kotoha": kotoha}

def parse_credits(raw: str) -> List[Dict]:
    """クレジット文字列を Key -> Value のペアに分解（Key:Value/KeyValue両対応）"""
    if not raw:
        return []
    s = raw.strip()
    # キー候補（英語を正規化）
    key_map = {
        "lyrics": "作詞",
        "music": "作曲",
        "arrangement": "編曲",
        "guitar": "ギター",
        "bass": "ベース",
        "keyboard": "キーボード",
        "programming": "プログラミング",
        "programing": "プログラミング",
        "drums": "ドラム",
        "chorus": "コーラス",
        # 追加: Chorusの表記ゆらぎに対応
        "backing chorus": "コーラス",
        "choir": "コーラス",
        "mix": "MIX",
        "mastering": "マスタリング",
        "illust": "イラスト",
        "movie": "映像",
        "animation": "アニメーション",
        # 既存: Strings/他
        "stringsarrangement": "ストリングスアレンジ",
        "strings arrangement": "ストリングスアレンジ",
        "strings": "ストリングス",
        "drum technician": "ドラムテクニシャン",
        "drumtechnician": "ドラムテクニシャン",
        "piano": "ピアノ",
        "strings programming": "ストリングスプログラミング",
        "stringsprogramming": "ストリングスプログラミング",
        "strings programing": "ストリングスプログラミング",
        # 追加: Acoustic Guitar / Electric Piano
        "acoustic guitar": "アコースティックギター",
        "acousticguitar": "アコースティックギター",
        "electric piano": "エレクトリックピアノ",
        "electricpiano": "エレクトリックピアノ",
    }
    keys = sorted(key_map.keys(), key=lambda k: -len(k))  # 長いキー優先
    pattern = re.compile(r'(?i)\b(' + '|'.join(keys) + r')\b(?:\s*[:：]?)')
    parts = []
    matches = list(pattern.finditer(s))
    for idx, m in enumerate(matches):
        k_en = m.group(1).lower()
        label = key_map.get(k_en, k_en)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(s)
        value = s[start:end].strip()
        # コロン無し「Bass小林修己」のようなケース補正
        if not value and end > start and end <= len(s):
            value = s[start:end].strip()
        # 区切りの置換
        value = value.replace(",", "、").strip()
        if value:
            parts.append({"label": label, "value": value})
    return parts

def read_songs_detailed(edit_url: str) -> List[Dict]:
    rows = fetch_csv_rows(edit_url)
    out: List[Dict] = []
    for r in rows:
        name = (r.get("楽曲名") or r.get("曲名") or r.get("タイトル") or r.get("name") or "").strip()
        if not name:
            continue
        sheet_id = to_int(r.get("ID") or r.get("id") or r.get("No") or r.get("no") or "")
        slug = make_song_slug(name, sheet_id)
        albums_raw = (r.get("収録") or r.get("収録(収録CD)") or r.get("album") or "").strip()
        albums = [a.strip() for a in albums_raw.split(",") if a.strip()]
        kind_raw = (r.get("種別") or r.get("タイプ") or r.get("カテゴリ") or r.get("category") or r.get("type") or "").strip()
        yt = (r.get("YouTubeリンク") or r.get("Youtubeリンク") or r.get("Youtube") or r.get("URL") or "").strip()
        cover_key = (r.get("表紙") or r.get("ジャケット") or r.get("cover") or r.get("image") or name).strip()
        # 詳細クレジット
        lyrics = (r.get("作詞") or "").strip()
        composer = (r.get("作曲") or "").strip()
        arranger = (r.get("編曲") or "").strip()
        vocal = (r.get("ボーカル") or r.get("vocal") or "").strip()
        credit_raw = (r.get("クレジット") or r.get("credit") or "").strip()

        out.append({
            "name": name,
            "slug": slug,
            "image": f"../image/CD/{cover_key}.png",  # ページから見た相対
            "release_date": to_iso_date(r.get("リリース日") or r.get("release_date") or ""),
            "albums": albums,
            "kind": kind_raw or "不明",
            "kind_code": kind_code(kind_raw),
            "youtube": yt,
            "lyrics": lyrics,
            "composer": composer,
            "arranger": arranger,
            "vocal": vocal,
            "credit_raw": credit_raw,
        })
    return out

def render_song_html(song: Dict) -> str:
    date_disp = song["release_date"].replace("-", "/") if song["release_date"] else ""
    # 収録CD → CDs/{slug}.html にリンク化
    albums_html = (
        "".join(f"<a class='chip' href='../CDs/{make_cd_slug(a)}.html'>{a}</a>" for a in song["albums"])
        or "<span class='chip muted'>（収録情報なし）</span>"
    )
    vocals_html = "".join(f"<span class='chip alt'>{v.strip()}</span>" for v in (song['vocal'].split(",") if song['vocal'] else [])) or "<span class='chip muted'>（ボーカル情報なし）</span>"
    yt_link_html = f"<a class='header-button youtube' href='{song['youtube']}' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a>" if song['youtube'] else ""
    credits_rows = []
    if song['lyrics']:   credits_rows.append(f"<tr><th>作詞</th><td>{song['lyrics']}</td></tr>")
    if song['composer']: credits_rows.append(f"<tr><th>作曲</th><td>{song['composer']}</td></tr>")
    if song['arranger']: credits_rows.append(f"<tr><th>編曲</th><td>{song['arranger']}</td></tr>")
    # 追加: クレジット解析結果をテーブルに追記（重複キーはスキップ）
    existing_labels = {"作詞", "作曲", "編曲"} if credits_rows else set()
    for item in parse_credits(song.get("credit_raw", "")):
        if item["label"] in existing_labels:
            continue
        credits_rows.append(f"<tr><th>{item['label']}</th><td>{item['value']}</td></tr>")

    credits_table = f"<table class='credit-table'>{''.join(credits_rows)}</table>" if credits_rows else "<p class='video-meta'>クレジット情報がありません。</p>"

    # 追加: フッター（共通リンク＆コピーライト）
    footer_html = """
<footer class='site-footer'>
  <div class='footer-content'>
    <div class='footer-links'>
      <a href='https://x.com/hanokoto901' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i> Twitter</a>
      <a href='https://www.youtube.com/channel/UCepZVSTaKBW4ux0RB-nQ_NQ' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a>
    </div>
    <div class='footer-copyright'>© 2025 - はのこと活動記録</div>
  </div>
</footer>
"""

    return f"""<!DOCTYPE html>
<html lang='ja'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>{song['name']}｜リリース曲詳細</title>
<link rel='stylesheet' href='songs.css'>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
<!-- 追加: サイト共通の基本設定（favicon / OG / Twitterカード） -->
<link rel='icon' type='image/png' href='../image/icon.png'>
<link rel='icon' type='image/x-icon' href='../image/icon.ico'>
<meta name='description' content='Hanon＆Kotoha（はのこと）とハコニワリリィ（ハコリリ）の活動を記録するファンアーカイブサイトのリリース曲詳細ページ。'>
<meta property='og:title' content='{song['name']}｜リリース曲詳細'>
<meta property='og:description' content='Hanon＆Kotoha（はのこと）とハコニワリリィ（ハコリリ）の活動を記録するファンアーカイブサイトのリリース曲詳細ページ。'>
<meta property='og:type' content='website'>
<meta property='og:url' content='https://yoursite.com/songs/{song['slug']}.html'>
<meta property='og:image' content='https://yoursite.com/image/ogp.png'>
<meta name='twitter:card' content='summary_large_image'>
</head>
<body>
<header class='site-header'>
  <div class='header-left'>
    <a href='../index.html' class='nav-link'><i class='fa-solid fa-arrow-left'></i> リリースへ戻る</a>
  </div>
</header>
<main class='section'>
  <h2 class='song-title'><i class='fa-solid fa-music'></i> {song['name']}</h2>

  <div class='song-hero'>
    <img src='{song["image"]}' alt='{song["name"]}' loading='lazy'>
    <div class='song-hero-meta'>
      <div class='video-meta'><i class='fa-regular fa-calendar'></i> {date_disp}</div>
      <div class='video-meta'><i class='fa-solid fa-tag'></i> {song["kind"]}</div>
      <div class='meta-row'>
        <span class='meta-label'>収録</span>
        <div class='chips'>{albums_html}</div>
      </div>
      <div class='meta-row'>
        <span class='meta-label'>ボーカル</span>
        <div class='chips'>{vocals_html}</div>
      </div>
      <div class='meta-row'>
        <div class='chips'>{yt_link_html or "<span class='chip muted'>（リンクなし）</span>"}</div>
      </div>
    </div>
  </div>

  <h3><i class='fa-solid fa-list-music'></i> クレジット</h3>
  {credits_table}
</main>
{footer_html}
<button class='back-to-top' aria-label='ページトップへ戻る'><i class='fa-solid fa-arrow-up'></i></button>
<script src='songs.js' defer></script>
</body>
</html>"""

def save_html(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    songs = read_songs_detailed(SONGS_SHEET_EDIT_URL)
    if not songs:
        print("楽曲データがありません。")
        return
    for s in songs:
        out_path = os.path.join(OUTPUT_DIR, f"{s['slug']}.html")
        save_html(out_path, render_song_html(s))
    print(f"{len(songs)}件の曲ページを生成しました。")

if __name__ == "__main__":
    main()
