from atlassian import Confluence
import re
import html
import os

# --- 設定情報 ---
url = 'https://suzukiglobalit.atlassian.net/'
username = 'hokamoto@hhq.suzuki.co.jp'
auth_token = os.getenv("ATLASSIAN_TOKEN")
space_key = '~55705839eda0d5ca27415cb26cf20dae91ddf6'
output_dir = "confluence_downloads"

# --- 関数の定義 ---
def clean_filename(filename):
    """ファイル名に使えない文字を削除・置換する"""
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

def download_page(confluence, page_id, page_title, p_status='current'):
    """ライブラリの自動補完をバイパスして、指定したステータスで直接取得する"""
    try:
        if not page_title:
            page_title = f"Untitled_{page_id}"

        # ライブラリの get ではなく request を使い、パラメータを辞書形式で渡します
        # これにより、ライブラリが status=current を勝手に付与するのを防ぎます
        response = confluence.request(
            method='GET',
            path=f"rest/api/content/{page_id}",
            params={
                'status': p_status,
                'expand': 'body.storage'
            }
        )

        # responseがResponseオブジェクトで返ってくる場合があるため、JSONに変換
        if hasattr(response, 'json'):
            data = response.json()
        else:
            data = response

        if 'body' not in data:
            print(f"ページ ID {page_id} の本文が見つかりませんでした。データ構造: {data}")
            return

        html_body = data['body']['storage']['value']

        # テキスト変換
        text_body = re.sub(r'</p>|</div>|<br\s*/?>|</li>', '\n', html_body)
        text_body = re.sub(r'<[^>]+>', '', text_body)
        text_body = html.unescape(text_body)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        file_path = os.path.join(output_dir, f"{clean_filename(page_title)}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {page_title}\nSTATUS: {p_status}\nID: {page_id}\n---\n\n{text_body}")
        
        print(f"成功！ '{file_path}' に保存しました。")

    except Exception as e:
        print(f"ページ ID {page_id} ({page_title}) の取得に失敗しました。")
        print(f"詳細なエラー内容: {e}")

# --- メイン処理 ---
confluence = Confluence(url=url, username=username, password=auth_token, cloud=True)

try:
    print(f"スペース [{space_key}] のページを取得中...")
    
    # 1. 公開済み（current）ページを取得
    current_pages = confluence.get_all_pages_from_space(space_key, start=0, limit=50, status='current')
    
    # 2. 下書き（draft）ページを取得
    draft_pages = confluence.get_all_pages_from_space(space_key, start=0, limit=50, status='draft')

    # 3. リストを統合
    all_pages = current_pages + draft_pages

    if not all_pages:
        print("表示できるページがありませんでした。")
    else:
        print("\n--- ダウンロード可能なページ一覧（[D]は下書き） ---")
        page_list = []
        for i, page in enumerate(all_pages):
            # ステータスを判別して表示
            p_status = page.get('status', 'current')
            prefix = "[D] " if p_status == 'draft' else "    "
            
            print(f"[{i:2}] {prefix}{page['title']}")
            page_list.append(page)

    # 4. ユーザー入力
        selection = input("\n選択する番号 (または 'all'): ")
        
        if selection.lower() == 'all':
            for p in page_list:
                # ページ情報からステータスを取得して渡す
                download_page(confluence, p['id'], p['title'], p.get('status', 'current'))
        else:
            idx = int(selection)
            target = page_list[idx]
            # ページ情報からステータスを取得して渡す
            download_page(confluence, target['id'], target['title'], target.get('status', 'current'))

except (ValueError, IndexError):
    print("正しい番号を入力してください。")
except Exception as e:
    print(f"エラーが発生しました: {e}")