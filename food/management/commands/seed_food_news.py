from django.core.management.base import BaseCommand
from datetime import date, timedelta
from food.models import FoodCategory, FoodEntry


class Command(BaseCommand):
    help = '食の新発売・イベントの初期シードデータを登録します'

    def handle(self, *args, **options):
        self.stdout.write('カテゴリのマスタデータを投入中...')
        
        categories_data = [
            {'slug': 'convenience', 'name': 'コンビニ', 'item_type': 'product', 'icon': '🏪', 'order': 1},
            {'slug': 'fastfood', 'name': 'ファストフード', 'item_type': 'product', 'icon': '🍔', 'order': 2},
            {'slug': 'sweets', 'name': 'スイーツ・お菓子', 'item_type': 'product', 'icon': '🍰', 'order': 3},
            {'slug': 'cafe', 'name': 'カフェ・ドリンク', 'item_type': 'product', 'icon': '☕', 'order': 4},
            {'slug': 'noodle', 'name': 'ラーメン・麺類', 'item_type': 'product', 'icon': '🍜', 'order': 5},
            {'slug': 'festival', 'name': 'フードフェス・祭り', 'item_type': 'event', 'icon': '🎪', 'order': 6},
            {'slug': 'fair', 'name': '物産展・デパ地下催事', 'item_type': 'event', 'icon': '🛍️', 'order': 7},
            {'slug': 'alcohol', 'name': 'クラフトビール・酒', 'item_type': 'all', 'icon': '🍺', 'order': 8},
        ]

        cat_objs = {}
        for cdata in categories_data:
            obj, created = FoodCategory.objects.update_or_create(
                slug=cdata['slug'],
                defaults=cdata
            )
            cat_objs[cdata['slug']] = obj

        self.stdout.write('新発売・イベントのシードデータを投入中...')
        today = date.today()

        entries_data = [
            # 1. マクドナルド
            {
                'title': '芳醇ふわとろ月見バーガー（トリュフ香る特製マヨ）',
                'item_type': 'product',
                'category': cat_objs['fastfood'],
                'brand': '日本マクドナルド',
                'catchphrase': '秋の風物詩「月見」に贅沢なトリュフマヨ仕立てが新登場！',
                'description': '毎年大人気の秋の定番「月見バーガー」に、ブラックトリュフの芳醇な香りが広がるリッチな特製マヨソースとふわとろ食感のスクランブルエッグを合わせたプレミアムな逸品。\n\n100%ビーフパティに香ばしいベーコン、濃厚なチェダーチーズが重なり、秋の夜長にぴったりの奥深い味わいに仕上がっています。',
                'price_info': '単品 520円(税込)〜 / セット 820円(税込)〜',
                'area_info': '全国のマクドナルド店舗（一部店舗を除く）',
                'start_date': today - timedelta(days=5),
                'end_date': today + timedelta(days=25),
                'is_period_limited': True,
                'is_featured': True,
                'official_url': 'https://www.mcdonalds.co.jp/',
                'tags': '月見, トリュフ, 期間限定, 秋バーガー',
            },
            # 2. セブン-イレブン
            {
                'title': 'イタリア栗の生搾り贅沢モンブラン',
                'item_type': 'product',
                'category': cat_objs['sweets'],
                'brand': 'セブン-イレブン',
                'catchphrase': '口どけなめらか！繊細な極細マロンクリームの本格秋スイーツ',
                'description': 'イタリア産栗を100%贅沢に使用した秋の新作モンブラン。\n細さ1mmの極細ノズルから絞り出したマロンクリームは、空気を含んでふわっと軽やかな口どけを実現。\n中にはミルキーなホイップクリームと香ばしいアーモンドスポンジ、アクセントのマロンダイスが隠れており、専門店のケーキに匹敵する本格派スイーツです。',
                'price_info': '398円(税込)',
                'area_info': '全国のセブン-イレブン各店',
                'start_date': today - timedelta(days=2),
                'end_date': today + timedelta(days=30),
                'is_period_limited': True,
                'is_featured': True,
                'official_url': 'https://www.sej.co.jp/',
                'tags': 'コンビニスイーツ, モンブラン, 栗, 期間限定',
            },
            # 3. スターバックス
            {
                'title': '焼き芋 香ばしカラメルフラペチーノ®',
                'item_type': 'product',
                'category': cat_objs['cafe'],
                'brand': 'スターバックス コーヒー',
                'catchphrase': 'ほくほく焼き芋にほろ苦カヌレ風カラメルチップが絶妙！',
                'description': 'じっくりと壺焼きにして甘みを極限まで引き出した焼き芋を丸ごとブレンド。\nトップにはほろ苦いビターカラメルソースと、カリカリ食感の焼き芋チップスをトッピング。飲むたびに秋の味覚が口いっぱいに広がる、デザート感満載の限定ビバレッジです。',
                'price_info': 'Tall 700円(税込)',
                'area_info': '全国のスターバックス店舗',
                'start_date': today - timedelta(days=8),
                'end_date': today + timedelta(days=20),
                'is_period_limited': True,
                'is_featured': True,
                'official_url': 'https://www.starbucks.co.jp/',
                'tags': 'スタバ新作, 焼き芋, フラペチーノ, 秋限定',
            },
            # 4. ミスタードーナツ
            {
                'title': 'さつまいもド 蜜いもブリュレ',
                'item_type': 'product',
                'category': cat_objs['sweets'],
                'brand': 'ミスタードーナツ',
                'catchphrase': 'ドーナツ生地に安納芋パウダー練り込み！パリパリキャラメリゼ仕立て',
                'description': 'さつまいもをイメージしたホクホク＆しっとり食感のドーナツにシロップを染み込ませ、表面をキャラメリゼしてカリッ・パリッとした食感に仕上げた秋の看板商品。\nひとくち食べると香ばしいキャラメルと濃密なお芋の甘みがジュワッと広がります。',
                'price_info': 'テイクアウト 194円(税込) / イートイン 198円(税込)',
                'area_info': '全国のミスタードーナツ全店',
                'start_date': today - timedelta(days=12),
                'end_date': today + timedelta(days=35),
                'is_period_limited': True,
                'is_featured': False,
                'official_url': 'https://www.misterdonut.jp/',
                'tags': 'ミスド, さつまいもド, ブリュレ, ドーナツ',
            },
            # 5. ローソン
            {
                'title': 'からあげクン すだちポン酢味（徳島県産すだち使用）',
                'item_type': 'product',
                'category': cat_objs['convenience'],
                'brand': 'ローソン',
                'catchphrase': '爽やかな柑橘の酸味とコク深いポン酢でさっぱりジューシー！',
                'description': '徳島県産の完熟すだち果汁と本醸造しょうゆを使用した爽快な新フレーバー。\n揚げたてのジューシーな鶏肉に、すだちの清涼感あふれるアロマと上品な酸味が絡み合い、何個でも食べたくなる後味すっきりの逸品。おやつやお酒のおつまみにも最適です。',
                'price_info': '259円(税込)',
                'area_info': '全国のローソン店舗（ナチュラルローソン除く）',
                'start_date': today + timedelta(days=2), # 近日発売
                'end_date': today + timedelta(days=28),
                'is_period_limited': True,
                'is_featured': False,
                'official_url': 'https://www.lawson.co.jp/',
                'tags': 'からあげクン, すだち, ホットスナック, 新発売',
            },
            # 6. 日清食品
            {
                'title': '特上 カップヌードル 黒トリュフ香る 濃厚バタークラムチャウダー',
                'item_type': 'product',
                'category': cat_objs['noodle'],
                'brand': '日清食品',
                'catchphrase': 'カップヌードル史上最高級のコク！贅沢トリュフオイル付き',
                'description': 'アサリと帆立の旨みが凝縮されたクリーミーなクラムチャウダースープに、北海道産バターの芳醇なコクをプラス。\n別添の「特製黒トリュフオイル」を加えることで、湯気とともに立ち上る高級感あふれる香りが食欲をそそります。',
                'price_info': '278円(税別)',
                'area_info': '全国のスーパー・コンビニエンスストア',
                'start_date': today - timedelta(days=1),
                'end_date': None,
                'is_period_limited': False,
                'is_featured': False,
                'official_url': 'https://www.nissin.com/',
                'tags': 'カップヌードル, トリュフ, クラムチャウダー, 新商品',
            },
            # 7. イベント: 北海道大物産展
            {
                'title': '秋の大北海道物産と観光展 2026',
                'item_type': 'event',
                'category': cat_objs['fair'],
                'brand': '阪神梅田本店 催事部',
                'catchphrase': '旬の秋鮭・いくら・新じゃが・絶品海鮮丼に札幌濃厚味噌ラーメンが集結！',
                'description': '百貨店物産展で圧倒的人気を誇る秋の北海道展が今年も開催！\n会場実演販売では、名物「こぼれいくら海鮮丼」や十勝牛の肉握り寿司、できたて生チーズタルト、濃厚ソフトクリームが勢ぞろい。\n茶屋コーナーでは札幌で行列のできる名店の限定濃厚ホタテ味噌ラーメンを熱々で味わえます。',
                'price_info': '入場無料（飲食・物販は別途）',
                'area_info': '大阪府大阪市北区梅田',
                'venue_name': '阪神梅田本店 8階 催事場',
                'venue_address': '大阪府大阪市北区梅田1丁目13-13',
                'start_date': today - timedelta(days=3),
                'end_date': today + timedelta(days=10),
                'is_period_limited': True,
                'is_featured': True,
                'official_url': 'https://www.hanshin-dept.jp/',
                'tags': '北海道物産展, 海鮮丼, 味噌ラーメン, スイーツ',
            },
            # 8. イベント: クラフトビール祭り
            {
                'title': 'けやきひろば 秋のビール祭り 2026',
                'item_type': 'event',
                'category': cat_objs['alcohol'],
                'brand': 'さいたまスーパーアリーナ',
                'catchphrase': '日本最大級のクラフトビールの祭典！全国・海外から400種類以上の生ビール',
                'description': '全国屈指の実力派ブルワリーが一堂に会する国内最大級のクラフトビールフェス。\nIPA、ペールエール、スタウト、フルーツセゾンなど、職人が魂を込めて仕込んだ鮮度抜群の樽生ビールを飲み比べできます。\nビールにぴったりの全国ご当地ソーセージや炭火焼き肉料理も充実。開放的な屋外エリアで最高の乾杯を！',
                'price_info': '入場無料（飲食はチケット・電子マネー決済）',
                'area_info': '埼玉県さいたま市中央区',
                'venue_name': 'さいたま新都心 けやきひろば',
                'venue_address': '埼玉県さいたま市中央区新都心10',
                'start_date': today + timedelta(days=4), # 近日開催
                'end_date': today + timedelta(days=8),
                'is_period_limited': True,
                'is_featured': True,
                'official_url': 'https://www.beerkeyaki.jp/',
                'tags': 'クラフトビール, ビールフェス, けやきひろば, 飲み比べ',
            },
            # 9. イベント: 激辛グルメ祭り
            {
                'title': '全日本 激辛グルメ祭り 2026 秋の陣',
                'item_type': 'event',
                'category': cat_objs['festival'],
                'brand': '激辛グルメ祭り実行委員会',
                'catchphrase': '辛いけど旨い！麻婆豆腐・ハバネロチキン・激辛カレーの名店が集結',
                'description': '世界各国の激辛料理を愛するフードファンが集う大人気フェス。\n四川本格麻婆豆腐、韓国ヤンニョムチキン、タイの激辛トムヤムクン、メキシカンハバネロタコスなど、辛さと旨味の限界に挑戦する名店メニューが目白押し。\n辛さのレベルを選べるので、激辛初心者からマニアまで幅広く楽しめます。',
                'price_info': '入場無料（食券制・キャッシュレス決済対応）',
                'area_info': '東京都新宿区歌舞伎町',
                'venue_name': '新宿・大久保公園 特設会場',
                'venue_address': '東京都新宿区歌舞伎町2-43',
                'start_date': today - timedelta(days=6),
                'end_date': today + timedelta(days=14),
                'is_period_limited': True,
                'is_featured': False,
                'official_url': 'https://www.gekikara-gourmet.com/',
                'tags': '激辛グルメ, 麻婆豆腐, カレー, 新宿',
            },
            # 10. イベント: ならクラフトビール祭り
            {
                'title': '奈良クラフトビール祭り 2026',
                'item_type': 'event',
                'category': cat_objs['alcohol'],
                'brand': '奈良クラフトビール祭り実行委員会',
                'catchphrase': '古都・奈良公園で古都のクラフトビールと地元吉野・大和食材を味わう',
                'description': '奈良県内のマイクロブルワリーをはじめ、関西の実力派醸造所が奈良公園に集結！\n若草山や東大寺を望む豊かな自然の中で、古都の仕込み水を使ったフレッシュなビールと、大和牛や吉野の燻製チーズなど奈良の厳選おつまみを満喫できます。\n心地よい秋風を感じながら贅沢な週末をお過ごしください。',
                'price_info': '入場無料（オリジナル試飲グラス付きチケット販売あり）',
                'area_info': '奈良県奈良市登大路町',
                'venue_name': '奈良公園 登大路園地',
                'venue_address': '奈良県奈良市登大路町',
                'start_date': today + timedelta(days=9),
                'end_date': today + timedelta(days=11),
                'is_period_limited': True,
                'is_featured': True,
                'official_url': 'https://naracraftbeer.jp/',
                'tags': '奈良, クラフトビール, 奈良公園, 観光フェス',
            },
            # 11. イベント: 東京ラーメンフェスタ
            {
                'title': '東京ラーメンフェスタ 2026',
                'item_type': 'event',
                'category': cat_objs['festival'],
                'brand': '日本ラーメン協会',
                'catchphrase': '全国の極上ご当地ラーメンが集結！日本最大級のラーメン屋外イベント',
                'description': '北は北海道から南は九州・沖縄まで、全国各地で愛されるご当地ラーメンと、ここでしか食べられない有名店同士のプレミアムコラボラーメンが勢ぞろい！\n豚骨、鶏白湯、淡麗煮干し醤油、濃厚海老味噌など、多種多様な一杯を青空の下で堪能できます。',
                'price_info': '入場無料（ラーメン1杯 1,000円全店共通食券制）',
                'area_info': '東京都世田谷区駒沢公園',
                'venue_name': '駒沢オリンピック公園 中央広場',
                'venue_address': '東京都世田谷区駒沢公園1-1',
                'start_date': today + timedelta(days=15),
                'end_date': today + timedelta(days=26),
                'is_period_limited': True,
                'is_featured': False,
                'official_url': 'https://ra-fes.com/',
                'tags': 'ラーメンフェスタ, 駒沢公園, ご当地ラーメン, 麺フェス',
            },
        ]

        created_count = 0
        for edata in entries_data:
            obj, created = FoodEntry.objects.update_or_create(
                title=edata['title'],
                brand=edata['brand'],
                defaults=edata
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'完了: カテゴリ {len(categories_data)} 件、食ニュース/イベント {len(entries_data)} 件を投入・同期しました（新規作成: {created_count} 件）'))
