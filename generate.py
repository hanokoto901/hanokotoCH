# はのこと活動記録 - HTML生成スクリプト（Web公開用）
# - 作業ログ的コメントを整理
# - 重要な説明のみ簡潔に記述
# - ロジックは変更なし

import sqlite3
from typing import List, Dict
from collections import defaultdict
import os
from datetime import datetime, timedelta
import csv
import urllib.request
import io

DB_FILE = "data/history.db"
OUTPUT_FILE = "index.html"
THANKS_CSV = "data/thanks.csv"
# 追加: ライブ管理DB（Z_concert-db管理で生成）
CONCERT_DB = "X_concert.db"
# スプレッドシート（編集URL → CSVエクスポートURLへ変換）
VIDEOS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/161eDUFzWgGW5TCuyzZ3GR3OCEaaNfq-LDWJibdF6Ar4/edit?gid=413704367#gid=413704367"
COVERS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1Y1mFAj-RHV8VFx9A7w1W1QyJ9-RYxcAW4c2tbF5N_-w/edit?gid=0#gid=0"
TRENDING_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1Y1mFAj-RHV8VFx9A7w1W1QyJ9-RYxcAW4c2tbF5N_-w/edit?gid=1174580202#gid=1174580202"
# 追加: ALL表（歌動画一覧）取得用URL
COVERS_ALL_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1Y1mFAj-RHV8VFx9A7w1W1QyJ9-RYxcAW4c2tbF5N_-w/edit?ouid=112508527560905085845&usp=sheets_home&ths=true"
# 追加: アルバム一覧（リリース）取得用URL
ALBUMS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=27271597#gid=27271597"
# 追加: シングル一覧（リリース）取得用URL
SINGLES_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=1975989717#gid=1975989717"
# 追加: リリース楽曲一覧（リリース）取得用URL
SONGS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=0#gid=0"

def get_conn():
    """SQLite データベース接続を取得"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_records() -> List[Dict]:
    """データベースから全レコードを取得"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT year, month, day, classification, genre, content, link FROM history ORDER BY year, month, day")
        return [dict(row) for row in cur.fetchall()]

def group_records_by_classification_and_date(records: List[Dict]) -> Dict:
    """レコードを分類ごとにグループ化し、さらに年と月ごとに整理"""
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for record in records:
        year = f"{record['year']}年"
        month = f"{record['month']}月"
        grouped[record['classification']][year][month][record['genre']].append(record)
    return grouped

def format_content(record: Dict) -> str:
    """レコードの内容をフォーマット"""
    day_content = f"{record['day']}日:{record['content']}"
    return f"<a href='{record['link']}' target='_blank'>{day_content}</a>" if record['link'] else day_content

def generate_table_rows(years: Dict) -> List[str]:
    """テーブル行を生成"""
    rows = []
    genres = ["主な出来事", "ライブ", "動画", "その他"]
    
    for year, months in years.items():
        year_rowspan = len(months)
        for idx, (month, genre_data) in enumerate(months.items()):
            row_parts = []
            if idx == 0:
                row_parts.append(f"<td rowspan='{year_rowspan}' class='date fit'>{year}</td>")
            row_parts.append(f"<td class='date fit'>{month}</td>")
            
            for genre in genres:
                contents = "<br>".join(format_content(r) for r in genre_data.get(genre, []))
                row_parts.append(f"<td class='fix'>{contents}</td>")
            
            rows.append(f"<tr>{''.join(row_parts)}</tr>")
    return rows

def fetch_thanks_groups(csv_path: str) -> Dict[str, List[str]]:
    """CSVから分類ごとに名前リストを取得（1列目:名前, 2列目:分類）"""
    groups = defaultdict(list)
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    name = row[0].strip()
                    group = row[1].strip() if len(row) > 1 and row[1].strip() else "その他"
                    groups[group].append(name)
    return groups

def build_csv_url(edit_url: str) -> str:
    """編集URLからCSVエクスポートURLを生成（gid未指定時は0）"""
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
    """CSVエクスポートURLから行を取得してDictのリストに変換"""
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

# 追加: 共通ユーティリティ（重複削減）
def to_int(val: str) -> int:
    s = (val or "").replace(",", "").replace("回", "").replace(" ", "")
    try:
        return int(s)
    except:
        return 0

def to_iso_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except:
            pass
    import re
    m = re.search(r"(\d{4})[./-]?(\d{1,2})(?:[./-]?(\d{1,2}))?", s)
    if m:
        y, mo, da = m.group(1), m.group(2).zfill(2), (m.group(3) or "01").zfill(2)
        return f"{y}-{mo}-{da}"
    return ""

def fetch_videos_from_sheet(edit_url: str) -> Dict[str, List[Dict]]:
    """Googleスプレッドシートから切り抜き(非公式)データを取得（種類ごとに分類）"""
    videos = defaultdict(list)
    try:
        for row in fetch_csv_rows(edit_url):
            category = (row.get("種類") or "").strip() or "その他"
            date_str = (row.get("投稿日時") or "").strip()
            try:
                date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            except:
                date_obj = datetime.min
            video_id = (row.get("video_id") or "").strip()
            title = (row.get("タイトル") or "").strip()
            if not video_id:
                continue
            videos[category].append({
                "video_id": video_id,
                "title": title,
                "date": date_str,
                "date_obj": date_obj
            })
        for category in videos:
            videos[category].sort(key=lambda x: x["date_obj"], reverse=True)
    except Exception as e:
        print(f"切り抜き(非公式)データ取得に失敗: {e}")
    return videos

def fetch_covers_from_sheet(edit_url: str, top_n: int = 10) -> List[Dict]:
    """100万未満の動画から上位N件を返す"""
    rows_csv = fetch_csv_rows(edit_url)
    out: List[Dict] = []
    try:
        for row in rows_csv:
            vid = (row.get("動画ID") or "").strip()
            if not vid:
                continue
            views = to_int(row.get("再生数") or "")
            if views > 1_000_000:
                continue
            out.append({
                "video_id": vid,
                "title": (row.get("タイトル") or "").strip() or "(タイトル不明)",
                "views": views,
                "date": (row.get("投稿日（日本時間）") or "").strip(),
                "gap_to_million": 1_000_000 - views
            })
        out.sort(key=lambda r: (r["gap_to_million"], -r["views"]))
        return out[:top_n]
    except Exception as e:
        print(f"歌動画取得に失敗: {e}")
        return []

def fetch_trending_from_sheet(edit_url: str, top_n: int | None = None) -> List[Dict]:
    """伸びた動画データを取得（top_n未指定時は全件）"""
    rows_csv = fetch_csv_rows(edit_url)
    out: List[Dict] = []
    try:
        for row in rows_csv:
            vid = (row.get("動画ID") or "").strip()
            if not vid:
                continue
            increase = to_int(row.get("増加数") or "")
            current_views = to_int(row.get("現在再生数") or "")
            out.append({
                "video_id": vid,
                "title": (row.get("タイトル") or "").strip() or "(タイトル不明)",
                "increase": increase,
                "current_views": current_views,
                "date": (row.get("投稿日") or "").strip(),
                "channel": (row.get("チャンネル") or "").strip(),
            })
        out.sort(key=lambda r: r["increase"], reverse=True)
        return out[:top_n] if top_n else out
    except Exception as e:
        print(f"伸びた動画取得に失敗: {e}")
        return []

