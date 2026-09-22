import re

# 基本料理ジャンル辞書 (標準1人前ベース)
BASE_FOOD_RULES = [
    # 麺類・ラーメン
    {
        'keywords': ['家系ラーメン', '二郎系', '二郎ラーメン', '背脂ラーメン'],
        'calories': 950.0, 'protein': 28.0, 'fat': 45.0, 'carbohydrates': 105.0, 'salt': 6.8,
        'category': 'ラーメン', 'reason': '濃厚・背脂系ラーメン基準'
    },
    {
        'keywords': ['つけ麺', 'つけめん'],
        'calories': 720.0, 'protein': 24.0, 'fat': 18.0, 'carbohydrates': 115.0, 'salt': 5.8,
        'category': 'ラーメン', 'reason': 'つけ麺(麺多め)基準'
    },
    {
        'keywords': ['豚骨ラーメン', 'とんこつラーメン'],
        'calories': 650.0, 'protein': 22.0, 'fat': 26.0, 'carbohydrates': 78.0, 'salt': 5.8,
        'category': 'ラーメン', 'reason': '豚骨ラーメン標準'
    },
    {
        'keywords': ['味噌ラーメン', 'みそラーメン'],
        'calories': 620.0, 'protein': 21.0, 'fat': 20.0, 'carbohydrates': 82.0, 'salt': 6.0,
        'category': 'ラーメン', 'reason': '味噌ラーメン標準'
    },
    {
        'keywords': ['醤油ラーメン', 'しょうゆラーメン', '中華そば', 'ラーメン', 'らーめん'],
        'calories': 550.0, 'protein': 19.0, 'fat': 14.0, 'carbohydrates': 78.0, 'salt': 5.2,
        'category': 'ラーメン', 'reason': '醤油ラーメン/中華そば標準'
    },
    {
        'keywords': ['焼きそば', 'やきそば'],
        'calories': 520.0, 'protein': 14.0, 'fat': 18.0, 'carbohydrates': 72.0, 'salt': 3.6,
        'category': '麺類', 'reason': 'ソース焼きそば標準'
    },
    {
        'keywords': ['カルボナーラ'],
        'calories': 740.0, 'protein': 22.0, 'fat': 32.0, 'carbohydrates': 85.0, 'salt': 3.2,
        'category': 'パスタ', 'reason': 'カルボナーラパスタ標準'
    },
    {
        'keywords': ['ミートソース', 'ボロネーゼ'],
        'calories': 620.0, 'protein': 20.0, 'fat': 18.0, 'carbohydrates': 88.0, 'salt': 3.0,
        'category': 'パスタ', 'reason': 'ミートソースパスタ標準'
    },
    {
        'keywords': ['ナポリタン'],
        'calories': 590.0, 'protein': 16.0, 'fat': 16.0, 'carbohydrates': 92.0, 'salt': 3.5,
        'category': 'パスタ', 'reason': 'ナポリタン標準'
    },
    {
        'keywords': ['ペペロンチーノ'],
        'calories': 490.0, 'protein': 12.0, 'fat': 15.0, 'carbohydrates': 74.0, 'salt': 2.4,
        'category': 'パスタ', 'reason': 'ペペロンチーノ標準'
    },
    {
        'keywords': ['パスタ', 'スパゲティ', 'スパゲッティ'],
        'calories': 580.0, 'protein': 18.0, 'fat': 16.0, 'carbohydrates': 85.0, 'salt': 2.8,
        'category': 'パスタ', 'reason': 'パスタ標準'
    },

    # 定食類 (ご飯・味噌汁・主菜・小鉢)
    {
        'keywords': ['チキン南蛮定食', 'チキン南蛮'],
        'calories': 920.0, 'protein': 34.0, 'fat': 44.0, 'carbohydrates': 98.0, 'salt': 4.2,
        'category': '定食', 'reason': 'チキン南蛮(タルタル付)定食基準'
    },
    {
        'keywords': ['とんかつ定食', 'トンカツ定食', 'ロースかつ定食', 'ロースカツ定食'],
        'calories': 890.0, 'protein': 30.0, 'fat': 42.0, 'carbohydrates': 95.0, 'salt': 3.8,
        'category': '定食', 'reason': 'ロースとんかつ定食基準'
    },
    {
        'keywords': ['唐揚げ定食', 'から揚げ定食', 'からあげ定食'],
        'calories': 830.0, 'protein': 32.0, 'fat': 34.0, 'carbohydrates': 96.0, 'salt': 3.6,
        'category': '定食', 'reason': '鶏唐揚げ定食基準'
    },
    {
        'keywords': ['生姜焼き定食', 'しょうが焼き定食'],
        'calories': 760.0, 'protein': 26.0, 'fat': 28.0, 'carbohydrates': 95.0, 'salt': 3.8,
        'category': '定食', 'reason': '豚生姜焼き定食基準'
    },
    {
        'keywords': ['ハンバーグ定食'],
        'calories': 790.0, 'protein': 25.0, 'fat': 32.0, 'carbohydrates': 96.0, 'salt': 3.5,
        'category': '定食', 'reason': 'ハンバーグ定食基準'
    },
    {
        'keywords': ['焼肉定食', 'カルビ定食'],
        'calories': 840.0, 'protein': 28.0, 'fat': 36.0, 'carbohydrates': 96.0, 'salt': 3.8,
        'category': '定食', 'reason': '牛焼肉定食基準'
    },
    {
        'keywords': ['焼き魚定食', 'サバの塩焼き定食', '鮭定食', 'ほっけ定食'],
        'calories': 650.0, 'protein': 30.0, 'fat': 18.0, 'carbohydrates': 88.0, 'salt': 3.2,
        'category': '定食', 'reason': '焼き魚和定食基準'
    },
    {
        'keywords': ['刺身定食'],
        'calories': 560.0, 'protein': 28.0, 'fat': 6.0, 'carbohydrates': 92.0, 'salt': 2.8,
        'category': '定食', 'reason': '刺身定食基準'
    },
    {
        'keywords': ['定食', '御膳'],
        'calories': 750.0, 'protein': 26.0, 'fat': 24.0, 'carbohydrates': 95.0, 'salt': 3.6,
        'category': '定食', 'reason': '和洋定食標準'
    },

    # 丼もの・ご飯もの
    {
        'keywords': ['カツカレー', 'かつカレー'],
        'calories': 980.0, 'protein': 26.0, 'fat': 38.0, 'carbohydrates': 128.0, 'salt': 4.2,
        'category': 'カレー', 'reason': 'カツカレー基準'
    },
    {
        'keywords': ['カレーライス', 'カレー', 'ポークカレー', 'チキンカレー'],
        'calories': 720.0, 'protein': 16.0, 'fat': 20.0, 'carbohydrates': 114.0, 'salt': 3.4,
        'category': 'カレー', 'reason': 'カレーライス標準'
    },
    {
        'keywords': ['カツ丼', 'かつ丼'],
        'calories': 860.0, 'protein': 28.0, 'fat': 30.0, 'carbohydrates': 112.0, 'salt': 4.0,
        'category': '丼もの', 'reason': '卵とじカツ丼基準'
    },
    {
        'keywords': ['天丼'],
        'calories': 780.0, 'protein': 18.0, 'fat': 24.0, 'carbohydrates': 116.0, 'salt': 3.6,
        'category': '丼もの', 'reason': '海老・野菜天丼基準'
    },
    {
        'keywords': ['牛丼'],
        'calories': 680.0, 'protein': 20.0, 'fat': 24.0, 'carbohydrates': 92.0, 'salt': 2.8,
        'category': '丼もの', 'reason': '牛丼(並)基準'
    },
    {
        'keywords': ['親子丼'],
        'calories': 620.0, 'protein': 26.0, 'fat': 14.0, 'carbohydrates': 94.0, 'salt': 3.2,
        'category': '丼もの', 'reason': '鶏親子丼基準'
    },
    {
        'keywords': ['海鮮丼', 'まぐろ丼', 'マグロ丼', '鉄火丼'],
        'calories': 560.0, 'protein': 26.0, 'fat': 6.0, 'carbohydrates': 96.0, 'salt': 2.5,
        'category': '丼もの', 'reason': '海鮮丼基準'
    },
    {
        'keywords': ['中華丼'],
        'calories': 640.0, 'protein': 18.0, 'fat': 18.0, 'carbohydrates': 96.0, 'salt': 3.8,
        'category': '丼もの', 'reason': '八宝菜中華丼基準'
    },
    {
        'keywords': ['炒飯', 'チャーハン', '焼き飯'],
        'calories': 640.0, 'protein': 15.0, 'fat': 20.0, 'carbohydrates': 95.0, 'salt': 3.5,
        'category': 'ご飯もの', 'reason': '五目炒飯標準'
    },
    {
        'keywords': ['オムライス'],
        'calories': 680.0, 'protein': 18.0, 'fat': 22.0, 'carbohydrates': 98.0, 'salt': 3.2,
        'category': 'ご飯もの', 'reason': 'チキンライスオムライス標準'
    },
    {
        'keywords': ['丼', 'どんぶり'],
        'calories': 680.0, 'protein': 22.0, 'fat': 20.0, 'carbohydrates': 96.0, 'salt': 3.2,
        'category': '丼もの', 'reason': '丼もの全般標準'
    },

    # 寿司・和食
    {
        'keywords': ['寿司', 'にぎり寿司', 'すし'],
        'calories': 520.0, 'protein': 24.0, 'fat': 6.0, 'carbohydrates': 88.0, 'salt': 2.8,
        'category': '和食', 'reason': 'にぎり寿司(8〜10貫)基準'
    },
    {
        'keywords': ['鍋', '寄せ鍋', 'キムチ鍋', 'ちゃんこ鍋'],
        'calories': 420.0, 'protein': 30.0, 'fat': 14.0, 'carbohydrates': 22.0, 'salt': 4.5,
        'category': '和食', 'reason': '1人前鍋料理基準'
    },

    # 中華・洋食・ファストフード
    {
        'keywords': ['餃子', 'ぎょうざ'],
        'calories': 280.0, 'protein': 9.0, 'fat': 14.0, 'carbohydrates': 28.0, 'salt': 1.6,
        'category': '中華', 'reason': '焼き餃子(6個)基準'
    },
    {
        'keywords': ['ピザ'],
        'calories': 680.0, 'protein': 26.0, 'fat': 26.0, 'carbohydrates': 82.0, 'salt': 3.6,
        'category': '洋食', 'reason': 'ピザ(Mサイズ1/2または1人前)基準'
    },
    {
        'keywords': ['ダブルチーズバーガー'],
        'calories': 460.0, 'protein': 26.0, 'fat': 25.0, 'carbohydrates': 31.0, 'salt': 2.8,
        'category': 'ファストフード', 'reason': 'ダブルチーズバーガー基準'
    },
    {
        'keywords': ['ハンバーガー', 'バーガー'],
        'calories': 380.0, 'protein': 18.0, 'fat': 16.0, 'carbohydrates': 38.0, 'salt': 2.2,
        'category': 'ファストフード', 'reason': 'ハンバーガー標準'
    },
    {
        'keywords': ['フライドポテト', 'ポテトフライ', 'ポテト'],
        'calories': 380.0, 'protein': 4.5, 'fat': 19.0, 'carbohydrates': 48.0, 'salt': 1.1,
        'category': 'サイド', 'reason': 'フライドポテト(Mサイズ)基準'
    },
    {
        'keywords': ['ファミチキ', 'からあげクン', 'チキン'],
        'calories': 250.0, 'protein': 14.0, 'fat': 16.0, 'carbohydrates': 12.0, 'salt': 1.4,
        'category': 'サイド', 'reason': 'ホットスナックチキン基準'
    },
    {
        'keywords': ['サンドイッチ', 'サンド'],
        'calories': 320.0, 'protein': 11.0, 'fat': 13.0, 'carbohydrates': 38.0, 'salt': 1.8,
        'category': 'パン', 'reason': 'ミックスサンドイッチ基準'
    },
    {
        'keywords': ['おにぎり', 'おむすび'],
        'calories': 180.0, 'protein': 4.2, 'fat': 1.5, 'carbohydrates': 37.0, 'salt': 1.1,
        'category': '主食', 'reason': 'コンビニおにぎり1個基準'
    },
    {
        'keywords': ['トースト', '食パン'],
        'calories': 180.0, 'protein': 6.0, 'fat': 4.0, 'carbohydrates': 30.0, 'salt': 0.9,
        'category': '主食', 'reason': 'バタートースト1枚基準'
    },
    {
        'keywords': ['サラダ'],
        'calories': 85.0, 'protein': 2.5, 'fat': 4.5, 'carbohydrates': 8.0, 'salt': 0.6,
        'category': '副菜', 'reason': 'ドレッシング付サラダ基準'
    },
    {
        'keywords': ['味噌汁', 'みそ汁', 'スープ'],
        'calories': 55.0, 'protein': 3.5, 'fat': 1.5, 'carbohydrates': 6.0, 'salt': 1.6,
        'category': '汁物', 'reason': '汁物標準'
    },

    # スイーツ・カフェ・飲料
    {
        'keywords': ['キャラメルマキアート', 'カフェモカ', 'フラペチーノ'],
        'calories': 260.0, 'protein': 6.5, 'fat': 8.5, 'carbohydrates': 38.0, 'salt': 0.3,
        'category': 'カフェ', 'reason': '甘味ラテ・カフェ飲料(トール)基準'
    },
    {
        'keywords': ['カフェラテ', 'カフェオレ'],
        'calories': 140.0, 'protein': 6.0, 'fat': 6.5, 'carbohydrates': 11.0, 'salt': 0.2,
        'category': 'カフェ', 'reason': 'カフェラテ標準'
    },
    {
        'keywords': ['ショートケーキ', 'ケーキ'],
        'calories': 340.0, 'protein': 4.5, 'fat': 22.0, 'carbohydrates': 32.0, 'salt': 0.3,
        'category': 'デザート', 'reason': 'カットケーキ1個基準'
    },
    {
        'keywords': ['アイスクリーム', 'アイス'],
        'calories': 220.0, 'protein': 3.5, 'fat': 12.0, 'carbohydrates': 24.0, 'salt': 0.1,
        'category': 'デザート', 'reason': 'カップアイス1個基準'
    },
    {
        'keywords': ['ビール', '生ビール'],
        'calories': 140.0, 'protein': 1.5, 'fat': 0.0, 'carbohydrates': 10.5, 'salt': 0.0,
        'category': 'アルコール', 'reason': 'ビール1缶(350ml)基準'
    },
    {
        'keywords': ['ハイボール', '酎ハイ', 'サワー'],
        'calories': 120.0, 'protein': 0.0, 'fat': 0.0, 'carbohydrates': 4.0, 'salt': 0.0,
        'category': 'アルコール', 'reason': '缶酎ハイ/ハイボール基準'
    },
]


