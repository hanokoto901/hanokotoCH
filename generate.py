import sqlite3
from typing import List, Dict
from collections import defaultdict
import os
from datetime import datetime
import csv
# 追加: GoogleスプレッドシートCSV取得用
import urllib.request
import io

DB_FILE = "data/history.db"
OUTPUT_FILE = "index.html"
THANKS_CSV = "data/thanks.csv"
# 変更: 切り抜き紹介用にスプレッドシートURLを追加（シート名：site）
VIDEOS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/161eDUFzWgGW5TCuyzZ3GR3OCEaaNfq-LDWJibdF6Ar4/edit?gid=413704367#gid=413704367"
# 追加: 歌みた紹介用スプレッドシートURL（編集リンク→CSVエクスポートURLに変換して使用）
COVERS_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1Y1mFAj-RHV8VFx9A7w1W1QyJ9-RYxcAW4c2tbF5N_-w/edit?gid=0#gid=0"
# 追加: 伸びた動画シート用URL
TRENDING_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1Y1mFAj-RHV8VFx9A7w1W1QyJ9-RYxcAW4c2tbF5N_-w/edit?gid=1882797807#gid=1882797807"

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

def fetch_thanks_names(csv_path: str) -> List[str]:
    """CSVから名前リストを取得（1列目のみ）"""
    names = []
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    names.append(row[0].strip())
    return names

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

# 追加: Googleスプレッドシートから切り抜き紹介データを取得
def fetch_videos_from_sheet(edit_url: str) -> Dict[str, List[Dict]]:
    """
    Googleスプレッドシートから切り抜き紹介データを取得（種類ごとに分類）
    期待ヘッダー: video_id, タイトル, 投稿日時, 種類
    """
    from datetime import datetime
    
    videos = defaultdict(list)
    try:
        # 編集URL → CSVエクスポートURLへ（gidを抽出してシート指定）
        parts = edit_url.split("/d/")
        if len(parts) < 2:
            return videos
        rest = parts[1]
        sheet_id = rest.split("/")[0]
        # gidを抽出（なければ0）
        gid = "0"
        if "gid=" in edit_url:
            try:
                gid = edit_url.split("gid=")[1].split("&")[0].split("#")[0]
            except:
                gid = "0"
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

        with urllib.request.urlopen(csv_url, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(data))
        
        for row in reader:
            category = row.get("種類", "").strip() or "その他"
            date_str = row.get("投稿日時", "").strip()
            
            # 日付をパース（YYYY/MM/DD形式を想定）
            try:
                date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            except:
                date_obj = datetime.min  # パース失敗時は最古扱い
            
            video_id = row.get("video_id", "").strip()
            title = row.get("タイトル", "").strip()
            
            if not video_id:
                continue
            
            videos[category].append({
                "video_id": video_id,
                "title": title,
                "date": date_str,
                "date_obj": date_obj
            })
        
        # 各カテゴリで日付降順にソート
        for category in videos:
            videos[category].sort(key=lambda x: x["date_obj"], reverse=True)
        
    except Exception as e:
        print(f"切り抜き紹介データ取得に失敗: {e}")
    
    return videos

