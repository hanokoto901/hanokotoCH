"""サイト全体を一括生成する

    python build.py

1. index.html（generate.py）
2. CDs/*.html（generate_CDs.py）
3. songs/*.html（generate_songs.py）

スプレッドシートは1回の実行につき1度だけ取得します。
どこかで取得に失敗した場合はその時点で止まり、それ以降のページは変更しません。
"""

import os
import sys

# どこから実行しても相対パス（data/, CDs/ など）が正しく解決されるようにする
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import generate          # noqa: E402
import generate_CDs      # noqa: E402
import generate_songs    # noqa: E402
from common import FetchError, clean_thumbnails  # noqa: E402

STEPS = [
    ("トップページ", generate.main),
    ("CDページ", generate_CDs.main),
    ("曲ページ", generate_songs.main),
]


def main() -> None:
    for label, step in STEPS:
        print(f"[{label}]")
        try:
            step()
        except FetchError as e:
            print(f"エラー: {e}\n{label}以降のページは変更していません。")
            sys.exit(1)
    clean_thumbnails()
    print("すべて完了しました。")


if __name__ == "__main__":
    main()