def fetch_covers_all_from_sheet(edit_url: str) -> List[Dict]:
    """ALL表から歌動画一覧を取得（タグをフラグ化）"""
    rows_csv = fetch_csv_rows(edit_url)
    try:
        def parse_tags(tag_raw: str) -> Dict[str, bool]:
            s = (tag_raw or "")
            s_lower = s.lower()
            has_unit = ("はのこと" in s) or ("ハコリリ" in s) or ("ハコニワリリィ" in s) or ("hakoniwa" in s_lower) or ("hakoniwalily" in s_lower)
            has_hanon = ("hanon" in s_lower)
            has_kotoha = ("kotoha" in s_lower)
            return {"unit": has_unit, "hanon": has_hanon, "kotoha": has_kotoha}

        rows: List[Dict] = []
        for row in rows_csv:
            vid = (row.get("動画ID") or row.get("video_id") or "").strip()
            if not vid:
                continue
            flags = parse_tags((row.get("タグ") or row.get("tag") or "").strip())
            main_tag = "unit" if (flags["unit"] or (flags["hanon"] and flags["kotoha"])) else ("hanon" if flags["hanon"] else ("kotoha" if flags["kotoha"] else "unit"))
            rows.append({
                "video_id": vid,
                "title": (row.get("タイトル") or "").strip() or "(タイトル不明)",
                "date": to_iso_date(row.get("投稿日") or row.get("投稿日（日本時間）") or row.get("投稿日時") or ""),
                "views": to_int(row.get("再生数") or row.get("現在再生数") or ""),
                "tag": main_tag,
                "unit_flag": 1 if flags["unit"] else 0,
                "hanon_flag": 1 if flags["hanon"] else 0,
                "kotoha_flag": 1 if flags["kotoha"] else 0,
            })
        return rows
    except Exception as e:
        print(f"歌動画ALL取得に失敗: {e}")
        return []

def fetch_albums_from_sheet(edit_url: str) -> List[Dict]:
    """アルバム一覧を取得（ネットワーク処理を共通化）"""
    rows_csv = fetch_csv_rows(edit_url)
    albums: List[Dict] = []
    try:
        for row in rows_csv:
            name = (row.get("名前") or row.get("name") or "").strip()
            if not name:
                continue
            albums.append({
                "name": name,
                "release_date": to_iso_date(row.get("リリース日") or row.get("release_date") or ""),
                "image": f"image/CD/{name}.png",
                "comment": (row.get("一言") or "").strip()
            })
        albums.sort(key=lambda a: a["release_date"] or "", reverse=True)
    except Exception as e:
        print(f"アルバム一覧取得に失敗: {e}")
    return albums

# 追加: シングル一覧を取得
def fetch_singles_from_sheet(edit_url: str) -> List[Dict]:
    """シングル一覧を取得（列名のゆらぎに対応）"""
    rows_csv = fetch_csv_rows(edit_url)
    singles: List[Dict] = []
    try:
        for row in rows_csv:
            # タイトル列のゆらぎに対応
            name = (row.get("名前") or row.get("title") or row.get("タイトル") or row.get("name") or "").strip()
            if not name:
                continue
            release_raw = (row.get("リリース日") or row.get("発売日") or row.get("release_date") or row.get("date") or "").strip()
            comment = (row.get("一言") or row.get("備考") or row.get("comment") or "").strip()
            singles.append({
                "name": name,
                "release_date": to_iso_date(release_raw),
                "image": f"image/CD/{name}.png",
                "comment": comment
            })
        singles.sort(key=lambda a: a["release_date"] or "", reverse=True)
    except Exception as e:
        print(f"シングル一覧取得に失敗: {e}")
    return singles

# 追加: リリース楽曲一覧を取得
def fetch_release_songs_from_sheet(edit_url: str) -> List[Dict]:
    """リリース楽曲一覧を取得（楽曲名・種別・表紙・歌唱フラグに対応）"""
    rows_csv = fetch_csv_rows(edit_url)
    songs: List[Dict] = []
    try:
        for row in rows_csv:
            name = (row.get("楽曲名") or row.get("曲名") or row.get("タイトル") or row.get("name") or "").strip()
            if not name:
                continue
            # 種別
            raw_kind = (row.get("種別") or row.get("タイプ") or row.get("カテゴリ") or row.get("category") or row.get("type") or "").strip()
            kind_lower = raw_kind.lower()
            kind_code = "original" if ("オリ" in raw_kind or "original" in kind_lower or kind_lower.startswith("ori")) else ("cover" if ("カバ" in raw_kind or "cover" in kind_lower) else "other")
            # 画像
            cover = (row.get("表紙") or row.get("ジャケット") or row.get("cover") or row.get("image") or name).strip()
            release_date = to_iso_date(row.get("リリース日") or row.get("release_date") or "")
            # 歌唱（タグ/歌唱者のゆらぎに対応）
            s_raw = (row.get("歌唱") or row.get("歌唱者") or row.get("歌手") or row.get("singer") or row.get("タグ") or row.get("tag") or "").strip()
            s_lower = s_raw.lower()
            has_unit = ("はのこと" in s_raw) or ("ハコリリ" in s_raw) or ("ハコニワリリィ" in s_raw) or ("hakoniwa" in s_lower) or ("hakoniwalily" in s_lower)
            has_hanon = ("hanon" in s_lower)
            has_kotoha = ("kotoha" in s_lower)
            # ID（並び順用)
            sheet_id = to_int(row.get("ID") or row.get("id") or row.get("No") or row.get("no") or "")

            songs.append({
                "name": name,
                "kind": raw_kind or "不明",
                "kind_code": kind_code,
                "image": f"image/CD/{cover}.png",
                "release_date": release_date,
                "unit_flag": 1 if has_unit else 0,
                "hanon_flag": 1 if has_hanon else 0,
                "kotoha_flag": 1 if has_kotoha else 0,
                "_id": sheet_id
            })

        # 並び順: シートIDの降順。IDが無ければ日付→名前の降順。
        if any(s.get("_id", 0) for s in songs):
            songs.sort(key=lambda a: a.get("_id", 0), reverse=True)
        else:
            songs.sort(key=lambda a: (a.get("release_date") or "", a["name"]), reverse=True)
    except Exception as e:
        print(f"リリース楽曲一覧取得に失敗: {e}")
    return songs