# 追加: 歌みた（カバー）動画データの取得
def fetch_covers_from_sheet(edit_url: str, top_n: int = 10) -> List[Dict]:
    """
    GoogleスプレッドシートからCSVを取得し、
    「再生数」100万以下で100万に近い順に上位N件を返す。
    期待ヘッダー: 動画ID, タイトル, 再生数, 投稿日（存在すれば）
    """
    try:
        # 編集URL → CSVエクスポートURLへ
        # 例: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0
        parts = edit_url.split("/d/")
        if len(parts) < 2:
            return []
        rest = parts[1]
        sheet_id = rest.split("/")[0]
        # gidを抽出（なければ0）
        gid = "0"
        if "gid=" in edit_url:
            try:
                gid = edit_url.split("gid=")[1].split("&")[0].split("#")[0]
            except:
                gid = "0"
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

        with urllib.request.urlopen(csv_url, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(data))
        rows = []
        for row in reader:
            vid = (row.get("動画ID") or "").strip()
            title = (row.get("タイトル") or "").strip()
            views_raw = (row.get("再生数") or "").strip()
            date_str = (row.get("投稿日（日本時間）") or "").strip()
            if not vid:
                continue
            # 再生数を数値化（カンマ等除去）
            try:
                views = int(views_raw.replace(",", "").replace("回", "").replace(" ", ""))
            except:
                continue
            # 変更: 100万超は除外
            if views > 1_000_000:
                continue
            rows.append({
                "video_id": vid,
                "title": title or "(タイトル不明)",
                "views": views,
                "date": date_str,
                # 変更: 下側の差分（非負）
                "gap_to_million": 1_000_000 - views
            })
        # 変更: 差分昇順、同差分は再生数多い順
        rows.sort(key=lambda r: (r["gap_to_million"], -r["views"]))
        return rows[:top_n]
    except Exception as e:
        # 失敗時は空リスト（標準出力に簡易ログ）
        print(f"歌みた取得に失敗: {e}")
        return []

# 追加: 伸びた動画データの取得
def fetch_trending_from_sheet(edit_url: str, top_n: int = 10) -> List[Dict]:
    """
    Googleスプレッドシートから伸びた動画データを取得（増加数順に上位N件）
    期待ヘッダー: 動画ID, タイトル, 1週間前再生数, 現在再生数, 増加数, 投稿日, チャンネル
    """
    try:
        parts = edit_url.split("/d/")
        if len(parts) < 2:
            return []
        rest = parts[1]
        sheet_id = rest.split("/")[0]
        gid = "0"
        if "gid=" in edit_url:
            try:
                gid = edit_url.split("gid=")[1].split("&")[0].split("#")[0]
            except:
                gid = "0"
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

        with urllib.request.urlopen(csv_url, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(data))
        rows = []
        for row in reader:
            vid = (row.get("動画ID") or "").strip()
            title = (row.get("タイトル") or "").strip()
            increase_raw = (row.get("増加数") or "").strip()
            current_views_raw = (row.get("現在再生数") or "").strip()
            date_str = (row.get("投稿日") or "").strip()
            channel = (row.get("チャンネル") or "").strip()
            
            if not vid:
                continue
            
            try:
                increase = int(increase_raw.replace(",", "").replace("回", "").replace(" ", ""))
                current_views = int(current_views_raw.replace(",", "").replace("回", "").replace(" ", ""))
            except:
                continue
            
            rows.append({
                "video_id": vid,
                "title": title or "(タイトル不明)",
                "increase": increase,
                "current_views": current_views,
                "date": date_str,
                "channel": channel
            })
        
        # 増加数降順でソート（既にソート済みだが念のため）
        rows.sort(key=lambda r: r["increase"], reverse=True)
        return rows[:top_n]
    except Exception as e:
        print(f"伸びた動画取得に失敗: {e}")
        return []

