"""はのこと活動記録 - 生成スクリプト共通モジュール

generate.py / generate_CDs.py / generate_songs.py から共通で使う
設定値・データ取得・文字列変換・HTML部品をまとめたもの。
"""

import csv
import glob
import html
import io
import os
import re
import urllib.request
from datetime import datetime
from typing import Dict, List

# ============================================================
# サイト設定
# ============================================================

# 公開URL（末尾スラッシュなし）。例: "https://example.github.io/hanokoto"
# 空のままだと og:url / og:image は出力しない（相対URLではSNSが画像を取得できないため）
SITE_URL = "https://hanokoto901.github.io/hanokotoCH/"
# OGP画像（サイトルートからの相対パス）。SNSでは 1200x630 程度の画像が推奨
OGP_IMAGE = "image/ogp.png"

# ジャケット画像: 元画像（image/CD/*.png）から表示用の縮小版（image/thumb/*.webp）を作って使う
CD_IMAGE_DIR = "image/CD"
CD_THUMB_DIR = "image/thumb"
CD_THUMB_SIZE = 600  # 長辺px（表示は最大220px程度。高解像度画面でもぼやけない大きさ）

SITE_NAME = "はのこと活動記録"
COPYRIGHT_START_YEAR = 2025
FONT_AWESOME_CSS = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"

TWITTER_URL = "https://x.com/hanokoto901"
YOUTUBE_URL = "https://www.youtube.com/channel/UCepZVSTaKBW4ux0RB-nQ_NQ"

# ============================================================
# スプレッドシート（編集URL → CSVエクスポートURLへ変換して取得）
# ============================================================

VIDEOS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/161eDUFzWgGW5TCuyzZ3GR3OCEaaNfq-LDWJibdF6Ar4/edit?gid=413704367#gid=413704367"
COVERS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1Y1mFAj-RHV8VFx9A7w1W1QyJ9-RYxcAW4c2tbF5N_-w/edit?gid=0#gid=0"
TRENDING_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1Y1mFAj-RHV8VFx9A7w1W1QyJ9-RYxcAW4c2tbF5N_-w/edit?gid=1174580202#gid=1174580202"
COVERS_ALL_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1Y1mFAj-RHV8VFx9A7w1W1QyJ9-RYxcAW4c2tbF5N_-w/edit?ouid=112508527560905085845&usp=sheets_home&ths=true"
ALBUMS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=27271597#gid=27271597"
SINGLES_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=1975989717#gid=1975989717"
SONGS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1JxMwz-tLJlrP2wjoWqDOOC3oly2qIGp9FDNJSpdu3Sc/edit?gid=0#gid=0"


class FetchError(Exception):
    """スプレッドシートの取得に失敗したことを表す例外"""


def build_csv_url(edit_url: str) -> str:
    """編集URLからCSVエクスポートURLを生成（gid未指定時は0）"""
    m = re.search(r"/d/([^/]+)", edit_url)
    if not m:
        return ""
    g = re.search(r"gid=(\d+)", edit_url)
    gid = g.group(1) if g else "0"
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={gid}"


# 同じプロセス内で同じシートを何度も取得しないためのキャッシュ（build.py で一括実行するとき用）
_csv_cache: Dict[str, List[Dict]] = {}


def fetch_csv_rows(edit_url: str) -> List[Dict]:
    """シートをCSVとして取得し Dict のリストで返す。失敗時は FetchError を送出する"""
    csv_url = build_csv_url(edit_url)
    if not csv_url:
        raise FetchError(f"スプレッドシートのURLが不正です: {edit_url}")
    if csv_url in _csv_cache:
        return _csv_cache[csv_url]
    try:
        with urllib.request.urlopen(csv_url, timeout=20) as resp:
            data = resp.read().decode("utf-8-sig", errors="replace")
    except Exception as e:
        raise FetchError(f"CSV取得に失敗しました（{csv_url}）: {e}") from e
    if data.lstrip().lower().startswith(("<!doctype html", "<html")):
        # 非公開シートなどではログイン画面のHTMLが返ってくる
        raise FetchError(f"CSVではなくHTMLが返されました。シートの公開設定を確認してください（{csv_url}）")
    rows = list(csv.DictReader(io.StringIO(data)))
    _csv_cache[csv_url] = rows
    return rows