def make_song_slug(name: str, sheet_id: int) -> str:
    """曲ページ用の安全なファイル名を生成（ID付き）"""
    import re
    base = (name or "").strip()
    # Windows不可文字を除去
    base = re.sub(r'[\\/:*?"<>|]', '', base)
    base = re.sub(r'\s+', '_', base)
    return f"{sheet_id}-{base}" if sheet_id and sheet_id > 0 else base

def make_cd_slug(name: str) -> str:
    """CDページ用の安全なファイル名を生成（名前のみでスラッグ化）"""
    import re
    base = (name or "").strip()
    base = re.sub(r'[\\/:*?"<>|]', '', base)  # Windows不可文字を除去
    base = re.sub(r'\s+', '_', base)          # 空白→アンダースコア
    return base or "untitled"

def generate_music_section(albums: List[Dict]) -> str:
    """リリース（アルバム一覧＋シングル一覧＋楽曲一覧）セクションHTML生成"""
    section_parts = ["""
<section id='music' class='section' role='region' aria-labelledby='music-heading'>
  <h2 id='music-heading'><i class='fa-solid fa-headphones'></i>リリース</h2>
"""]

    # アルバム一覧
    section_parts.append("""
  <h3 class='videos-heading'><i class='fa-solid fa-compact-disc'></i> アルバム</h3>
""")
    if albums:
        section_parts.append("""
  <div class='videos-carousel-wrapper'>
    <button class='carousel-btn prev' aria-label='前へ'>
      <i class='fa-solid fa-chevron-left'></i>
    </button>
    <div class='videos-carousel'>
""")
        for a in albums:
            disp_date = a["release_date"].replace("-", "/") if a["release_date"] else ""
            comment_html = f"<div class='album-comment'>{a.get('comment', '')}</div>" if a.get("comment") else ""
            slug = make_cd_slug(a["name"])  # 追加: スラッグ
            section_parts.append(f"""
      <div class='video-card'>
        <a href='CDs/{slug}.html' class='video-thumb album-thumb' aria-label='{a['name']}の詳細ページ'>
          <img src='{a["image"]}' alt='{a['name']}' loading='lazy'>
        </a>
        <div>
          <div class='video-meta'><i class='fa-regular fa-calendar'></i> {disp_date}</div>
          {comment_html}
          <a class='video-title' href='CDs/{slug}.html'>{a['name']}</a>
        </div>
      </div>
""")
        section_parts.append("""
    </div>
    <button class='carousel-btn next' aria-label='次へ'>
      <i class='fa-solid fa-chevron-right'></i>
    </button>
  </div>
""")
    else:
        section_parts.append("<p class='video-meta'>アルバム情報を取得できませんでした。</p>\n")

    # シングル一覧
    singles = fetch_singles_from_sheet(SINGLES_SHEET_EDIT_URL)
    section_parts.append("""
  <h3 class='videos-heading'><i class='fa-solid fa-music'></i> シングル</h3>
""")
    if singles:
        section_parts.append("""
  <div class='videos-carousel-wrapper'>
    <button class='carousel-btn prev' aria-label='前へ'>
      <i class='fa-solid fa-chevron-left'></i>
    </button>
    <div class='videos-carousel'>
""")
        for s in singles:
            disp_date = s["release_date"].replace("-", "/") if s["release_date"] else ""
            comment_html = f"<div class='album-comment'>{s.get('comment', '')}</div>" if s.get("comment") else ""
            slug = make_cd_slug(s["name"])  # 追加: スラッグ
            section_parts.append(f"""
      <div class='video-card'>
        <a href='CDs/{slug}.html' class='video-thumb album-thumb' aria-label='{s['name']}の詳細ページ'>
          <img src='{s["image"]}' alt='{s['name']}' loading='lazy'>
        </a>
        <div>
          <div class='video-meta'><i class='fa-regular fa-calendar'></i> {disp_date}</div>
          {comment_html}
          <a class='video-title' href='CDs/{slug}.html'>{s['name']}</a>
        </div>
      </div>
""")
        section_parts.append("""
    </div>
    <button class='carousel-btn next' aria-label='次へ'>
      <i class='fa-solid fa-chevron-right'></i>
    </button>
  </div>
""")
    else:
        section_parts.append("<p class='video-meta'>シングル情報を取得できませんでした。</p>\n")

    # リリース楽曲一覧（フィルター＋全件グリッド表示）
    songs = fetch_release_songs_from_sheet(SONGS_SHEET_EDIT_URL)
    section_parts.append("""
  <h3 class='videos-heading'><i class='fa-solid fa-list'></i> リリース曲一覧（ALL）</h3>
  <div class='covers-controls list-controls' id='release-songs-controls' aria-label='リリース曲のフィルター'>
    <div class='filter-group' role='group' aria-label='歌唱でフィルター'>
      <label class='filter-chip'><input type='radio' name='release-singer' value='all' checked> すべて</label>
      <label class='filter-chip'><input type='radio' name='release-singer' value='unit'> はのこと／ハコリリ</label>
      <label class='filter-chip'><input type='radio' name='release-singer' value='hanon'> Hanon</label>
      <label class='filter-chip'><input type='radio' name='release-singer' value='kotoha'> Kotoha</label>
    </div>
    　
    <div class='filter-group' role='group' aria-label='種別でフィルター'>
      <label class='filter-chip'><input type='radio' name='release-kind' value='all' checked> すべて</label>
      <label class='filter-chip'><input type='radio' name='release-kind' value='original'> オリジナル</label>
      <label class='filter-chip'><input type='radio' name='release-kind' value='cover'> カバー</label>
    </div>
    <!-- 追加: キーワード検索 -->
    <div class='search-group' role='search' aria-label='キーワード検索'>
      <input type='text' class='list-search release-search' placeholder='キーワード検索（曲名）'>
      <button type='button' class='list-search-clear release-search-clear' aria-label='検索クリア'>×</button>
    </div>
  </div>
""")
    if songs:
        section_parts.append("""
  <div class='songs-grid' id='release-songs-grid' aria-live='polite'>
""")
        for s in songs:
            # 追加: 各曲ページへのリンク
            slug = make_song_slug(s['name'], int(s.get('_id', 0)))
            kind_html = f"<div class='video-meta'><i class='fa-solid fa-tag'></i> {s.get('kind','')}</div>" if s.get("kind") else ""
            section_parts.append(f"""
    <div class='song-card'
         data-unit='{s.get('unit_flag',0)}'
         data-hanon='{s.get('hanon_flag',0)}'
         data-kotoha='{s.get('kotoha_flag',0)}'
         data-kind='{s.get('kind_code','other')}'
         data-title='{s['name']}'
         data-slug='{slug}'>
      <a href='songs/{slug}.html' class='video-thumb' aria-label='{s['name']}の詳細ページ'>
        <img src='{s["image"]}' alt='{s['name']}' loading='lazy'>
      </a>
      <div>
        {kind_html}
        <a href='songs/{slug}.html' class='video-title'>{s['name']}</a>
      </div>
    </div>
""")
        section_parts.append("""
  </div>
""")
    else:
        section_parts.append("<p class='video-meta'>楽曲情報を取得できませんでした。</p>\n")

    # セクション終端
    section_parts.append("</section>\n")
    return "".join(section_parts)

