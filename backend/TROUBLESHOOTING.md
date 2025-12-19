# トラブルシューティング

## サーバーが起動しない

### 問題: `ModuleNotFoundError: No module named 'pydantic_settings'`

**原因**: 依存関係がインストールされていない

**解決方法**:
```bash
cd backend
pip install -r requirements.txt
```

### 問題: `ERROR: No matching distribution found for fastapi>=0.104.0`

**原因**: Pythonのバージョンが古い（Python 3.8以上が必要）

**解決方法**:
1. Pythonのバージョンを確認:
   ```bash
   python --version
   ```

2. Python 3.8以上をインストール:
   - [Python公式サイト](https://www.python.org/downloads/)から最新版をダウンロード
   - または、pyenvを使用してバージョン管理

3. 仮想環境を再作成:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

### 問題: `ValueError: 本番環境では JWT_SECRET_KEY を強力な値に変更してください`

**原因**: 本番環境（`ENVIRONMENT=production`）で必須設定が不足している

**解決方法**:
1. `.env`ファイルで`ENVIRONMENT=development`に設定（開発環境の場合）
2. または、本番環境の場合は必須の環境変数を設定:
   - `JWT_SECRET_KEY`: 強力な秘密鍵（`openssl rand -hex 32`で生成）
   - `GEMINI_API_KEY`: Google Gemini APIキー

### 問題: `ImportError: cannot import name 'Settings' from 'app.config'`

**原因**: 設定ファイルのインポートエラー

**解決方法**:
1. `backend`ディレクトリにいることを確認
2. 仮想環境が有効化されていることを確認
3. 依存関係がインストールされていることを確認

### 問題: ポート8000が既に使用されている

**原因**: 別のプロセスがポート8000を使用している

**解決方法**:
1. 別のポートを使用:
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

2. または、ポート8000を使用しているプロセスを終了

### 問題: データベースエラー

**原因**: データベースファイルのパスまたは権限の問題

**解決方法**:
1. `data/`ディレクトリが存在することを確認:
   ```bash
   mkdir -p data
   ```

2. 書き込み権限があることを確認

3. `DATABASE_URL`が正しい形式であることを確認

## その他の問題

### ログを確認

サーバー起動時のエラーメッセージを確認してください。詳細なエラー情報が表示されます。

### デバッグモード

より詳細なエラー情報を表示するには:
```bash
uvicorn app.main:app --reload --log-level debug
```