def first_value(row: Dict, *keys: str) -> str:
    """列名のゆらぎに対応して、最初に値が入っている列の値を返す（前後空白除去）"""
    for k in keys:
        v = row.get(k)
        if v and v.strip():
            return v.strip()
    return ""


# ============================================================
# 文字列変換
# ============================================================

def to_int(val: str) -> int:
    s = (val or "").replace(",", "").replace("回", "").replace(" ", "")
    try:
        return int(s)
    except ValueError:
        return 0


def to_iso_date(s: str) -> str:
    """いろいろな日付表記を YYYY-MM-DD に揃える（日が無ければ01日）"""
    s = (s or "").strip()
    if not s:
        return ""
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    m = re.search(r"(\d{4})[./-]?(\d{1,2})(?:[./-]?(\d{1,2}))?", s)
    if m:
        y, mo, da = m.group(1), m.group(2).zfill(2), (m.group(3) or "01").zfill(2)
        return f"{y}-{mo}-{da}"
    return ""


def kind_code(raw_kind: str) -> str:
    """種別（オリジナル/カバー）をフィルター用コードに変換"""
    raw = raw_kind or ""
    k = raw.strip().lower()
    if ("オリ" in raw) or ("original" in k) or k.startswith("ori"):
        return "original"
    if ("カバ" in raw) or ("cover" in k):
        return "cover"
    return "other"


def _safe_filename(name: str) -> str:
    base = (name or "").strip()
    base = re.sub(r'[\\/:*?"<>|]', '', base)  # Windowsで使えない文字を除去
    return re.sub(r'\s+', '_', base)          # 空白→アンダースコア


def make_song_slug(name: str, sheet_id: int) -> str:
    """曲ページのファイル名（ID-曲名）"""
    base = _safe_filename(name) or "untitled"
    return f"{sheet_id}-{base}" if sheet_id and sheet_id > 0 else base


def make_cd_slug(name: str) -> str:
    """CDページのファイル名（名前のみ）"""
    return _safe_filename(name) or "untitled"