# 追加: 歌動画セクション（TOP10/ALL一覧）
def generate_covers_section(trending: List[Dict], covers_all: List[Dict]) -> str:
    section = """
<section id='covers' class='section' role='region' aria-labelledby='covers-heading'>
  <h2 id='covers-heading'><i class='fa-solid fa-microphone-lines'></i>歌動画</h2>
"""
    # 伸びた動画TOP10
    if trending:
        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime("%Y/%m/%d")
        end_date = (today - timedelta(days=1)).strftime("%Y/%m/%d")
        section += f"""
  <h3 class='videos-heading'>
    <i class='fa-solid fa-chart-line'></i> 伸びた動画TOP10
  </h3>
  <p class='video-meta spaced'>直近7日間の再生数増加ランキング<span class="br-sp"></span>（{start_date}～{end_date}）</p>
  <div class='videos-carousel-wrapper'>
    <button class='carousel-btn prev' aria-label='前へ'>
      <i class='fa-solid fa-chevron-left'></i>
    </button>
    <div class='videos-carousel'>
"""
        cards = []
        for i, v in enumerate(trending[:10], 1):
            thumb = f"https://i.ytimg.com/vi/{v['video_id']}/mqdefault.jpg"
            url = f"https://www.youtube.com/watch?v={v['video_id']}"
            current_fmt = f"{v['current_views']:,}"
            date_part = f"<div class='video-meta'><i class='fa-regular fa-calendar'></i> {v.get('date','')}</div>" if v.get("date") else ""
            channel_part = f"<div class='video-meta'><i class='fa-solid fa-tv'></i> {v.get('channel','')}</div>" if v.get("channel") else ""
            cards.append(f"""
      <div class='video-card'>
        <div class='video-rank'>{i}</div>
        <a href='{url}' target='_blank' rel='noopener noreferrer' class='video-thumb'>
          <img src='{thumb}' alt='{v['title']}' loading='lazy'>
        </a>
        <div>
          {date_part}
          {channel_part}
          <div class='video-meta'><i class='fa-solid fa-eye'></i> {current_fmt} 回</div>
          <a href='{url}' target='_blank' rel='noopener noreferrer'>{v['title']}</a>
        </div>
      </div>
""")
        section += "".join(cards) + """
    </div>
    <button class='carousel-btn next' aria-label='次へ'>
      <i class='fa-solid fa-chevron-right'></i>
    </button>
  </div>
"""

    trending_increase_map = { v.get("video_id"): int(v.get("increase", 0)) for v in (trending or []) }
    section += """
  <h3 class='videos-heading'>
    <i class='fa-solid fa-list'></i> 歌動画一覧（ALL）
  </h3>
"""
    if covers_all:
        section += """
  <div class='covers-controls list-controls' aria-label='歌動画のフィルターと並び替え'>
    <div class='filter-group' role='group' aria-label='チャンネル種別でフィルター'>
      <label class='filter-chip'><input type='radio' name='covers-tag' value='all' checked> すべて</label>
      <label class='filter-chip'><input type='radio' name='covers-tag' value='unit'> はのこと／ハコリリ</label>
      <label class='filter-chip'><input type='radio' name='covers-tag' value='hanon'> Hanon</label>
      <label class='filter-chip'><input type='radio' name='covers-tag' value='kotoha'> Kotoha</label>
    </div>
    <div class='sort-group'>
      <label>
        <select class='covers-sort-key'>
          <option value='date_desc'>投稿日（新しい順）</option>
          <option value='date_asc'>投稿日（古い順）</option>
          <option value='views_desc'>再生数（多い順）</option>
          <option value='views_asc'>再生数（少ない順）</option>
          <option value='popularity_desc'>人気順（直近7日増加数）</option>
        </select>
      </label>
    </div>
    <!-- 追加: キーワード検索 -->
    <div class='search-group' role='search' aria-label='キーワード検索'>
      <input type='text' class='list-search covers-search' placeholder='キーワード検索（タイトル）'>
      <button type='button' class='list-search-clear covers-search-clear' aria-label='検索クリア'>×</button>
    </div>
  </div>
  <div class='songs-grid' id='covers-all-grid' aria-live='polite'>
"""
        cards = []
        for r in covers_all:
            popularity = trending_increase_map.get(r['video_id'], 0)
            thumb = f"https://i.ytimg.com/vi/{r['video_id']}/mqdefault.jpg"
            url = f"https://www.youtube.com/watch?v={r['video_id']}"
            views_fmt = f"{int(r.get('views', 0)):,}"
            date_disp = r["date"].replace("-", "/") if r["date"] else ""
            cards.append(f"""
    <div class='song-card'
         data-tag='{r['tag']}'
         data-unit='{1 if r.get('unit_flag') else 0}'
         data-hanon='{1 if r.get('hanon_flag') else 0}'
         data-kotoha='{1 if r.get('kotoha_flag') else 0}'
         data-views='{int(r.get('views', 0))}'
         data-date='{r['date']}'
         data-title='{r['title']}'
         data-popularity='{popularity}'>
      <a href='{url}' target='_blank' rel='noopener noreferrer' class='video-thumb'>
        <img src='{thumb}' alt='{r['title']}' loading='lazy'>
      </a>
      <div>
        <div class='video-meta'><i class='fa-regular fa-calendar'></i> {date_disp}</div>
        <div class='video-meta'><i class='fa-solid fa-eye'></i> {views_fmt} 回</div>
        <a href='{url}' target='_blank' rel='noopener noreferrer'>{r['title']}</a>
      </div>
    </div>
""")
        section += "".join(cards) + """
  </div>
"""
    else:
        section += "<p class='video-meta'>ALL表のデータを取得できませんでした。</p>"

    section += """
</section>
"""
    return section

