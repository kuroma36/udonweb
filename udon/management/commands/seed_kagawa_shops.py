import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from udon.models import Shop, Trip, TripMember, TripStop, Review, UserProfile


class Command(BaseCommand):
    help = 'Seeds famous Kagawa Sanuki Udon shops and demo trip matching UI mockup'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Kagawa Sanuki Udon data...')
        
        with transaction.atomic():
            # 1. Create starter Udonchu User Profiles
            users_data = [
                {'username': 'dashi_mania', 'nickname': '出汁マニア', 'color': '#E67E22', 'fav': 'かけうどん', 'title': '出汁ソムリエ'},
                {'username': 'udon_taro', 'nickname': 'うどん太郎', 'color': '#2980B9', 'fav': '釜玉うどん', 'title': '巡礼皆伝'},
                {'username': 'sanuki_girl', 'nickname': 'さぬき女子', 'color': '#C84B31', 'fav': '冷やしぶっかけ', 'title': '香川うどん人'},
                {'username': 'tempura_master', 'nickname': '天ぷら奉行', 'color': '#27AE60', 'fav': '天ぷらうどん', 'title': '揚げ物名人'},
                {'username': 'udon_guest', 'nickname': 'お試しうどん人', 'color': '#D99B26', 'fav': '肉ぶっかけ', 'title': 'ゲスト巡礼者'},
            ]
            for ud in users_data:
                u, _ = User.objects.get_or_create(username=ud['username'], defaults={'email': f"{ud['username']}@krmts.com"})
                u.set_password('password123')
                u.save()
                UserProfile.objects.update_or_create(
                    user=u,
                    defaults={
                        'nickname': ud['nickname'],
                        'avatar_color': ud['color'],
                        'avatar_icon': 'udonchu',
                        'favorite_udon': ud['fav'],
                        'level_title': ud['title'],
                    }
                )

            user = User.objects.get(username='dashi_mania')

            # 2. Create Famous Sanuki Udon Shops
            shops_data = [
                {
                    'name': '香川うどん (がもううどん)',
                    'address': '香川県坂出市加茂町420-1',
                    'lat': 34.3015,
                    'lng': 133.8961,
                    'place_id': 'ChIJg_gamou_sakaide',
                    'google_rating': 4.4,
                    'google_user_ratings_total': 3420,
                    'featured_menu': '温かけうどん + 揚げ',
                    'price_range': '250円〜500円',
                    'opening_hours': '8:30〜13:30 (定休日: 日・月)',
                    'photo_url': '',
                    'description': 'のどかな田園風景の中に佇む香川うどんの聖地。いりこの芳醇な出汁と、ふんわりモチモチした至高の麺が楽しめます。',
                },
                {
                    'name': '山越うどん (やまごえ)',
                    'address': '香川県綾歌郡綾川町羽床上602-2',
                    'lat': 34.2142,
                    'lng': 133.9214,
                    'place_id': 'ChIJy_yamagoe_ayagawa',
                    'google_rating': 4.3,
                    'google_user_ratings_total': 4890,
                    'featured_menu': 'かまたまうどん (釜玉)',
                    'price_range': '300円〜600円',
                    'opening_hours': '9:00〜13:30 (定休日: 水・日)',
                    'photo_url': '/static/udon/images/kamatama.jpg',
                    'description': '「かまたまうどん」発祥の超有名店。美しい庭園席で、熱々の茹でたて麺に卵と特製出汁醤油を絡めていただきます。',
                },
                {
                    'name': '須崎食料品店',
                    'address': '香川県三豊市高瀬町上麻3778',
                    'lat': 34.1685,
                    'lng': 133.7548,
                    'place_id': 'ChIJs_suzaki_mitoyo',
                    'google_rating': 4.5,
                    'google_user_ratings_total': 2750,
                    'featured_menu': 'しょうゆうどん (冷・温)',
                    'price_range': '280円〜550円',
                    'opening_hours': '9:00〜11:30 (玉がなくなり次第終了)',
                    'photo_url': '',
                    'description': '食料品店の奥で打たれる究極の剛麺うどん。小麦の香りと強烈なコシ、生卵と出汁醤油のシンプルなハーモニーが絶品。',
                },
                {
                    'name': '手打十段 うどんバカ一代',
                    'address': '香川県高松市多賀町1-6-7',
                    'lat': 34.3378,
                    'lng': 134.0573,
                    'place_id': 'ChIJb_bakaichidai_takamatsu',
                    'google_rating': 4.2,
                    'google_user_ratings_total': 5610,
                    'featured_menu': '釜バターうどん',
                    'price_range': '400円〜750円',
                    'opening_hours': '6:00〜18:00 (年中無休)',
                    'photo_url': '/static/udon/images/kamatama.jpg',
                    'description': '朝6時から営業！茹でたて熱々のうどんにバターと黒胡椒、生卵を落とした「釜バターうどん」はまるで和風カルボナーラ。',
                },
                {
                    'name': '日の出製麺所',
                    'address': '香川県坂出市富士見町1-8-5',
                    'lat': 34.3168,
                    'lng': 133.8569,
                    'place_id': 'ChIJh_hinode_sakaide',
                    'google_rating': 4.3,
                    'google_user_ratings_total': 3150,
                    'featured_menu': 'ぬるいうどん + ねぎハサミ切り',
                    'price_range': '150円〜350円',
                    'opening_hours': '11:30〜12:30 (昼の1時間のみ営業)',
                    'photo_url': '',
                    'description': '製麺所直営、1日わずか1時間だけイートイン営業する幻の名店。ネギを自分でハサミで切って入れる体験も名物。',
                },
                {
                    'name': '長田 in 香の香 (ながた いん かのか)',
                    'address': '香川県善通寺市金蔵寺町1180',
                    'lat': 34.2405,
                    'lng': 133.7845,
                    'place_id': 'ChIJn_kanoka_zentsuji',
                    'google_rating': 4.4,
                    'google_user_ratings_total': 3820,
                    'featured_menu': '釜あげうどん (徳利出汁)',
                    'price_range': '350円〜700円',
                    'opening_hours': '9:00〜16:00 (定休日: 水・木)',
                    'photo_url': '/static/udon/images/tempura.jpg',
                    'description': '熱々の陶器徳利に入った濃厚いりこ出汁で味わう「釜あげうどん」の最高峰。ふっくらもっちりした麺が出汁と絡み合います。',
                },
                {
                    'name': 'うどん本陣 山田家 本店',
                    'address': '香川県高松市牟礼町牟礼3186',
                    'lat': 34.3642,
                    'lng': 134.1235,
                    'place_id': 'ChIJy_yamadaya_mure',
                    'google_rating': 4.3,
                    'google_user_ratings_total': 4120,
                    'featured_menu': 'ざるぶっかけ定食',
                    'price_range': '600円〜1,500円',
                    'opening_hours': '10:00〜20:00 (年中無休)',
                    'photo_url': '/static/udon/images/tempura.jpg',
                    'description': '国の登録有形文化財の広大な屋敷と日本庭園で楽しむ絶品香川うどん。揚げたて大海老天ぷらとコシの強い麺が自慢。',
                },
            ]

            shop_objects = {}
            for item in shops_data:
                # Deduplicate if duplicate exists
                existing_shops = Shop.objects.filter(name=item['name'])
                if existing_shops.count() > 1:
                    keep = existing_shops.first()
                    existing_shops.exclude(id=keep.id).delete()
                    shop = keep
                    for k, v in item.items():
                        setattr(shop, k, v)
                    shop.save()
                elif existing_shops.count() == 1:
                    shop = existing_shops.first()
                    for k, v in item.items():
                        setattr(shop, k, v)
                    shop.save()
                else:
                    shop = Shop.objects.create(**item)

                shop_objects[item['name']] = shop
                self.stdout.write(f'  Created/Updated shop: {shop.name}')

            # 3. Create the Main Demo Trip matching Screen 1 and Screen 3
            # Delete any existing demo trips with the same title to ensure clean state
            Trip.objects.filter(title='香川うどん巡礼2026').delete()
            trip = Trip.objects.create(
                title='香川うどん巡礼2026',
                owner=user,
                start_date=date(2026, 6, 13),
                end_date=date(2026, 6, 23),
                is_public=True,
                memo='香川県を代表する名店をめぐる、こだわりのうどん巡礼旅！',
            )

            # Clear existing members and stops for clean seed
            trip.members.all().delete()
            trip.stops.all().delete()

            # Add Trip Members (Screen 1 & 3: 4 members)
            members_data = [
                {'name': '出汁マニア', 'role': 'owner', 'color': '#E67E22', 'icon': '出'},
                {'name': 'さぬき女子', 'role': 'member', 'color': '#C84B31', 'icon': 'さ'},
                {'name': 'うどん太郎', 'role': 'member', 'color': '#2980B9', 'icon': 'う'},
                {'name': '天ぷら奉行', 'role': 'member', 'color': '#27AE60', 'icon': '天'},
            ]
            for m in members_data:
                m_user = User.objects.filter(profile__nickname=m['name']).first()
                TripMember.objects.create(
                    trip=trip,
                    user=m_user,
                    name=m['name'],
                    role=m['role'],
                    avatar_color=m['color'],
                    avatar_icon=m['icon']
                )

            # Add Stops matching Screen 1 (1: がもう, 2: 山越, 3: 須崎)
            stop_shops = [
                (shop_objects['香川うどん (がもううどん)'], 1, '車で18分'),
                (shop_objects['山越うどん (やまごえ)'], 2, '車で18分'),
                (shop_objects['須崎食料品店'], 3, '車で18分'),
            ]
            for shop, order, travel_time in stop_shops:
                TripStop.objects.create(
                    trip=trip,
                    shop=shop,
                    visit_order=order,
                    travel_time_text=travel_time,
                    status='planned',
                )

            # 4. Create Detailed Reviews matching Screen 2
            first_shop = shop_objects['香川うどん (がもううどん)']
            first_shop.reviews.all().delete()

            reviews_data = [
                {
                    'author_name': '会員さん',
                    'author_avatar_color': '#D99B26',
                    'author_avatar_icon': '会',
                    'score_noodle': 9,
                    'score_soup': 10,
                    'score_atmosphere': 9,
                    'score_tempura': 8,
                    'score_cost': 10,
                    'score_total': 4.8,
                    'comment': '香川うどんの味だけで、天ぷらも楽しいのに、恩恵を深く感じています。田園風景を眺めながら食べるかけうどんは唯一無二！',
                    'stamp_type': '香川人選',
                },
                {
                    'author_name': '大員さん',
                    'author_avatar_color': '#2980B9',
                    'author_avatar_icon': '大',
                    'score_noodle': 8,
                    'score_soup': 9,
                    'score_atmosphere': 9,
                    'score_tempura': 9,
                    'score_cost': 10,
                    'score_total': 4.8,
                    'comment': '釜から上がったばかりの麺は程よい弾力と小麦の甘み。出汁を自分でタンクから注ぐセルフスタイルも楽しいです。',
                    'stamp_type': '名店認定',
                },
                {
                    'author_name': '会員さん',
                    'author_avatar_color': '#27AE60',
                    'author_avatar_icon': '会',
                    'score_noodle': 9,
                    'score_soup': 9,
                    'score_atmosphere': 8,
                    'score_tempura': 8,
                    'score_cost': 9,
                    'score_total': 4.7,
                    'comment': 'うどん巡回の最初の一歩でした。朝の澄んだ空気の中で食べる熱々の一杯は感動もの。',
                    'stamp_type': '香川人選',
                }
            ]

            for r in reviews_data:
                Review.objects.create(
                    trip=trip,
                    shop=first_shop,
                    user=user,
                    **r
                )

            # Add reviews for other shops
            for name, s in shop_objects.items():
                if name != '香川うどん (がもううどん)':
                    Review.objects.create(
                        trip=trip,
                        shop=s,
                        user=user,
                        author_name='うどん巡礼マスター',
                        author_avatar_color='#8E44AD',
                        author_avatar_icon='巡',
                        score_noodle=9,
                        score_soup=9,
                        score_atmosphere=8,
                        score_tempura=9,
                        score_cost=9,
                        score_total=4.7,
                        comment=f'{s.name}の看板メニュー「{s.featured_menu}」は感動的な美味しさでした。',
                        stamp_type='香川人選',
                    )

        self.stdout.write(self.style.SUCCESS('Successfully seeded Kagawa Udon data and Demo Trip!'))