# 変更: 歌みた紹介セクション生成（横スクロールカルーセル + 伸びた動画を統合）
def generate_covers_section(covers: List[Dict], trending: List[Dict]) -> str:
    section = """
<section id='covers' class='section' role='region' aria-labelledby='covers-heading'>
  <h2 id='covers-heading'><i class='fa-solid fa-microphone-lines'></i>歌みた紹介</h2>
"""
    
    # 変更: 伸びた動画TOP10を先に表示（期間を動的計算）
    if trending:
        # 期間計算（今日-7日～今日-1日）
        from datetime import datetime, timedelta
        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime("%Y/%m/%d")
        end_date = (today - timedelta(days=1)).strftime("%Y/%m/%d")
        
        section += f"""
  <h3 class='videos-heading'>
    <i class='fa-solid fa-chart-line'></i> 伸びた動画TOP10
  </h3>
  <p class='video-meta' style='margin-bottom: 16px;'>直近7日間の再生数増加ランキング（{start_date}～{end_date}）</p>
  <div class='videos-carousel-wrapper'>
    <button class='carousel-btn prev' aria-label='前へ'>
      <i class='fa-solid fa-chevron-left'></i>
    </button>
    <div class='videos-carousel'>
"""
        for i, v in enumerate(trending, 1):
            thumb = f"https://i.ytimg.com/vi/{v['video_id']}/mqdefault.jpg"
            url = f"https://www.youtube.com/watch?v={v['video_id']}"
            increase_fmt = f"{v['increase']:,}"
            current_fmt = f"{v['current_views']:,}"
            date_part = f"<div class='video-meta'><i class='fa-regular fa-calendar'></i> {v['date']}</div>" if v.get("date") else ""
            channel_part = f"<div class='video-meta'><i class='fa-solid fa-tv'></i> {v['channel']}</div>" if v.get("channel") else ""
            
            section += f"""
      <div class='video-card'>
        <div class='video-rank'>{i}</div>
        <a href='{url}' target='_blank' rel='noopener noreferrer' class='video-thumb'>
          <img src='{thumb}' alt='{v['title']}' loading='lazy'>
        </a>
        <div>
          {date_part}
          {channel_part}
          <div class='video-meta'><i class='fa-solid fa-arrow-trend-up'></i> +{increase_fmt} 回</div>
          <div class='video-meta'><i class='fa-solid fa-eye'></i> {current_fmt} 回</div>
          <a href='{url}' target='_blank' rel='noopener noreferrer'>{v['title']}</a>
        </div>
      </div>
"""
        section += """
    </div>
    <button class='carousel-btn next' aria-label='次へ'>
      <i class='fa-solid fa-chevron-right'></i>
    </button>
  </div>
"""
    
    # 変更: 100万再生まであと少しを後に表示
    if covers:
        section += """
  <h3 class='videos-heading'>
    <i class='fa-solid fa-hands-bubbles'></i> 100万再生まであと少し！
  </h3>
  <div class='videos-carousel-wrapper'>
    <button class='carousel-btn prev' aria-label='前へ'>
      <i class='fa-solid fa-chevron-left'></i>
    </button>
    <div class='videos-carousel'>
"""
        for v in covers:
            thumb = f"https://i.ytimg.com/vi/{v['video_id']}/mqdefault.jpg"
            url = f"https://www.youtube.com/watch?v={v['video_id']}"
            views_fmt = f"{v['views']:,}"
            date_part = f"<div class='video-meta'><i class='fa-regular fa-calendar'></i> {v['date']}</div>" if v.get("date") else ""
            section += f"""
      <div class='video-card'>
        <a href='{url}' target='_blank' rel='noopener noreferrer' class='video-thumb'>
          <img src='{thumb}' alt='{v['title']}' loading='lazy'>
        </a>
        <div>
          {date_part}
          <div class='video-meta'><i class='fa-solid fa-eye'></i> {views_fmt} 回</div>
          <a href='{url}' target='_blank' rel='noopener noreferrer'>{v['title']}</a>
        </div>
      </div>
"""
        section += """
    </div>
    <button class='carousel-btn next' aria-label='次へ'>
      <i class='fa-solid fa-chevron-right'></i>
    </button>
  </div>
"""
    
    if not covers and not trending:
        section += "<p class='video-meta'>データを取得できませんでした。</p>"
    
    section += """
</section>
"""
    return section