def fetch_concerts_from_db(db_path: str) -> List[Dict]:
    """ライブ管理DB: ツアー→公演→セトリ。セトリはツアー単位でINクエリ一括取得."""
    data: List[Dict] = []
    if not os.path.exists(db_path):
        return data
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            # 変更: sort_order で昇順ソート（NULL は末尾）
            cur.execute("""
                SELECT id, name, page_link, goods, sort_order
                FROM tours
                ORDER BY COALESCE(sort_order, 999999), id
            """)
            tours = cur.fetchall()
            for tour_id, tour_name, page_link, goods, sort_order in tours:
                cur.execute(
                    "SELECT id, name, date, venue, performer FROM concerts WHERE tour_id=? ORDER BY date, id",
                    (tour_id,)
                )
                concerts_raw = cur.fetchall()
                concert_ids = [row[0] for row in concerts_raw]
                setlists_map: Dict[int, List[Dict]] = defaultdict(list)
                if concert_ids:
                    placeholders = ",".join("?" for _ in concert_ids)
                    cur.execute(
                        f"SELECT concert_id, order_no, song_title, singer, encore FROM setlists WHERE concert_id IN ({placeholders}) ORDER BY concert_id, order_no",
                        concert_ids
                    )
                    for cid, order_no, title, singer, encore in cur.fetchall():
                        setlists_map[cid].append({
                            "order": order_no, "title": title, "singer": (singer or ""), "encore": 1 if (encore or 0) else 0
                        })
                concerts: List[Dict] = []
                for concert_id, concert_name, date, venue, performer in concerts_raw:
                    concerts.append({
                        "id": concert_id,
                        "name": concert_name or "",
                        "date": date or "",
                        "venue": venue or "",
                        "performer": performer or "",
                        "setlist": setlists_map.get(concert_id, [])
                    })
                data.append({
                    "id": tour_id,
                    "name": tour_name or "",
                    "page_link": page_link or "",
                    "goods": goods or "",
                    "sort_order": sort_order,  # 任意保持
                    "concerts": concerts
                })
    except Exception as e:
        print(f"ライブデータ取得に失敗: {e}")
    return data

# 追加: コンサートセクションHTML生成（削除されていたため復元）
def generate_concert_section(concert_data: List[Dict]) -> str:
    section = """
<section id='concert' class='section' role='region' aria-labelledby='concert-heading'>
  <h2 id='concert-heading'><i class='fa-solid fa-music'></i>ライブ</h2>
"""
    if not concert_data:
        section += "<p class='video-meta'>ライブデータがありません。</p></section>"
        return section

    section += """
  <div class='concert-layout'>
    <nav class='concert-list' aria-label='ライブ一覧'>
"""
    def perf_class(p: str) -> str:
        if p == "Hanon":
            return "perf-hanon"
        if p == "Kotoha":
            return "perf-kotoha"
        if p == "はのこと/ハコリリ":
            return "perf-unit"
        return ""

    first_concert_id = None
    for tour in concert_data:
        link_part = ""
        if tour.get("goods"):
            link_part += f" <a href='{tour['goods']}' target='_blank' rel='noopener noreferrer'><i class='fa-solid fa-bag-shopping'></i></a>"
        if tour.get("page_link"):
            link_part += f" <a href='{tour['page_link']}' target='_blank' rel='noopener noreferrer'><i class='fa-solid fa-link'></i></a>"
        section += f"      <div class='concert-group'>\n"
        section += (
            f"        <div class='concert-tour'>"
            f"<button class='concert-toggle' type='button' aria-expanded='false' aria-controls='tour-items-{tour['id']}'>"
            f"<i class='fa-solid fa-caret-right caret' aria-hidden='true'></i>{tour['name']}</button>"
            f"{link_part}</div>\n"
        )
        section += f"        <ul id='tour-items-{tour['id']}' class='concert-items' hidden>\n"
        for c in tour["concerts"]:
            if first_concert_id is None:
                first_concert_id = c["id"]
            name_part = f" {c['name']}" if c["name"] else ""
            venue_part = f" @ {c['venue']}" if c["venue"] else ""
            perf_cls = perf_class(c.get("performer", ""))
            perf_dot = f"<span class='perf-dot {perf_cls}' title='{c.get('performer','')}' aria-hidden='true'></span>" if perf_cls else ""
            section += (
                f"          <li class='concert-item' tabindex='0' data-concert-id='{c['id']}' "
                f"aria-controls='concert-detail-{c['id']}'><span class='concert-date'>"
                f"{perf_dot}{c['date']}</span>"
                f"<span class='concert-name'>{name_part}</span><span class='concert-venue'>{venue_part}</span></li>\n"
            )
        section += f"        </ul>\n"
        section += f"      </div>\n"
    section += "    </nav>\n"

    section += "    <div class='concert-detail' role='region' aria-live='polite'>\n"
    for tour in concert_data:
        for c in tour["concerts"]:
            active = " active" if c["id"] == first_concert_id else ""
            section += f"      <div id='concert-detail-{c['id']}' class='concert-detail-panel{active}' data-concert-id='{c['id']}'>\n"
            # 変更: タイトルを2ブロックに分割（1行目: 日付＋公演名、2行目: 会場）
            main_line = f"{c['date']}" + (f" {c['name']}" if c.get("name") else "")
            venue_html = c.get("venue", "")
            perf_cls = perf_class(c.get("performer", ""))
            perf_dot = f"<span class='perf-dot {perf_cls}' title='{c.get('performer','')}' aria-hidden='true'></span>" if perf_cls else ""
            section += (
                "        <h3 class='concert-detail-title'>"
                f"<span class='concert-title-row'>{perf_dot}<span class='concert-title-main'>{main_line}</span></span>"
            )
            if venue_html:
                section += f"<span class='concert-venue'>{venue_html}</span>"
            section += "</h3>\n"
            if c["setlist"]:
                section += "        <ol class='setlist'>\n"
                for s in c["setlist"]:
                    encore_part = " <span class='setlist-encore'>[EN]</span>" if s.get("encore") else ""
                    singer_part = f" <span class='setlist-singer'>({s['singer']})</span>" if s["singer"] else ""
                    section += f"          <li><span class='setlist-title'>{s['title']}</span>{encore_part}{singer_part}</li>\n"
                section += "        </ol>\n"
            else:
                section += "        <p class='video-meta'>セトリ情報がありません。</p>\n"
            section += "      </div>\n"
    section += "    </div>\n"
    section += "  </div>\n</section>\n"
    return section

