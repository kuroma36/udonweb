import json
import logging
import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from .models import FoodItem, ScanLog

logger = logging.getLogger(__name__)

# よくあるアレルゲンの日本語マップ
ALLERGEN_MAP = {
    'en:gluten': '小麦/グルテン',
    'en:wheat': '小麦',
    'en:milk': '乳',
    'en:eggs': '卵',
    'en:soybeans': '大豆',
    'en:peanuts': '落花生(ピーナッツ)',
    'en:buckwheat': 'そば',
    'en:crustaceans': 'えび・かに(甲殻類)',
    'en:fish': '魚介類',
    'en:nuts': '木の実/アーモンド',
    'en:sesame-seeds': 'ごま',
    'en:pork': '豚肉',
    'en:chicken': '鶏肉',
    'en:beef': '牛肉',
    'en:gelatin': 'ゼラチン',
}

# 初回・体験用のサンプル商品定義（有名定番商品）
PRESET_SAMPLES = [
    {
        "barcode": "4902705126558",
        "name": "明治 おいしい牛乳 900ml",
        "brand": "Meiji (明治)",
        "calories": 68.5,
        "protein": 3.4,
        "fat": 3.9,
        "carbohydrates": 4.95,
        "salt": 0.11,
        "allergens": "乳",
        "image_url": "https://images.openfoodfacts.org/images/products/490/270/512/6558/front_en.7.400.jpg",
        "category": "乳飲料・牛乳",
        "serving_size": "100mlあたり",
        "ingredients": "生乳100%（国産）"
    },
    {
        "barcode": "4901330578916",
        "name": "じゃがりこ チーズ",
        "brand": "Calbee (カルビー)",
        "calories": 254.0,
        "protein": 3.4,
        "fat": 12.2,
        "carbohydrates": 32.7,
        "salt": 0.6,
        "allergens": "乳, 大豆",
        "image_url": "https://images.openfoodfacts.org/images/products/490/133/057/8916/front_en.4.400.jpg",
        "category": "スナック菓子",
        "serving_size": "1カップ(52g)あたり",
        "ingredients": "じゃがいも（国産）、植物油、チェダーチーズ、チーズパウダー、ホエイパウダー、食塩、ホワイトペッパー／乳化剤、調味料（アミノ酸等）、香料、カロチノイド色素"
    },
    {
        "barcode": "4902102140553",
        "name": "コカ・コーラ ゼロ",
        "brand": "Coca-Cola (コカ・コーラ)",
        "calories": 0.0,
        "protein": 0.0,
        "fat": 0.0,
        "carbohydrates": 0.0,
        "salt": 0.01,
        "allergens": "",
        "image_url": "https://images.openfoodfacts.org/images/products/490/210/214/0553/front_en.5.400.jpg",
        "category": "炭酸飲料",
        "serving_size": "100mlあたり",
        "ingredients": "炭酸、カラメル色素、酸味料、甘味料（スクラロース、アセスルファムK）、香料、カフェイン"
    },
    {
        "barcode": "4901360353606",
        "name": "アルフォート ミニチョコレート",
        "brand": "Bourbon (ブルボン)",
        "calories": 314.0,
        "protein": 4.1,
        "fat": 17.6,
        "carbohydrates": 35.1,
        "salt": 0.4,
        "allergens": "小麦, 乳, 大豆",
        "image_url": "https://images.openfoodfacts.org/images/products/490/136/035/3606/front_en.3.400.jpg",
        "category": "チョコレート菓子",
        "serving_size": "1箱(59g)あたり",
        "ingredients": "砂糖、小麦粉、全粉乳、カカオマス、ショートニング、植物油脂、ココアバター、小麦全粒粉、小麦ふすま、食塩、脱脂小麦胚芽／膨脹剤、乳化剤（大豆由来）、香料"
    },
    {
        "barcode": "4901085179611",
        "name": "健康ミネラルむぎ茶 650ml",
        "brand": "伊藤園 (Itoen)",
        "calories": 0.0,
        "protein": 0.0,
        "fat": 0.0,
        "carbohydrates": 0.0,
        "salt": 0.03,
        "allergens": "",
        "image_url": "https://images.openfoodfacts.org/images/products/490/108/517/9611/front_en.13.400.jpg",
        "category": "茶系飲料",
        "serving_size": "100mlあたり",
        "ingredients": "大麦（カナダ、オーストラリア、その他）、麦芽、海洋深層水／ビタミンC"
    }
]