def generate_videos_section(videos_by_category: Dict[str, List[Dict]]) -> str:
    """切り抜き紹介セクションHTML生成（種類ごとに分類表示、横スクロール対応）"""
    section = """
<section id='videos' class='section' role='region' aria-labelledby='videos-heading'>
  <h2 id='videos-heading'><i class='fa-brands fa-youtube'></i>切り抜き紹介</h2>
"""
    
    # 表示順を定義
    category_order = ["はのこと", "見どころはのぴ", "ことメモ"]
    category_icons = {
        "はのこと": "fa-solid fa-users",
        "見どころはのぴ": "fa-solid fa-user",
        "ことメモ": "fa-solid fa-user"
    }
    
    for category in category_order:
        videos = videos_by_category.get(category, [])
        if not videos:
            continue
        
        icon = category_icons.get(category, "fa-solid fa-video")
        section += f"""
  <h3 class='videos-heading'>
    <i class='{icon}'></i> {category}
  </h3>
  <div class='videos-carousel-wrapper'>
    <button class='carousel-btn prev' aria-label='前へ'>
      <i class='fa-solid fa-chevron-left'></i>
    </button>
    <div class='videos-carousel'>
"""
        for v in videos:
            thumb = f"https://i.ytimg.com/vi/{v['video_id']}/mqdefault.jpg"
            url = f"https://www.youtube.com/watch?v={v['video_id']}"
            section += f"""
      <div class='video-card'>
        <a href='{url}' target='_blank' rel='noopener noreferrer' class='video-thumb'>
          <img src='{thumb}' alt='{v['title']}' loading='lazy'>
        </a>
        <div>
          <div class='video-meta'><i class='fa-regular fa-calendar'></i> {v['date']}</div>
          <a href='{url}' target='_blank' rel='noopener noreferrer'>{v['title']}</a>
        </div>
      </div>
"""
        section += """
    </div>
    <button class='carousel-btn next' aria-label='次へ'>
      <i class='fa-solid fa-chevron-right'></i>
    </button>
  </div>
"""
    
    section += """
</section>
"""
    return section

# 削除: generate_trending_section関数は不要になったため削除

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
<a href='#main' class='skip-link'>メインコンテンツへスキップ</a>
<header class='site-header'>
  <div class='header-left'>
    <img src='image/header.png' alt='はのこと活動記録' class='header-logo'>
    <nav class='header-nav' aria-label='サイト内メニュー'>
      <a class='nav-link' href='#home' data-section='home' aria-controls='home' aria-current='page'><i class='fa-solid fa-house'></i>ホーム</a>
      <a class='nav-link' href='#about' data-section='about' aria-controls='about'><i class='fa-solid fa-circle-info'></i>サイトについて</a>
      <a class='nav-link' href='#contribute' data-section='contribute' aria-controls='contribute'><i class='fa-brands fa-wpforms'></i>情報提供</a>
      <a class='nav-link' href='#thanks' data-section='thanks' aria-controls='thanks'><i class='fa-solid fa-heart'></i>Thanks</a>
      <!-- 追加: 歌みた紹介 -->
      <a class='nav-link' href='#covers' data-section='covers' aria-controls='covers'><i class='fa-solid fa-microphone-lines'></i>歌みた紹介</a>
      <a class='nav-link' href='#videos' data-section='videos' aria-controls='videos'><i class='fa-brands fa-youtube'></i>切り抜き紹介</a>
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
      <p class='notice-text'><strong>β版</strong>のため、<strong>データは一部のみ</strong>掲載しています。<br>サイトの改善に向けてアンケートを実施しています。ご協力いただいた方のお名前（ご希望の方のみ）は<strong>Thanksページ</strong>に掲載させていただきます。</p>
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

    # 追加: 分類ごとの総件数を算出（バッジ表示用）
    classification_counts = {}
    for cls in classifications:
        years = grouped_records.get(cls, {})
        classification_counts[cls] = sum(
            len(items)
            for months in years.values()
            for genres in months.values()
            for items in genres.values()
        )

    # タブ生成
    tabs = []
    panels = []
    for i, classification in enumerate(classifications):
        is_active = i == 0
        active_class = "active" if is_active else ""
        aria_selected = "true" if is_active else "false"
        tab_id, panel_id = f"tab-{i}", f"panel-{i}"
        count = classification_counts.get(classification, 0)

        # タブラベルの短縮版を設定
        short_label = classification.replace("はのこと・ハコリリ", "はのこと")

        # 変更: フル/短縮ラベルを両方含める
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
        
        # パネル生成
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

    # セクション追加
    about_section = """
<section id='about' class='section' role='region' aria-labelledby='about-heading'>
  <h2 id='about-heading'><i class='fa-solid fa-circle-info'></i>サイトについて</h2>

  <div class='about-lead'>
    <i class='fa-solid fa-book-open' aria-hidden='true'></i>
    <p>このサイトは、Hanon、Kotohaおよび2人のユニットであるハコニワリリィの活動を年表形式で記録したものです。</p>
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
        <li><a href='https://youtube.com/channel/UCepZVSTaKBW4ux0RB-nQ_NQ' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-youtube'></i> YouTube</a></li>
        <li><a href='https://x.com/hanokoto901?s=21&t=GjebMqravZ_3NXQHjvY-8g' target='_blank' rel='noopener noreferrer'><i class='fa-brands fa-twitter'></i> Twitter</a></li>
      </ul>
    </div>

    <div class='about-card'>
      <h3><i class='fa-solid fa-desktop'></i>動作環境</h3>
      <p>最新版のChrome、Firefox、Safari、Edgeでの閲覧を推奨しています。スマートフォンでも閲覧可能です。</p>

      <h3><i class='fa-solid fa-envelope'></i>お問い合わせ</h3>
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

    contribute_section = """
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
      <a href='https://docs.google.com/forms/d/e/1FAIpQLSc61BbrO9hLEr_GXxsUcD9sxGXIZm7mXlKDlP7YnyS_kAnARA/viewform'
         target='_blank' rel='noopener noreferrer' class='google-form-button'>
        <i class='fa-brands fa-wpforms'></i> フォームに記入する
      </a>
    </div>
    <p class='form-note-text'>
      フォームが使いづらい場合は、TwitterのDMでも受け付けています：
      <a href='https://x.com/hanokoto901' target='_blank' rel='noopener noreferrer'>@hanokoto901</a>
    </p>
  </div>