def normalize_title(s: str) -> str:
    """曲名のゆるい正規化（空白/記号の除去・小文字化）。CDの収録曲と曲ページの照合用"""
    s = (s or "").strip().lower()
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[\\/:*?"<>|()\[\]{}【】（）・・、,，。.!！?？\'"～〜\-–—_^`　]+', '', s)
    return s


def cd_image(key: str, prefix: str = "") -> str:
    """ジャケット画像のパス（prefix はページから見た相対位置。例: "../"）。
    縮小版を作れればそれを、作れなければ元のPNGを返す。縮小版は元画像が新しくなったときだけ作り直す"""
    src = os.path.join(CD_IMAGE_DIR, f"{key}.png")
    thumb = os.path.join(CD_THUMB_DIR, f"{key}.webp")
    if os.path.exists(src):
        try:
            # GitHub Actions 上ではチェックアウト時に更新日時がそろわないため、縮小版が無いときだけ作る
            outdated = not os.environ.get("CI") and os.path.getmtime(thumb) < os.path.getmtime(src) \
                if os.path.exists(thumb) else True
            if outdated:
                from PIL import Image  # Pillow が無い環境では元のPNGを使う
                os.makedirs(CD_THUMB_DIR, exist_ok=True)
                with Image.open(src) as im:
                    im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
                    im.thumbnail((CD_THUMB_SIZE, CD_THUMB_SIZE), Image.LANCZOS)
                    im.save(thumb, "WEBP", quality=85, method=6)
            return f"{prefix}{CD_THUMB_DIR}/{key}.webp"
        except Exception as e:  # 画像処理に失敗してもページ生成は止めない
            print(f"  注意: 縮小画像を作れませんでした（{src}）: {e}")
    return f"{prefix}{CD_IMAGE_DIR}/{key}.png"


def clean_thumbnails() -> None:
    """元画像が無くなった縮小版を削除する"""
    for path in glob.glob(os.path.join(CD_THUMB_DIR, "*.webp")):
        key = os.path.splitext(os.path.basename(path))[0]
        if not os.path.exists(os.path.join(CD_IMAGE_DIR, f"{key}.png")):
            os.remove(path)
            print(f"  古い縮小画像を削除: {path}")


def split_list(raw: str) -> List[str]:
    """カンマ区切りを分割してトリム（空要素は除外）"""
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


# ============================================================
# HTML
# ============================================================

def esc(s) -> str:
    """テキスト・属性値用のHTMLエスケープ（' と " も変換）"""
    return html.escape(str(s if s is not None else ""), quote=True)


def esc_url(url: str) -> str:
    """リンクURL用。javascript: などのスキームは無効化してからエスケープ"""
    u = (url or "").strip()
    if re.match(r"(?i)^\s*(javascript|data|vbscript):", u):
        return ""
    return esc(u)


def copyright_text() -> str:
    year = datetime.now().year
    years = f"{COPYRIGHT_START_YEAR}" if year <= COPYRIGHT_START_YEAR else f"{COPYRIGHT_START_YEAR}-{year}"
    return f"© {years} - {SITE_NAME}"


def ogp_meta(title: str, description: str, page_path: str = "") -> str:
    """OGP / Twitterカードのmetaタグ。SITE_URL 未設定時は絶対URLが必要なタグを省く"""
    tags = [
        f"<meta property='og:title' content='{esc(title)}'>",
        f"<meta property='og:description' content='{esc(description)}'>",
        "<meta property='og:type' content='website'>",
        f"<meta property='og:site_name' content='{esc(SITE_NAME)}'>",
    ]
    if SITE_URL:
        base = SITE_URL.rstrip("/")
        tags.append(f"<meta property='og:url' content='{esc(base + '/' + page_path)}'>")
        tags.append(f"<meta property='og:image' content='{esc(base + '/' + OGP_IMAGE)}'>")
        tags.append("<meta name='twitter:card' content='summary_large_image'>")
    else:
        tags.append("<meta name='twitter:card' content='summary'>")
    return "\n".join(tags)


def render_footer(updated: str = "") -> str:
    """全ページ共通フッター。updated を渡すと最終更新日時を表示"""
    updated_html = (
        f"\n    <div class='footer-updated'><i class='fa-solid fa-clock'></i> 最終更新: {esc(updated)}</div>"
        if updated else ""
    )
    return f"""
<footer class='site-footer'>
  <div class='footer-content'>{updated_html}
    <div class='footer-links'>
      <a href='{TWITTER_URL}' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i> Twitter</a>
      <a href='{YOUTUBE_URL}' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a>
    </div>
    <div class='footer-copyright'>{copyright_text()}</div>
  </div>
</footer>
"""


def render_detail_page(*, title: str, description: str, page_path: str, body_class: str, main_html: str) -> str:
    """曲ページ・CDページ共通のHTML骨格（songs/ や CDs/ から ../ で参照）"""
    return f"""<!DOCTYPE html>
<html lang='ja'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>{esc(title)}</title>
<meta name='description' content='{esc(description)}'>
{ogp_meta(title, description, page_path)}
<link rel='icon' type='image/png' href='../image/icon.png'>
<link rel='icon' type='image/x-icon' href='../image/icon.ico'>
<link rel='stylesheet' href='{FONT_AWESOME_CSS}'>
<link rel='stylesheet' href='../assets/detail.css'>
</head>
<body class='{body_class}'>
<header class='site-header'>
  <div class='header-left'>
    <a href='../index.html?restore=music' class='nav-link'><i class='fa-solid fa-arrow-left'></i> リリースへ戻る</a>
  </div>
</header>
<main class='section'>
{main_html}
</main>
{render_footer()}
<button class='back-to-top' aria-label='ページトップへ戻る'><i class='fa-solid fa-arrow-up'></i></button>
<script src='../assets/detail.js' defer></script>
</body>
</html>"""


def save_html(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def write_pages(output_dir: str, pages: Dict[str, str]) -> None:
    """ファイル名→HTML の辞書を出力し、今回生成しなかった古い .html を削除する"""
    os.makedirs(output_dir, exist_ok=True)
    for filename, content in pages.items():
        save_html(os.path.join(output_dir, filename), content)
    for path in glob.glob(os.path.join(output_dir, "*.html")):
        if os.path.basename(path) not in pages:
            os.remove(path)
            print(f"  古いページを削除: {path}")
