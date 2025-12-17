import sys
import re
import html
import os
from atlassian import Confluence
from dotenv import load_dotenv

# --- 設定情報の読み込み ---
load_dotenv()  # .env ファイルから環境変数をロード

url = os.getenv("CONFLUENCE_URL")
username = os.getenv("CONFLUENCE_USERNAME")
auth_token = os.getenv("ATLASSIAN_TOKEN")
base_output_dir = "confluence_downloads"

# 設定が不足している場合のチェック
if not all([url, username, auth_token]):
    print("エラー: 環境変数 (CONFLUENCE_URL, CONFLUENCE_USERNAME, ATLASSIAN_TOKEN) が設定されていません。")
    print(".env ファイルを確認してください。")
    sys.exit(1)

# --- 関数の定義 ---
def clean_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

def download_page(confluence, page_id, page_title, space_name, p_status='current'):
    try:
        if not page_title:
            page_title = f"Untitled_{page_id}"

        response = confluence.request(
            method='GET',
            path=f"rest/api/content/{page_id}",
            params={'status': p_status, 'expand': 'body.storage'}
        )
        data = response.json() if hasattr(response, 'json') else response

        if 'body' not in data:
            print(f"ページ ID {page_id} の本文が見つかりませんでした。")
            return

        html_body = data['body']['storage']['value']
        text_body = re.sub(r'</p>|</div>|<br\s*/?>|</li>', '\n', html_body)
        text_body = re.sub(r'<[^>]+>', '', text_body)
        text_body = html.unescape(text_body)

        space_dir = os.path.join(base_output_dir, clean_filename(space_name))
        if not os.path.exists(space_dir):
            os.makedirs(space_dir)
        
        file_path = os.path.join(space_dir, f"{clean_filename(page_title)}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {page_title}\nSTATUS: {p_status}\nID: {page_id}\n---\n\n{text_body}")
        print(f"成功！ '{file_path}' に保存しました。")
    except Exception as e:
        print(f"ページ ID {page_id} の取得に失敗しました: {e}")

def main():
    confluence = Confluence(url=url, username=username, password=auth_token, cloud=True)
    script_name = os.path.basename(sys.argv[0])

    if len(sys.argv) < 2:
        print(f"使用法:")
        print(f"  python {script_name} --list                 # 全てのスペースを表示")
        print(f"  python {script_name} [名前(部分一致) / Key]  # スペースを指定して開始")
        return

    input_arg = sys.argv[1]

    print("スペース情報を取得中...")
    try:
        spaces_data = confluence.get_all_spaces(start=0, limit=500)
        results = spaces_data.get('results', [])
    except Exception as e:
        print(f"Confluence への接続に失敗しました。URLやトークンを確認してください。\nエラー: {e}")
        return

    if input_arg == "--list":
        print(f"\n--- 全スペース一覧 ({len(results)}件) ---")
        print(f"{'[No]':<5} {'Space Name':<40} | {'Space Key':<20}")
        print("-" * 70)
        for idx, s in enumerate(results):
            print(f"[{idx:3}] {s['name'][:38]:<40} | {s['key']:<20}")
        return

    target_space_key = None
    target_space_name = None

    key_match = next((s for s in results if s['key'] == input_arg), None)
    
    if key_match:
        target_space_key = key_match['key']
        target_space_name = key_match['name']
    else:
        matched_spaces = [s for s in results if input_arg.lower() in s['name'].lower()]
        if not matched_spaces:
            print(f"エラー: '{input_arg}' に一致するスペースが見つかりませんでした。")
            return
        
        print(f"\n--- 一致するスペース候補 ({len(matched_spaces)}件) ---")
        for idx, s in enumerate(matched_spaces):
            print(f"[{idx}] {s['name']} (Key: {s['key']})")
        
        try:
            s_selection = input("\n対象とするスペースの番号を入力してください: ")
            selected = matched_spaces[int(s_selection)]
            target_space_key = selected['key']
            target_space_name = selected['name']
        except (ValueError, IndexError):
            print("無効な入力です。")
            return

    print(f"\nスペース [{target_space_name}] のページリストを取得します...")
    try:
        current_pages = confluence.get_all_pages_from_space(target_space_key, start=0, limit=100, status='current')
        draft_pages = confluence.get_all_pages_from_space(target_space_key, start=0, limit=100, status='draft')
        all_pages = current_pages + draft_pages

        if not all_pages:
            print("表示できるページがありませんでした。")
            return

        print("\n--- ページ一覧 ([D]=下書き) ---")
        for i, page in enumerate(all_pages):
            p_status = page.get('status', 'current')
            prefix = "[D] " if p_status == 'draft' else "    "
            print(f"[{i:2}] {prefix}{page['title']}")

        p_selection = input("\nダウンロードする番号 (または 'all'): ")
        
        if p_selection.lower() == 'all':
            for p in all_pages:
                download_page(confluence, p['id'], p['title'], target_space_name, p.get('status', 'current'))
        else:
            idx = int(p_selection)
            target = all_pages[idx]
            download_page(confluence, target['id'], target['title'], target_space_name, target.get('status', 'current'))

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()