</section>"""

    # Thanksセクション生成（分類ごとにまとめて表示）
    thanks_groups = fetch_thanks_groups(THANKS_CSV)
    thanks_section = """
<section id='thanks' class='section' role='region' aria-labelledby='thanks-heading'>
  <h2 id='thanks-heading'><i class='fa-solid fa-heart'></i>Thanks</h2>
  <p style='margin-bottom: 16px; color: var(--text-secondary); font-size: 14px;'>
    このサイトの運営にご協力いただいた皆様のお名前を掲載しています（公開希望者のみ）。<br>
    情報提供やアンケートへのご協力、誠にありがとうございます。
  </p>
"""
    for group, names in thanks_groups.items():
        thanks_section += f"<h3><i class='fa-solid fa-users'></i> {group}</h3>\n"
        thanks_section += "<ul class='thanks-name-list'>"
        for name in names:
            thanks_section += f"<li class='thanks-name-item'>{name}</li>"
        thanks_section += "</ul>\n"
    thanks_section += "<p class='thanks-note'>（順不同・公開希望者のみ掲載）</p>\n</section>\n"

    # 切り抜き紹介セクション追加
    videos = fetch_videos_from_sheet(VIDEOS_SHEET_EDIT_URL)
    videos_section = generate_videos_section(videos)

    # 追加: 歌みた紹介セクションを生成（伸びた動画を内包）
    covers = fetch_covers_from_sheet(COVERS_SHEET_EDIT_URL, top_n=10)
    trending = fetch_trending_from_sheet(TRENDING_SHEET_EDIT_URL, top_n=10)
    covers_section = generate_covers_section(covers, trending)

    # フッター追加
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

    # 追加した歌みた紹介セクション（covers_section）を切り抜き紹介セクション（videos_section）の前後に配置
    return f"{header}{''.join(tabs)}</div>{''.join(panels)}</section>{covers_section}{videos_section}{about_section}{contribute_section}{thanks_section}{footer}"

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