def generate_videos_section(videos_by_category: Dict[str, List[Dict]]) -> str:
    """切り抜き(非公式)セクションHTML生成（一覧のみ）"""
    section = """
<section id='videos' class='section' role='region' aria-labelledby='videos-heading'>
  <h2 id='videos-heading'><i class='fa-brands fa-youtube'></i>切り抜き(非公式)</h2>
"""
    # フラット化
    all_items = []
    cat_token = {"はのこと": "hanokoto", "見どころはのぴ": "hanopi", "ことメモ": "kotomemo"}
    for cat, items in videos_by_category.items():
        for v in items:
            date_obj = v.get("date_obj")
            iso_date = date_obj.strftime("%Y-%m-%d") if isinstance(date_obj, datetime) and date_obj != datetime.min else ""
            all_items.append({
                "video_id": v["video_id"],
                "title": v["title"],
                "date": v.get("date", ""),
                "iso_date": iso_date,
                "cat": cat_token.get(cat, "other")
            })
    all_items.sort(key=lambda x: x["iso_date"], reverse=True)

    section += """
  <h3 class='videos-heading'>
    <i class='fa-solid fa-list'></i> 切り抜き一覧（ALL）
  </h3>
  <div class='covers-controls list-controls' aria-label='切り抜きのフィルターと並び替え'>
    <div class='filter-group' role='group' aria-label='種類でフィルター'>
      <label class='filter-chip'><input type='radio' name='clips-cat' value='all' checked> すべて</label>
      <label class='filter-chip'><input type='radio' name='clips-cat' value='hanokoto'> はのこと</label>
      <label class='filter-chip'><input type='radio' name='clips-cat' value='hanopi'> 見どころはのぴ</label>
      <label class='filter-chip'><input type='radio' name='clips-cat' value='kotomemo'> ことメモ</label>
    </div>
    <div class='sort-group'>
      <label>
        <select class='clips-sort-key'>
          <option value='date_desc'>投稿日（新しい順）</option>
          <option value='date_asc'>投稿日（古い順）</option>
        </select>
      </label>
    </div>
  </div>
  <div class='songs-grid' id='clips-all-grid' aria-live='polite'>
"""
    cards = []
    for r in all_items:
        thumb = f"https://i.ytimg.com/vi/{r['video_id']}/mqdefault.jpg"
        url = f"https://www.youtube.com/watch?v={r['video_id']}"
        date_disp = (r["iso_date"].replace("-", "/") if r["iso_date"] else r["date"])
        cards.append(f"""
    <div class='song-card' data-cat='{r['cat']}' data-date='{r['iso_date']}' data-title='{r['title']}'>
      <a href='{url}' target='_blank' rel='noopener noreferrer' class='video-thumb'>
        <img src='{thumb}' alt='{r['title']}' loading='lazy'>
      </a>
      <div>
        <div class='video-meta'><i class='fa-regular fa-calendar'></i> {date_disp}</div>
        <a href='{url}' target='_blank' rel='noopener noreferrer'>{r['title']}</a>
      </div>
    </div>
""")
    section += "".join(cards) + """
  </div>
</section>
"""
    return section

# 追加: タイムライン用のタブ/パネルIDを生成
def make_timeline_ids(index: int):
    return f"timeline-tab-{index}", f"timeline-panel-{index}"

# 追加: サイトについてセクション生成
def generate_about_section() -> str:
    return """
<section id='about' class='section' role='region' aria-labelledby='about-heading'>
  <h2 id='about-heading'><i class='fa-solid fa-circle-info'></i>サイトについて</h2>
  <div class='about-lead'>
    <i class='fa-solid fa-book-open' aria-hidden='true'></i>
    <p>このサイトは、Hanon、Kotohaおよび2人のユニットであるハコニワリリィの活動記録するものです。</p>
  </div>
  <div class='about-grid'>
    <div class='about-card'>
      <h3><i class='fa-solid fa-bullseye'></i>目的</h3>
      <ul>
        <li>過去の出来事を振り返りやすくする</li>
        <li>新規ファンが活動履歴を把握しやすくする</li>
      </ul>
      <h3><i class='fa-solid fa-user-gear'></i>運営者</h3>
      <p><strong>はのこと切り抜きch</strong></p>
      <ul class='about-links'>
      <p>サイトに関するお問い合わせは、以下のいずれかの方法でご連絡ください。</p>
      <ul class='about-links'>
        <li><a href='https://x.com/hanokoto901' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i> Twitter</a></li>
        <li><a href='https://docs.google.com/forms/d/e/1FAIpQLSc61BbrO9hLEr_GXxsUcD9sxGXIZm7mXlKDlP7YnyS_kAnARA/viewform' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-wpforms'></i> Googleフォーム</a></li>
      </ul>
    </div>
  </div>
  <div class='about-card'>
    <h3><i class='fa-solid fa-link'></i>参考元</h3>
    <div class='reference-links'>
      <div class='ref-group'>
        <h4>ハコニワリリィ (Hanon × Kotoha)</h4>
        <ul class='about-links'>
          <li><a href='https://hakoniwalily.jp/' target='_blank' rel='noopener noreferrer'><i class='fa-solid fa-globe'></i> 公式HP</a></li>
          <li><a href='https://twitter.com/HaKoniwalily' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i> Twitter</a></li>
          <li><a href='https://www.youtube.com/@HaKoniwalily' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a></li>
          <li><a href='https://vt.tiktok.com/ZSJGuyk4H/' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-tiktok'></i> TikTok</a></li>
        </ul>
      </div>
      <div class='ref-group'>
        <h4>Hanon</h4>
        <ul class='about-links'>
          <li><a href='https://twitter.com/Hanon_moco' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i> Twitter</a></li>
          <li><a href='https://www.youtube.com/@Hanon_moco' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a></li>
          <li><a href='https://twitcasting.tv/hanon_moco/' target='_blank' rel='noopener noreferrer'><i class='fa-solid fa-broadcast-tower'></i> ツイキャス</a></li>
        </ul>
      </div>
      <div class='ref-group'>
        <h4>Kotoha</h4>
        <ul class='about-links'>
          <li><a href='https://twitter.com/Kotoha_ktnh' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i> Twitter</a></li>
          <li><a href='https://www.youtube.com/@Kotoha_ktnh' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a></li>
          <li><a href='https://twitcasting.tv/kotoha_ktnh/' target='_blank' rel='noopener noreferrer'><i class='fa-solid fa-broadcast-tower'></i> ツイキャス</a></li>
          <li><a href='https://www.twitch.tv/kotoha_hkll' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitch'></i> Twitch</a></li>
        </ul>
      </div>
      <div class='ref-group'>
        <h4>AiceClass</h4>
        <ul class='about-links'>
          <li><a href='https://aiceclass.com/' target='_blank' rel='noopener noreferrer'><i class='fa-solid fa-globe'></i> 公式HP</a></li>
          <li><a href='https://twitter.com/aiceclass' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i> Twitter</a></li>
          <li><a href='https://www.youtube.com/@aiceclass' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a></li>
        </ul>
      </div>
    </div>
  </div>
  <div class='about-card about-disclaimer'>
    <h3><i class='fa-solid fa-shield-halved'></i>免責事項</h3>
    <p>このサイトは非公式のファンサイトです。掲載されている情報は可能な限り正確性を保つよう努めていますが、誤りや漏れがある可能性があります。公式情報は各公式チャンネルやSNSアカウントをご確認ください。</p>
  </div>
</section>"""

