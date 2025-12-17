# Confluence Page Downloader

Confluence Cloud からページを検索し、テキスト形式で一括ダウンロードするための Python ツールです。
通常の API では取得しにくい **下書き（Draft）状態のページ** もリストアップして取得可能です。

## 🎨 特徴

  * **柔軟な検索**: スペース名の一部を入力するだけで、候補を一覧表示し対話的に選択可能。
  * **一括・個別ダウンロード**: スペース内の全ページ、または特定のページを番号で選択して保存。
  * **下書き対応**: `status=draft` のページも取得対象に含めることが可能。
  * **スペース別フォルダ管理**: 保存先をスペース名ごとに自動でフォルダ分けし、整理を容易に。
  * **安全な設計**: 認証情報を `.env` ファイルで外部管理し、コードの安全性を確保。

## 🚀 セットアップ

### 1\. 依存ライブラリのインストール

```bash
pip install atlassian-python-api python-dotenv
```

### 2\. 環境設定ファイル (`.env`) の準備

`.env.example` をコピーして `.env` を作成し、自身の情報を入力してください。

```bash
cp .env.example .env
```

`.env` 内の各項目を編集します：

  * `CONFLUENCE_URL`: ご利用の Confluence の URL（例: `https://your-domain.atlassian.net/`）
  * `CONFLUENCE_USERNAME`: アカウントのメールアドレス
  * `ATLASSIAN_TOKEN`: [Atlassian API トークン](https://id.atlassian.com/manage-profile/security/api-tokens) のページで発行したトークン

## 🛠 使い方

### スペースの一覧を表示する

登録されている全てのスペースを表示して、Keyや名称を確認したい場合に使用します。

```bash
python script.py --list
```

### スペース名で検索してダウンロードを開始する

名前の一部（キーワード）を入力すると候補が表示されます。番号でスペースを選択した後、ダウンロードしたいページ番号（または `all`）を入力します。

```bash
python script.py "検索キーワード"
```

### スペースKeyを直接指定する

スペースの Key（例: `~5570...`）がわかっている場合は、直接指定して即座にページ選択画面へ進めます。

```bash
python script.py "SPACEKEY"
```

## 📂 ディレクトリ構造

ダウンロードしたファイルは以下のように自動で整理されます。

```text
confluence_downloads/
  └── スペース名A/
      ├── ページタイトル1.txt
      └── ページタイトル2.txt
  └── スペース名B/
      └── ...
```

## ⚖️ ライセンス

このプロジェクトは **Apache License 2.0** の下で公開されています。
詳細は [LICENSE](https://www.google.com/search?q=LICENSE) ファイルを参照してください。
