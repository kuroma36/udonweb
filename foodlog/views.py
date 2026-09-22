import json
import logging
from datetime import date, datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q
from .models import UserProfile, DailyLog, MealEntry, MealItem, GeneralFood
from foodscan.models import FoodItem

logger = logging.getLogger(__name__)

# 定番料理・食品初期シードデータ
PRESET_FOODS = [
    # 主食
    {"name": "白米 (普通盛り 150g)", "category": "staple", "serving_size": "1杯(150g)", "calories": 234, "protein": 3.8, "fat": 0.5, "carbohydrates": 53.4, "salt": 0.0, "icon": "fa-bowl-rice"},
    {"name": "白米 (大盛り 200g)", "category": "staple", "serving_size": "1杯(200g)", "calories": 312, "protein": 5.0, "fat": 0.6, "carbohydrates": 71.2, "salt": 0.0, "icon": "fa-bowl-rice"},
    {"name": "食パン (6枚切り 1枚)", "category": "staple", "serving_size": "1枚(60g)", "calories": 158, "protein": 5.6, "fat": 2.6, "carbohydrates": 28.0, "salt": 0.8, "icon": "fa-bread-slice"},
    {"name": "玄米ご飯 (150g)", "category": "staple", "serving_size": "1杯(150g)", "calories": 228, "protein": 4.2, "fat": 1.5, "carbohydrates": 51.3, "salt": 0.0, "icon": "fa-bowl-rice"},
    {"name": "オートミール (30g)", "category": "staple", "serving_size": "1食(30g)", "calories": 114, "protein": 4.1, "fat": 1.7, "carbohydrates": 20.7, "salt": 0.0, "icon": "fa-bowl-rice"},
    {"name": "おにぎり (鮭)", "category": "staple", "serving_size": "1個(100g)", "calories": 175, "protein": 4.5, "fat": 1.2, "carbohydrates": 36.5, "salt": 1.1, "icon": "fa-cookie"},
    
    # うどん (讃岐うどん連携メニュー)
    {"name": "讃岐うどん (かけ・並 1玉)", "category": "udon", "serving_size": "1杯(250g)", "calories": 320, "protein": 8.5, "fat": 1.2, "carbohydrates": 68.0, "salt": 4.2, "icon": "fa-bowl-food"},
    {"name": "讃岐うどん (ぶっかけ・冷 1玉)", "category": "udon", "serving_size": "1杯(250g)", "calories": 335, "protein": 8.8, "fat": 1.3, "carbohydrates": 71.0, "salt": 3.5, "icon": "fa-bowl-food"},
    {"name": "讃岐うどん (釜玉うどん 1玉)", "category": "udon", "serving_size": "1杯(280g)", "calories": 410, "protein": 14.5, "fat": 7.5, "carbohydrates": 70.0, "salt": 3.2, "icon": "fa-bowl-food"},
    {"name": "ちくわ天 (讃岐トッピング)", "category": "udon", "serving_size": "1本", "calories": 145, "protein": 4.5, "fat": 7.2, "carbohydrates": 15.5, "salt": 0.9, "icon": "fa-shrimp"},
    {"name": "とり天 (讃岐トッピング)", "category": "udon", "serving_size": "1個", "calories": 160, "protein": 11.0, "fat": 9.5, "carbohydrates": 7.0, "salt": 0.6, "icon": "fa-drumstick-bite"},

    # 主菜
    {"name": "目玉焼き (1個)", "category": "main", "serving_size": "卵1個", "calories": 95, "protein": 6.2, "fat": 7.2, "carbohydrates": 0.2, "salt": 0.4, "icon": "fa-egg"},
    {"name": "ゆで卵 (1個)", "category": "main", "serving_size": "卵1個", "calories": 76, "protein": 6.3, "fat": 5.3, "carbohydrates": 0.2, "salt": 0.2, "icon": "fa-egg"},
    {"name": "納豆 (1パック 45g)", "category": "main", "serving_size": "1パック", "calories": 86, "protein": 7.4, "fat": 4.5, "carbohydrates": 5.4, "salt": 0.6, "icon": "fa-cubes-stacked"},
    {"name": "鶏むね肉のソテー (100g)", "category": "main", "serving_size": "100g", "calories": 145, "protein": 23.3, "fat": 4.8, "carbohydrates": 0.1, "salt": 0.5, "icon": "fa-drumstick-bite"},
    {"name": "豚の生姜焼き (1人前)", "category": "main", "serving_size": "1人前", "calories": 380, "protein": 18.5, "fat": 26.0, "carbohydrates": 8.5, "salt": 2.2, "icon": "fa-bacon"},
    {"name": "鮭の塩焼き (1切れ)", "category": "main", "serving_size": "1切れ(80g)", "calories": 155, "protein": 20.2, "fat": 8.0, "carbohydrates": 0.1, "salt": 1.2, "icon": "fa-fish"},
    {"name": "サラダチキン (1個 110g)", "category": "main", "serving_size": "1パック", "calories": 125, "protein": 24.5, "fat": 1.5, "carbohydrates": 1.0, "salt": 1.4, "icon": "fa-drumstick-bite"},
    {"name": "鶏の唐揚げ (3個)", "category": "main", "serving_size": "3個(90g)", "calories": 270, "protein": 12.6, "fat": 18.5, "carbohydrates": 9.2, "salt": 1.5, "icon": "fa-drumstick-bite"},
    {"name": "ハンバーグ (デミグラス 1人前)", "category": "main", "serving_size": "1個(150g)", "calories": 395, "protein": 17.5, "fat": 25.0, "carbohydrates": 18.0, "salt": 2.5, "icon": "fa-burger"},

    # 副菜
    {"name": "グリーンサラダ (ドレッシング別)", "category": "side", "serving_size": "1皿(80g)", "calories": 25, "protein": 1.2, "fat": 0.3, "carbohydrates": 4.5, "salt": 0.1, "icon": "fa-leaf"},
    {"name": "きゅうりとワカメの酢の物", "category": "side", "serving_size": "小鉢1皿", "calories": 35, "protein": 1.0, "fat": 0.2, "carbohydrates": 7.0, "salt": 0.8, "icon": "fa-leaf"},
    {"name": "冷奴 (半丁 150g)", "category": "side", "serving_size": "半丁", "calories": 84, "protein": 7.4, "fat": 4.5, "carbohydrates": 2.4, "salt": 0.4, "icon": "fa-cube"},
    {"name": "ほうれん草のおひたし", "category": "side", "serving_size": "小鉢1皿", "calories": 28, "protein": 2.2, "fat": 0.4, "carbohydrates": 3.5, "salt": 0.7, "icon": "fa-seedling"},

    # 汁物
    {"name": "豆腐とわかめの味噌汁", "category": "soup", "serving_size": "1杯(160g)", "calories": 55, "protein": 3.8, "fat": 1.8, "carbohydrates": 5.2, "salt": 1.5, "icon": "fa-mug-hot"},
    {"name": "豚汁 (具だくさん)", "category": "soup", "serving_size": "1杯(200g)", "calories": 165, "protein": 8.5, "fat": 9.2, "carbohydrates": 10.5, "salt": 2.1, "icon": "fa-mug-hot"},
    {"name": "コーンスープ", "category": "soup", "serving_size": "1杯(150g)", "calories": 115, "protein": 2.5, "fat": 4.2, "carbohydrates": 16.5, "salt": 1.2, "icon": "fa-mug-hot"},

    # 間食・ドリンク
    {"name": "プロテインシェイク (水割り)", "category": "snack", "serving_size": "1杯(粉25g)", "calories": 100, "protein": 20.0, "fat": 1.2, "carbohydrates": 2.5, "salt": 0.3, "icon": "fa-bottle-water"},
    {"name": "バナナ (1本)", "category": "snack", "serving_size": "1本(100g)", "calories": 86, "protein": 1.1, "fat": 0.2, "carbohydrates": 22.5, "salt": 0.0, "icon": "fa-apple-whole"},
    {"name": "無糖ヨーグルト (100g)", "category": "snack", "serving_size": "100g", "calories": 62, "protein": 3.6, "fat": 3.0, "carbohydrates": 4.9, "salt": 0.1, "icon": "fa-bowl-food"},
    {"name": "ブラックコーヒー (無糖)", "category": "snack", "serving_size": "1杯", "calories": 4, "protein": 0.3, "fat": 0.0, "carbohydrates": 0.7, "salt": 0.0, "icon": "fa-mug-saucer"},
]


