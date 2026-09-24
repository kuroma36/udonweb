import re
import time
import requests
import feedparser
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from bs4 import BeautifulSoup
from .models import FoodArticle

# クローリング対象のフィード定義
FEED_SOURCES = [
    {
        'query': '新発売 食品',
        'url': 'https://news.google.com/rss/search?q=%E6%96%B0%E7%99%BA%E5%A3%B2+%E9%A3%9F%E5%93%81+when:7d&hl=ja&gl=JP&ceid=JP:ja',
        'default_cat': 'new_product',
    },
    {
        'query': 'グルメ イベント フェス',
        'url': 'https://news.google.com/rss/search?q=%E3%82%B0%E3%83%AB%E3%83%A1+%E3%82%A4%E3%83%99%E3%83%B3%E3%83%88+when:7d&hl=ja&gl=JP&ceid=JP:ja',
        'default_cat': 'event',
    },
    {
        'query': 'コンビニ スイーツ 新作',
        'url': 'https://news.google.com/rss/search?q=%E3%82%B3%E3%83%B3%E3%83%93%E3%83%88%E3%82%B9%E3%82%A4%E3%83%BC%E3%83%84+%E6%96%B0%E5%95%86%E5%93%81+when:7d&hl=ja&gl=JP&ceid=JP:ja',
        'default_cat': 'sweets',
    },
    {
        'query': 'ファストフード 期間限定',
        'url': 'https://news.google.com/rss/search?q=%E3%83%95%E3%82%A1%E3%82%B9%E3%83%88%E3%83%95%E3%83%BC%E3%83%89+%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A+when:7d&hl=ja&gl=JP&ceid=JP:ja',
        'default_cat': 'fastfood',
    },
    {
        'query': '物産展 フードフェス',
        'url': 'https://news.google.com/rss/search?q=%E7%89%A9%E7%94%A3%E5%B1%95+%E3%83%95%E3%83%BC%E3%83%89%E3%83%95%E3%82%A7%E3%82%B9+when:14d&hl=ja&gl=JP&ceid=JP:ja',
        'default_cat': 'event',
    },
    {
        'query': 'ラーメン ご当地麺',
        'url': 'https://news.google.com/rss/search?q=%E3%83%A9%E3%83%BC%E3%83%A1%E3%83%B3+%E6%96%B0%E4%BD%9C+%E3%83%95%E3%82%A7%E3%82%B9+when:14d&hl=ja&gl=JP&ceid=JP:ja',
        'default_cat': 'noodle',
    },
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}


def classify_category(title, default_cat='new_product'):
    """記事タイトルからカテゴリをインテリジェントに自動分類"""
    t = title.lower()

    if any(k in t for k in ['物産展', 'フェス', '祭り', 'まつり', 'イベント', 'フェア', 'マルシェ', 'オクトーバーフェスト', '万博', '大北海道展', 'うまいもの']):
        return 'event'
    if any(k in t for k in ['スイーツ', 'アイス', 'チョコ', 'ケーキ', 'パフェ', 'モンブラン', 'プリン', 'ドーナツ', 'クッキー', '焼き芋', '栗', 'お菓子', 'マカロン', 'あんこ']):
        return 'sweets'
    if any(k in t for k in ['マクドナルド', 'ミスド', 'ミスタードーナツ', 'モスバーガー', 'すき家', '吉野家', '松屋', 'バーガー', 'ケンタッキー', 'kfc', '丸亀製麺', 'ガスト', 'サイゼリヤ', 'スシロー', 'くら寿司', 'はま寿司']):
        return 'fastfood'
    if any(k in t for k in ['セブン', 'ローソン', 'ファミマ', 'ファミリーマート', 'ミニストップ', 'コンビニ']):
        return 'convenience'
    if any(k in t for k in ['ラーメン', 'つけ麺', 'うどん', 'そば', 'パスタ', '焼きそば', 'カップヌードル', '麺類']):
        return 'noodle'
    if any(k in t for k in ['カフェ', 'ドリンク', 'フラペチーノ', 'ラテ', 'コーヒー', 'ビール', 'ワイン', '日本酒', '酎ハイ', 'お茶', 'スタバ', 'スターバックス', 'タリーズ']):
        return 'drinks'
    if any(k in t for k in ['新発売', '新商品', '新作', '発売', '登場', '限定', '先行']):
        return 'new_product'
    
    return default_cat or 'trend'


def clean_summary_html(html_text):
    """HTMLからテキストのみ抽出"""
    if not html_text:
        return ''
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text(separator=' ').strip()
    return re.sub(r'\s+', ' ', text)


def fetch_all_food_news():
    """Webから最新の食ニュース記事を一括収集してDBに保存"""
    total_found = 0
    created_count = 0
    updated_count = 0

    for feed_info in FEED_SOURCES:
        q_name = feed_info['query']
        url = feed_info['url']
        default_cat = feed_info['default_cat']

        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue

            feed = feedparser.parse(resp.content)
            entries = feed.entries

            for e in entries:
                raw_title = e.get('title', '').strip()
                link = e.get('link', '').strip()
                if not raw_title or not link:
                    continue

                total_found += 1

                # 配信元メディア名の抽出（「タイトル - 媒体名」形式）
                source_name = ''
                if hasattr(e, 'source') and isinstance(e.source, dict) and e.source.get('title'):
                    source_name = e.source.title.strip()
                
                clean_title = raw_title
                if ' - ' in raw_title:
                    parts = raw_title.rsplit(' - ', 1)
                    clean_title = parts[0].strip()
                    if not source_name:
                        source_name = parts[1].strip()

                if not source_name:
                    source_name = 'Webニュース'

                # 公開日時のパース
                published_at = timezone.now()
                if hasattr(e, 'published_parsed') and e.published_parsed:
                    published_at = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=dt_timezone.utc)

                # カテゴリ判定
                cat = classify_category(clean_title, default_cat=default_cat)

                # 要約の取得
                summary = clean_summary_html(e.get('summary', ''))

                # DB保存（URLでユニーク重複チェック）
                article, is_created = FoodArticle.objects.update_or_create(
                    url=link,
                    defaults={
                        'title': clean_title,
                        'source_name': source_name,
                        'category': cat,
                        'summary': summary,
                        'published_at': published_at,
                        'keyword_query': q_name,
                    }
                )

                if is_created:
                    created_count += 1
                else:
                    updated_count += 1

        except Exception as err:
            print(f"Error fetching feed for '{q_name}': {err}")

    return {
        'total_found': total_found,
        'created_count': created_count,
        'updated_count': updated_count,
    }
