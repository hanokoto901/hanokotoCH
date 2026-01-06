import os
import re
import csv
import io
import urllib.request
from datetime import datetime
from typing import List, Dict

ALBUMS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=27271597#gid=27271597"
SINGLES_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=1975989717#gid=1975989717"
SONGS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=0#gid=0"
OUTPUT_DIR = "CDs"

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

def normalize_title(s: str) -> str:
    """曲名のゆるい正規化（空白/記号の除去・小文字化）"""
    s = (s or "").strip().lower()
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[\\/:*?"<>|()\[\]{}【】（）・・、,，。.!！?？\'"～〜\-–—_^`　]+', '', s)
    return s

def make_cd_slug(name: str) -> str:
    base = (name or "").strip()
    base = re.sub(r'[\\/:*?"<>|]', '', base)
    base = re.sub(r'\s+', '_', base)
    return base or "untitled"

def make_song_slug(name: str, sheet_id: int) -> str:
    """songs側のスラッグ規則に合わせて生成（ID-安全化）"""
    base = (name or "").strip()
    base = re.sub(r'[\\/:*?"<>|]', '', base)
    base = re.sub(r'\s+', '_', base)
    return f"{sheet_id}-{base}" if sheet_id and sheet_id > 0 else base or "untitled"

def parse_csv_list(raw: str) -> List[str]:
    # カンマ区切りで分割しトリム（空文字は除外）
    return [p.strip() for p in (raw or "").split(",") if p.strip()]

def read_items(edit_url: str) -> List[Dict]:
    rows = fetch_csv_rows(edit_url)
    out: List[Dict] = []
    for r in rows:
        name = (r.get("名前") or r.get("name") or "").strip()
        if not name:
            continue
        date_iso = to_iso_date(r.get("リリース日") or r.get("release_date") or "")
        oneword = (r.get("一言") or r.get("comment") or "").strip()
        tracks = parse_csv_list(r.get("収録曲") or r.get("tracks") or "")
        video_raw = (r.get("視聴動画") or r.get("video") or "").strip()
        videos = parse_csv_list(video_raw) if "," in video_raw else ([video_raw] if video_raw else [])
        desc = (r.get("説明") or r.get("description") or "").strip()
        out.append({
            "name": name,
            "slug": make_cd_slug(name),
            "image": f"../image/CD/{name}.png",
            "date": date_iso,
            "oneword": oneword,
            "tracks": tracks,
            "videos": videos,
            "desc": desc
        })
    return out

def read_songs_index(edit_url: str) -> dict[str, str]:
    """楽曲シートから 正規化タイトル → スラッグ の索引を作成"""
    index: dict[str, str] = {}
    try:
        for r in fetch_csv_rows(edit_url):
            name = (r.get("楽曲名") or r.get("曲名") or r.get("タイトル") or r.get("name") or "").strip()
            if not name:
                continue
            sheet_id_raw = (r.get("ID") or r.get("id") or r.get("No") or r.get("no") or "").strip()
            try:
                sheet_id = int(sheet_id_raw.replace(",", "")) if sheet_id_raw else 0
            except:
                sheet_id = 0
            slug = make_song_slug(name, sheet_id)
            key = normalize_title(name)
            # 同名は後勝ちで上書き（任意）
            if key:
                index[key] = slug
    except Exception as e:
        print(f"楽曲索引の作成に失敗: {e}")
    return index

def render_cd_html(item: Dict, kind_label: str, songs_index: dict[str, str]) -> str:
    date_disp = item["date"].replace("-", "/") if item["date"] else ""
    # 収録曲をリンク化
    if item["tracks"]:
        lis = []
        for t in item["tracks"]:
            key = normalize_title(t)
            slug = songs_index.get(key)
            if slug:
                lis.append(f"<li><a href='../songs/{slug}.html'>{t}</a></li>")
            else:
                lis.append(f"<li>{t}</li>")
        tracks_html = "<ol class='tracks'>" + "".join(lis) + "</ol>"
    else:
        tracks_html = "<p class='video-meta'>収録曲情報がありません。</p>"
    # 視聴動画（無い場合は非表示）
    videos_html = ""
    if item["videos"]:
        links = "".join(
            f"<a class='header-button youtube' href='{v}' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> 視聴動画</a> "
            for v in item["videos"]
        )
        videos_html = f"<div class='meta-row'><div class='chips'>{links}</div></div>"
    # 一言と説明（説明はヒーローの外へ）
    oneword_html = f"<div class='album-comment'>{item['oneword']}</div>" if item["oneword"] else ""
    desc_html = f"<div class='desc-note'>{item['desc']}</div>" if item["desc"] else ""

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
<title>{item['name']}｜{kind_label}詳細</title>
<link rel='stylesheet' href='songs.css'>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
<link rel='icon' type='image/png' href='../image/icon.png'>
<link rel='icon' type='image/x-icon' href='../image/icon.ico'>
<meta name='description' content='Hanon＆Kotoha（はのこと）とハコニワリリィ（ハコリリ）の活動を記録するファンアーカイブサイトの{kind_label}詳細ページ。'>
<meta property='og:title' content='{item['name']}｜{kind_label}詳細'>
<meta property='og:description' content='Hanon＆Kotoha（はのこと）とハコニワリリィ（ハコリリ）の活動を記録するファンアーカイブサイトの{kind_label}詳細ページ。'>
<meta property='og:type' content='website'>
<meta property='og:url' content='https://yoursite.com/CDs/{item['slug']}.html'>
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
  <h2 class='song-title'><i class='fa-solid fa-compact-disc'></i> {item['name']}</h2>

  <div class='song-hero'>
    <img src='{item["image"]}' alt='{item["name"]}' loading='lazy'>
    <div class='song-hero-meta'>
      <div class='video-meta'><i class='fa-regular fa-calendar'></i> {date_disp}</div>
      {oneword_html}
      {desc_html}
      <h3><i class='fa-solid fa-list-music'></i> 収録曲</h3>
      {tracks_html}
      {videos_html}
    </div>
  </div>

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
    albums = read_items(ALBUMS_SHEET_EDIT_URL)
    singles = read_items(SINGLES_SHEET_EDIT_URL)
    songs_index = read_songs_index(SONGS_SHEET_EDIT_URL)  # 追加: 楽曲索引

    for a in albums:
        save_html(os.path.join(OUTPUT_DIR, f"{a['slug']}.html"), render_cd_html(a, "アルバム", songs_index))
    for s in singles:
        save_html(os.path.join(OUTPUT_DIR, f"{s['slug']}.html"), render_cd_html(s, "シングル", songs_index))

    print(f"アルバム {len(albums)} 件、シングル {len(singles)} 件のページを生成しました。")

if __name__ == "__main__":
    main()
