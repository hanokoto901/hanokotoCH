"""リリース曲の詳細ページ（songs/*.html）を生成する"""

import os
import re
import sys
from typing import Dict, List

from common import (
    SONGS_SHEET_EDIT_URL, FetchError, fetch_csv_rows, first_value, to_int, to_iso_date,
    kind_code, make_song_slug, make_cd_slug, cd_image, split_list, esc, esc_url,
    render_detail_page, write_pages,
)

OUTPUT_DIR = "songs"
CD_PAGES_DIR = "CDs"  # generate_CDs.py の出力先（収録CDのリンク先が存在するかの確認に使う）
_missing_albums: Dict[str, int] = {}
PAGE_DESCRIPTION = "Hanon＆Kotoha（はのこと）とハコニワリリィ（ハコリリ）の活動を記録するファンアーカイブサイトのリリース曲詳細ページ。"

# クレジットのキー（英語）→ 表示ラベル。複数語のキーは空白の有無を問わず一致する
CREDIT_LABELS = {
    "lyrics": "作詞",
    "music": "作曲",
    "arrangement": "編曲",
    "guitar": "ギター",
    "acoustic guitar": "アコースティックギター",
    "bass": "ベース",
    "keyboard": "キーボード",
    "piano": "ピアノ",
    "electric piano": "エレクトリックピアノ",
    "programming": "プログラミング",
    "programing": "プログラミング",
    "drums": "ドラム",
    "drum technician": "ドラムテクニシャン",
    "chorus": "コーラス",
    "backing chorus": "コーラス",
    "choir": "コーラス",
    "strings": "ストリングス",
    "strings arrangement": "ストリングスアレンジ",
    "strings programming": "ストリングスプログラミング",
    "strings programing": "ストリングスプログラミング",
    "mix": "MIX",
    "mastering": "マスタリング",
    "illust": "イラスト",
    "movie": "映像",
    "animation": "アニメーション",
}
_LABEL_BY_NORMALIZED_KEY = {k.replace(" ", ""): v for k, v in CREDIT_LABELS.items()}
# 長いキーを優先。前後が英字でないことで単語の区切りを判定する
# （\b は「Bass小林」のように漢字が続くと区切りとみなされないため使わない）
_CREDIT_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z])("
    + "|".join(k.replace(" ", r"\s*") for k in sorted(CREDIT_LABELS, key=len, reverse=True))
    + r")(?![A-Za-z])\s*[:：]?"
)


def parse_credits(raw: str) -> List[Dict[str, str]]:
    """「Guitar:中西 Bass小林修己」のようなクレジット文字列を ラベル→値 のリストに分解"""
    s = (raw or "").strip()
    matches = list(_CREDIT_PATTERN.finditer(s))
    parts = []
    for i, m in enumerate(matches):
        key = re.sub(r"\s+", "", m.group(1)).lower()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(s)
        value = s[m.end():end].strip().replace(",", "、")
        if value:
            parts.append({"label": _LABEL_BY_NORMALIZED_KEY.get(key, key), "value": value})
    return parts


def read_songs(edit_url: str) -> List[Dict]:
    out: List[Dict] = []
    for r in fetch_csv_rows(edit_url):
        name = first_value(r, "楽曲名", "曲名", "タイトル", "name")
        if not name:
            continue
        kind_raw = first_value(r, "種別", "タイプ", "カテゴリ", "category", "type")
        cover_key = first_value(r, "表紙", "ジャケット", "cover", "image") or name
        out.append({
            "name": name,
            "slug": make_song_slug(name, to_int(first_value(r, "ID", "id", "No", "no"))),
            "image": cd_image(cover_key, "../"),
            "release_date": to_iso_date(first_value(r, "リリース日", "release_date")),
            "albums": split_list(first_value(r, "収録", "収録(収録CD)", "album")),
            "kind": kind_raw or "不明",
            "kind_code": kind_code(kind_raw),
            "youtube": first_value(r, "YouTubeリンク", "Youtubeリンク", "Youtube", "URL"),
            "lyrics": first_value(r, "作詞"),
            "composer": first_value(r, "作曲"),
            "arranger": first_value(r, "編曲"),
            "vocals": split_list(first_value(r, "ボーカル", "vocal")),
            "credit_raw": first_value(r, "クレジット", "credit"),
        })
    return out


