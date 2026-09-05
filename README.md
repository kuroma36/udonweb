# 讃岐うどん巡礼システム (Sanuki Udon Pilgrimage Platform) 🍜

香川県の讃岐うどん巡礼（食べ歩き旅行）を仲間と共に計画・共有・記録するためのWebアプリケーションです。  
Google Maps連携による巡回ルートマップ、移動時間自動計算、5軸評価レーダーチャート、リアルタイム写真共有、ソーシャル機能（いいね/コメント/通知）、そして公式マスコット「うどんちゅ」を搭載しています。

---

## 🌟 主な機能

1. **うどん旅ルートマップ**
   - Google Maps 上に巡回予定店舗をピン留め＆ルート結線表示
   - 店舗間の移動時間を自動計算（「車で18分」等）
   - ストップの並び替え、追加、削除
2. **5軸うどんレビュー & レーダーチャート**
   - 麺のコシ、出汁の旨味、店舗情緒、天ぷらサクサク度、コスパの5軸評価（各10点満点）
   - Chart.js による美しい動的レーダーチャート
   - 店舗写真・レビュー写真のリアルタイムギャラリー連動
3. **ソーシャル & 交流**
   - レビューへの「いいね」・スレッド形式コメント
   - ヘッダーベルアイコンでの新着アクティビティ通知
   - お気に入り店舗登録（★）
4. **快適なユーザー体験**
   - ワンタップ即時ユーザー切り替えログイン（最近利用順ソート・最新バッジ）
   - 和モダン＆Glassmorphismを取り入れた上質なレスポンシブデザイン
   - 公式マスコット「うどんちゅ」による親しみやすい演出
   - PWA（Progressive Web App）対応によるネイティブアプリ風の利用体験

---

## 🛠 技術スタック

- **Backend**: Python 3.12, Django 6.1
- **Database**: SQLite3
- **WSGI / Web Server**: Gunicorn + Nginx (HTTPS)
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System), JavaScript
- **Visualization**: Chart.js v4.4.1
- **External API**: Google Maps Platform (Maps JavaScript API, Places API)

---

## 🚀 セットアップ手順

### 1. 依存ライブラリのインストール
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境変数の設定
`.env.example` をコピーして `.env` を作成し、必要なキーを設定します。
```bash
cp .env.example .env
```

### 3. データベースマイグレーション
```bash
python manage.py migrate
```

### 4. 初期名店データの投入（任意）
香川県全域の讃岐うどん名店マスターデータを投入します。
```bash
python manage.py seed_kagawa_shops
```

### 5. 開発サーバーの起動
```bash
python manage.py runserver 0.0.0.0:8000
```

---

## 📑 ドキュメント

- [詳細設計書 (Excel)](./讃岐うどん巡礼_詳細設計書.xlsx): システム概要、機能要件、画面設計、全テーブル・カラム定義、API仕様、権限マトリクスを完全網羅。
