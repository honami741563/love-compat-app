# 恋愛相性診断アプリ（MVP）

仕様書に基づいた Flask + SQLite の最小実装です。VS Code でそのまま開いて動かせます。

## 動かし方（VS Code）

1. このフォルダを VS Code で開く（File > Open Folder）
2. ターミナルを開いて仮想環境を作成（任意ですが推奨）
   ```bash
   python -m venv venv
   # Windows: venv\Scripts\activate
   # Mac/Linux: source venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```
4. アプリを起動
   ```bash
   python app.py
   ```
5. ブラウザで `http://127.0.0.1:5000` を開く

初回起動時に `app.db`（SQLiteファイル）が自動生成されます。

## できること（実装済み）

- `/`            診断回答画面（Q1〜Q17）
- `/submit`      回答を受け取り、スコアを計算してセッションに一時保存
- `/nickname`    ニックネーム入力 → DBに保存 → 結果画面へ
- `/result/<hash_id>`  レーダーチャートと共有URL表示
- `/compare`     手動モード（スライダーでリアルタイム相性計算、DB保存なし）
- `/match/<hash_id>`   シェアモード（自分の診断済みスコアと相手のスコアで相性計算）

採点ロジックとマッチングロジックは `scoring.py` に、仕様書の数式をそのまま実装しています。

## 今後の拡張案

- **本番DBへの移行**: `db.py` のSQLite部分をSupabase(PostgreSQL)クライアントに差し替え。テーブル定義はほぼそのまま流用できます。仕様書にある「RLSで全件SELECTを禁止し、hash_id一致の1件のみ許可」は、Supabase移行時にRLSポリシーとして設定してください（現状はアプリ側のクエリで担保）。
- **本番デプロイ**: Render / Railway / Fly.io などにFlaskごとデプロイ可能。`app.secret_key` は必ず環境変数から読むように変更してください。
- **匿名化CSVエクスポート**: `db.py` に `export_anonymized_csv()` を用意済み。管理用スクリプトやCLIコマンドから呼び出して使えます。
- **キャラクター演出**: 結果画面で最もスコアが高いパラメータに応じて、SDキャラクター画像を出し分ける演出を追加すると仕様書の提案に沿った形になります（`result.html` にキャラ画像の条件分岐を追加する形で拡張可能）。

## ファイル構成

```
love_compat_app/
├── app.py              # Flaskルーティング
├── scoring.py          # 質問データ・採点ロジック・マッチングロジック
├── db.py                # SQLite読み書き
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── quiz.html         # 診断回答画面
│   ├── nickname.html     # ニックネーム入力
│   ├── result.html        # マイ結果（レーダーチャート）
│   ├── compare_manual.html # 手動相性診断
│   └── compare_share.html  # シェアモード相性診断
└── static/
    └── style.css
```