def estimate_nutrition(food_name: str) -> dict:
    """
    料理名・食品名のキーワードや修飾子から、標準的な栄養素(カロリー・PFC・塩分)を高速推計
    """
    name = (food_name or '').strip()
    if not name:
        return {
            'found': False,
            'name': '',
            'calories': 0.0, 'protein': 0.0, 'fat': 0.0, 'carbohydrates': 0.0, 'salt': 0.0,
            'reason': '入力が空です'
        }

    # 1. サイズ修飾子の判定 (倍率係数)
    multiplier = 1.0
    size_note = ""
    if re.search(r'(メガ|特盛|特大|大盛り|大盛|大)', name):
        multiplier = 1.35
        size_note = " (大盛り・特盛換算)"
    elif re.search(r'(ミニ|小盛り|小盛|ハーフ|小|半分)', name):
        multiplier = 0.65
        size_note = " (小盛り・ハーフ換算)"

    # 2. キーワードマッチング
    matched_rule = None
    for rule in BASE_FOOD_RULES:
        for kw in rule['keywords']:
            if kw.lower() in name.lower():
                matched_rule = rule
                break
        if matched_rule:
            break

    # 3. マッチしなかった場合のフォールバック (デフォルト一般料理)
    if not matched_rule:
        # デフォルト一般定食/一品料理
        matched_rule = {
            'calories': 500.0,
            'protein': 18.0,
            'fat': 16.0,
            'carbohydrates': 68.0,
            'salt': 2.5,
            'category': '一般料理',
            'reason': '一般的な一品料理の標準値'
        }
        confidence = 'low'
    else:
        confidence = 'high'

    # 倍率を適用
    cal = round(matched_rule['calories'] * multiplier, 1)
    p = round(matched_rule['protein'] * multiplier, 1)
    f = round(matched_rule['fat'] * multiplier, 1)
    c = round(matched_rule['carbohydrates'] * multiplier, 1)
    salt = round(matched_rule['salt'] * multiplier, 2)

    return {
        'found': True,
        'name': name,
        'calories': cal,
        'protein': p,
        'fat': f,
        'carbohydrates': c,
        'salt': salt,
        'category': matched_rule['category'],
        'reason': matched_rule['reason'] + size_note,
        'confidence': confidence,
    }
