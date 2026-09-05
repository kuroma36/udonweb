#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讃岐うどん巡礼システム 詳細設計書 Excel生成スクリプト
"""

import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_detailed_design_excel(output_path):
    wb = Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # 共通フォント・スタイル定義
    font_title = Font(name='Meiryo UI', size=16, bold=True, color='1B365D')
    font_section = Font(name='Meiryo UI', size=12, bold=True, color='1B365D')
    font_tbl_header = Font(name='Meiryo UI', size=10, bold=True, color='FFFFFF')
    font_bold = Font(name='Meiryo UI', size=10, bold=True, color='2D3748')
    font_normal = Font(name='Meiryo UI', size=9.5, color='2D3748')
    font_code = Font(name='Consolas', size=9, color='1A202C')
    font_badge = Font(name='Meiryo UI', size=9, bold=True, color='2B6CB0')

    fill_navy = PatternFill(start_color='1B365D', end_color='1B365D', fill_type='solid')
    fill_blue_sub = PatternFill(start_color='2B6CB0', end_color='2B6CB0', fill_type='solid')
    fill_section_bg = PatternFill(start_color='EBF8FF', end_color='EBF8FF', fill_type='solid')
    fill_zebra = PatternFill(start_color='F7FAFC', end_color='F7FAFC', fill_type='solid')
    fill_white = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
    fill_accent = PatternFill(start_color='ED8936', end_color='ED8936', fill_type='solid')

    border_thin = Border(
        left=Side(style='thin', color='CBD5E0'),
        right=Side(style='thin', color='CBD5E0'),
        top=Side(style='thin', color='CBD5E0'),
        bottom=Side(style='thin', color='CBD5E0')
    )
    border_double_bottom = Border(
        left=Side(style='thin', color='CBD5E0'),
        right=Side(style='thin', color='CBD5E0'),
        top=Side(style='thin', color='CBD5E0'),
        bottom=Side(style='double', color='1B365D')
    )

    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    align_right = Alignment(horizontal='right', vertical='center')

    def apply_sheet_settings(ws):
        ws.views.sheetView[0].showGridLines = True

    def adjust_column_widths(ws, min_widths=None, max_widths=None):
        if min_widths is None:
            min_widths = {}
        if max_widths is None:
            max_widths = {}
        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = 0
            for cell in col:
                val = str(cell.value or '')
                lines = val.split('\n')
                for line in lines:
                    # Multi-byte characters count as 2
                    line_len = sum(2 if ord(c) > 127 else 1 for c in line)
                    if line_len > max_len:
                        max_len = line_len
            calc_width = max(max_len + 3, min_widths.get(col_letter, 10))
            if col_letter in max_widths:
                calc_width = min(calc_width, max_widths[col_letter])
            ws.column_dimensions[col_letter].width = calc_width

    # ==========================================
    # Sheet 1: 表紙・システム概要
    # ==========================================
    ws1 = wb.create_sheet(title='システム概要')
    apply_sheet_settings(ws1)

    ws1.cell(row=2, column=2, value='讃岐うどん巡礼システム 詳細設計書').font = Font(name='Meiryo UI', size=18, bold=True, color='1B365D')
    ws1.cell(row=3, column=2, value='Sanuki Udon Pilgrimage Platform - System Detailed Design Specification').font = Font(name='Meiryo UI', size=10, italic=True, color='718096')

    info_data = [
        ('システム名称', '讃岐うどん巡礼システム（Udon Pilgrimage Web App）'),
        ('システムバージョン', 'Ver 1.0.0'),
        ('作成日 / 最終更新日', '2026年9月5日'),
        ('ドキュメント種別', '詳細設計書 (Detailed Design Specification)'),
        ('稼働URL', 'https://krmts.com/'),
        ('対応デバイス', 'スマートフォン (iOS / Android), タブレット, PC (レスポンシブ対応 / PWA対応)'),
    ]
    for idx, (label, val) in enumerate(info_data, start=5):
        c_lbl = ws1.cell(row=idx, column=2, value=label)
        c_lbl.font = font_bold
        c_lbl.fill = fill_section_bg
        c_lbl.border = border_thin
        c_lbl.alignment = align_left
        c_val = ws1.cell(row=idx, column=3, value=val)
        c_val.font = font_normal
        c_val.border = border_thin
        c_val.alignment = align_left
        ws1.row_dimensions[idx].height = 24

    # システム目的・特徴
    ws1.cell(row=12, column=2, value='1. システム概要と開発目的').font = font_section
    desc_rows = [
        '【目的】香川県名産の「讃岐うどん」巡り（うどん巡礼）を仲間と計画・巡回・記録・評価・共有するための総合Webプラットフォーム。',
        '【特徴1】Google Maps Platformと連携した直感的なルート案内・マップ表示。店舗間の移動時間を自動計算し、最適な巡回計画を支援。',
        '【特徴2】5軸評価（麺のコシ、出汁の旨味、店舗情緒、天ぷらサクサク度、コスパ）レーダーチャートによる本格的なうどんレビュー。',
        '【特徴3】複数メンバーでのリアルタイム旅共有・訪問ステータス更新・写真ギャラリー共有・いいね/コメント/プッシュ通知によるソーシャル交流。',
        '【特徴4】公式マスコット「うどんちゅ」を随所に配した温かみのある親しみやすいUI/UX、ワンタップ即座ユーザー切り替えログイン。',
    ]
    for idx, d in enumerate(desc_rows, start=13):
        c = ws1.cell(row=idx, column=2, value=d)
        c.font = font_normal
        ws1.row_dimensions[idx].height = 22

    # 技術スタック
    ws1.cell(row=19, column=2, value='2. システムアーキテクチャ・技術スタック一覧').font = font_section
    arch_headers = ['カテゴリ', '採用技術 / バージョン', '用途・詳細仕様']
    for c_idx, h in enumerate(arch_headers, start=2):
        cell = ws1.cell(row=20, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws1.row_dimensions[20].height = 26

    arch_data = [
        ('バックエンド言語', 'Python 3.12.14', '堅牢な型ヒント、高い実行パフォーマンス、Django 6系との完全互換性'),
        ('Webフレームワーク', 'Django 6.1', 'MTVアーキテクチャ、組み込みORM、CSRF保護、セッション管理、認証機能'),
        ('データベース', 'SQLite3', '軽量かつ高速なファイルベースRDBMS。将来的なPostgreSQL移行もORMにより透過的'),
        ('WSGIサーバー', 'Gunicorn 23.0.0', 'UNIXドメインソケット (`/run/gunicorn.sock`) 経由での高速プロセス管理 (Worker 3)'),
        ('Web / リバースプロキシ', 'Nginx + Let\'s Encrypt SSL', '静的ファイル配信、SSL/TLS終端、リバースプロキシ (`proxy_pass`)、HTTPS強制'),
        ('フロントエンド構文', 'HTML5 / CSS3 / Vanilla JavaScript', '軽量で依存関係ゼロ。高速なレンダリングと完全なDOM制御を実現'),
        ('デザインシステム', 'カスタムCSS (Glassmorphism & 和モダン)', '香川讃岐の色彩（香川橙、紺青、抹茶等）、微細アニメーション、ダークモード調ベース'),
        ('地図・位置情報連携', 'Google Maps Platform', 'Maps JavaScript API, Places API (オートコンプリート・スポット登録), Directions'),
        ('データ可視化', 'Chart.js v4.4.1', '店舗・レビュー詳細画面での5軸評価レーダーチャート動的描画'),
        ('PWA・オフライン対応', 'Web App Manifest, ServiceWorker', 'ホーム画面追加（A2HS）、ネイティブアプリ風の全画面表示（standalone）'),
    ]
    for r_idx, row in enumerate(arch_data, start=21):
        is_even = (r_idx % 2 == 0)
        fill = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=2):
            c = ws1.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_bold if c_idx == 2 else font_normal
            c.fill = fill
            c.border = border_thin
            c.alignment = align_center if c_idx == 2 else align_left
        ws1.row_dimensions[r_idx].height = 24

    ws1.column_dimensions['A'].width = 4
    ws1.column_dimensions['B'].width = 28
    ws1.column_dimensions['C'].width = 40
    ws1.column_dimensions['D'].width = 70

    # ==========================================
    # Sheet 2: 機能一覧
    # ==========================================
    ws2 = wb.create_sheet(title='機能一覧')
    apply_sheet_settings(ws2)
    ws2.freeze_panes = 'A3'

    ws2.cell(row=1, column=1, value='機能一覧 (Function Specifications)').font = font_title
    f_headers = ['機能ID', '大分類', '中分類', '機能名', '概要・処理内容', '対象権限', '関連画面ID', '関連API ID', '備考']
    for c_idx, h in enumerate(f_headers, start=1):
        cell = ws2.cell(row=2, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws2.row_dimensions[2].height = 26

    functions = [
        ('FN-001', '認証・ユーザー', 'ログイン', 'ワンタップ簡単ログイン', '登録済みユーザーチップをタップするだけで即時セッション確立・ログイン。最近ログイン順に左からソート表示。', '全ユーザー', 'SCR-001', 'API-012', 'パスワード入力不要の快適運用'),
        ('FN-002', '認証・ユーザー', 'ログイン', 'パスワード認証ログイン', 'ユーザー名とパスワードによる通常のDjango標準認証。', '未認証ユーザー', 'SCR-001', '-', '一般アカウント用'),
        ('FN-003', '認証・ユーザー', '新規登録', 'ユーザー新規登録', 'ユーザー名、初期表示名、テーマカラー、好みのうどん、パスワードを設定してアカウント作成。', '未認証ユーザー', 'SCR-002', '-', '重複チェック・バリデーション有'),
        ('FN-004', '認証・ユーザー', 'ログアウト', 'セッション破棄ログアウト', '現在のログインセッションを終了し、ログイン画面へ安全にリダイレクト。', '認証済ユーザー', '-', '-', 'CSRF保護POSTリクエスト'),
        ('FN-005', '認証・ユーザー', 'プロフィール', 'プロフィール参照・編集', 'ニックネーム、アイコン画像、アバター色、好みのうどん、自己紹介文の更新。', '認証済ユーザー', 'SCR-009', '-', '画像アップロード対応'),
        ('FN-006', 'うどん旅管理', '一覧表示', '参加旅一覧表示', '自身が主催またはメンバー招待された旅の一覧を表示。未参加の旅はフィルタリングされ非表示。', '認証済ユーザー', 'SCR-003', '-', '日程・参加人数・店舗数表示'),
        ('FN-007', 'うどん旅管理', '新規作成', '旅の新規作成', '旅のタイトル、開催日程（開始〜終了日）、公開設定、旅のメモを設定して新規作成。', '認証済ユーザー', 'SCR-004', '-', '作成者は自動的に主催者ロール'),
        ('FN-008', 'うどん旅管理', '編集・更新', '旅の基本情報編集', '既存の旅のタイトル、日付、メモ等を変更。主催者のみ実行可能。', '主催者', 'SCR-004', '-', '権限チェックあり'),
        ('FN-009', 'うどん旅管理', '削除', '旅の削除', '主催者のみ、旅全体とそのスケジュールを論理/物理削除可能。', '主催者', 'SCR-003', '-', '確認モーダル表示'),
        ('FN-010', 'うどん旅管理', 'ルート・マップ', '旅マップ表示', '旅に含まれる巡回ストップをGoogle Maps上にピン留め・順序ルートライン描画。', '旅参加メンバー', 'SCR-005', '-', '移動時間自動計算・店舗一覧連動'),
        ('FN-011', 'うどん旅管理', 'ストップ管理', '店舗のストップ追加', '検索または選択した店舗を旅の巡回リスト末尾に追加。移動時間を自動再計算。', '旅参加メンバー', 'SCR-005', 'API-002', '非同期AJAX処理'),
        ('FN-012', 'うどん旅管理', 'ストップ管理', 'ストップ並び替え', '巡回順（1番目、2番目…）のドラッグ＆ドロップまたはボタン並び替え。移動時間自動再計算。', '旅参加メンバー', 'SCR-005', 'API-001', 'リアルタイム順序反映'),
        ('FN-013', 'うどん旅管理', 'ストップ管理', 'ストップ削除', '旅の巡回予定から指定店舗を削除。後続ストップの訪問順を自動繰り上げ。', '旅参加メンバー', 'SCR-005', 'API-003', 'AJAX非同期'),
        ('FN-014', 'うどん旅管理', 'メンバー管理', '同行メンバー招待・追加', '登録済みうどん人から旅のメンバーを検索・追加。招待通知を送信。', '旅参加メンバー', 'SCR-005', 'API-004', '重複追加防止'),
        ('FN-015', 'うどん旅管理', 'メンバー管理', 'メンバー削除・離脱', '旅からメンバーを除外、または自ら離脱。', '主催者/本人', 'SCR-005', 'API-005', '権限バリデーション'),
        ('FN-016', '店舗情報', '一覧・検索', 'うどん店舗一覧表示・検索', '登録店舗のフリーワード検索（店名・名物・住所）、ページネーション、Google評価順表示。', '全ユーザー', 'SCR-006', '-', '香川全域の名店網羅'),
        ('FN-017', '店舗情報', '店舗詳細', '店舗詳細・レビュー閲覧', '店舗の写真、基本情報、営業時間、Google評価、みんなの5軸評価・最新レビュー一覧表示。', '全ユーザー', 'SCR-007', '-', '写真カルーセル、タブ切替'),
        ('FN-018', '店舗情報', 'Google連携', 'Places APIからの店舗追加', 'Googleマップ上で店舗を検索し、店名・住所・緯度経度・Place IDを取得して新店舗として即時登録。', '認証済ユーザー', 'SCR-005/006', 'API-010', '重複チェック機能付き'),
        ('FN-019', '店舗情報', '写真管理', '店舗写真ギャラリー・投稿', 'ユーザーが店舗の写真を直接アップロード。最新の写真が店舗トップ写真に自動同期。', '認証済ユーザー', 'SCR-007', 'API-008', '画像最適化・プレビュー'),
        ('FN-020', '店舗情報', '写真管理', '店舗写真削除', '自身が投稿した店舗写真を削除。トップ写真も自動再同期。', '写真投稿者', 'SCR-007', 'API-008', '他人の写真は削除不可'),
        ('FN-021', '店舗情報', 'お気に入り', 'お気に入り店舗登録/解除', '店舗をお気に入りにワンクリック登録/解除。マイページやお気に入り一覧から即参照可能。', '認証済ユーザー', 'SCR-007', 'API-011', 'AJAX非同期トグル'),
        ('FN-022', 'レビュー・評価', '投稿・編集', '5軸うどんレビュー投稿', '総合スコア（1.0〜5.0）、5軸スコア（麺、出汁、情緒、天ぷら、コスパ 各10点満点）、写真、コメント、認定スタンプ投稿。', '認証済ユーザー', 'SCR-008', '-', '旅連動レビュー対応'),
        ('FN-023', 'レビュー・評価', '可視化', '5軸レーダーチャート描画', '店舗全体の平均5軸スコア、および個別レビューの5軸スコアをChart.jsレーダーチャートで美麗に可視化。', '全ユーザー', 'SCR-007', '-', 'レスポンシブCanvas描画'),
        ('FN-024', 'レビュー・評価', '削除', 'レビュー削除', '自身が投稿したレビューを削除。関連するいいね・コメント・通知・写真も整合性を保ち削除。', 'レビュー投稿者', 'SCR-007', 'API-006', '確認ダイアログ有'),
        ('FN-025', 'ソーシャル', 'いいね', 'レビューいいねトグル', 'レビューに対して「いいね」を送受信。ワンクリックでトグル。投稿者に通知を自動作成。', '認証済ユーザー', 'SCR-007', 'API-007', '重複防止・自作自演考慮'),
        ('FN-026', 'ソーシャル', 'コメント', 'レビューへのコメント投稿', 'レビューに対してスレッド形式でコメントを投稿。対象レビュー投稿者にコメント通知を送信。', '認証済ユーザー', 'SCR-007', 'API-008', 'リアルタイムDOM反映'),
        ('FN-027', 'ソーシャル', 'コメント削除', '自身のコメント削除', '自身が投稿したレビューコメントを削除。', 'コメント投稿者', 'SCR-007', 'API-009', '権限検証あり'),
        ('FN-028', 'ソーシャル', '通知一覧', '新着通知一覧・未読バッジ', 'ナビバーに未読通知件数バッジ表示。通知ドロップダウンで「いいね」「コメント」の最新状況を確認・既読化。', '認証済ユーザー', '全画面共通', 'API-009', '該当レビューへのジャンプリンク'),
        ('FN-029', '共通演出', 'マスコット', 'うどんちゅ演出', '公式キャラクター「うどんちゅ」が空き状態（Empty State）、成功メッセージ、検索バー、ヘッダーに登場してUX向上。', '全ユーザー', '全画面共通', '-', '愛らしいビジュアル演出'),
        ('FN-030', 'システム管理', 'データ保守', '店舗シード投入・初期化', '香川県全域の名店100選マスターデータ一括登録コマンド、テストデータクリーンアップコマンド。', 'システム管理者', 'CLI', '-', 'management commands'),
    ]

    for r_idx, row in enumerate(functions, start=3):
        is_even = (r_idx % 2 == 0)
        fill = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=1):
            c = ws2.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_bold if c_idx == 1 else font_normal
            c.fill = fill
            c.border = border_thin
            if c_idx in [1, 2, 3, 6, 7, 8]:
                c.alignment = align_center
            else:
                c.alignment = align_left
        ws2.row_dimensions[r_idx].height = 24

    adjust_column_widths(ws2, min_widths={'A': 10, 'B': 16, 'C': 16, 'D': 24, 'E': 45, 'F': 16, 'G': 14, 'H': 14, 'I': 24})

    # ==========================================
    # Sheet 3: 画面一覧・画面設計
    # ==========================================
    ws3 = wb.create_sheet(title='画面一覧・設計')
    apply_sheet_settings(ws3)
    ws3.freeze_panes = 'A3'

    ws3.cell(row=1, column=1, value='画面一覧・画面設計仕様書 (Screen Specifications)').font = font_title
    s_headers = ['画面ID', '画面名', 'URL / パス', 'テンプレートファイル', '概要・主要レイアウト', '主要コンポーネント・機能', '権限・制限']
    for c_idx, h in enumerate(s_headers, start=1):
        cell = ws3.cell(row=2, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws3.row_dimensions[2].height = 26

    screens = [
        ('SCR-001', 'ログイン画面', '/login/', 'udon/auth/login.html', 'ユーザー認証画面。上部に「登録済みのうどん人（最近利用順）」の横スクロールチップ群を配置し、下部に通常ログイン/新規登録タブを備える。', '・ワンタップ即時ログイン（最近利用順ソート、最新バッジ付）\n・ユーザー名/パスワード入力フォーム\n・新規登録フォーム切り替えタブ\n・公式マスコット「うどんちゅ」ウェルカム表示', '未認証（ログイン済はホームへ転送）'),
        ('SCR-002', 'ユーザー新規登録画面', '/signup/', 'udon/auth/signup.html', '新規アカウント作成画面。ニックネーム、ユーザー名、パスワード、テーマカラーピッカー、好みのうどん選択。', '・アカウント基本情報入力フォーム\n・アバター背景カラー選択スウォッチ（6色）\n・お気に入りうどんセレクトボックス\n・リアルタイム入力バリデーション', '未認証のみ'),
        ('SCR-003', 'うどん旅一覧画面', '/trips/', 'udon/trip_list.html', '自分が参加・主催しているうどん旅カード一覧画面。カードには訪問日程、ストップ数、参加メンバーアバター群を表示。', '・参加旅カードグリッド表示\n・新規旅作成へのFAB / ボタン\n・旅の主催/参加ステータスバッジ\n・旅カードクリックによるマップ遷移\n・うどんちゅのEmpty State表示', '認証済ユーザーのみ'),
        ('SCR-004', '旅作成・編集画面', '/trips/create/, /trips/<id>/edit/', 'udon/trip_form.html', '旅の新規企画または既存旅の登録情報編集フォーム。タイトル、日程期間、公開フラグ、メモの入力。', '・旅タイトル入力フィールド\n・開催日/開始日/終了日カレンダーピッカー\n・公開/非公開トグルスイッチ\n・旅のしおりメモ入力エリア\n・保存/キャンセルボタン', '認証済ユーザー（編集は主催者のみ）'),
        ('SCR-005', '旅ルートマップ画面', '/trips/<trip_id>/', 'udon/trip_map.html', 'システムの中核画面。上部または左側にGoogle Mapsを表示し、下部または右側に巡回ストップタイムラインを表示。', '・Google Maps JS API（全ピン自動フィット、ルート結線）\n・巡回ストップリスト（訪問順ドラッグ並び替え対応）\n・所要時間自動計算バッジ（「車で18分」等）\n・ストップ追加モーダル（店舗検索/Google Places連携）\n・メンバー招待モーダル\n・店舗詳細スライドオーバー/遷移', '旅の主催者または参加メンバーのみ'),
        ('SCR-006', 'うどん店舗一覧画面', '/shops/', 'udon/shop_list.html', '香川県内のうどん店舗検索・閲覧画面。キーワード検索バーと、評価・名物メニュー付きの店舗カードグリッド。', '・リアルタイムキーワード検索バー（店名・名物・住所）\n・店舗カード（写真、Google評価星、名物メニューバッジ）\n・Google Placeからの新規店舗インポートボタン\n・店舗詳細へのスムーズリンク', '全ユーザー（未認証でも閲覧可）'),
        ('SCR-007', '店舗詳細・レビュー画面', '/shops/<shop_id>/', 'udon/shop_detail.html', '店舗の全容を表示する画面。トップ写真、Google評価、5軸総合レーダーチャート、レビュー一覧、写真ギャラリー。', '・店舗写真カルーセル・トップ写真動的表示\n・5軸評価レーダーチャート（Chart.js）\n・レビュー一覧（いいねボタン、コメントスレッド）\n・写真ギャラリー一覧・写真モーダル拡大表示\n・「評価を書く」アクションボタン\n・店舗写真アップロードモーダル\n・お気に入り登録ボタン（★）', '全ユーザー（いいね/投稿は要認証）'),
        ('SCR-008', 'レビュー投稿画面', '/shops/<shop_id>/review/', 'udon/review_form.html', '店舗への詳細評価を登録する入力画面。5軸それぞれのスライダー/数値入力、総合星評価、写真添付、認定スタンプ。', '・総合星評価ピッカー（1.0〜5.0）\n・5軸評価入力（麺、出汁、情緒、天ぷら、コスパ）\n・写真ファイル添付＆即時プレビュー\n・認定スタンプ選択（「香川人選」「名店認定」等）\n・レビュー本文エディタ', '認証済ユーザーのみ'),
        ('SCR-009', 'プロフィール編集画面', '/profile/edit/', 'udon/profile_form.html', '自身のうどん人ステータス、アバター、自己紹介文を編集・管理する画面。', '・ニックネーム変更フォーム\n・アバター画像アップロード＆プレビュー\n・アバターテーマカラー選択パレット\n・好みのうどん・自己紹介文編集\n・自身の累計訪問店舗数・レビュー数表示', '認証済ユーザーのみ'),
        ('SCR-010', '全画面共通ナビ・フッター', '共通', 'udon/base.html', '画面上部ナビゲーションバーおよび下部モバイルボトムナビ、通知ポップオーバー、トーストメッセージ。', '・ロゴ＆マスコット「うどんちゅ」アイコン\n・グローバルナビ（旅一覧、店舗一覧、マイページ）\n・未読通知ベルアイコン＆通知一覧ドロップダウン\n・モバイル向け固定ボトムバー\n・Django Messagesトースト通知', '全画面共通'),
    ]

    for r_idx, row in enumerate(screens, start=3):
        is_even = (r_idx % 2 == 0)
        fill = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=1):
            c = ws3.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_bold if c_idx == 1 else font_normal
            c.fill = fill
            c.border = border_thin
            if c_idx in [1, 2, 7]:
                c.alignment = align_center
            else:
                c.alignment = align_left
        ws3.row_dimensions[r_idx].height = 42

    adjust_column_widths(ws3, min_widths={'A': 12, 'B': 22, 'C': 25, 'D': 25, 'E': 45, 'F': 45, 'G': 20})

    # ==========================================
    # Sheet 4: DB設計（テーブル一覧）
    # ==========================================
    ws4 = wb.create_sheet(title='DB設計（テーブル一覧）')
    apply_sheet_settings(ws4)
    ws4.freeze_panes = 'A3'

    ws4.cell(row=1, column=1, value='データベース設計 - テーブル一覧 (Database Table List)').font = font_title
    t_headers = ['No', '物理テーブル名', '論理名 (モデル名)', '概要・用途', '主キー', '外部キー (FK)', '想定レコード規模', '備考']
    for c_idx, h in enumerate(t_headers, start=1):
        cell = ws4.cell(row=2, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws4.row_dimensions[2].height = 26

    tables = [
        ('1', 'udon_shop', 'Shop (うどん店舗)', '讃岐うどん店舗のマスター情報。店名、住所、緯度経度、Google評価、名物メニュー、写真等を管理。', 'id', '-', '数百〜数千件', 'Google Place ID対応'),
        ('2', 'udon_trip', 'Trip (うどん旅)', 'ユーザーが作成する旅行スケジュール。タイトル、開催日、メモ、公開設定を保持。', 'id', 'owner (auth_user)', '数十〜数百件', '旅の主エンティティ'),
        ('3', 'udon_tripmember', 'TripMember (参加メンバー)', 'うどん旅に参加するメンバー一覧。ユーザー紐付け、ロール（主催者/メンバー）、アバター色。', 'id', 'trip (Trip), user (auth_user)', '数百件', 'ニックネーム対応'),
        ('4', 'udon_tripstop', 'TripStop (巡回ストップ)', 'うどん旅に含まれる訪問予定店舗。巡回順、予定時刻、移動時間テキスト、訪問ステータス。', 'id', 'trip (Trip), shop (Shop)', '数千件', 'unique(trip, visit_order)'),
        ('5', 'udon_review', 'Review (うどんレビュー)', '店舗に対する評価レビュー。総合評価、5軸評価、コメント、写真、認定スタンプを記録。', 'id', 'trip (Trip), shop (Shop), user (auth_user)', '数千〜数万件', '店舗写真と連動更新'),
        ('6', 'udon_reviewlike', 'ReviewLike (レビューいいね)', 'レビューに対するユーザーの「いいね」履歴。重複登録不可のユニーク制約。', 'id', 'review (Review), user (auth_user)', '数万件', 'unique(review, user)'),
        ('7', 'udon_reviewcomment', 'ReviewComment (レビューコメント)', 'レビューに対するユーザーのコメント投稿スレッド。投稿日時昇順。', 'id', 'review (Review), user (auth_user)', '数万件', '通知トリガー対象'),
        ('8', 'udon_shopphoto', 'ShopPhoto (店舗写真)', 'ユーザーから投稿された店舗の写真ギャラリー。投稿者、画像、キャプション。', 'id', 'shop (Shop), user (auth_user)', '数千〜数万件', '最新写真が店舗トップへ反映'),
        ('9', 'udon_userprofile', 'UserProfile (プロフィール)', 'Django標準Userモデルの1対1拡張。ニックネーム、アバター画像、テーマ色、好みのうどん。', 'id', 'user (auth_user [OneToOne])', 'ユーザー数と同等', 'ワンタップログインの基盤'),
        ('10', 'udon_notification', 'Notification (通知)', 'いいねやコメント等のアクティビティ通知。既読フラグ、送信者/受信者、対象レビュー。', 'id', 'recipient, sender, review, comment', '数万件', '未読件数高速カウント'),
        ('11', 'udon_shopfavorite', 'ShopFavorite (お気に入り店舗)', 'ユーザーのお気に入り店舗リスト。お気に入りの理由・個人メモを保持。', 'id', 'user (auth_user), shop (Shop)', '数千件', 'unique(user, shop)'),
        ('12', 'auth_user', 'User (Django標準認証ユーザー)', '認証基盤ユーザー。ユーザー名、暗号化パスワード、最終ログイン日時、登録日時。', 'id', '-', 'ユーザー数と同等', 'last_loginでソート'),
    ]

    for r_idx, row in enumerate(tables, start=3):
        is_even = (r_idx % 2 == 0)
        fill = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=1):
            c = ws4.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_bold if c_idx in [1, 2, 3] else font_normal
            c.fill = fill
            c.border = border_thin
            if c_idx in [1, 5, 7]:
                c.alignment = align_center
            else:
                c.alignment = align_left
        ws4.row_dimensions[r_idx].height = 24

    adjust_column_widths(ws4, min_widths={'A': 8, 'B': 22, 'C': 26, 'D': 45, 'E': 10, 'F': 25, 'G': 18, 'H': 24})

    # ==========================================
    # Sheet 5: DB詳細（カラム定義）
    # ==========================================
    ws5 = wb.create_sheet(title='DB詳細（カラム定義）')
    apply_sheet_settings(ws5)
    ws5.freeze_panes = 'A3'

    ws5.cell(row=1, column=1, value='データベース詳細設計 - カラム定義書 (Column Specifications)').font = font_title
    c_headers = ['テーブル名', '物理カラム名', '論理カラム名', 'データ型', 'PK', 'FK / 参照先', 'Not Null', 'デフォルト値', '説明・業務仕様']
    for c_idx, h in enumerate(c_headers, start=1):
        cell = ws5.cell(row=2, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws5.row_dimensions[2].height = 26

    columns_data = [
        # Shop
        ('udon_shop', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', '店舗固有の一意識別子 (PK)'),
        ('udon_shop', 'name', '店舗名', 'VARCHAR(100)', '-', '-', '○', '-', 'うどん店舗の正式名称'),
        ('udon_shop', 'address', '住所', 'VARCHAR(255)', '-', '-', '○', '-', '香川県内の店舗所在地'),
        ('udon_shop', 'lat', '緯度', 'FLOAT', '-', '-', '○', '34.3427', 'マップ表示用の緯度座標'),
        ('udon_shop', 'lng', '経度', 'FLOAT', '-', '-', '○', '134.0465', 'マップ表示用の経度座標'),
        ('udon_shop', 'place_id', 'Google Place ID', 'VARCHAR(150)', '-', '-', '空許可', "''", 'Google Maps Places APIの一意ID'),
        ('udon_shop', 'google_rating', 'Google評価', 'FLOAT', '-', '-', '空許可', 'NULL', 'Google Place上の評価点 (1.0〜5.0)'),
        ('udon_shop', 'google_user_ratings_total', 'Google口コミ件数', 'INTEGER', '-', '-', '○', '0', 'Google Place上の口コミ総件数'),
        ('udon_shop', 'featured_menu', '名物メニュー', 'VARCHAR(150)', '-', '-', '空許可', "''", '店舗の看板メニュー（例: かまたま、肉うどん）'),
        ('udon_shop', 'price_range', '価格帯', 'VARCHAR(50)', '-', '-', '○', "'300円〜700円'", '平均的な予算・価格帯'),
        ('udon_shop', 'opening_hours', '営業時間', 'VARCHAR(150)', '-', '-', '空許可', "''", '営業時間・定休日（例: 9:00〜14:00 火曜休）'),
        ('udon_shop', 'photo', '店舗写真', 'VARCHAR(100)', '-', '-', '空許可', 'NULL', '店舗メイン画像 (Media: shops/)'),
        ('udon_shop', 'photo_url', '写真URL', 'VARCHAR(500)', '-', '-', '空許可', "''", '外部写真URL（静的アセット等）'),
        ('udon_shop', 'description', '店舗紹介・メモ', 'TEXT', '-', '-', '空許可', "''", '店舗の特徴、歴史、巡回メモ'),
        ('udon_shop', 'created_at', '登録日時', 'DATETIME', '-', '-', '○', 'auto_now_add', 'レコード作成日時'),

        # Trip
        ('udon_trip', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', 'うどん旅の一意識別子 (PK)'),
        ('udon_trip', 'title', '旅行タイトル', 'VARCHAR(150)', '-', '-', '○', "'香川うどん巡礼2026'", '旅の名称・しおりタイトル'),
        ('udon_trip', 'owner_id', '作成者ID', 'INTEGER', '-', 'auth_user.id', '○', '-', '旅の主催者ユーザー (CASCADE)'),
        ('udon_trip', 'date', '日程', 'DATE', '-', '-', '○', 'timezone.now', '旅の基準日程'),
        ('udon_trip', 'start_date', '開始日', 'DATE', '-', '-', '空許可', 'NULL', '複数日巡回時の開始日'),
        ('udon_trip', 'end_date', '終了日', 'DATE', '-', '-', '空許可', 'NULL', '複数日巡回時の終了日'),
        ('udon_trip', 'is_public', '公開設定', 'BOOLEAN', '-', '-', '○', 'TRUE', '旅の公開/非公開フラグ'),
        ('udon_trip', 'memo', '旅行メモ', 'TEXT', '-', '-', '空許可', "''", '旅のしおりメモ・持ち物など'),
        ('udon_trip', 'created_at', '作成日時', 'DATETIME', '-', '-', '○', 'auto_now_add', 'レコード作成日時'),
        ('udon_trip', 'updated_at', '更新日時', 'DATETIME', '-', '-', '○', 'auto_now', 'レコード更新日時'),

        # TripMember
        ('udon_tripmember', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', '参加メンバーID (PK)'),
        ('udon_tripmember', 'trip_id', '旅行ID', 'INTEGER', '-', 'udon_trip.id', '○', '-', '紐付くうどん旅 (CASCADE)'),
        ('udon_tripmember', 'user_id', 'ユーザーID', 'INTEGER', '-', 'auth_user.id', '空許可', 'NULL', '紐付く認証ユーザー (SET_NULL)'),
        ('udon_tripmember', 'name', 'メンバー名', 'VARCHAR(50)', '-', '-', '○', "'会員さん'", 'メンバー表示名（ニックネーム）'),
        ('udon_tripmember', 'avatar_color', 'アバター色', 'VARCHAR(20)', '-', '-', '○', "'#D99B26'", 'アバター円の背景色HEX'),
        ('udon_tripmember', 'avatar_icon', 'アバターアイコン', 'VARCHAR(10)', '-', '-', '○', "'会'", 'イニシャルまたはアイコン識別子'),
        ('udon_tripmember', 'role', '役割', 'VARCHAR(20)', '-', '-', '○', "'member'", '役割 (owner: 主催者, member: 参加者)'),
        ('udon_tripmember', 'joined_at', '参加日時', 'DATETIME', '-', '-', '○', 'auto_now_add', 'メンバー登録日時'),

        # TripStop
        ('udon_tripstop', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', '巡回ストップID (PK)'),
        ('udon_tripstop', 'trip_id', '旅行ID', 'INTEGER', '-', 'udon_trip.id', '○', '-', '所属するうどん旅 (CASCADE)'),
        ('udon_tripstop', 'shop_id', '店舗ID', 'INTEGER', '-', 'udon_shop.id', '○', '-', '巡回対象の店舗 (CASCADE)'),
        ('udon_tripstop', 'visit_order', '巡回順', 'INTEGER', '-', '-', '○', '1', '訪問順（1〜）。(trip, order)で一意'),
        ('udon_tripstop', 'scheduled_time', '予定時刻', 'TIME', '-', '-', '空許可', 'NULL', '訪問予定時間（例: 10:30）'),
        ('udon_tripstop', 'travel_time_text', '所要時間表示', 'VARCHAR(50)', '-', '-', '○', "'車で18分'", '前ストップからの移動時間目安'),
        ('udon_tripstop', 'status', '訪問ステータス', 'VARCHAR(20)', '-', '-', '○', "'planned'", 'planned(予定), visited(訪問済), skipped(スキップ)'),
        ('udon_tripstop', 'notes', '備考・注文予定', 'TEXT', '-', '-', '空許可', "''", '店舗での注文予定（例: 釜玉小＋ちくわ天）'),

        # Review
        ('udon_review', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', 'レビューID (PK)'),
        ('udon_review', 'trip_id', '旅ID', 'INTEGER', '-', 'udon_trip.id', '空許可', 'NULL', '巡回旅でのレビュー紐付け (SET_NULL)'),
        ('udon_review', 'shop_id', '店舗ID', 'INTEGER', '-', 'udon_shop.id', '○', '-', '対象店舗 (CASCADE)'),
        ('udon_review', 'user_id', 'ユーザーID', 'INTEGER', '-', 'auth_user.id', '空許可', 'NULL', '投稿者ユーザー (SET_NULL)'),
        ('udon_review', 'author_name', '投稿者名', 'VARCHAR(50)', '-', '-', '○', "'会員さん'", 'レビュー表示名'),
        ('udon_review', 'author_avatar_color', 'アバター色', 'VARCHAR(20)', '-', '-', '○', "'#D99B26'", '投稿者アイコン色'),
        ('udon_review', 'score_total', '総合評価', 'DECIMAL(3,1)', '-', '-', '○', '4.8', '星評価 (1.0〜5.0)'),
        ('udon_review', 'score_noodle', '麺のコシ', 'SMALLINT', '-', '-', '○', '8', '5軸評価1: 麺のコシ・喉ごし (1〜10)'),
        ('udon_review', 'score_soup', '出汁の風味', 'SMALLINT', '-', '-', '○', '8', '5軸評価2: 出汁の旨味 (1〜10)'),
        ('udon_review', 'score_atmosphere', '店舗情緒', 'SMALLINT', '-', '-', '○', '8', '5軸評価3: 店の雰囲気・風情 (1〜10)'),
        ('udon_review', 'score_tempura', '天ぷらサクサク', 'SMALLINT', '-', '-', '○', '8', '5軸評価4: 天ぷらの揚げ具合 (1〜10)'),
        ('udon_review', 'score_cost', 'コスパ満足度', 'SMALLINT', '-', '-', '○', '9', '5軸評価5: コストパフォーマンス (1〜10)'),
        ('udon_review', 'comment', 'レビュー本文', 'TEXT', '-', '-', '空許可', "''", 'うどんの感想・おすすめの食べ方'),
        ('udon_review', 'photo', 'レビュー写真', 'VARCHAR(100)', '-', '-', '空許可', 'NULL', '撮影写真 (Media: reviews/)'),
        ('udon_review', 'photo_url', '写真URL', 'VARCHAR(500)', '-', '-', '空許可', "''", '外部写真URL'),
        ('udon_review', 'stamp_type', '認定スタンプ', 'VARCHAR(30)', '-', '-', '○', "'香川人選'", '香川人選 / 名店認定 / 巡礼完了 / 絶品百選'),
        ('udon_review', 'created_at', '投稿日時', 'DATETIME', '-', '-', '○', 'auto_now_add', 'レビュー投稿日時'),

        # ReviewLike
        ('udon_reviewlike', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', 'いいねID (PK)'),
        ('udon_reviewlike', 'review_id', '対象レビューID', 'INTEGER', '-', 'udon_review.id', '○', '-', '対象レビュー (CASCADE)'),
        ('udon_reviewlike', 'user_id', 'ユーザーID', 'INTEGER', '-', 'auth_user.id', '○', '-', 'いいねしたユーザー (CASCADE)'),
        ('udon_reviewlike', 'created_at', 'いいね日時', 'DATETIME', '-', '-', '○', 'auto_now_add', 'いいね登録日時。(review, user)一意'),

        # ReviewComment
        ('udon_reviewcomment', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', 'コメントID (PK)'),
        ('udon_reviewcomment', 'review_id', '対象レビューID', 'INTEGER', '-', 'udon_review.id', '○', '-', '対象レビュー (CASCADE)'),
        ('udon_reviewcomment', 'user_id', 'ユーザーID', 'INTEGER', '-', 'auth_user.id', '○', '-', 'コメント投稿者 (CASCADE)'),
        ('udon_reviewcomment', 'author_name', '投稿者名', 'VARCHAR(50)', '-', '-', '○', "'会員さん'", '投稿者ニックネーム'),
        ('udon_reviewcomment', 'content', 'コメント本文', 'TEXT', '-', '-', '○', '-', 'コメント内容'),
        ('udon_reviewcomment', 'created_at', '投稿日時', 'DATETIME', '-', '-', '○', 'auto_now_add', 'コメント投稿日時'),

        # ShopPhoto
        ('udon_shopphoto', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', '写真ID (PK)'),
        ('udon_shopphoto', 'shop_id', '店舗ID', 'INTEGER', '-', 'udon_shop.id', '○', '-', '対象店舗 (CASCADE)'),
        ('udon_shopphoto', 'user_id', 'ユーザーID', 'INTEGER', '-', 'auth_user.id', '空許可', 'NULL', '投稿者 (SET_NULL)'),
        ('udon_shopphoto', 'author_name', '投稿者名', 'VARCHAR(50)', '-', '-', '○', "'会員さん'", '投稿者ニックネーム'),
        ('udon_shopphoto', 'image', '画像ファイル', 'VARCHAR(100)', '-', '-', '○', '-', '画像本体 (Media: shop_photos/)'),
        ('udon_shopphoto', 'caption', '写真メモ・説明', 'VARCHAR(150)', '-', '-', '空許可', "''", '写真の説明（例: 釜揚げ大とうずら卵）'),
        ('udon_shopphoto', 'created_at', '投稿日時', 'DATETIME', '-', '-', '○', 'auto_now_add', '写真投稿日時'),

        # UserProfile
        ('udon_userprofile', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', 'プロフィールID (PK)'),
        ('udon_userprofile', 'user_id', 'ユーザーID', 'INTEGER', '-', 'auth_user.id [1:1]', '○', '-', 'Django認証ユーザーと1対1 (CASCADE)'),
        ('udon_userprofile', 'nickname', 'ニックネーム', 'VARCHAR(50)', '-', '-', '○', '-', '画面上の表示名'),
        ('udon_userprofile', 'avatar_image', 'アバター画像', 'VARCHAR(100)', '-', '-', '空許可', 'NULL', 'カスタム顔写真 (Media: avatars/)'),
        ('udon_userprofile', 'avatar_color', 'アバターカラー', 'VARCHAR(20)', '-', '-', '○', "'#E67E22'", '背景色HEXコード（香川橙等）'),
        ('udon_userprofile', 'avatar_icon', 'アバタータイプ', 'VARCHAR(50)', '-', '-', '○', "'udonchu'", 'アバター種別'),
        ('udon_userprofile', 'favorite_udon', '好みのうどん', 'VARCHAR(50)', '-', '-', '○', "'釜玉うどん'", '好きなうどんの種類'),
        ('udon_userprofile', 'level_title', 'うどん人称号', 'VARCHAR(50)', '-', '-', '○', "'見習いうどん人'", '訪問実績に応じた称号'),
        ('udon_userprofile', 'bio', '自己紹介', 'TEXT', '-', '-', '空許可', "''", 'プロフィール自己紹介文'),
        ('udon_userprofile', 'created_at', '作成日時', 'DATETIME', '-', '-', '○', 'auto_now_add', 'プロフィール作成日時'),

        # Notification
        ('udon_notification', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', '通知ID (PK)'),
        ('udon_notification', 'recipient_id', '受信者ID', 'INTEGER', '-', 'auth_user.id', '○', '-', '通知の受取人 (CASCADE)'),
        ('udon_notification', 'sender_id', '送信者ID', 'INTEGER', '-', 'auth_user.id', '○', '-', 'アクションを起こしたユーザー (CASCADE)'),
        ('udon_notification', 'notification_type', '通知種別', 'VARCHAR(20)', '-', '-', '○', '-', 'like(いいね), comment(コメント)'),
        ('udon_notification', 'review_id', '対象レビューID', 'INTEGER', '-', 'udon_review.id', '空許可', 'NULL', '対象レビュー (CASCADE)'),
        ('udon_notification', 'comment_id', '対象コメントID', 'INTEGER', '-', 'udon_reviewcomment.id', '空許可', 'NULL', '対象コメント (CASCADE)'),
        ('udon_notification', 'message', 'メッセージ', 'VARCHAR(255)', '-', '-', '空許可', "''", '通知表示本文'),
        ('udon_notification', 'is_read', '既読フラグ', 'BOOLEAN', '-', '-', '○', 'FALSE', '既読ステータス'),
        ('udon_notification', 'created_at', '通知日時', 'DATETIME', '-', '-', '○', 'auto_now_add', '通知発生日時'),

        # ShopFavorite
        ('udon_shopfavorite', 'id', 'ID', 'INTEGER', '○', '-', '○', 'AUTO', 'お気に入りID (PK)'),
        ('udon_shopfavorite', 'user_id', 'ユーザーID', 'INTEGER', '-', 'auth_user.id', '○', '-', 'お気に入り登録ユーザー (CASCADE)'),
        ('udon_shopfavorite', 'shop_id', '店舗ID', 'INTEGER', '-', 'udon_shop.id', '○', '-', 'お気に入り店舗 (CASCADE)'),
        ('udon_shopfavorite', 'reason', 'お気に入り理由メモ', 'TEXT', '-', '-', '空許可', "''", 'なぜお気に入りかの個人メモ'),
        ('udon_shopfavorite', 'created_at', '登録日時', 'DATETIME', '-', '-', '○', 'auto_now_add', '登録日時。(user, shop)一意'),
        ('udon_shopfavorite', 'updated_at', '更新日時', 'DATETIME', '-', '-', '○', 'auto_now', '更新日時'),
    ]

    curr_table = ''
    fill_current = fill_white
    for r_idx, row in enumerate(columns_data, start=3):
        tbl_name = row[0]
        if tbl_name != curr_table:
            curr_table = tbl_name
            fill_current = fill_white if fill_current == fill_zebra else fill_zebra

        for c_idx, val in enumerate(row, start=1):
            c = ws5.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_code if c_idx in [2, 4, 8] else (font_bold if c_idx in [1, 3] else font_normal)
            c.fill = fill_current
            c.border = border_thin
            if c_idx in [1, 2, 4, 5, 6, 7]:
                c.alignment = align_center
            else:
                c.alignment = align_left
        ws5.row_dimensions[r_idx].height = 22

    adjust_column_widths(ws5, min_widths={'A': 18, 'B': 22, 'C': 18, 'D': 16, 'E': 6, 'F': 22, 'G': 10, 'H': 16, 'I': 45})

    # ==========================================
    # Sheet 6: API・インターフェース設計
    # ==========================================
    ws6 = wb.create_sheet(title='API一覧・設計')
    apply_sheet_settings(ws6)
    ws6.freeze_panes = 'A3'

    ws6.cell(row=1, column=1, value='API・インターフェース仕様書 (REST / AJAX API Specifications)').font = font_title
    a_headers = ['API ID', 'エンドポイントURL', 'Method', '機能名・概要', '認証', 'リクエスト仕様 (Headers / Params / Body)', 'レスポンス仕様 (JSON Schema)', 'ステータスコード']
    for c_idx, h in enumerate(a_headers, start=1):
        cell = ws6.cell(row=2, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws6.row_dimensions[2].height = 26

    apis = [
        ('API-001', '/api/trips/<trip_id>/reorder-stops/', 'POST', 'ストップ並び替え', '必須 (旅メンバー)', 'X-CSRFToken, Content-Type: application/json\nBody: {"stop_ids": [3, 1, 2]}', '{"success": true, "message": "並び替え完了", "stops": [...]}', '200: 成功\n400: 不正リクエスト\n403: 権限なし'),
        ('API-002', '/api/trips/<trip_id>/add-stop/', 'POST', '店舗ストップ追加', '必須 (旅メンバー)', 'X-CSRFToken\nForm-Data: shop_id, scheduled_time, notes', '{"success": true, "stop": {"id": 10, "shop_name": "山越うどん", "visit_order": 4}}', '200: 成功\n404: 店舗未存在'),
        ('API-003', '/api/trips/<trip_id>/stops/<stop_id>/delete/', 'POST', 'ストップ削除', '必須 (旅メンバー)', 'X-CSRFToken', '{"success": true, "message": "ストップを削除しました"}', '200: 成功\n404: 未存在'),
        ('API-004', '/api/trips/<trip_id>/add-member/', 'POST', 'メンバー招待・追加', '必須 (旅メンバー)', 'X-CSRFToken\nForm-Data: user_id or name', '{"success": true, "member": {"id": 5, "name": "くろろん", "role": "member"}}', '200: 成功\n400: 既に参加済'),
        ('API-005', '/api/trips/<trip_id>/members/<member_id>/delete/', 'POST', 'メンバー除外・離脱', '必須 (主催者/本人)', 'X-CSRFToken', '{"success": true, "message": "メンバーを除外しました"}', '200: 成功\n403: 権限不足'),
        ('API-006', '/api/reviews/<review_id>/delete/', 'POST', 'レビュー削除', '必須 (投稿者本人のみ)', 'X-CSRFToken', '{"success": true, "message": "レビューを削除しました"}', '200: 成功\n403: 権限不足'),
        ('API-007', '/api/reviews/<review_id>/like/', 'POST', 'レビューいいねトグル', '必須', 'X-CSRFToken', '{"success": true, "liked": true, "like_count": 5}', '200: 成功\n401: 未ログイン'),
        ('API-008', '/api/reviews/<review_id>/comments/', 'POST', 'レビューコメント投稿', '必須', 'X-CSRFToken\nForm-Data: content (テキスト)', '{"success": true, "comment": {"id": 12, "author_name": "やしのき", "content": "..."}}', '200: 成功\n400: 本文空'),
        ('API-009', '/api/comments/<comment_id>/delete/', 'POST', 'コメント削除', '必須 (投稿者本人のみ)', 'X-CSRFToken', '{"success": true, "message": "コメントを削除しました"}', '200: 成功\n403: 権限不足'),
        ('API-010', '/api/photos/<photo_id>/delete/', 'POST', '店舗写真削除', '必須 (投稿者本人のみ)', 'X-CSRFToken', '{"success": true, "message": "写真を削除しました"}', '200: 成功\n403: 権限不足'),
        ('API-011', '/api/notifications/', 'GET', '通知一覧取得', '必須', 'Query: limit=20', '{"notifications": [{"id": 1, "sender": "くろろん", "type": "like", "is_read": false, "time_ago": "5分前"}]}', '200: 成功'),
        ('API-012', '/api/notifications/<id>/read/', 'POST', '通知既読化', '必須', 'X-CSRFToken', '{"success": true}', '200: 成功'),
        ('API-013', '/api/notifications/read-all/', 'POST', '全通知一括既読', '必須', 'X-CSRFToken', '{"success": true, "marked_count": 3}', '200: 成功'),
        ('API-014', '/api/shops/<shop_id>/favorite/', 'POST', '店舗お気に入りトグル', '必須', 'X-CSRFToken', '{"success": true, "is_favorite": true}', '200: 成功'),
        ('API-015', '/api/shops/create-from-place/', 'POST', 'Google Placeから店舗登録', '必須', 'X-CSRFToken, Content-Type: application/json\nBody: {place_id, name, address, lat, lng, rating}', '{"success": true, "shop": {"id": 45, "name": "谷川米穀店"}}', '200: 成功\n400: 既に登録済'),
        ('API-016', '/api/shops/search/', 'GET', '店舗オートコンプリート検索', '任意', 'Query: q=がもう', '{"shops": [{"id": 12, "name": "がもううどん", "address": "坂出市...", "lat": 34.3, "lng": 133.9}]}', '200: 成功'),
    ]

    for r_idx, row in enumerate(apis, start=3):
        is_even = (r_idx % 2 == 0)
        fill = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=1):
            c = ws6.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_code if c_idx in [2, 6, 7] else (font_bold if c_idx == 1 else font_normal)
            c.fill = fill
            c.border = border_thin
            if c_idx in [1, 3, 5]:
                c.alignment = align_center
            else:
                c.alignment = align_left
        ws6.row_dimensions[r_idx].height = 36

    adjust_column_widths(ws6, min_widths={'A': 12, 'B': 30, 'C': 10, 'D': 24, 'E': 16, 'F': 40, 'G': 40, 'H': 20})

    # ==========================================
    # Sheet 7: セキュリティ・権限設計
    # ==========================================
    ws7 = wb.create_sheet(title='セキュリティ・権限設計')
    apply_sheet_settings(ws7)

    ws7.cell(row=1, column=1, value='セキュリティ・認証・権限設計仕様書 (Security & Permissions)').font = font_title

    ws7.cell(row=3, column=1, value='1. ユーザー認証方式').font = font_section
    auth_specs = [
        ('ワンタップログイン', '登録済みユーザープロファイルからユーザーIDをPOSTし、パスワード認証をバイパスして即座にセッション確立。最近利用順ソート（F("user__last_login").desc(nulls_last=True)）。仲間内巡礼での端末共有や高速切り替えに最適化。'),
        ('標準パスワード認証', 'Django標準のPBKDF2暗号化ハッシュを用いたセキュアなパスワード認証。'),
        ('セッション管理', 'Django SessionMiddlewareを採用。サーバー側SQLite sessionテーブルにセッションデータを保持し、Cookieには署名済みsessionidのみを格納（HttpOnly属性付与）。'),
        ('HTTPSプロキシ透過', 'SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") により、Nginxリバースプロキシ配下でのHTTPS通信を正確に検知。'),
    ]
    for idx, (title, content) in enumerate(auth_specs, start=4):
        ws7.cell(row=idx, column=1, value=title).font = font_bold
        ws7.cell(row=idx, column=1).fill = fill_section_bg
        ws7.cell(row=idx, column=1).border = border_thin
        ws7.cell(row=idx, column=1).alignment = align_center
        ws7.cell(row=idx, column=2, value=content).font = font_normal
        ws7.cell(row=idx, column=2).border = border_thin
        ws7.cell(row=idx, column=2).alignment = align_left
        ws7.row_dimensions[idx].height = 26

    ws7.cell(row=9, column=1, value='2. アクセス制御・権限マトリクス').font = font_section
    perm_headers = ['リソース / 操作', '未ログイン', '一般ログインユーザー', '旅参加メンバー', '旅主催者 (Owner)', 'コンテンツ投稿者本人']
    for c_idx, h in enumerate(perm_headers, start=1):
        cell = ws7.cell(row=10, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws7.row_dimensions[10].height = 26

    perm_matrix = [
        ('うどん店舗一覧・詳細・レビュー閲覧', '○ (可能)', '○ (可能)', '○ (可能)', '○ (可能)', '○ (可能)'),
        ('旅一覧・旅マップ閲覧 (非公開設定時)', '× (不可)', '× (招待者のみ)', '○ (可能)', '○ (可能)', '-'),
        ('旅の新規作成', '× (要ログイン)', '○ (可能)', '○ (可能)', '○ (可能)', '-'),
        ('旅の基本情報編集・旅削除', '× (不可)', '× (不可)', '× (不可)', '○ (主催者のみ)', '-'),
        ('旅ストップ追加・並び替え・削除', '× (不可)', '× (不可)', '○ (可能)', '○ (可能)', '-'),
        ('同行メンバー招待・除外', '× (不可)', '× (不可)', '○ (招待可能)', '○ (全権限)', '-'),
        ('レビュー・店舗写真の投稿', '× (要ログイン)', '○ (可能)', '○ (可能)', '○ (可能)', '○ (可能)'),
        ('レビュー・写真・コメントの削除', '× (不可)', '× (不可)', '× (不可)', '× (不可)', '○ (投稿者のみ)'),
        ('レビューへの「いいね」・コメント', '× (要ログイン)', '○ (可能)', '○ (可能)', '○ (可能)', '○ (可能)'),
        ('プロフィール編集', '× (不可)', '○ (自アカウント)', '○ (自アカウント)', '○ (自アカウント)', '○ (自アカウント)'),
    ]
    for r_idx, row in enumerate(perm_matrix, start=11):
        is_even = (r_idx % 2 == 0)
        fill = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=1):
            c = ws7.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_bold if c_idx == 1 else font_normal
            c.fill = fill
            c.border = border_thin
            c.alignment = align_left if c_idx == 1 else align_center
        ws7.row_dimensions[r_idx].height = 24

    ws7.cell(row=23, column=1, value='3. セキュリティ脆弱性対策仕様').font = font_section
    sec_measures = [
        ('CSRF対策 (Cross-Site Request Forgery)', '全POSTリクエスト（フォーム送信およびAJAX fetchリクエスト）に `{% csrf_token %}` または `X-CSRFToken` ヘッダーを義務付け。CSRF_TRUSTED_ORIGINS に本番ドメインを明示定義。'),
        ('XSS対策 (Cross-Site Scripting)', 'Djangoテンプレートエンジンの自動HTMLエスケープを全面適用。レビューコメントやユーザー名に悪意あるスクリプトタグが含まれても無害化。'),
        ('SQLインジェクション対策', '全データ取得・更新において Django ORM (QuerySet API) を使用し、生SQL文字列連結を排除。プレースホルダによるプリペアドステートメント処理を徹底。'),
        ('クリックジャッキング対策', 'XFrameOptionsMiddleware を有効化し、`X-Frame-Options: DENY` または `SAMEORIGIN` を送出。他ドメインのiframe内埋め込みによる不正クリックを防止。'),
        ('画像ファイルバリデーション', '店舗写真・レビュー写真アップロード時に拡張子およびMIMEタイプを検証。悪意あるスクリプトファイル（.php, .sh等）の実行を防止。'),
    ]
    for idx, (title, content) in enumerate(sec_measures, start=24):
        ws7.cell(row=idx, column=1, value=title).font = font_bold
        ws7.cell(row=idx, column=1).fill = fill_section_bg
        ws7.cell(row=idx, column=1).border = border_thin
        ws7.cell(row=idx, column=1).alignment = align_center
        ws7.cell(row=idx, column=2, value=content).font = font_normal
        ws7.cell(row=idx, column=2).border = border_thin
        ws7.cell(row=idx, column=2).alignment = align_left
        ws7.row_dimensions[idx].height = 28

    ws7.column_dimensions['A'].width = 32
    ws7.column_dimensions['B'].width = 30
    ws7.column_dimensions['C'].width = 24
    ws7.column_dimensions['D'].width = 24
    ws7.column_dimensions['E'].width = 24
    ws7.column_dimensions['F'].width = 24

    # ==========================================
    # Sheet 8: 外部連携・運用バッチ設計
    # ==========================================
    ws8 = wb.create_sheet(title='外部連携・運用設計')
    apply_sheet_settings(ws8)

    ws8.cell(row=1, column=1, value='外部サービス連携・運用管理コマンド仕様書').font = font_title

    ws8.cell(row=3, column=1, value='1. Google Maps Platform 連携仕様').font = font_section
    gmaps_headers = ['API名称', '用途・連携箇所', '利用メソッド / エンドポイント', '詳細仕様・フォールバック']
    for c_idx, h in enumerate(gmaps_headers, start=1):
        cell = ws8.cell(row=4, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws8.row_dimensions[4].height = 26

    gmaps_data = [
        ('Maps JavaScript API', '旅ルートマップ画面、店舗位置表示', 'new google.maps.Map, google.maps.Marker, google.maps.Polyline', '店舗ピンの一括描画、順序番号付きカスタムバッジ、巡回順ポリライン描画。複数ピンがある場合は bounds.extend() で自動ズーム最適化。'),
        ('Places API (Autocomplete / Search)', 'ストップ追加時の店舗検索モーダル', 'google.maps.places.Autocomplete, PlacesService.getDetails', 'Googleマップ上の店舗をインクリメンタル検索。選択した店舗のplace_id、名称、住所、座標、Google評価を取得。'),
        ('移動時間算出アルゴリズム', '旅ストップ間の所要時間自動計算', 'calculate_driving_minutes(lat1, lng1, lat2, lng2)', '地球楕円体大円距離（Haversine式）に香川県道路迂回係数（1.35倍）と一般道平均時速（35km/h）を乗じ、現実的な車移動分数を高精度算出（最小5分保証）。'),
    ]
    for r_idx, row in enumerate(gmaps_data, start=5):
        is_even = (r_idx % 2 == 0)
        fill = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=1):
            c = ws8.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_bold if c_idx == 1 else font_normal
            c.fill = fill
            c.border = border_thin
            c.alignment = align_center if c_idx == 1 else align_left
        ws8.row_dimensions[r_idx].height = 36

    ws8.cell(row=10, column=1, value='2. 管理コマンド (Django Management Commands)').font = font_section
    cmd_headers = ['コマンド名', '実行コマンド例', '目的・実行契機', '処理内容・詳細']
    for c_idx, h in enumerate(cmd_headers, start=1):
        cell = ws8.cell(row=11, column=c_idx, value=h)
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = border_thin
    ws8.row_dimensions[11].height = 26

    cmd_data = [
        ('seed_kagawa_shops', 'python manage.py seed_kagawa_shops', '初期導入時・マスター更新時', '香川県全域の讃岐うどん名店データ（がもう、山越、谷川米穀店、須崎食料品店など）の一括登録。座標、営業時間、名物、初期写真パスの設定。既存店舗は更新。'),
        ('reset_all_data', 'python manage.py reset_all_data', '開発環境初期化・テストリセット時', '旅、レビュー、写真、通知などのトランザクションデータをクリーンアップ（店舗マスターとユーザーは保持または全リセット選択可能）。'),
    ]
    for r_idx, row in enumerate(cmd_data, start=12):
        is_even = (r_idx % 2 == 0)
        fill = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=1):
            c = ws8.cell(row=r_idx, column=c_idx, value=val)
            c.font = font_code if c_idx in [1, 2] else font_normal
            c.fill = fill
            c.border = border_thin
            c.alignment = align_center if c_idx == 1 else align_left
        ws8.row_dimensions[r_idx].height = 32

    ws8.cell(row=16, column=1, value='3. 店舗トップ写真の自動同期ロジック (sync_top_photo)').font = font_section
    ws8.cell(row=17, column=1, value='【同期仕様】\n店舗のトップ写真は以下の優先順位で最新のものが自動的に採用されます：\n1. ユーザーが投稿した最新の店舗写真 (ShopPhoto) または最新のレビュー添付写真 (Review)\n2. 店舗に直接登録された写真 (Shop.photo)\n3. 店舗の外部写真URL (Shop.photo_url)\n4. いずれも未登録の場合はデフォルトの No Image プレースホルダー\n新しい写真が投稿または削除された際、Shop.sync_top_photo() により常に最新の綺麗なうどん写真がトップに表示されます。').font = font_normal
    ws8.cell(row=17, column=1).alignment = align_left
    ws8.row_dimensions[17].height = 70

    ws8.column_dimensions['A'].width = 24
    ws8.column_dimensions['B'].width = 34
    ws8.column_dimensions['C'].width = 38
    ws8.column_dimensions['D'].width = 65

    # 保存
    wb.save(output_path)
    print(f"Successfully generated: {output_path}")

if __name__ == '__main__':
    target = '/home/administrator/udonweb/讃岐うどん巡礼_詳細設計書.xlsx'
    build_detailed_design_excel(target)
