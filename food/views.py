from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta
from .models import FoodCategory, FoodEntry


def food_list(request):
    """食の新発売・イベント一覧画面"""
    today = date.today()
    item_type = request.GET.get('type', 'all')
    cat_slug = request.GET.get('cat', '')
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'active') # active, upcoming, all, ended
    sort_by = request.GET.get('sort', 'default')

    # 公開中の全件
    qs = FoodEntry.objects.filter(is_published=True).select_related('category')

    # タイプ絞り込み
    if item_type in ['product', 'event']:
        qs = qs.filter(item_type=item_type)

    # カテゴリ絞り込み
    current_category = None
    if cat_slug:
        current_category = FoodCategory.objects.filter(slug=cat_slug).first()
        if current_category:
            qs = qs.filter(category=current_category)

    # 検索キーワード
    if query:
        qs = qs.filter(
            Q(title__icontains=query) |
            Q(brand__icontains=query) |
            Q(catchphrase__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query) |
            Q(venue_name__icontains=query) |
            Q(area_info__icontains=query)
        )

    # ステータス絞り込み
    if status_filter == 'active':
        # 開催中または直近（過去14日以内の新発売含む、または終了日が今日以降）
        two_weeks_ago = today - timedelta(days=14)
        qs = qs.filter(
            Q(item_type='product', start_date__gte=two_weeks_ago) |
            Q(item_type='event', start_date__lte=today, end_date__gte=today) |
            Q(item_type='event', start_date__lte=today, end_date__isnull=True)
        )
    elif status_filter == 'upcoming':
        # 近日登場・開催前
        qs = qs.filter(start_date__gt=today)
    elif status_filter == 'ended':
        # 終了
        qs = qs.filter(end_date__lt=today)

    # ソート
    if sort_by == 'newest':
        qs = qs.order_by('-start_date', '-id')
    elif sort_by == 'oldest':
        qs = qs.order_by('start_date', 'id')
    elif sort_by == 'featured':
        qs = qs.order_by('-is_featured', 'start_date')
    else: # default: 注目の後に日付順
        qs = qs.order_by('-is_featured', 'start_date', '-created_at')

    # 注目のピックアップアイテム（上部カルーセル・ハイライト用）
    featured_items = FoodEntry.objects.filter(
        is_published=True,
        is_featured=True
    ).select_related('category')[:6]

    # 集計バッジ用カウント
    this_week_start = today - timedelta(days=today.weekday())
    this_week_end = this_week_start + timedelta(days=6)
    products_count = FoodEntry.objects.filter(is_published=True, item_type='product').count()
    events_count = FoodEntry.objects.filter(is_published=True, item_type='event').count()

    categories = FoodCategory.objects.all().order_by('order', 'id')

    context = {
        'items': qs,
        'featured_items': featured_items,
        'categories': categories,
        'current_type': item_type,
        'current_category': current_category,
        'cat_slug': cat_slug,
        'query': query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'total_count': qs.count(),
        'products_count': products_count,
        'events_count': events_count,
        'today': today,
    }
    return render(request, 'food/index.html', context)


def food_detail(request, pk):
    """食の新発売・イベント詳細画面"""
    item = get_object_or_404(FoodEntry.objects.select_related('category'), pk=pk, is_published=True)
    
    # 関連アイテム（同カテゴリ、または同じ種別の最新アイテム）
    related_items = FoodEntry.objects.filter(
        is_published=True,
        item_type=item.item_type
    ).exclude(pk=item.pk)
    
    if item.category:
        cat_matches = related_items.filter(category=item.category)[:4]
        if cat_matches.exists():
            related_items = cat_matches
        else:
            related_items = related_items.order_by('-start_date')[:4]
    else:
        related_items = related_items.order_by('-start_date')[:4]

    context = {
        'item': item,
        'related_items': related_items,
    }
    return render(request, 'food/detail.html', context)
