from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from .models import FoodCategory, FoodEntry, FoodArticle
from .crawler import fetch_all_food_news


def food_list(request):
    """食の新着ニュース・Web記事アグリゲーション一覧画面"""
    cat_filter = request.GET.get('cat', 'all')
    source_filter = request.GET.get('source', '')
    query = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)

    # Web収集記事
    articles_qs = FoodArticle.objects.all().order_by('-published_at')

    # カテゴリ絞り込み
    if cat_filter and cat_filter != 'all':
        articles_qs = articles_qs.filter(category=cat_filter)

    # 配信元絞り込み
    if source_filter:
        articles_qs = articles_qs.filter(source_name=source_filter)

    # キーワード検索
    if query:
        articles_qs = articles_qs.filter(
            Q(title__icontains=query) |
            Q(summary__icontains=query) |
            Q(source_name__icontains=query) |
            Q(keyword_query__icontains=query)
        )

    # ページネーション（1ページ24件）
    paginator = Paginator(articles_qs, 24)
    page_obj = paginator.get_page(page_number)

    # カテゴリ別集計カウント
    cat_counts = dict(FoodArticle.objects.values('category').annotate(c=Count('id')).values_list('category', 'c'))
    total_articles = FoodArticle.objects.count()

    # 配信元メディア一覧（上位25メディア）
    top_sources = (
        FoodArticle.objects.values('source_name')
        .annotate(c=Count('id'))
        .order_by('-c')[:25]
    )

    # 本日の新着件数（過去24時間以内）
    since_yesterday = timezone.now() - timedelta(hours=24)
    today_count = FoodArticle.objects.filter(published_at__gte=since_yesterday).count()

    # 特集ピックアップ（手動登録された注目イベント・新商品）
    featured_entries = FoodEntry.objects.filter(
        is_published=True,
        is_featured=True
    ).select_related('category')[:4]

    # 定義カテゴリ一覧
    category_tabs = [
        {'id': 'all', 'name': 'すべて', 'icon': '🌟', 'count': total_articles},
        {'id': 'new_product', 'name': '新商品・新発売', 'icon': '🍔', 'count': cat_counts.get('new_product', 0)},
        {'id': 'sweets', 'name': 'スイーツ・お菓子', 'icon': '🍰', 'count': cat_counts.get('sweets', 0)},
        {'id': 'convenience', 'name': 'コンビニ', 'icon': '🏪', 'count': cat_counts.get('convenience', 0)},
        {'id': 'fastfood', 'name': '外食・チェーン', 'icon': '🍟', 'count': cat_counts.get('fastfood', 0)},
        {'id': 'event', 'name': 'イベント・物産展', 'icon': '🎪', 'count': cat_counts.get('event', 0)},
        {'id': 'drinks', 'name': 'カフェ・お酒', 'icon': '☕', 'count': cat_counts.get('drinks', 0)},
        {'id': 'noodle', 'name': 'ラーメン・麺類', 'icon': '🍜', 'count': cat_counts.get('noodle', 0)},
    ]

    context = {
        'page_obj': page_obj,
        'articles': page_obj.object_list,
        'category_tabs': category_tabs,
        'current_cat': cat_filter,
        'current_source': source_filter,
        'top_sources': top_sources,
        'query': query,
        'total_articles': total_articles,
        'today_count': today_count,
        'featured_entries': featured_entries,
    }
    return render(request, 'food/index.html', context)


@require_POST
def fetch_news_api(request):
    """画面上のボタンからWebの最新ニュースを即時収集するAPI"""
    try:
        res = fetch_all_food_news()
        return JsonResponse({
            'status': 'ok',
            'message': f"Webから最新ニュースを収集しました（取得: {res['total_found']}件 / 新着: {res['created_count']}件）",
            'data': res
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def food_detail(request, pk):
    """手動登録イベント・詳細画面"""
    item = get_object_or_404(FoodEntry.objects.select_related('category'), pk=pk, is_published=True)
    related_items = FoodEntry.objects.filter(is_published=True, item_type=item.item_type).exclude(pk=item.pk)[:4]
    return render(request, 'food/detail.html', {'item': item, 'related_items': related_items})