# 追加: 情報提供セクション生成
def generate_contribute_section() -> str:
    return """
<section id='contribute' class='section contribute-section' role='region' aria-labelledby='contribute-heading'>
  <h2 id='contribute-heading'><i class='fa-brands fa-wpforms'></i>情報提供</h2>
  <p class='contribute-subtitle'>年表に追加・訂正すべき情報がありましたら、Googleフォームからお知らせください。入力内容は次の<strong>7項目</strong>です。<br>ご協力いただいた方のお名前は<strong>Thanksページに掲載</strong>させていただきます（ご希望の方のみ）。</p>
  <div class='contribute-chips'>
    <span class='chip'><i class='fa-solid fa-calendar-days'></i> 時期</span>
    <span class='chip'><i class='fa-solid fa-note-sticky'></i> 内容</span>
    <span class='chip'><i class='fa-solid fa-link'></i> リンク</span>
    <span class='chip'><i class='fa-solid fa-paperclip'></i> 内容を補足するファイル</span>
    <span class='chip'><i class='fa-solid fa-user'></i> お名前</span>
    <span class='chip'><i class='fa-solid fa-at'></i> 連絡先</span>
    <span class='chip'><i class='fa-solid fa-circle-info'></i> その他</span>
  </div>
  <div class='contribute-grid'>
    <div class='contribute-card'>
      <h3>記入項目</h3>
      <dl class='form-fields'>
        <dt><i class='fa-solid fa-calendar-days'></i> 時期</dt>
        <dd>出来事が発生した時期（例：YYYY/MM/DD、YYYY年MM月頃 など）</dd>
        <dt><i class='fa-solid fa-note-sticky'></i> 内容</dt>
        <dd>出来事の概要（できるだけ具体的に）</dd>
        <dt><i class='fa-solid fa-link'></i> リンク</dt>
        <dd>関連する動画や配信、SNSの投稿等のURL</dd>
        <dt><i class='fa-solid fa-paperclip'></i> 内容を補足するファイル</dt>
        <dd>任意。スクリーンショットや資料など</dd>
        <dt><i class='fa-solid fa-user'></i> お名前</dt>
        <dd>任意。SNSのユーザー名やハンドルネーム</dd>
        <dt><i class='fa-solid fa-at'></i> 連絡先</dt>
        <dd>任意。確認が必要な場合の連絡手段（Twitter/メアド等）</dd>
        <dt><i class='fa-solid fa-circle-info'></i> その他</dt>
        <dd>任意。補足情報や注意事項などがあればご記入ください。</dd>
      </dl>
    </div>
    <div class='contribute-card'>
      <h3>記入例</h3>
      <div class='form-sample'>
        <p><strong>時期：</strong>2021年4月頃</p>
        <p><strong>内容：</strong> Kotohaちゃんが鍋の蓋を割る</p>
        <p><strong>リンク：</strong> <a href='https://x.com/Kotoha_ktnh/status/1377621531304603648' target='_blank' rel='noopener noreferrer'>https://x.com/Kotoha_ktnh/status/1377621531304603648</a></p>
        <p><strong>内容を補足するファイル：</strong> なし</p>
        <p><strong>お名前：</strong> はのこと切り抜きch</p>
        <p><strong>連絡先：</strong> @hanokoto901 (Twitter)</p>
        <p><strong>その他：</strong> なし</p>
      </div>
    </div>
  </div>
  <div class='contribute-cta'>
    <div class='notice-emphasis' role='note' aria-live='polite'>
      <i class='fa-solid fa-circle-exclamation icon' aria-hidden='true'></i>
      <span>ボタンを押すと、<strong>Googleフォーム</strong>が開きます。送信内容は<strong>管理者が確認後</strong>、<strong>年表に反映</strong>します。</span>
    </div>
    <div class='google-form-container'>
      <a href='https://docs.google.com/forms/d/e/1FAIpQLSc61BbrO9hLEr_GXxsUcD9sxGXIZm7mXlKDlP7YnyS_kAnARA/viewform' target='_blank' rel='noopener noreferrer' class='google-form-button'>
        <i class='fa-brands fa-wpforms'></i> フォームに記入する
      </a>
    </div>
    <p class='form-note-text'>
      フォームが使いづらい場合は、TwitterのDMでも受け付けています：
      <a href='https://x.com/hanokoto901' target='_blank' rel='noopener noreferrer'>@hanokoto901</a>
    </p>
  </div>
</section>"""

# 追加: Thanksセクション生成
def generate_thanks_section(thanks_groups: Dict[str, List[str]]) -> str:
    parts = ["""
<section id='thanks' class='section' role='region' aria-labelledby='thanks-heading'>
  <h2 id='thanks-heading'><i class='fa-solid fa-heart'></i>Thanks</h2>
  <p style='margin-bottom: 16px; color: var(--text-secondary); font-size: 14px;'>
    このサイトの運営にご協力いただいた皆様のお名前を掲載しています（公開希望者のみ）。<br>
    情報提供やアンケートへのご協力、誠にありがとうございます。
  </p>
"""]
    for group, names in thanks_groups.items():
        parts.append(f"<h3><i class='fa-solid fa-users'></i> {group}</h3>\n<ul class='thanks-name-list'>")
        for name in names:
            parts.append(f"<li class='thanks-name-item'>{name}</li>")
        parts.append("</ul>\n")
    parts.append("<p class='thanks-note'>（順不同・公開希望者のみ掲載）</p>\n</section>\n")
    return "".join(parts)

