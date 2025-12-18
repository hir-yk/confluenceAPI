import os
import sys
import argparse
import html
from pathlib import Path

from dotenv import load_dotenv
from atlassian import Confluence


# --- 設定情報の読み込み (.env) ---
def load_config():
    """
    .env から Confluence 接続情報を読み込む。
    参考スクリプトと同じ環境変数名を使用。
    """
    load_dotenv()  # カレント or 上位ディレクトリの .env を自動探索

    url = os.getenv("CONFLUENCE_URL")
    username = os.getenv("CONFLUENCE_USERNAME")
    auth_token = os.getenv("ATLASSIAN_TOKEN")

    if not all([url, username, auth_token]):
        print(
            "エラー: 環境変数 (CONFLUENCE_URL, CONFLUENCE_USERNAME, ATLASSIAN_TOKEN) "
            "が設定されていません。.env ファイルを確認してください。"
        )
        sys.exit(1)

    return url, username, auth_token


# --- テキスト → Confluence storage 形式 ---
def read_local_file(path: Path) -> str:
    """
    ローカルファイルを UTF-8 で読み込み、文字列として返す。
    """
    return path.read_text(encoding="utf-8")


def make_storage_body_from_text(text: str) -> str:
    """
    読み込んだテキストを Confluence の storage 形式(HTML)に変換。

    - 先頭に「ローカルファイルから自動作成」の note を表示
    - 元テキストは <pre> 内にそのまま保持（Rovo で編集しやすいように）
    """
    escaped = html.escape(text)

    notice_panel = (
        '<ac:structured-macro ac:name="note">'
        "<ac:rich-text-body>"
        "<p>※ このページはローカルファイルから自動作成されました。"
        "現在は Rovo で手動ブラッシュアップを行う運用です。</p>"
        "</ac:rich-text-body>"
        "</ac:structured-macro>"
    )

    body = f"{notice_panel}<p></p><pre>{escaped}</pre>"
    return body


# --- 将来の外部 LLM 用フック（今は素通し） ---
def improve_body_with_llm(storage_body: str) -> str:
    """
    将来的に「外部 LLM でブラッシュアップ」するためのフック関数。
    今は何もせず、そのまま返す（= 手動ブラッシュアップ前提）。
    """
    # ここに将来、外部 LLM 呼び出し処理を実装する想定
    return storage_body


# --- スペース選択ロジック（参考スクリプトと同じ流れ） ---
def select_space(confluence: Confluence, input_arg: str | None):
    """
    - input_arg が '--list'なら、全スペース一覧を表示して終了
    - input_arg が Space Key と一致すればそれを採用
    - 一致しなければ「名前部分一致」で候補を出し、対話的に選択
    """
    script_name = os.path.basename(sys.argv[0])

    if input_arg is None:
        print("エラー: 書き込み先スペースを指定してください。")
        print(f"使用例:")
        print(f"  python {script_name} --file path/to/file.txt --space --list")
        print(f"  python {script_name} --file path/to/file.txt --space SPACEKEY")
        print(f"  python {script_name} --file path/to/file.txt --space '一部の名前'")
        sys.exit(1)

    print("スペース情報を取得中...")

    try:
        spaces_data = confluence.get_all_spaces(start=0, limit=500)
        results = spaces_data.get("results", [])
    except Exception as e:
        print(
            f"Confluence への接続に失敗しました。URLやトークンを確認してください。\nエラー: {e}"
        )
        sys.exit(1)

    # --- 一覧表示のみ ---
    if input_arg == "--list":
        print(f"\n--- 全スペース一覧 ({len(results)}件) ---")
        print(f"{'[No]':<5} {'Space Name':<40} | {'Space Key':<20}")
        print("-" * 70)
        for idx, s in enumerate(results):
            print(f"[{idx:3}] {s['name'][:38]:<40} | {s['key']:<20}")
        sys.exit(0)

    # --- 完全一致 (Space Key) を優先 ---
    key_match = next((s for s in results if s["key"] == input_arg), None)

    if key_match:
        return key_match["key"], key_match["name"]

    # --- 名前部分一致 ---
    matched_spaces = [
        s for s in results if input_arg.lower() in s["name"].lower()
    ]

    if not matched_spaces:
        print(f"エラー: '{input_arg}' に一致するスペースが見つかりませんでした。")
        sys.exit(1)

    # 複数候補がある場合は番号選択
    print(f"\n--- 一致するスペース候補 ({len(matched_spaces)}件) ---")
    for idx, s in enumerate(matched_spaces):
        print(f"[{idx}] {s['name']} (Key: {s['key']})")

    try:
        s_selection = input("\n対象とするスペースの番号を入力してください: ")
        selected = matched_spaces[int(s_selection)]
        return selected["key"], selected["name"]
    except (ValueError, IndexError):
        print("無効な入力です。")
        sys.exit(1)


