import re

# 基本料理ジャンル・食品辞書 (標準1人前・1本・1個ベース)
BASE_FOOD_RULES = [
    # -------------------------------------------------------------
    # 1. 無糖飲料・水・お茶類 (最優先: ほぼ0〜2kcal)
    # -------------------------------------------------------------
    {
        'keywords': [
            '麦茶', 'むぎ茶', 'むぎちゃ', '緑茶', 'お茶', '日本茶', 'ほうじ茶', 
            '玄米茶', '烏龍茶', 'ウーロン茶', 'ウーロン', 'ジャスミン茶', 'ジャスミンティー',
            'ブレンド茶', '爽健美茶', '十六茶', '綾鷹', '伊右衛門', '生茶', 'おーいお茶',
            '水', 'ミネラルウォーター', '天然水', '白湯', 'お冷', '炭酸水', 'スパークリングウォーター',
            'ブラックコーヒー', '無糖コーヒー', 'アイスコーヒー(無糖)', 'ホットコーヒー(無糖)',
            'エスプレッソ', 'アメリカンコーヒー', 'ストレートティー', '無糖紅茶', 
            'ハーブティー', 'ルイボスティー', 'コーン茶', 'そば茶', 'ノンカロリー', 'ゼロカロリー'
        ],
        'calories': 2.0, 'protein': 0.0, 'fat': 0.0, 'carbohydrates': 0.5, 'salt': 0.0,
        'category': '飲料(無糖)', 'reason': '無糖茶・水・ブラックコーヒー基準 (約0〜2kcal)'
    },

    # -------------------------------------------------------------
    # 2. 清涼飲料・ジュース・乳飲料・プロテイン
    # -------------------------------------------------------------
    {
        'keywords': ['プロテイン', 'プロテインドリンク', 'ザバス', 'SAVAS', 'ホエイプロテイン', 'ソイプロテイン'],
        'calories': 110.0, 'protein': 20.0, 'fat': 1.5, 'carbohydrates': 3.5, 'salt': 0.3,
        'category': 'プロテイン', 'reason': 'プロテインドリンク1食分基準 (高たんぱく)'
    },
    {
        'keywords': ['豆乳', '調整豆乳', '無調整豆乳', 'ソイミルク'],
        'calories': 105.0, 'protein': 8.5, 'fat': 5.5, 'carbohydrates': 5.5, 'salt': 0.2,
        'category': '乳飲料', 'reason': '豆乳200mlパック基準'
    },
    {
        'keywords': ['牛乳', 'ミルク', '低脂肪乳', '成分無調整牛乳'],
        'calories': 135.0, 'protein': 6.8, 'fat': 7.8, 'carbohydrates': 9.9, 'salt': 0.2,
        'category': '乳飲料', 'reason': '普通牛乳200mlコップ1杯基準'
    },
    {
        'keywords': ['飲むヨーグルト', 'のむヨーグルト', 'R-1', 'ヤクルト'],
        'calories': 130.0, 'protein': 6.0, 'fat': 2.0, 'carbohydrates': 22.0, 'salt': 0.2,
        'category': '乳飲料', 'reason': '乳酸菌飲料・飲むヨーグルト基準'
    },
    {
        'keywords': ['スポーツドリンク', 'ポカリスエット', 'ポカリ', 'アクエリアス', '経口補水液', 'OS-1'],
        'calories': 65.0, 'protein': 0.0, 'fat': 0.0, 'carbohydrates': 16.0, 'salt': 0.3,
        'category': '飲料', 'reason': 'スポーツドリンク(500ml換算/半分量目安)'
    },
    {
        'keywords': ['コーラ', 'サイダー', '炭酸飲料', 'ジンジャーエール', 'メロンソーダ', 'ファンタ'],
        'calories': 140.0, 'protein': 0.0, 'fat': 0.0, 'carbohydrates': 35.0, 'salt': 0.0,
        'category': '飲料', 'reason': '加糖炭酸飲料1本基準'
    },
    {
        'keywords': ['オレンジジュース', 'りんごジュース', 'アップルジュース', 'グレープジュース', '果汁100%', '野菜ジュース', '野菜生活'],
        'calories': 90.0, 'protein': 1.0, 'fat': 0.0, 'carbohydrates': 21.0, 'salt': 0.05,
        'category': '飲料', 'reason': '果汁/野菜ジュース200ml基準'
    },
    {
        'keywords': ['ミルクティー', 'ロイヤルミルクティー', 'レモンティー', '午後の紅茶'],
        'calories': 110.0, 'protein': 2.0, 'fat': 2.0, 'carbohydrates': 20.0, 'salt': 0.1,
        'category': '飲料', 'reason': '加糖紅茶・ミルクティー基準'
    },
    {
        'keywords': ['ココア', 'ホットココア'],
        'calories': 150.0, 'protein': 4.0, 'fat': 4.5, 'carbohydrates': 24.0, 'salt': 0.2,
        'category': '飲料', 'reason': 'ミルクココア1杯基準'
    },
    {
        'keywords': ['キャラメルマキアート', 'カフェモカ', 'フラペチーノ'],
        'calories': 260.0, 'protein': 6.5, 'fat': 8.5, 'carbohydrates': 38.0, 'salt': 0.3,
        'category': 'カフェ', 'reason': '甘味カフェ飲料(トール)基準'
    },
    {
        'keywords': ['カフェラテ', 'カフェオレ'],
        'calories': 140.0, 'protein': 6.0, 'fat': 6.5, 'carbohydrates': 11.0, 'salt': 0.2,
        'category': 'カフェ', 'reason': 'カフェラテ標準'
    },
    {
        'keywords': ['コーヒー', 'ホットコーヒー', 'アイスコーヒー'],
        'calories': 15.0, 'protein': 0.5, 'fat': 0.2, 'carbohydrates': 2.5, 'salt': 0.0,
        'category': 'カフェ', 'reason': 'コーヒー(少量のミルク/砂糖含み想定)'
    },

    # -------------------------------------------------------------
    # 3. 日常の単品食材・小鉢・果物
    # -------------------------------------------------------------
    {
        'keywords': ['納豆', 'なっとう'],
        'calories': 90.0, 'protein': 7.5, 'fat': 4.5, 'carbohydrates': 6.0, 'salt': 0.6,
        'category': '副菜', 'reason': '納豆1パック(たれ・からし付)基準'
    },
    {
        'keywords': ['生卵', 'ゆで卵', 'ゆでたまご', '温泉卵', '温玉', '目玉焼き', '卵', 'たまご'],
        'calories': 80.0, 'protein': 6.5, 'fat': 5.5, 'carbohydrates': 0.2, 'salt': 0.2,
        'category': '主菜', 'reason': '鶏卵Mサイズ1個基準'
    },
    {
        'keywords': ['冷奴', '豆腐', '絹ごし豆腐', '木綿豆腐', 'とうふ'],
        'calories': 72.0, 'protein': 6.6, 'fat': 4.2, 'carbohydrates': 2.0, 'salt': 0.1,
        'category': '副菜', 'reason': '豆腐1/2丁(約150g)基準'
    },
    {
        'keywords': ['サラダチキン', '蒸し鶏'],
        'calories': 115.0, 'protein': 24.0, 'fat': 1.5, 'carbohydrates': 0.5, 'salt': 1.2,
        'category': '主菜', 'reason': '市販サラダチキン1パック(110g)基準'
    },
    {
        'keywords': ['ヨーグルト', 'プレーンヨーグルト', 'ギリシャヨーグルト'],
        'calories': 70.0, 'protein': 4.0, 'fat': 3.0, 'carbohydrates': 6.0, 'salt': 0.1,
        'category': '乳製品', 'reason': 'プレーンヨーグルト(100g)基準'
    },
    {
        'keywords': ['チーズ', 'プロセスチーズ', 'スライスチーズ', 'ベビーチーズ'],
        'calories': 65.0, 'protein': 4.5, 'fat': 5.5, 'carbohydrates': 0.3, 'salt': 0.5,
        'category': '乳製品', 'reason': 'プロセスチーズ1個(20g)基準'
    },
    {
        'keywords': ['バナナ'],
        'calories': 86.0, 'protein': 1.1, 'fat': 0.2, 'carbohydrates': 22.5, 'salt': 0.0,
        'category': '果物', 'reason': '生バナナ1本(可食部約90g)基準'
    },
    {
        'keywords': ['りんご', 'リンゴ'],
        'calories': 105.0, 'protein': 0.4, 'fat': 0.3, 'carbohydrates': 28.0, 'salt': 0.0,
        'category': '果物', 'reason': '生りんご1/2個〜中玉基準'
    },
    {
        'keywords': ['みかん', 'ミカン'],
        'calories': 45.0, 'protein': 0.7, 'fat': 0.1, 'carbohydrates': 11.5, 'salt': 0.0,
        'category': '果物', 'reason': '温州みかん1個基準'
    },
    {
        'keywords': ['トマト', 'ミニトマト', 'プチトマト'],
        'calories': 30.0, 'protein': 1.1, 'fat': 0.1, 'carbohydrates': 6.5, 'salt': 0.0,
        'category': '野菜', 'reason': 'トマト1個/ミニトマト数個基準'
    },
    {
        'keywords': ['味噌汁', 'みそ汁'],
        'calories': 55.0, 'protein': 3.5, 'fat': 1.5, 'carbohydrates': 6.0, 'salt': 1.6,
        'category': '汁物', 'reason': '具入り味噌汁1杯基準'
    },
    {
        'keywords': ['わかめスープ', '中華スープ', 'コンソメスープ', 'お吸い物', 'すまし汁'],
        'calories': 30.0, 'protein': 1.5, 'fat': 0.5, 'carbohydrates': 4.0, 'salt': 1.5,
        'category': '汁物', 'reason': '澄まし・あっさり系スープ1杯基準'
    },
    {
        'keywords': ['コーンスープ', 'ポタージュ', 'クラムチャウダー', '豚汁', 'とん汁'],
        'calories': 130.0, 'protein': 4.0, 'fat': 5.0, 'carbohydrates': 18.0, 'salt': 1.5,
        'category': '汁物', 'reason': '濃厚スープ・具沢山豚汁1杯基準'
    },
    {
        'keywords': ['スープ'],
        'calories': 60.0, 'protein': 2.5, 'fat': 2.0, 'carbohydrates': 8.0, 'salt': 1.5,
        'category': '汁物', 'reason': 'スープ標準'
    },
    {
        'keywords': ['サラダ', '生野菜', 'キャベツ千切り'],
        'calories': 85.0, 'protein': 2.5, 'fat': 4.5, 'carbohydrates': 8.0, 'salt': 0.6,
        'category': '副菜', 'reason': 'ドレッシング付サラダ1皿基準'
    },

    # -------------------------------------------------------------
    # 4. 主食 (ご飯・パン・おにぎり)
    # -------------------------------------------------------------
    {
        'keywords': ['大盛りご飯', 'ごはん大盛り', 'ライス大盛り'],
        'calories': 350.0, 'protein': 5.5, 'fat': 0.8, 'carbohydrates': 80.0, 'salt': 0.0,
        'category': '主食', 'reason': '白米大盛り(220g)基準'
    },
    {
        'keywords': ['白米', 'ご飯', 'ごはん', 'お米', 'ライス', '玄米', '麦飯', '雑穀米'],
        'calories': 234.0, 'protein': 3.8, 'fat': 0.5, 'carbohydrates': 53.4, 'salt': 0.0,
        'category': '主食', 'reason': '白米ご飯(普通盛り150g)基準'
    },
    {
        'keywords': ['ツナマヨおにぎり', 'マヨおにぎり'],
        'calories': 220.0, 'protein': 4.8, 'fat': 6.5, 'carbohydrates': 37.0, 'salt': 1.1,
        'category': '主食', 'reason': 'ツナマヨおにぎり基準'
    },
    {
        'keywords': ['おにぎり', 'おむすび'],
        'calories': 180.0, 'protein': 4.2, 'fat': 1.5, 'carbohydrates': 37.0, 'salt': 1.1,
        'category': '主食', 'reason': 'コンビニ定番おにぎり(鮭/梅/昆布等)1個基準'
    },
    {
        'keywords': ['トースト', 'バタートースト'],
        'calories': 195.0, 'protein': 6.0, 'fat': 6.5, 'carbohydrates': 30.0, 'salt': 1.0,
        'category': '主食', 'reason': 'バタートースト(6枚切1枚)基準'
    },
    {
        'keywords': ['食パン', 'ロールパン', 'フランスパン', 'ベーグル'],
        'calories': 160.0, 'protein': 5.5, 'fat': 2.5, 'carbohydrates': 29.0, 'salt': 0.8,
        'category': '主食', 'reason': '食パン1枚/ロールパン2個基準'
    },
    {
        'keywords': ['クロワッサン', 'デニッシュ', 'メロンパン', '菓子パン'],
        'calories': 360.0, 'protein': 6.5, 'fat': 16.0, 'carbohydrates': 48.0, 'salt': 0.8,
        'category': '主食', 'reason': '菓子パン・クロワッサン1個基準'
    },

    # -------------------------------------------------------------
    # 5. 讃岐うどん・麺類・パスタ
    # -------------------------------------------------------------
    {
        'keywords': ['天ぷらうどん', '肉うどん', 'カレーうどん'],
        'calories': 560.0, 'protein': 16.0, 'fat': 14.0, 'carbohydrates': 92.0, 'salt': 5.5,
        'category': 'うどん', 'reason': '具入り温うどん1玉基準'
    },
    {
        'keywords': ['讃岐うどん', 'かけうどん', 'ぶっかけうどん', '生醤油うどん', '釜玉うどん', 'ざるうどん', 'うどん'],
        'calories': 420.0, 'protein': 10.5, 'fat': 3.5, 'carbohydrates': 78.0, 'salt': 4.2,
        'category': 'うどん', 'reason': '讃岐手打ちうどん(並1玉)基準'
    },
    {
        'keywords': ['天ぷらそば', '鴨南蛮そば', '肉そば'],
        'calories': 520.0, 'protein': 18.0, 'fat': 12.0, 'carbohydrates': 85.0, 'salt': 5.2,
        'category': '麺類', 'reason': '具入り温そば基準'
    },
    {
        'keywords': ['ざるそば', 'もりそば', 'かけそば', 'そば', '蕎麦', 'そうめん', '素麺'],
        'calories': 380.0, 'protein': 14.0, 'fat': 2.5, 'carbohydrates': 75.0, 'salt': 4.0,
        'category': '麺類', 'reason': '日本そば/そうめん標準'
    },
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

    # -------------------------------------------------------------
    # 6. 定食類 (ご飯・味噌汁・主菜・小鉢)
    # -------------------------------------------------------------
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
        'keywords': ['ハンバーグ定食', 'ハンバーグ'],
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

    # -------------------------------------------------------------
    # 7. 丼もの・ご飯もの・カレー
    # -------------------------------------------------------------
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

    # -------------------------------------------------------------
    # 8. 寿司・和食・鍋
    # -------------------------------------------------------------
    {
        'keywords': ['寿司', 'にぎり寿司', 'すし', 'お寿司'],
        'calories': 520.0, 'protein': 24.0, 'fat': 6.0, 'carbohydrates': 88.0, 'salt': 2.8,
        'category': '和食', 'reason': 'にぎり寿司(8〜10貫)基準'
    },
    {
        'keywords': ['鍋', '寄せ鍋', 'キムチ鍋', 'ちゃんこ鍋'],
        'calories': 420.0, 'protein': 30.0, 'fat': 14.0, 'carbohydrates': 22.0, 'salt': 4.5,
        'category': '和食', 'reason': '1人前鍋料理基準'
    },

    # -------------------------------------------------------------
    # 9. ファストフード・中華・スナック
    # -------------------------------------------------------------
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
        'keywords': ['ファミチキ', 'からあげクン', 'から揚げ', '唐揚げ', 'フライドチキン'],
        'calories': 260.0, 'protein': 14.0, 'fat': 17.0, 'carbohydrates': 12.0, 'salt': 1.4,
        'category': 'サイド', 'reason': 'ホットスナックチキン/唐揚げ(3〜4個)基準'
    },
    {
        'keywords': ['サンドイッチ', 'サンド'],
        'calories': 320.0, 'protein': 11.0, 'fat': 13.0, 'carbohydrates': 38.0, 'salt': 1.8,
        'category': 'パン', 'reason': 'ミックスサンドイッチ基準'
    },

    # -------------------------------------------------------------
    # 10. スイーツ・アルコール
    # -------------------------------------------------------------
    {
        'keywords': ['ショートケーキ', 'ケーキ', 'シュークリーム'],
        'calories': 320.0, 'protein': 4.5, 'fat': 20.0, 'carbohydrates': 30.0, 'salt': 0.3,
        'category': 'デザート', 'reason': '洋生菓子1個基準'
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
        'keywords': ['ハイボール', '酎ハイ', 'サワー', 'レモンサワー'],
        'calories': 120.0, 'protein': 0.0, 'fat': 0.0, 'carbohydrates': 4.0, 'salt': 0.0,
        'category': 'アルコール', 'reason': '缶酎ハイ/ハイボール基準'
    },
]


