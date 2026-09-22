import json
import logging
from datetime import date, datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q
from .models import UserProfile, DailyLog, MealEntry, MealItem, GeneralFood
from .estimator import estimate_nutrition
from .fixtures_foods import EXPANDED_FOOD_MASTER
from foodscan.models import FoodItem

logger = logging.getLogger(__name__)


def seed_expanded_foods():
    """拡張食品マスタの投入 (未登録品を追加入力)"""
    for f in EXPANDED_FOOD_MASTER:
        if not GeneralFood.objects.filter(name=f["name"]).exists():
            GeneralFood.objects.create(
                name=f["name"],
                category=f["category"],
                serving_size=f["serving_size"],
                calories=f["calories"],
                protein=f["protein"],
                fat=f["fat"],
                carbohydrates=f["carbohydrates"],
                salt=f["salt"],
                icon=f.get("icon", "fa-utensils"),
            )


def get_or_create_profile(user=None):
    """プロファイルの取得または生成"""
    if user and user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=user)
    else:
        profile = UserProfile.objects.first()
        if not profile:
            profile = UserProfile.objects.create(nickname="ダイエッター")
    return profile


def index(request):
    """メイン画面レンダリング"""
    seed_expanded_foods()
    profile = get_or_create_profile(request.user)

    target_date_str = request.GET.get('date')
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    daily_log, _ = DailyLog.objects.get_or_create(date=target_date)

    # 4区分のEntryを確保
    for m_type, _ in MealEntry.MEAL_TYPES:
        MealEntry.objects.get_or_create(daily_log=daily_log, meal_type=m_type)

    summary = daily_log.get_summary(profile)

    # カテゴリ別プリセット食品
    convenience_foods = GeneralFood.objects.filter(category='convenience')[:12]
    fastfood_foods = GeneralFood.objects.filter(category='fastfood')[:12]
    staples = GeneralFood.objects.filter(category='staple')[:12]
    mains = GeneralFood.objects.filter(category='main')[:12]
    sides = GeneralFood.objects.filter(category='side')[:12]
    udons = GeneralFood.objects.filter(category='udon')[:12]

    context = {
        'target_date': target_date.strftime('%Y-%m-%d'),
        'prev_date': (target_date - timedelta(days=1)).strftime('%Y-%m-%d'),
        'next_date': (target_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        'is_today': target_date == date.today(),
        'profile': profile.to_dict(),
        'summary': summary,
        'convenience_foods': [f.to_dict() for f in convenience_foods],
        'fastfood_foods': [f.to_dict() for f in fastfood_foods],
        'staples': [f.to_dict() for f in staples],
        'mains': [f.to_dict() for f in mains],
        'sides': [f.to_dict() for f in sides],
        'udons': [f.to_dict() for f in udons],
    }
    return render(request, 'foodlog/index.html', context)


@require_GET
def api_day(request):
    """指定日のサマリー＆明細取得API"""
    date_str = request.GET.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        t_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': '不正な日付形式です'}, status=400)

    profile = get_or_create_profile(request.user)
    daily_log, _ = DailyLog.objects.get_or_create(date=t_date)

    for m_type, _ in MealEntry.MEAL_TYPES:
        MealEntry.objects.get_or_create(daily_log=daily_log, meal_type=m_type)

    summary = daily_log.get_summary(profile)
    return JsonResponse({'success': True, 'summary': summary})


@require_GET
def api_estimate(request):
    """
    料理名・商品名からルールベースで標準栄養素を即座に推計するAPI
    外部AI不要・完全ローカル
    """
    name = request.GET.get('name', '').strip()
    result = estimate_nutrition(name)
    return JsonResponse({'success': True, 'estimate': result})


@csrf_exempt
@require_POST
def api_add_meal(request):
    """食事アイテムの追加API"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
        meal_type = data.get('meal_type', 'lunch')
        t_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        daily_log, _ = DailyLog.objects.get_or_create(date=t_date)
        entry, _ = MealEntry.objects.get_or_create(daily_log=daily_log, meal_type=meal_type)

        serving_amount = float(data.get('serving_amount', 1.0))
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'error': '品目名は必須です'}, status=400)

        cal_base = float(data.get('calories', 0.0))
        p_base = float(data.get('protein', 0.0))
        f_base = float(data.get('fat', 0.0))
        c_base = float(data.get('carbohydrates', 0.0))
        salt_base = float(data.get('salt', 0.0))
        image_url = data.get('image_url', '').strip()

        # もしカロリーが0で送られてきた場合は、ルールベース推計を自動補完！
        if cal_base == 0.0:
            est = estimate_nutrition(name)
            if est.get('calories', 0) > 0:
                cal_base = est['calories']
                p_base = est['protein']
                f_base = est['fat']
                c_base = est['carbohydrates']
                salt_base = est['salt']

        barcode = data.get('barcode', '').strip()
        food_item = None
        if barcode:
            food_item = FoodItem.objects.filter(barcode=barcode).first()

        item = MealItem.objects.create(
            meal_entry=entry,
            food_item=food_item,
            name=name,
            serving_amount=serving_amount,
            serving_unit=data.get('serving_unit', '人前'),
            calories=cal_base * serving_amount,
            protein=p_base * serving_amount,
            fat=f_base * serving_amount,
            carbohydrates=c_base * serving_amount,
            salt=salt_base * serving_amount,
            image_url=image_url,
        )

        profile = get_or_create_profile(request.user)
        updated_summary = daily_log.get_summary(profile)

        return JsonResponse({
            'success': True,
            'message': f'「{name}」を{entry.get_meal_type_display()}に登録しました！',
            'item': item.to_dict(),
            'summary': updated_summary,
        })
    except Exception as e:
        logger.error(f"Failed to add meal: {e}")
        return JsonResponse({'error': f'食事の追加に失敗しました: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def api_delete_meal(request):
    """食事アイテムの削除API"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        item_id = data.get('item_id')
        item = MealItem.objects.filter(id=item_id).first()
        if not item:
            return JsonResponse({'error': '対象の品目が見つかりません'}, status=404)

        daily_log = item.meal_entry.daily_log
        item.delete()

        profile = get_or_create_profile(request.user)
        updated_summary = daily_log.get_summary(profile)

        return JsonResponse({
            'success': True,
            'message': '品目を削除しました',
            'summary': updated_summary,
        })
    except Exception as e:
        logger.error(f"Failed to delete meal: {e}")
        return JsonResponse({'error': f'削除に失敗しました: {str(e)}'}, status=500)


@require_GET
def api_search_foods(request):
    """料理＆食品マスタ検索API (インクリメンタル検索)"""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})

    results = []

    # 1. 一般料理マスタから検索
    gen_foods = GeneralFood.objects.filter(name__icontains=q)[:15]
    for gf in gen_foods:
        results.append({
            'type': 'general',
            'name': gf.name,
            'category': gf.get_category_display(),
            'serving_size': gf.serving_size,
            'calories': gf.calories,
            'protein': gf.protein,
            'fat': gf.fat,
            'carbohydrates': gf.carbohydrates,
            'salt': gf.salt,
            'image_url': '',
            'barcode': '',
            'icon': gf.icon,
        })

    # 2. バーコード登録済み食品 (FoodItem) から検索
    scanned_foods = FoodItem.objects.filter(Q(name__icontains=q) | Q(brand__icontains=q))[:15]
    for sf in scanned_foods:
        # カロリーがnullの場合はルール推計で補完
        cal = sf.calories
        p = sf.protein or 0
        f = sf.fat or 0
        c = sf.carbohydrates or 0
        salt = sf.salt or 0
        if cal is None:
            est = estimate_nutrition(sf.name)
            cal = est['calories']
            p = est['protein']
            f = est['fat']
            c = est['carbohydrates']
            salt = est['salt']

        results.append({
            'type': 'scanned',
            'name': f"{sf.name} ({sf.brand})" if sf.brand else sf.name,
            'category': sf.category or "市販品",
            'serving_size': sf.serving_size or "1包装/100g",
            'calories': cal,
            'protein': p,
            'fat': f,
            'carbohydrates': c,
            'salt': salt,
            'image_url': sf.image_url,
            'barcode': sf.barcode,
            'icon': 'fa-barcode',
        })

    return JsonResponse({'results': results})