def seed_general_foods_if_empty():
    """一般料理マスタが空の場合は初期投入"""
    if GeneralFood.objects.count() == 0:
        for f in PRESET_FOODS:
            GeneralFood.objects.create(
                name=f["name"],
                category=f["category"],
                serving_size=f["serving_size"],
                calories=f["calories"],
                protein=f["protein"],
                fat=f["fat"],
                carbohydrates=f["carbohydrates"],
                salt=f["salt"],
                icon=f["icon"],
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
    seed_general_foods_if_empty()
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

    # プリセット料理（カテゴリ別）
    staples = GeneralFood.objects.filter(category__in=['staple', 'udon'])[:10]
    mains = GeneralFood.objects.filter(category='main')[:10]
    sides = GeneralFood.objects.filter(category__in=['side', 'soup'])[:10]
    snacks = GeneralFood.objects.filter(category='snack')[:10]

    context = {
        'target_date': target_date.strftime('%Y-%m-%d'),
        'prev_date': (target_date - timedelta(days=1)).strftime('%Y-%m-%d'),
        'next_date': (target_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        'is_today': target_date == date.today(),
        'profile': profile.to_dict(),
        'summary': summary,
        'staples': [f.to_dict() for f in staples],
        'mains': [f.to_dict() for f in mains],
        'sides': [f.to_dict() for f in sides],
        'snacks': [f.to_dict() for f in snacks],
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

    # 4区分のEntryを確保
    for m_type, _ in MealEntry.MEAL_TYPES:
        MealEntry.objects.get_or_create(daily_log=daily_log, meal_type=m_type)

    summary = daily_log.get_summary(profile)
    return JsonResponse({'success': True, 'summary': summary})


@csrf_exempt
@require_POST
def api_add_meal(request):
    """
    食事アイテムの追加API
    バーコード経由(FoodItem)、一般料理(GeneralFood)、手動入力すべてに対応
    """
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

        # FoodItem (バーコード商品) との紐付け (あれば)
        barcode = data.get('barcode', '').strip()
        food_item = None
        if barcode:
            food_item = FoodItem.objects.filter(barcode=barcode).first()

        # 倍率計算
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
    gen_foods = GeneralFood.objects.filter(name__icontains=q)[:10]
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
    scanned_foods = FoodItem.objects.filter(Q(name__icontains=q) | Q(brand__icontains=q))[:10]
    for sf in scanned_foods:
        results.append({
            'type': 'scanned',
            'name': f"{sf.name} ({sf.brand})" if sf.brand else sf.name,
            'category': sf.category or "市販品",
            'serving_size': sf.serving_size or "1包装/100g",
            'calories': sf.calories or 0,
            'protein': sf.protein or 0,
            'fat': sf.fat or 0,
            'carbohydrates': sf.carbohydrates or 0,
            'salt': sf.salt or 0,
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
        
        # 目標カロリーが明示されていれば更新、なければ自動計算
        if data.get('target_calories'):
            profile.target_calories = float(data['target_calories'])
        else:
            _, _, auto_cal = profile.calc_bmr_and_tdee()
            profile.target_calories = auto_cal

        if data.get('target_p_ratio'): profile.target_p_ratio = float(data['target_p_ratio'])
        if data.get('target_f_ratio'): profile.target_f_ratio = float(data['target_f_ratio'])
        if data.get('target_c_ratio'): profile.target_c_ratio = float(data['target_c_ratio'])
        if data.get('target_salt'): profile.target_salt = float(data['target_salt'])

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
    """讃岐うどん巡礼アプリの実食レビューから最新品目を取得（独自連携機能）"""
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