def get_client_ip(request):
    """Nginxリバースプロキシ環境での実クライアントIP取得"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def seed_preset_samples_if_empty():
    """初回DBが空の場合にサンプル商品を登録しておく"""
    for item_data in PRESET_SAMPLES:
        if not FoodItem.objects.filter(barcode=item_data["barcode"]).exists():
            FoodItem.objects.create(
                barcode=item_data["barcode"],
                name=item_data["name"],
                brand=item_data["brand"],
                category=item_data.get("category", ""),
                image_url=item_data.get("image_url", ""),
                serving_size=item_data.get("serving_size", "100g"),
                calories=item_data.get("calories"),
                protein=item_data.get("protein"),
                fat=item_data.get("fat"),
                carbohydrates=item_data.get("carbohydrates"),
                salt=item_data.get("salt"),
                ingredients=item_data.get("ingredients", ""),
                allergens=item_data.get("allergens", ""),
                source="manual",
                scan_count=5
            )


def index(request):
    """メイン画面表示"""
    # 必要に応じてサンプル初期データを投入
    seed_preset_samples_if_empty()
    
    # 最近スキャンされた商品（最新8件）
    recent_items = FoodItem.objects.order_by('-updated_at')[:8]
    
    context = {
        'recent_items': [item.to_dict() for item in recent_items],
        'preset_samples': PRESET_SAMPLES,
    }
    return render(request, 'foodscan/index.html', context)


@require_GET
def api_lookup(request):
    """
    バーコード番号から食品情報を検索するAPI
    1. 自前DB (FoodItem) を検索
    2. 見つからなければ Open Food Facts API に問い合わせ
    3. ヒットすれば自前DBにキャッシュ保存して返却
    """
    barcode = request.GET.get('barcode', '').strip()
    # 全角数字を半角に変換
    barcode = barcode.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    
    if not barcode:
        return JsonResponse({'error': 'バーコードが指定されていません'}, status=400)

    # 1. ローカルDBを検索
    item = FoodItem.objects.filter(barcode=barcode).first()
    if item:
        item.scan_count += 1
        item.save(update_fields=['scan_count', 'updated_at'])
        
        # スキャン履歴を記録
        ScanLog.objects.create(
            food_item=item,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:250]
        )
        return JsonResponse({
            'found': True,
            'source': 'local_db',
            'product': item.to_dict()
        })

    # 2. Open Food Facts API へリクエスト
    try:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        headers = {
            'User-Agent': 'FoodScanWeb/1.0 (krmts.com - Food Barcode Scanner Demo; admin@krmts.com)',
            'Accept-Encoding': 'gzip, deflate',
        }
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 1 and 'product' in data:
                p = data['product']
                
                name = p.get('product_name_ja') or p.get('product_name') or f"商品 ({barcode})"
                brand = p.get('brands') or ""
                category = p.get('categories') or ""
                image_url = p.get('image_front_url') or p.get('image_url') or ""
                serving_size = p.get('serving_size') or "100gあたり"
                
                nutriments = p.get('nutriments', {})
                # エネルギー (kcal)
                kcal = nutriments.get('energy-kcal_100g') or nutriments.get('energy-kcal_serving') or nutriments.get('energy-kcal')
                protein = nutriments.get('proteins_100g') or nutriments.get('proteins_serving') or nutriments.get('proteins')
                fat = nutriments.get('fat_100g') or nutriments.get('fat_serving') or nutriments.get('fat')
                carbs = nutriments.get('carbohydrates_100g') or nutriments.get('carbohydrates_serving') or nutriments.get('carbohydrates')
                sugar = nutriments.get('sugars_100g') or nutriments.get('sugars_serving') or nutriments.get('sugars')
                fiber = nutriments.get('fiber_100g') or nutriments.get('fiber_serving') or nutriments.get('fiber')
                salt = nutriments.get('salt_100g') or nutriments.get('salt_serving') or nutriments.get('salt')

                # アレルゲン整形
                allergen_tags = p.get('allergens_tags', [])
                allergens_list = []
                for tag in allergen_tags:
                    allergens_list.append(ALLERGEN_MAP.get(tag, tag.replace('en:', '')))
                allergens_str = ", ".join(allergens_list)

                # 原材料
                ingredients = p.get('ingredients_text_ja') or p.get('ingredients_text') or ""

                # DBに新規作成・キャッシュ保存
                new_item = FoodItem.objects.create(
                    barcode=barcode,
                    name=name,
                    brand=brand,
                    category=category[:250],
                    image_url=image_url,
                    serving_size=serving_size,
                    calories=float(kcal) if kcal is not None else None,
                    protein=float(protein) if protein is not None else None,
                    fat=float(fat) if fat is not None else None,
                    carbohydrates=float(carbs) if carbs is not None else None,
                    sugar=float(sugar) if sugar is not None else None,
                    fiber=float(fiber) if fiber is not None else None,
                    salt=float(salt) if salt is not None else None,
                    ingredients=ingredients,
                    allergens=allergens_str,
                    source='openfoodfacts',
                    scan_count=1
                )

                # 履歴記録
                ScanLog.objects.create(
                    food_item=new_item,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:250]
                )

                return JsonResponse({
                    'found': True,
                    'source': 'openfoodfacts',
                    'product': new_item.to_dict()
                })
    except Exception as e:
        logger.warning(f"Open Food Facts lookup failed: {e}")

    # 見つからなかった場合
    return JsonResponse({
        'found': False,
        'barcode': barcode,
        'message': f'バーコード「{barcode}」の食品データは見つかりませんでした。手動登録が可能です。'
    })


@csrf_exempt
@require_POST
def api_register(request):
    """ユーザーによる未登録食品の手動登録API"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        barcode = data.get('barcode', '').strip()
        name = data.get('name', '').strip()
        
        if not barcode or not name:
            return JsonResponse({'error': 'バーコードと商品名は必須です'}, status=400)

        # 既存チェック
        item, created = FoodItem.objects.get_or_create(
            barcode=barcode,
            defaults={
                'name': name,
                'brand': data.get('brand', '').strip(),
                'category': data.get('category', '').strip(),
                'image_url': data.get('image_url', '').strip(),
                'serving_size': data.get('serving_size', '100g').strip(),
                'calories': float(data['calories']) if data.get('calories') else None,
                'protein': float(data['protein']) if data.get('protein') else None,
                'fat': float(data['fat']) if data.get('fat') else None,
                'carbohydrates': float(data['carbohydrates']) if data.get('carbohydrates') else None,
                'salt': float(data['salt']) if data.get('salt') else None,
                'ingredients': data.get('ingredients', '').strip(),
                'allergens': data.get('allergens', '').strip(),
                'source': 'user',
            }
        )

        if not created:
            # 既存なら情報を更新
            item.name = name
            item.brand = data.get('brand', item.brand)
            if data.get('calories'): item.calories = float(data['calories'])
            if data.get('protein'): item.protein = float(data['protein'])
            if data.get('fat'): item.fat = float(data['fat'])
            if data.get('carbohydrates'): item.carbohydrates = float(data['carbohydrates'])
            if data.get('salt'): item.salt = float(data['salt'])
            if data.get('ingredients'): item.ingredients = data['ingredients']
            if data.get('allergens'): item.allergens = data['allergens']
            item.source = 'user'
            item.save()

        # 履歴記録
        ScanLog.objects.create(
            food_item=item,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:250]
        )

        return JsonResponse({
            'success': True,
            'message': '食品データを登録しました！',
            'product': item.to_dict()
        })
    except Exception as e:
        logger.error(f"Failed to register item: {e}")
        return JsonResponse({'error': f'登録処理に失敗しました: {str(e)}'}, status=500)


@require_GET
def api_history(request):
    """最新スキャン履歴一覧"""
    recent = FoodItem.objects.order_by('-updated_at')[:10]
    return JsonResponse({
        'items': [item.to_dict() for item in recent]
    })