@csrf_exempt
@require_POST
def api_update_profile(request):
    """ユーザー目標・身体データの更新API"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        profile = get_or_create_profile(request.user)

        if 'gender' in data: profile.gender = data['gender']
        if 'birth_year' in data: profile.birth_year = int(data['birth_year'])
        if 'height' in data: profile.height = float(data['height'])
        if 'current_weight' in data: profile.current_weight = float(data['current_weight'])
        if 'target_weight' in data: profile.target_weight = float(data['target_weight'])
        if 'activity_level' in data: profile.activity_level = data['activity_level']
        if 'goal_type' in data: profile.goal_type = data['goal_type']
        
        if data.get('target_calories'):
            profile.target_calories = float(data['target_calories'])
        else:
            _, _, auto_cal = profile.calc_bmr_and_tdee()
            profile.target_calories = auto_cal

        profile.save()

        return JsonResponse({
            'success': True,
            'message': '目標設定を更新しました！',
            'profile': profile.to_dict(),
        })
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        return JsonResponse({'error': f'目標の更新に失敗しました: {str(e)}'}, status=500)


@require_GET
def api_udon_recent(request):
    """讃岐うどん巡礼アプリの実食レビューから最新品目を取得"""
    try:
        from udon.models import Review
        reviews = Review.objects.select_related('shop').order_by('-created_at')[:6]
        items = []
        for r in reviews:
            menu_name = r.shop.featured_menu or "名物讃岐うどん"
            items.append({
                'shop_name': r.shop.name,
                'menu_name': menu_name,
                'calories': 420.0,
                'protein': 10.5,
                'fat': 3.5,
                'carbohydrates': 78.0,
                'salt': 4.2,
                'visited_at': r.created_at.strftime('%Y-%m-%d'),
            })
        return JsonResponse({'items': items})
    except Exception as e:
        logger.warning(f"Udon app integration note: {e}")
        return JsonResponse({'items': []})
