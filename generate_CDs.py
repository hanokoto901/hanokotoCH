"""アルバム・シングルの詳細ページ（CDs/*.html）を生成する"""

import sys
from typing import Dict, List

from common import (
    ALBUMS_SHEET_EDIT_URL, SINGLES_SHEET_EDIT_URL, SONGS_SHEET_EDIT_URL,
    FetchError, fetch_csv_rows, first_value, to_int, to_iso_date,
    make_cd_slug, make_song_slug, cd_image, normalize_title, split_list, esc, esc_url,
    render_detail_page, write_pages,
)

OUTPUT_DIR = "CDs"


def read_items(edit_url: str) -> List[Dict]:
    out: List[Dict] = []
    for r in fetch_csv_rows(edit_url):
        name = first_value(r, "名前", "name")
        if not name:
            continue
        out.append({
            "name": name,
            "slug": make_cd_slug(name),
            "image": cd_image(name, "../"),
            "date": to_iso_date(first_value(r, "リリース日", "release_date")),
            "oneword": first_value(r, "一言", "comment"),
            "tracks": split_list(first_value(r, "収録曲", "tracks")),
            "videos": split_list(first_value(r, "視聴動画", "video")),
            "desc": first_value(r, "説明", "description"),
        })
    return out


def read_songs_index(edit_url: str) -> Dict[str, str]:
    """楽曲シートから 正規化タイトル → 曲ページのスラッグ の索引を作成（同名は後勝ち）"""
    index: Dict[str, str] = {}
    for r in fetch_csv_rows(edit_url):
        name = first_value(r, "楽曲名", "曲名", "タイトル", "name")
        key = normalize_title(name)
        if key:
            index[key] = make_song_slug(name, to_int(first_value(r, "ID", "id", "No", "no")))
    return index


def render_cd_html(item: Dict, kind_label: str, songs_index: Dict[str, str]) -> str:
    date_disp = item["date"].replace("-", "/")
    if item["tracks"]:
        lis = []
        for t in item["tracks"]:
            slug = songs_index.get(normalize_title(t))
            lis.append(f"<li><a href='../songs/{esc(slug)}.html'>{esc(t)}</a></li>" if slug else f"<li>{esc(t)}</li>")
        tracks_html = "<ol class='tracks'>" + "".join(lis) + "</ol>"
    else:
        tracks_html = "<p class='video-meta'>収録曲情報がありません。</p>"

    links = "".join(
        f"<a class='header-button youtube' href='{esc_url(v)}' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> 視聴動画</a> "
        for v in item["videos"] if esc_url(v)
    )
    videos_html = f"<div class='meta-row'><div class='chips'>{links}</div></div>" if links else ""
    # 一言・説明は管理者がHTML（<br> など）を書く欄なのでエスケープしない
    oneword_html = f"<div class='album-comment'>{item['oneword']}</div>" if item["oneword"] else ""
    desc_html = f"<div class='desc-note'>{item['desc']}</div>" if item["desc"] else ""
    name = esc(item["name"])

    main_html = f"""  <h2 class='song-title'><i class='fa-solid fa-compact-disc'></i> {name}</h2>

  <div class='song-hero'>
    <img src='{esc(item["image"])}' alt='{name}' loading='lazy'>
    <div class='song-hero-meta'>
      <div class='video-meta'><i class='fa-regular fa-calendar'></i> {date_disp}</div>
      {oneword_html}
      {desc_html}
      <h3><i class='fa-solid fa-list'></i> 収録曲</h3>
      {tracks_html}
      {videos_html}
    </div>
  </div>
"""
    return render_detail_page(
        title=f"{item['name']}｜{kind_label}詳細",
        description=f"Hanon＆Kotoha（はのこと）とハコニワリリィ（ハコリリ）の活動を記録するファンアーカイブサイトの{kind_label}詳細ページ。",
        page_path=f"CDs/{item['slug']}.html",
        body_class="page-cd",
        main_html=main_html,
    )


def main() -> None:
    albums = read_items(ALBUMS_SHEET_EDIT_URL)
    singles = read_items(SINGLES_SHEET_EDIT_URL)
    songs_index = read_songs_index(SONGS_SHEET_EDIT_URL)
    if not (albums or singles):
        raise FetchError("アルバム・シングルのシートにデータがありません。")
    if not songs_index:
        raise FetchError("楽曲シートにデータがありません（収録曲のリンクを作れません）。")

    pages: Dict[str, str] = {}
    for a in albums:
        pages[f"{a['slug']}.html"] = render_cd_html(a, "アルバム", songs_index)
    for s in singles:
        pages[f"{s['slug']}.html"] = render_cd_html(s, "シングル", songs_index)
    write_pages(OUTPUT_DIR, pages)
    print(f"アルバム {len(albums)} 件、シングル {len(singles)} 件のページを生成しました。")


if __name__ == "__main__":
    try:
        main()
    except FetchError as e:
        print(f"エラー: {e}\n既存のページは変更していません。")
        sys.exit(1)