def estimate_nutrition(food_name: str) -> dict:
    """
    料理名・食品名のキーワードや修飾子から、標準的な栄養素(カロリー・PFC・塩分)を高速推計。
    何にもマッチしない場合は無理に500kcalを返さず、found=Falseとして安全にフォールバックする。
    """
    name = (food_name or '').strip()
    if not name:
        return {
            'found': False,
            'name': '',
            'calories': 0.0, 'protein': 0.0, 'fat': 0.0, 'carbohydrates': 0.0, 'salt': 0.0,
            'category': '',
            'reason': '入力が空です',
            'confidence': 'none'
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

    # 2. キーワードマッチング (完全一致または長いキーワードを優先)
    matched_rule = None
    best_match_len = 0

    lower_name = name.lower()

    for rule in BASE_FOOD_RULES:
        for kw in rule['keywords']:
            kw_lower = kw.lower()
            if kw_lower in lower_name:
                # より長いキーワード（具体的な単語）での一致を優先
                if len(kw_lower) > best_match_len:
                    best_match_len = len(kw_lower)
                    matched_rule = rule

    # 3. マッチしなかった場合の安全なフォールバック
    if not matched_rule:
        return {
            'found': False,
            'name': name,
            'calories': 0.0,
            'protein': 0.0,
            'fat': 0.0,
            'carbohydrates': 0.0,
            'salt': 0.0,
            'category': '未分類',
            'reason': '該当する標準データがありません。数値を直接ご入力ください',
            'confidence': 'none',
        }

    # 倍率を適用 (カロリーが元々極小の無糖飲料などは倍率計算で不自然に増減させない)
    if matched_rule['calories'] <= 5.0:
        cal = matched_rule['calories']
        p = matched_rule['protein']
        f = matched_rule['fat']
        c = matched_rule['carbohydrates']
        salt = matched_rule['salt']
    else:
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
        'confidence': 'high',
    }