# --- ページ作成 ---
def create_confluence_page(
    confluence: Confluence,
    space_key: str,
    title: str,
    body: str,
    parent_id: str | None = None,
):
    page = confluence.create_page(
        space=space_key,
        title=title,
        body=body,
        representation="storage",
        parent_id=parent_id,
    )
    return page


def main():
    # --- 引数パース ---
    parser = argparse.ArgumentParser(
        description="ローカルファイルから Confluence ページを作成するスクリプト"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="アップロード元となるローカルファイルパス",
    )
    parser.add_argument(
        "--space",
        required=True,
        help=(
            "書き込み先スペース指定。"
            "'--list' で一覧表示, または SpaceKey / 名前(部分一致) を指定"
        ),
    )
    parser.add_argument(
        "--title",
        required=False,
        help="作成する Confluence ページのタイトル（省略時はファイル名）",
    )
    parser.add_argument(
        "--parent-id",
        required=False,
        help="親ページID（特定の親ページ配下に作りたい場合のみ指定）",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="将来的に外部 LLM による自動ブラッシュアップを有効化するフラグ（今はダミー）",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"エラー: ファイルが存在しません: {file_path}")
        sys.exit(1)

    # --- Confluence クライアント生成 ---
    url, username, auth_token = load_config()
    confluence = Confluence(url=url, username=username, password=auth_token, cloud=True)

    # --- スペース選択 ---
    target_space_key, target_space_name = select_space(confluence, args.space)
    print(f"\n選択されたスペース: {target_space_name} (Key: {target_space_key})")

    # --- ページタイトル決定（ファイル名も指定できるように） ---
    if args.title:
        page_title = args.title
    else:
        # デフォルトはファイル名（拡張子なし）
        page_title = file_path.stem

    print(f"作成するページタイトル: {page_title}")

    # --- ファイル読み込み & body 生成 ---
    text = read_local_file(file_path)
    storage_body = make_storage_body_from_text(text)

    # 将来用: 外部 LLM でブラッシュアップ（今はそのまま）
    if args.use_llm:
        storage_body = improve_body_with_llm(storage_body)

    # --- ページ作成実行 ---
    page = create_confluence_page(
        confluence=confluence,
        space_key=target_space_key,
        title=page_title,
        body=storage_body,
        parent_id=args.parent_id,
    )

    page_id = page.get("id")
    webui_link = page.get("_links", {}).get("webui")
    if webui_link:
        full_url = url.rstrip("/") + webui_link
    else:
        full_url = f"{url.rstrip('/')}/pages/{page_id}"

    print("\nページを作成しました。")
    print(f"Space : {target_space_name} (Key: {target_space_key})")
    print(f"Title : {page_title}")
    print(f"Page ID: {page_id}")
    print(f"URL    : {full_url}")
    print()
    print("このページを開き、Rovo に対して次のように依頼してください:")
    print("  - 「このページの内容を整理して、見出し・箇条書き・表・パネルを使って読みやすくしてください」")
    print("  - 「<pre> 内のテキストをベースに、新しい構成案を作ってください」")


if __name__ == "__main__":
    main()