def render_credits(song: Dict) -> str:
    rows = []
    shown = set()
    for label, value in (("作詞", song["lyrics"]), ("作曲", song["composer"]), ("編曲", song["arranger"])):
        if value:
            rows.append((label, value))
            shown.add(label)
    # クレジット文字列の解析結果を追加（専用列で表示済みのラベルだけスキップ）
    for item in parse_credits(song["credit_raw"]):
        if item["label"] not in shown:
            rows.append((item["label"], item["value"]))
    if not rows:
        return "<p class='video-meta'>クレジット情報がありません。</p>"
    trs = "".join(f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>" for label, value in rows)
    return f"<table class='credit-table'>{trs}</table>"


def render_song_html(song: Dict) -> str:
    date_disp = song["release_date"].replace("-", "/")
    album_chips = []
    for a in song["albums"]:
        slug = make_cd_slug(a)
        if os.path.exists(os.path.join(CD_PAGES_DIR, f"{slug}.html")):
            album_chips.append(f"<a class='chip' href='../CDs/{esc(slug)}.html'>{esc(a)}</a>")
        else:
            # CDページが無い（シートの表記ゆれ等）場合はリンクにしない
            album_chips.append(f"<span class='chip'>{esc(a)}</span>")
            _missing_albums[a] = _missing_albums.get(a, 0) + 1
    albums_html = "".join(album_chips) or "<span class='chip muted'>（収録情報なし）</span>"
    vocals_html = (
        "".join(f"<span class='chip alt'>{esc(v)}</span>" for v in song["vocals"])
        or "<span class='chip muted'>（ボーカル情報なし）</span>"
    )
    yt_url = esc_url(song["youtube"])
    yt_html = (
        f"<a class='header-button youtube' href='{yt_url}' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a>"
        if yt_url else "<span class='chip muted'>（リンクなし）</span>"
    )
    name = esc(song["name"])
    main_html = f"""  <h2 class='song-title'><i class='fa-solid fa-music'></i> {name}</h2>

  <div class='song-hero'>
    <img src='{esc(song["image"])}' alt='{name}' loading='lazy'>
    <div class='song-hero-meta'>
      <div class='video-meta'><i class='fa-regular fa-calendar'></i> {date_disp}</div>
      <div class='video-meta'><i class='fa-solid fa-tag'></i> {esc(song["kind"])}</div>
      <div class='meta-row'>
        <span class='meta-label'>収録</span>
        <div class='chips'>{albums_html}</div>
      </div>
      <div class='meta-row'>
        <span class='meta-label'>ボーカル</span>
        <div class='chips'>{vocals_html}</div>
      </div>
      <div class='meta-row'>
        <div class='chips'>{yt_html}</div>
      </div>
    </div>
  </div>

  <h3><i class='fa-solid fa-list'></i> クレジット</h3>
  {render_credits(song)}"""
    return render_detail_page(
        title=f"{song['name']}｜リリース曲詳細",
        description=PAGE_DESCRIPTION,
        page_path=f"songs/{song['slug']}.html",
        body_class="page-song",
        main_html=main_html,
    )


def main() -> None:
    songs = read_songs(SONGS_SHEET_EDIT_URL)
    if not songs:
        raise FetchError("楽曲シートにデータがありません。")
    pages = {f"{s['slug']}.html": render_song_html(s) for s in songs}
    if len(pages) < len(songs):
        print(f"  注意: ファイル名が重複している曲があります（{len(songs)}曲 → {len(pages)}ページ）")
    write_pages(OUTPUT_DIR, pages)
    print(f"{len(pages)}件の曲ページを生成しました。")
    for name, count in _missing_albums.items():
        print(f"  注意: 収録「{name}」に対応するCDページがありません（{count}曲）。"
              f"楽曲シートの「収録」とアルバム/シングルシートの「名前」の表記をそろえてください。")


if __name__ == "__main__":
    try:
        main()
    except FetchError as e:
        print(f"エラー: {e}\n既存のページは変更していません。")
        sys.exit(1)