def generate_html_with_classification_tabs(grouped_records: Dict) -> str:
    """分類ごとのレコードをタブ切り替えで表示する HTML を生成"""
    header = """<!DOCTYPE html>
<html lang='ja'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>はのこと活動記録｜Hanon＆Kotoha・ハコニワリリィ活動記録</title>
<meta name='description' content='Hanon＆Kotoha（はのこと）とハコニワリリィ（ハコリリ）の活動を時系列でまとめたファンアーカイブサイト。年表形式で二人の歩みを記録しています。'>
<meta property='og:title' content='はのこと活動記録｜Hanon＆Kotoha・ハコニワリリィ活動記録'>
<meta property='og:description' content='Hanon＆Kotoha（はのこと）とハコニワリリィ（ハコリリ）の活動を時系列でまとめたファンアーカイブサイト。年表形式で二人の歩みを記録しています。'>
<meta property='og:type' content='website'>
<meta property='og:url' content='https://yoursite.com/'>
<meta property='og:image' content='https://yoursite.com/image/ogp.png'>
<meta name='twitter:card' content='summary_large_image'>
<link rel='icon' type='image/png' href='image/icon.png'>
<link rel='icon' type='image/x-icon' href='image/icon.ico'>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
<link rel='stylesheet' href='style.css'>
<script src='script.js' defer></script>
</head>
<body>
<header class='site-header'>
  <div class='header-left'>
    <img src='image/header.png' alt='はのこと活動記録' class='header-logo'>
    <nav class='header-nav' aria-label='サイト内メニュー'>
      <a class='nav-link' href='#home' data-section='home' aria-controls='home' aria-current='page'><i class='fa-solid fa-house'></i>ホーム</a>
      <a class='nav-link' href='#music' data-section='music' aria-controls='music'><i class='fa-solid fa-headphones'></i>リリース</a>
      <a class='nav-link' href='#covers' data-section='covers' aria-controls='covers'><i class='fa-solid fa-microphone-lines'></i>歌動画</a>
      <a class='nav-link' href='#concert' data-section='concert' aria-controls='concert'><i class='fa-solid fa-music'></i>ライブ</a>
      <a class='nav-link' href='#videos' data-section='videos' aria-controls='videos'><i class='fa-brands fa-youtube'></i>切り抜き(非公式)</a>
      <a class='nav-link' href='#about' data-section='about' aria-controls='about'><i class='fa-solid fa-circle-info'></i>サイトについて</a>
      <a class='nav-link' href='#contribute' data-section='contribute' aria-controls='contribute'><i class='fa-brands fa-wpforms'></i>情報提供</a>
      <a class='nav-link' href='#thanks' data-section='thanks' aria-controls='thanks'><i class='fa-solid fa-heart'></i>Thanks</a>
    </nav>
  </div>
  <a class='header-button' href='https://x.com/hanokoto901' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i>Twitter</a>
  <a class='header-button youtube' href='https://www.youtube.com/channel/UCepZVSTaKBW4ux0RB-nQ_NQ' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i>YouTube</a>
</header>
<main id='main' tabindex='-1'>
<section id='home' class='section home-section' role='region' aria-labelledby='home-heading'>  
  <div class='home-notice'>
    <i class='fa-solid fa-bullhorn notice-icon' aria-hidden='true'></i>
    <div class='notice-content'>
      <div class='notice-title'>
        <i class='fa-solid fa-flask'></i> このサイトはβ版です
      </div>
      <p class='notice-text'>サイトの改善に向けてアンケートを実施しています。ご協力いただいた方のお名前（ご希望の方のみ）は<strong>Thanksページ</strong>に掲載させていただきます。<br><br><strong>年表</strong>や<strong>一部ライブ</strong>のセトリの入力が終わっていませんのでご注意ください。<br></p>
      <a href='https://docs.google.com/forms/d/e/1FAIpQLSfw4X07SbSNHFhH0NzdOS8S7BHTFsmAt9LtLw0Ij1ihuhWvUg/viewform?usp=preview' target='_blank' rel='noopener noreferrer' class='notice-link'>
        <i class='fa-brands fa-wpforms'></i> アンケートに回答する
      </a>
    </div>
  </div>
    <h2 id='home-heading'><i class="fa-solid fa-book"></i>年表</h2>
  <div class='tabs' role='tablist' aria-label='年表分類タブ'>"""
    # タブ順の整備
    classifications = list(grouped_records.keys())
    preferred = "はのこと・ハコリリ"
    if preferred in classifications:
        classifications.remove(preferred)
        classifications.insert(0, preferred)

    # 件数カウント
    classification_counts = {}
    for cls in classifications:
        years = grouped_records.get(cls, {})
        classification_counts[cls] = sum(
            len(items)
            for months in years.values()
            for genres in months.values()
            for items in genres.values()
        )

    # タブとパネル
    tabs = []
    panels = []
    for i, classification in enumerate(classifications):
        is_active = i == 0
        active_class = "active" if is_active else ""
        aria_selected = "true" if is_active else "false"
        # ここをわかりやすいIDに統一
        tab_id, panel_id = make_timeline_ids(i)
        count = classification_counts.get(classification, 0)
        short_label = classification.replace("はのこと・ハコリリ", "はのこと")

        tabs.append(
            f"<button class='tab {active_class}' data-class='{classification}' role='tab' "
            f"id='{tab_id}' aria-controls='{panel_id}' aria-selected='{aria_selected}' "
            f"tabindex='{'0' if is_active else '-1'}' aria-label='{classification}（{count}件）'>"
            f"<span class='tab-label'>"
            f"<span class='tab-text-full'>{classification}</span>"
            f"<span class='tab-text-short'>{short_label}</span>"
            f"<span class='tab-badge'>{count}</span>"
            f"</span>"
            f"</button>"
        )

        table_rows = generate_table_rows(grouped_records[classification])
        panels.append(
            f"<div class='tab-content {active_class}' role='tabpanel' id='{panel_id}' "
            f"aria-labelledby='{tab_id}' aria-hidden='{'false' if is_active else 'true'}'>"
            f"<div class='table-responsive'>"
            f"<table><thead><tr><th class='fit'>年</th><th class='fit'>月</th>"
            f"<th class='fix'>主な出来事</th><th class='fix'>ライブ</th>"
            f"<th class='fix'>動画</th><th class='fix'>その他</th></tr></thead>"
            f"<tbody>{''.join(table_rows)}</tbody></table>"
            f"</div></div>"
        )

    # 既存セクションを順に生成
    # リリース
    albums = fetch_albums_from_sheet(ALBUMS_SHEET_EDIT_URL)
    music_section = generate_music_section(albums)
    # 歌動画
    trending = fetch_trending_from_sheet(TRENDING_SHEET_EDIT_URL, top_n=None)
    covers_all = fetch_covers_all_from_sheet(COVERS_ALL_SHEET_EDIT_URL)
    covers_section = generate_covers_section(trending, covers_all)
    # 切り抜き(非公式)
    videos = fetch_videos_from_sheet(VIDEOS_SHEET_EDIT_URL)
    videos_section = generate_videos_section(videos)
    # ライブ
    concert_data = fetch_concerts_from_db(CONCERT_DB)
    concert_section = generate_concert_section(concert_data)
    # サイトについて / 情報提供 / Thanks を分離関数で生成
    about_section = generate_about_section()
    contribute_section = generate_contribute_section()
    thanks_section = generate_thanks_section(fetch_thanks_groups(THANKS_CSV))

    # フッター
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    footer = f"""
</main>
<footer class='site-footer'>
  <div class='footer-content'>
    <div class='footer-updated'>
      <i class='fa-solid fa-clock'></i> 最終更新: {current_time}
    </div>
    <div class='footer-links'>
      <a href='https://x.com/hanokoto901' target='_blank' rel='noopener noreferrer'>
        <i class='fa-brands fa-twitter'></i> Twitter
      </a>
      <a href='https://www.youtube.com/channel/UCepZVSTaKBW4ux0RB-nQ_NQ' target='_blank' rel='noopener noreferrer'>
        <i class='fa-brands fa-youtube'></i> YouTube
      </a>
    </div>
    <div class='footer-copyright'>
      © 2025 - はのこと活動記録
    </div>
  </div>
</footer>
</body></html>"""

    return f"{header}{''.join(tabs)}</div>{''.join(panels)}</section>{music_section}{covers_section}{videos_section}{concert_section}{about_section}{contribute_section}{thanks_section}{footer}"

def save_html(content: str, filepath: str):
    """HTML コンテンツをファイルに保存"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    """メイン処理"""
    if not os.path.exists(DB_FILE):
        print(f"データベースファイル '{DB_FILE}' が見つかりません。")
        return

    records = fetch_records()
    if not records:
        print("データベースにレコードがありません。")
        return

    grouped_records = group_records_by_classification_and_date(records)
    html_content = generate_html_with_classification_tabs(grouped_records)
    save_html(html_content, OUTPUT_FILE)
    print(f"年表を '{OUTPUT_FILE}' に生成しました。")

if __name__ == "__main__":
    main()
