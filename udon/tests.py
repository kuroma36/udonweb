import json
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from udon.models import Shop, Trip, TripMember, TripStop, Review, UserProfile, ShopPhoto, ReviewLike, ReviewComment, Notification, ShopFavorite


class UdonAppTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test_user', password='password123')
        self.profile = UserProfile.objects.create(
            user=self.user,
            nickname='テスト太郎',
            avatar_color='#E67E22',
            favorite_udon='釜玉うどん',
            level_title='見習いうどん人'
        )
        
        self.shop1 = Shop.objects.create(
            name='香川うどん (がもううどん)',
            address='香川県坂出市加茂町420-1',
            lat=34.3015,
            lng=133.8961,
            featured_menu='温かけうどん',
            price_range='250円〜500円',
        )
        self.shop2 = Shop.objects.create(
            name='山越うどん',
            address='香川県綾歌郡綾川町羽床上602-2',
            lat=34.2142,
            lng=133.9214,
            featured_menu='かまたまうどん',
            price_range='300円〜600円',
        )
        self.shop3 = Shop.objects.create(
            name='須崎食料品店',
            address='香川県三豊市高瀬町上麻3778',
            lat=34.1685,
            lng=133.7548,
            featured_menu='しょうゆうどん',
            price_range='280円〜550円',
        )

        self.trip = Trip.objects.create(
            title='香川うどん巡礼2026',
            owner=self.user,
            start_date=date(2026, 6, 13),
            end_date=date(2026, 6, 23),
            is_public=True
        )

        self.member1 = TripMember.objects.create(
            trip=self.trip,
            name='会員さん',
            avatar_color='#E67E22',
            avatar_icon='👩',
            role='owner'
        )

        self.stop1 = TripStop.objects.create(
            trip=self.trip,
            shop=self.shop1,
            visit_order=1,
            travel_time_text='車で18分'
        )
        self.stop2 = TripStop.objects.create(
            trip=self.trip,
            shop=self.shop2,
            visit_order=2,
            travel_time_text='車で18分'
        )
        self.stop3 = TripStop.objects.create(
            trip=self.trip,
            shop=self.shop3,
            visit_order=3,
            travel_time_text='車で18分'
        )

        self.review1 = Review.objects.create(
            trip=self.trip,
            shop=self.shop1,
            user=self.user,
            author_name='会員さん',
            score_noodle=9,
            score_soup=10,
            score_atmosphere=9,
            score_tempura=8,
            score_cost=10,
            score_total=4.8,
            comment='香川うどんの味だけで、天ぷらも楽しいのに...',
            stamp_type='香川人選'
        )

    def test_home_redirects_to_login_if_anonymous(self):
        response = self.client.get(reverse('udon:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_home_redirects_to_trip_map_if_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('udon:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/trips/{self.trip.id}/', response.url)

    def test_name_only_login_and_registration(self):
        """Test simple name-based login and auto profile creation."""
        # 1. Register with new name
        response = self.client.post(reverse('udon:login'), {
            'nickname': '新しい香川うどん人',
            'avatar_color': '#27AE60',
            'favorite_udon': '釜玉うどん',
        })
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.filter(nickname='新しい香川うどん人').first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.favorite_udon, '釜玉うどん')
        self.assertEqual(profile.avatar_color, '#27AE60')

        # 2. Logout and login with same name
        self.client.logout()
        response = self.client.post(reverse('udon:login'), {
            'nickname': '新しい香川うどん人',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_user_switching_and_cache_headers(self):
        """Test switching users directly via login POST even if previously authenticated, and verify never_cache header."""
        # Check never_cache header on login page
        get_res = self.client.get(reverse('udon:login'))
        self.assertEqual(get_res.status_code, 200)
        self.assertIn('no-cache', get_res.headers.get('Cache-Control', ''))

        # Login as User 1
        user1 = User.objects.create_user(username='user1', password='pass')
        UserProfile.objects.create(user=user1, nickname='ユーザー1')
        self.client.force_login(user1)

        # Create User 2
        user2 = User.objects.create_user(username='user2', password='pass')
        UserProfile.objects.create(user=user2, nickname='ユーザー2')

        # Simulate clicking User 2 on login page while already authenticated as User 1
        post_res = self.client.post(reverse('udon:login'), {'user_id': user2.id}, follow=True)
        self.assertEqual(post_res.status_code, 200)

        # Context/request user must now be User 2!
        self.assertEqual(int(self.client.session['_auth_user_id']), user2.id)

    def test_screen_1_trip_map_view_for_owner(self):
        """Screen 1: Verify map route and shop orders for trip owner."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('udon:trip_map', kwargs={'trip_id': self.trip.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '香川うどん巡礼2026')
        self.assertContains(response, '訪問店舗')
        self.assertContains(response, '移動時間')
        self.assertContains(response, '車で')
        self.assertContains(response, '香川うどん (がもううどん)')
        self.assertContains(response, '山越うどん')
        self.assertContains(response, '須崎食料品店')
        self.assertContains(response, 'map-container')
        self.assertContains(response, 'map-current-location-btn')
        self.assertContains(response, 'map-fit-route-btn')

    def test_trip_access_control_for_unauthorized_user(self):
        """Test that user cannot view or edit trips they do not belong to."""
        other_user = User.objects.create_user(username='other_user', password='password123')
        self.client.force_login(other_user)

        # 1. trip_map should redirect to trip_list with error message
        response = self.client.get(reverse('udon:trip_map', kwargs={'trip_id': self.trip.id}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('udon:trip_list'), response.url)

        # 2. trip_edit should redirect to trip_list
        response = self.client.get(reverse('udon:trip_edit', kwargs={'trip_id': self.trip.id}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('udon:trip_list'), response.url)

        # 3. trip_list should NOT contain the unauthorized trip
        response = self.client.get(reverse('udon:trip_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '香川うどん巡礼2026')
        self.assertContains(response, '参加している旅程がありません')

        # 4. API endpoints should return 403 Forbidden
        api_res = self.client.post(
            reverse('udon:api_reorder_stops', kwargs={'trip_id': self.trip.id}),
            data=json.dumps({'stops': []}),
            content_type='application/json'
        )
        self.assertEqual(api_res.status_code, 403)

    def test_trip_accessible_by_invited_member(self):
        """Test that invited member CAN view and edit the trip."""
        invited_user = User.objects.create_user(username='invited_user', password='password123')
        invited_profile = UserProfile.objects.create(
            user=invited_user,
            nickname='招待された人',
            avatar_color='#2980B9'
        )
        # Invite user by nickname
        TripMember.objects.create(
            trip=self.trip,
            name='招待された人',
            role='member'
        )

        self.client.force_login(invited_user)

        # 1. trip_list should display the trip with "参加中" badge
        response = self.client.get(reverse('udon:trip_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '香川うどん巡礼2026')
        self.assertContains(response, '参加中')

        # 2. trip_map should be accessible (200 OK)
        response = self.client.get(reverse('udon:trip_map', kwargs={'trip_id': self.trip.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '香川うどん巡礼2026')

        # 3. trip_edit should be accessible (200 OK)
        response = self.client.get(reverse('udon:trip_edit', kwargs={'trip_id': self.trip.id}))
        self.assertEqual(response.status_code, 200)

    def test_shops_and_comments_require_login(self):
        """Test that shop info and reviews require login (guest or registered user)."""
        # 1. Unauthenticated user is redirected to login for shop list
        response = self.client.get(reverse('udon:shop_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

        # 2. Unauthenticated user is redirected to login for shop detail
        response = self.client.get(reverse('udon:shop_detail', kwargs={'shop_id': self.shop1.id}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

        # 3. Authenticated user (e.g. guest or user) can view shop list
        self.client.force_login(self.user)
        response = self.client.get(reverse('udon:shop_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '香川うどん (がもううどん)')
        self.assertContains(response, '山越うどん')

        # 4. Authenticated user can view shop detail and comments
        response = self.client.get(reverse('udon:shop_detail', kwargs={'shop_id': self.shop1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '香川うどん (がもううどん)')
        self.assertContains(response, '4.8')
        self.assertContains(response, '[麺]')
        self.assertContains(response, '[出汁]')
        self.assertContains(response, 'メンバー評価・コメント')
        self.assertContains(response, '香川うどんの味だけで')

    def test_trip_create_initial_stops_is_empty(self):
        """Test that creating a new trip starts with an empty stop list (no default shops)."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('udon:trip_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'まだ店舗が登録されていません')
        self.assertNotContains(response, '<div class="dnd-stop-item"')

    def test_screen_2_shop_detail_view(self):
        """Screen 2: Verify shop title, photo gallery, 5-axis bars, and member comments."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('udon:shop_detail_in_trip', kwargs={'trip_id': self.trip.id, 'shop_id': self.shop1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '香川うどん (がもううどん)')
        self.assertContains(response, '4.8')
        self.assertContains(response, '[麺]')
        self.assertContains(response, '[出汁]')
        self.assertContains(response, '[店の雰囲気]')
        self.assertContains(response, '[天ぷら]')
        self.assertContains(response, '[コスパ]')
        self.assertContains(response, '投稿写真')
        self.assertContains(response, 'メンバー評価・コメント')
        self.assertContains(response, 'テスト太郎')
        self.assertContains(response, '香川うどんの味だけで')

    def test_screen_3_trip_management_view(self):
        """Screen 3: Verify title, date, memo, members, and DND stop list."""
        self.trip.memo = '朝7時高松駅集合！'
        self.trip.save()

        self.client.force_login(self.user)
        response = self.client.get(reverse('udon:trip_edit', kwargs={'trip_id': self.trip.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '旅行管理作成')
        self.assertContains(response, '香川うどん巡礼2026')
        self.assertContains(response, '巡礼日程')
        self.assertContains(response, '旅のメモ・心得')
        self.assertContains(response, '朝7時高松駅集合！')
        self.assertContains(response, '参加メンバー')
        self.assertContains(response, 'ドラッグ と ドロップ ストップリスト')
        self.assertContains(response, 'うどんの店に行き予定を再建築できるよう。')
        self.assertContains(response, 'dnd-stop-item')

    def test_5_axis_review_submission(self):
        """Test submitting a 5-axis review using logged in user's profile nickname."""
        self.client.force_login(self.user)
        data = {
            'author_name': '入力した仮ネーム',
            'score_total': '4.9',
            'score_noodle': 10,
            'score_soup': 10,
            'score_atmosphere': 8,
            'score_tempura': 9,
            'score_cost': 9,
            'stamp_type': '絶品百選',
            'comment': '喉ごし最高峰の麺といりこ出汁が最高！',
        }
        response = self.client.post(reverse('udon:review_create_in_trip', kwargs={'trip_id': self.trip.id, 'shop_id': self.shop2.id}), data)
        self.assertEqual(response.status_code, 302)
        review = Review.objects.filter(shop=self.shop2, user=self.user).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.author_name, 'テスト太郎')  # Prioritizes login nickname
        self.assertEqual(review.score_noodle, 10)
        self.assertEqual(review.score_soup, 10)

    def test_ajax_reorder_stops_api(self):
        """Test live drag and drop stop reordering API."""
        self.client.force_login(self.user)
        payload = {
            'stops': [
                {'id': self.stop3.id, 'order': 1},
                {'id': self.stop1.id, 'order': 2},
                {'id': self.stop2.id, 'order': 3},
            ]
        }
        response = self.client.post(
            reverse('udon:api_reorder_stops', kwargs={'trip_id': self.trip.id}),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'ok')
        
        self.stop3.refresh_from_db()
        self.stop1.refresh_from_db()
        self.assertEqual(self.stop3.visit_order, 1)
        self.assertEqual(self.stop1.visit_order, 2)

    def test_api_search_shops(self):
        """Test API searching registered shops for map search autocomplete."""
        self.client.force_login(self.user)
        # Search by keyword
        response = self.client.get(reverse('udon:api_search_shops'), {'q': 'がもう'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(any('がもう' in s['name'] for s in data['shops']))

        # Empty query returns initial shops
        response = self.client.get(reverse('udon:api_search_shops'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertGreater(len(data['shops']), 0)

    def test_map_view_has_search_bar_and_preview_card(self):
        """Test that map view includes the top search box and pin preview script."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('udon:trip_map', kwargs={'trip_id': self.trip.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'map-shop-search-input')
        self.assertContains(response, 'この店を旅程に追加')

    def test_profile_edit_page_renders_and_username_immutable(self):
        """Test that profile edit page renders correctly and display name (nickname) & username are read-only."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('udon:profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ユーザー情報の編集')
        self.assertContains(response, self.profile.nickname)
        self.assertContains(response, '変更不可')

        # POST update bio, favorite_udon, etc., and attempt to change nickname and username
        original_nickname = self.profile.nickname
        post_data = {
            'nickname': '香川レジェンド',  # attempt to change display name
            'favorite_udon': '冷やしぶっかけ',
            'avatar_color': '#D99B26',
            'level_title': 'うどん巡礼マスター',
            'bio': '香川のうどんを完全制覇するのが夢です！',
            'username': 'hacked_username',  # attempt to change username
        }
        post_response = self.client.post(reverse('udon:profile_edit'), post_data, follow=True)
        self.assertEqual(post_response.status_code, 200)

        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        # Username and Nickname must remain unchanged (immutable)
        self.assertEqual(self.user.username, 'test_user')
        self.assertEqual(self.profile.nickname, original_nickname)
        # Other profile fields are updated
        self.assertEqual(self.profile.favorite_udon, '冷やしぶっかけ')
        self.assertEqual(self.profile.bio, '香川のうどんを完全制覇するのが夢です！')

        # Test uploading base64 avatar image
        tiny_png_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        post_data2 = {
            'nickname': '香川レジェンド',
            'avatar_base64': tiny_png_base64,
        }
        res2 = self.client.post(reverse('udon:profile_edit'), post_data2, follow=True)
        self.assertEqual(res2.status_code, 200)
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.avatar_image)
        self.assertTrue(bool(self.profile.avatar_image.name))

    def test_trip_member_duplicate_prevention_and_delete(self):
        """Test that duplicate member additions are prevented and members can be deleted."""
        self.client.force_login(self.user)

        # 1. Test adding a member via API
        add_url = reverse('udon:api_add_member', kwargs={'trip_id': self.trip.id})
        res = self.client.post(add_url, {'name': '新規うどん友', 'avatar_color': '#2980B9'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')
        member_id = data['member']['id']

        # Verify User and UserProfile was created automatically
        self.assertTrue(UserProfile.objects.filter(nickname='新規うどん友').exists())
        new_prof = UserProfile.objects.get(nickname='新規うどん友')
        self.assertIsNotNone(new_prof.user)
        self.assertEqual(new_prof.avatar_color, '#2980B9')

        # 2. Test duplicate member addition (same name) - must be rejected
        res_dup = self.client.post(add_url, {'name': '新規うどん友', 'avatar_color': '#2980B9'})
        self.assertEqual(res_dup.status_code, 400)
        self.assertIn('既に参加メンバーに含まれています', res_dup.json()['message'])

        # 3. Test deleting the member
        del_url = reverse('udon:api_delete_member', kwargs={'trip_id': self.trip.id, 'member_id': member_id})
        del_res = self.client.post(del_url)
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()['status'], 'ok')
        self.assertFalse(TripMember.objects.filter(id=member_id).exists())

        # 4. Test deleting owner member - must be forbidden
        owner_member = self.trip.members.filter(role='owner').first()
        if owner_member:
            del_owner_url = reverse('udon:api_delete_member', kwargs={'trip_id': self.trip.id, 'member_id': owner_member.id})
            del_owner_res = self.client.post(del_owner_url)
            self.assertEqual(del_owner_res.status_code, 400)
            self.assertIn('主催者', del_owner_res.json()['message'])
            self.assertTrue(TripMember.objects.filter(id=owner_member.id).exists())

    def test_unrated_shop_and_google_rating_display(self):
        """Test that shops without reviews display '未評価' and show Google Map rating."""
        unrated_shop = Shop.objects.create(
            name='新規未評価うどん店',
            address='香川県高松市1-1-1',
            lat=34.34,
            lng=134.04,
            google_rating=4.4,
            google_user_ratings_total=1200,
        )
        self.assertFalse(unrated_shop.has_reviews)
        self.assertIsNone(unrated_shop.average_score_total)

        self.client.force_login(self.user)

        # 1. Check shop list shows 未評価 and Google rating
        res_list = self.client.get(reverse('udon:shop_list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, '新規未評価うどん店')
        self.assertContains(res_list, '未評価')
        self.assertContains(res_list, '★4.4')

        # 2. Check shop detail shows 未評価 and Google Map Rating Card
        res_detail = self.client.get(reverse('udon:shop_detail', kwargs={'shop_id': unrated_shop.id}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, '未評価')
        self.assertContains(res_detail, 'Google マップ評価')
        self.assertContains(res_detail, '★ 4.4')
        self.assertContains(res_detail, '1200件')
        self.assertContains(res_detail, 'まだアプリ内での詳細評価がありません')

    def test_user_score_parameters_and_deduplication(self):
        """Test individual score parameter tags and deduplicating latest review per user."""
        self.client.force_login(self.user)

        # Create a second review for the same shop by the same user (older one is self.review1)
        older_review = self.review1
        newer_review = Review.objects.create(
            trip=self.trip,
            shop=self.shop1,
            user=self.user,
            author_name='会員さん',
            score_noodle=10,
            score_soup=10,
            score_atmosphere=9,
            score_tempura=10,
            score_cost=10,
            score_total=5.0,
            comment='リピート訪問！相変わらず最高の一杯でした！',
        )

        res = self.client.get(reverse('udon:shop_detail', kwargs={'shop_id': self.shop1.id}))
        self.assertEqual(res.status_code, 200)

        # 1. Check newer review is displayed and older review is deduplicated
        self.assertContains(res, 'リピート訪問！相変わらず最高の一杯でした！')
        self.assertNotContains(res, '香川うどんの味だけで、天ぷらも楽しいのに...')

        # 2. Check user individual score parameters are displayed
        self.assertContains(res, '麺 <strong>10</strong>')
        self.assertContains(res, '出汁 <strong>10</strong>')
        self.assertContains(res, '雰囲気 <strong>9</strong>')

        # 3. Check delete button is rendered for own review
        self.assertContains(res, 'btn-review-delete')

    def test_review_delete_api(self):
        """Test API for deleting own review and forbidding deletion of other user's review."""
        other_user = User.objects.create_user(username='other_user', password='password123')
        other_review = Review.objects.create(
            trip=self.trip,
            shop=self.shop1,
            user=other_user,
            author_name='他ユーザー',
            score_total=4.0,
            comment='他人のレビューです',
        )

        # 1. User cannot delete other_user's review (403 Forbidden)
        self.client.force_login(self.user)
        del_res = self.client.post(reverse('udon:api_delete_review', kwargs={'review_id': other_review.id}))
        self.assertEqual(del_res.status_code, 403)
        self.assertTrue(Review.objects.filter(id=other_review.id).exists())

        # 2. User can delete own review (200 OK)
        del_own_res = self.client.post(reverse('udon:api_delete_review', kwargs={'review_id': self.review1.id}))
        self.assertEqual(del_own_res.status_code, 200)
        self.assertEqual(del_own_res.json()['status'], 'ok')
        self.assertFalse(Review.objects.filter(id=self.review1.id).exists())

    def test_trip_delete_by_owner_keeps_reviews_and_photos(self):
        """Test that trip owner can delete trip, and reviews/photos remain in database."""
        self.client.force_login(self.user)
        trip_id = self.trip.id
        review_id = self.review1.id

        self.assertEqual(self.review1.trip, self.trip)

        # Delete trip via POST
        del_res = self.client.post(reverse('udon:trip_delete', kwargs={'trip_id': trip_id}))
        self.assertEqual(del_res.status_code, 302)
        self.assertRedirects(del_res, reverse('udon:trip_list'))

        # Trip is deleted
        self.assertFalse(Trip.objects.filter(id=trip_id).exists())

        # Review and Shop still exist, review.trip is SET_NULL (None)
        review = Review.objects.filter(id=review_id).first()
        self.assertIsNotNone(review)
        self.assertIsNone(review.trip)
        self.assertTrue(Shop.objects.filter(id=self.shop1.id).exists())

    def test_trip_delete_forbidden_for_non_owner(self):
        """Test that non-owner member cannot delete the trip."""
        non_owner = User.objects.create_user(username='non_owner_user', password='password123')
        TripMember.objects.create(
            trip=self.trip,
            user=non_owner,
            name='一般メンバー',
            role='member'
        )
        self.client.force_login(non_owner)
        trip_id = self.trip.id

        del_res = self.client.post(reverse('udon:trip_delete', kwargs={'trip_id': trip_id}))
        self.assertEqual(del_res.status_code, 302)

        # Trip must NOT be deleted
        self.assertTrue(Trip.objects.filter(id=trip_id).exists())

    def test_shop_default_no_image_and_top_photo_on_review(self):
        """Test that newly created shop defaults to no_image.svg, and posting a review with photo updates shop photo."""
        new_shop = Shop.objects.create(
            name='新規うどん店',
            address='香川県高松市1-1',
            lat=34.34,
            lng=134.04,
            photo_url=''
        )
        # 1. Default photo is no_image.svg
        self.assertEqual(new_shop.display_photo, '/static/udon/images/no_image.svg')
        self.assertFalse(new_shop.has_photo)

        # 2. Post a review with a photo
        self.client.force_login(self.user)
        dummy_image = SimpleUploadedFile(
            name='test_udon.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b',
            content_type='image/gif'
        )
        post_data = {
            'author_name': 'テスト太郎',
            'score_total': 4.9,
            'score_noodle': 9,
            'score_soup': 9,
            'score_atmosphere': 8,
            'score_tempura': 9,
            'score_cost': 9,
            'comment': '写真付きレビュー！最高でした',
            'stamp_type': '香川人選',
            'photo': dummy_image,
        }
        res = self.client.post(reverse('udon:review_create', kwargs={'shop_id': new_shop.id}), post_data)
        self.assertEqual(res.status_code, 302)

        # 3. Shop now has the uploaded photo as its top photo
        new_shop.refresh_from_db()
        self.assertTrue(new_shop.has_photo)
        self.assertNotEqual(new_shop.display_photo, '/static/udon/images/no_image.svg')
        self.assertIn('test_udon', new_shop.display_photo)

        # 4. Detail page renders with photo
        detail_res = self.client.get(reverse('udon:shop_detail', kwargs={'shop_id': new_shop.id}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'test_udon')

        # 5. Delete the review and check fallback to no_image.svg
        rev = new_shop.reviews.first()
        del_res = self.client.post(reverse('udon:api_delete_review', kwargs={'review_id': rev.id}))
        self.assertEqual(del_res.status_code, 200)
        new_shop.refresh_from_db()
        self.assertEqual(new_shop.display_photo, '/static/udon/images/no_image.svg')
        self.assertFalse(new_shop.has_photo)

    def test_review_form_prefill_and_update(self):
        """Verify that existing review data is pre-filled and correctly updated."""
        shop = Shop.objects.create(name='プレフィル確認店', address='高松市瓦町1-1')
        self.client.force_login(self.user)

        # 1. Post initial review
        initial_data = {
            'author_name': '初期投稿者',
            'score_total': 3.7,
            'score_noodle': 6,
            'score_soup': 7,
            'score_atmosphere': 8,
            'score_tempura': 6,
            'score_cost': 7,
            'comment': '前回の初回レビューコメントです',
            'stamp_type': '香川人選',
        }
        res1 = self.client.post(reverse('udon:review_create', kwargs={'shop_id': shop.id}), initial_data)
        self.assertEqual(res1.status_code, 302)
        self.assertEqual(shop.reviews.count(), 1)
        rev = shop.reviews.first()
        self.assertEqual(float(rev.score_total), 3.7)

        # 2. GET review_create should pre-fill with existing review
        get_res = self.client.get(reverse('udon:review_create', kwargs={'shop_id': shop.id}))
        self.assertEqual(get_res.status_code, 200)
        self.assertIn('existing_review', get_res.context)
        self.assertEqual(get_res.context['existing_review'].id, rev.id)
        self.assertContains(get_res, '前回の初回レビューコメントです')
        self.assertContains(get_res, '前回のレビュー内容を表示中')

        # 3. POST updated review should update the same review record
        update_data = {
            'author_name': '初期投稿者',
            'score_total': 4.9,
            'score_noodle': 10,
            'score_soup': 9,
            'score_atmosphere': 9,
            'score_tempura': 9,
            'score_cost': 10,
            'comment': '更新後の絶賛コメントです！',
            'stamp_type': '絶品百選',
        }
        res2 = self.client.post(reverse('udon:review_create', kwargs={'shop_id': shop.id}), update_data)
        self.assertEqual(res2.status_code, 302)
        
        # Verify still only 1 review exists and fields were updated
        self.assertEqual(shop.reviews.count(), 1)
        rev.refresh_from_db()
        self.assertEqual(float(rev.score_total), 4.9)
        self.assertEqual(rev.score_noodle, 10)
        self.assertEqual(rev.comment, '更新後の絶賛コメントです！')
        self.assertEqual(rev.stamp_type, '絶品百選')

    def test_multiple_shop_photos_upload_outside_review(self):
        """Verify uploading multiple photos outside of reviews and gallery display."""
        shop = Shop.objects.create(name='複数写真投稿テスト店', address='丸亀市1-1')
        self.assertEqual(shop.display_photo, '/static/udon/images/no_image.svg')
        self.client.force_login(self.user)

        img1 = SimpleUploadedFile('photo1.jpg', b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b', content_type='image/gif')
        img2 = SimpleUploadedFile('photo2.jpg', b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b', content_type='image/gif')

        # 1. Upload multiple photos
        res = self.client.post(
            reverse('udon:shop_photo_upload', kwargs={'shop_id': shop.id}),
            {'photos': [img1, img2], 'caption': '名物かけうどん二杯'},
        )
        self.assertEqual(res.status_code, 302)
        
        # Verify 2 ShopPhoto instances created
        self.assertEqual(shop.photos.count(), 2)

        # 2. Shop top photo is updated
        shop.refresh_from_db()
        self.assertTrue(shop.has_photo)
        self.assertNotEqual(shop.display_photo, '/static/udon/images/no_image.svg')

        # 3. Shop detail renders both photos in gallery
        detail_res = self.client.get(reverse('udon:shop_detail', kwargs={'shop_id': shop.id}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'photo1')
        self.assertContains(detail_res, 'photo2')

        # 4. Delete one photo
        photo_to_del = shop.photos.first()
        del_res = self.client.post(reverse('udon:api_delete_shop_photo', kwargs={'photo_id': photo_to_del.id}))
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(shop.photos.count(), 1)
        shop.refresh_from_db()
        self.assertTrue(shop.has_photo)

        # 5. Delete remaining photo and verify fallback
        last_photo = shop.photos.first()
        del_res2 = self.client.post(reverse('udon:api_delete_shop_photo', kwargs={'photo_id': last_photo.id}))
        self.assertEqual(del_res2.status_code, 200)
        self.assertEqual(shop.photos.count(), 0)
        shop.refresh_from_db()
        self.assertEqual(shop.display_photo, '/static/udon/images/no_image.svg')
        self.assertFalse(shop.has_photo)

    def test_review_screen_user_photos_and_photo_deletion(self):
        """Verify that review screen lists user photos and allows deleting review photo without deleting review."""
        shop = Shop.objects.create(name='写真管理テスト店', address='坂出市1-1')
        self.client.force_login(self.user)

        # 1. Post a review with a photo
        dummy_img1 = SimpleUploadedFile('rev_photo.jpg', b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b', content_type='image/gif')
        post_data = {
            'author_name': '写真管理太郎',
            'score_total': 4.5,
            'score_noodle': 8,
            'score_soup': 8,
            'score_atmosphere': 8,
            'score_tempura': 8,
            'score_cost': 8,
            'comment': '写真付きレビュー',
            'stamp_type': '香川人選',
            'photo': dummy_img1,
        }
        self.client.post(reverse('udon:review_create', kwargs={'shop_id': shop.id}), post_data)

        # 2. Upload standalone shop photo
        dummy_img2 = SimpleUploadedFile('shop_photo.jpg', b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b', content_type='image/gif')
        self.client.post(reverse('udon:shop_photo_upload', kwargs={'shop_id': shop.id}), {'photos': [dummy_img2], 'caption': '外観写真'})

        # 3. GET review_create should have user_photos with 2 items (1 review photo + 1 shop photo)
        get_res = self.client.get(reverse('udon:review_create', kwargs={'shop_id': shop.id}))
        self.assertEqual(get_res.status_code, 200)
        self.assertIn('user_photos', get_res.context)
        self.assertEqual(len(get_res.context['user_photos']), 2)
        self.assertContains(get_res, '投稿写真の管理')
        self.assertContains(get_res, 'rev_photo')
        self.assertContains(get_res, 'shop_photo')

        # 4. Clear review photo via api_delete_review_photo
        rev = shop.reviews.first()
        self.assertTrue(bool(rev.photo))
        del_photo_res = self.client.post(reverse('udon:api_delete_review_photo', kwargs={'review_id': rev.id}))
        self.assertEqual(del_photo_res.status_code, 200)
        
        # Verify review still exists, but photo is cleared
        rev.refresh_from_db()
        self.assertFalse(bool(rev.photo))
        self.assertEqual(float(rev.score_total), 4.5)
        self.assertEqual(rev.comment, '写真付きレビュー')

        # Verify shop still has photo (fallback to the standalone ShopPhoto)
        shop.refresh_from_db()
        self.assertTrue(shop.has_photo)
        self.assertIn('shop_photo', shop.display_photo)

    def test_review_like_toggle(self):
        """Test toggling likes on reviews."""
        shop = self.shop1
        review = Review.objects.create(
            shop=shop,
            user=self.user,
            author_name='テスト太郎',
            score_total=4.5,
            score_noodle=8,
            score_soup=8,
            score_atmosphere=8,
            score_tempura=8,
            score_cost=8,
            comment='うまい！'
        )

        other_user = User.objects.create_user(username='other_user', password='password123')

        # 1. Anonymous user cannot like (401)
        anon_res = self.client.post(reverse('udon:api_toggle_review_like', kwargs={'review_id': review.id}))
        self.assertEqual(anon_res.status_code, 401)

        # 2. Authenticated user likes review
        self.client.force_login(other_user)
        like_res = self.client.post(reverse('udon:api_toggle_review_like', kwargs={'review_id': review.id}))
        self.assertEqual(like_res.status_code, 200)
        data = like_res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['liked'])
        self.assertEqual(data['like_count'], 1)
        self.assertTrue(ReviewLike.objects.filter(review=review, user=other_user).exists())

        # 3. Authenticated user unlikes review
        unlike_res = self.client.post(reverse('udon:api_toggle_review_like', kwargs={'review_id': review.id}))
        self.assertEqual(unlike_res.status_code, 200)
        data = unlike_res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertFalse(data['liked'])
        self.assertEqual(data['like_count'], 0)
        self.assertFalse(ReviewLike.objects.filter(review=review, user=other_user).exists())

    def test_review_comment_crud(self):
        """Test creating and deleting review comments."""
        shop = self.shop1
        review = Review.objects.create(
            shop=shop,
            user=self.user,
            author_name='テスト太郎',
            score_total=4.5,
            score_noodle=8,
            score_soup=8,
            score_atmosphere=8,
            score_tempura=8,
            score_cost=8,
            comment='本場讃岐の味！'
        )

        other_user = User.objects.create_user(username='commenter', password='password123')
        UserProfile.objects.create(
            user=other_user,
            nickname='うどん好き次郎',
            avatar_color='#3498DB'
        )

        # 1. Anonymous cannot comment (401)
        res = self.client.post(reverse('udon:api_create_review_comment', kwargs={'review_id': review.id}), {'content': '参考になります！'})
        self.assertEqual(res.status_code, 401)

        # 2. Member posts comment
        self.client.force_login(other_user)
        res = self.client.post(reverse('udon:api_create_review_comment', kwargs={'review_id': review.id}), {'content': 'ここ行ってみたかったです！'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['comment_count'], 1)
        self.assertEqual(data['comment']['author_name'], 'うどん好き次郎')
        self.assertEqual(data['comment']['content'], 'ここ行ってみたかったです！')
        comment_id = data['comment']['id']

        # 3. Empty comment gives 400
        empty_res = self.client.post(reverse('udon:api_create_review_comment', kwargs={'review_id': review.id}), {'content': '   '})
        self.assertEqual(empty_res.status_code, 400)

        # 4. Another user cannot delete someone else's comment (403)
        self.client.force_login(self.user)
        del_fail = self.client.post(reverse('udon:api_delete_review_comment', kwargs={'comment_id': comment_id}))
        self.assertEqual(del_fail.status_code, 403)

        # 5. Comment author can delete own comment
        self.client.force_login(other_user)
        del_ok = self.client.post(reverse('udon:api_delete_review_comment', kwargs={'comment_id': comment_id}))
        self.assertEqual(del_ok.status_code, 200)
        del_data = del_ok.json()
        self.assertEqual(del_data['status'], 'ok')
        self.assertEqual(del_data['comment_count'], 0)
        self.assertFalse(ReviewComment.objects.filter(id=comment_id).exists())

    def test_shop_detail_renders_likes_and_comments(self):
        """Test shop_detail view context and rendering for likes and comments."""
        shop = self.shop1
        review = Review.objects.create(
            shop=shop,
            user=self.user,
            author_name='テスト太郎',
            score_total=4.5,
            score_noodle=8,
            score_soup=8,
            score_atmosphere=8,
            score_tempura=8,
            score_cost=8,
            comment='最高の一杯'
        )
        ReviewLike.objects.create(review=review, user=self.user)
        ReviewComment.objects.create(review=review, user=self.user, author_name='テスト太郎', content='返信テスト')

        self.client.force_login(self.user)
        res = self.client.get(reverse('udon:shop_detail', kwargs={'shop_id': shop.id}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'btn-review-like')
        self.assertContains(res, 'is-liked')
        self.assertContains(res, 'btn-review-comment-toggle')
        self.assertContains(res, '返信テスト')

    def test_like_notification_flow(self):
        """Test notification generation on review like and self-like exclusion."""
        shop = self.shop1
        author = self.user
        liker = User.objects.create_user(username='liker_user', password='password123')
        UserProfile.objects.create(user=liker, nickname='いいね花子', avatar_color='#E74C3C')

        review = Review.objects.create(
            shop=shop,
            user=author,
            author_name='テスト太郎',
            score_total=4.5,
            score_noodle=8,
            score_soup=8,
            score_atmosphere=8,
            score_tempura=8,
            score_cost=8,
            comment='うどん最高！'
        )

        # 1. Author liking their own review does NOT create notification
        self.client.force_login(author)
        self.client.post(reverse('udon:api_toggle_review_like', kwargs={'review_id': review.id}))
        self.assertEqual(Notification.objects.filter(recipient=author).count(), 0)

        # 2. Another user likes author's review -> notification created
        self.client.force_login(liker)
        self.client.post(reverse('udon:api_toggle_review_like', kwargs={'review_id': review.id}))
        self.assertEqual(Notification.objects.filter(recipient=author, notification_type='like').count(), 1)
        notif = Notification.objects.filter(recipient=author, notification_type='like').first()
        self.assertIn('いいね花子', notif.message)
        self.assertIn(shop.name, notif.message)
        self.assertFalse(notif.is_read)

        # 3. Liker unlikes review -> unread notification is removed
        self.client.post(reverse('udon:api_toggle_review_like', kwargs={'review_id': review.id}))
        self.assertEqual(Notification.objects.filter(recipient=author, notification_type='like', is_read=False).count(), 0)

    def test_comment_notification_flow(self):
        """Test notification generation on review comment."""
        shop = self.shop1
        author = self.user
        commenter = User.objects.create_user(username='commenter_2', password='password123')
        UserProfile.objects.create(user=commenter, nickname='コメント次郎', avatar_color='#2ECC71')

        review = Review.objects.create(
            shop=shop,
            user=author,
            author_name='テスト太郎',
            score_total=4.5,
            score_noodle=8,
            score_soup=8,
            score_atmosphere=8,
            score_tempura=8,
            score_cost=8,
            comment='絶品出汁！'
        )

        # 1. Author commenting on their own review does NOT notify themselves
        self.client.force_login(author)
        self.client.post(reverse('udon:api_create_review_comment', kwargs={'review_id': review.id}), {'content': '自己返信テスト'})
        self.assertEqual(Notification.objects.filter(recipient=author, notification_type='comment').count(), 0)

        # 2. Another user comments on author's review -> notification created
        self.client.force_login(commenter)
        self.client.post(reverse('udon:api_create_review_comment', kwargs={'review_id': review.id}), {'content': '私もそう思います！'})
        self.assertEqual(Notification.objects.filter(recipient=author, notification_type='comment').count(), 1)
        notif = Notification.objects.filter(recipient=author, notification_type='comment').first()
        self.assertIn('コメント次郎', notif.message)
        self.assertIn('私もそう思います！', notif.message)

    def test_notification_apis_and_read_state(self):
        """Test fetching, reading, and marking all notifications read."""
        user = self.user
        sender = User.objects.create_user(username='sender_user', password='password123')
        UserProfile.objects.create(user=sender, nickname='通知送子', avatar_color='#9B59B6')

        n1 = Notification.objects.create(
            recipient=user,
            sender=sender,
            notification_type='like',
            message='通知1'
        )
        n2 = Notification.objects.create(
            recipient=user,
            sender=sender,
            notification_type='comment',
            message='通知2'
        )

        # 1. Unauthenticated request gives 401
        anon_res = self.client.get(reverse('udon:api_get_notifications'))
        self.assertEqual(anon_res.status_code, 401)

        # 2. Authenticated get
        self.client.force_login(user)
        res = self.client.get(reverse('udon:api_get_notifications'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['unread_count'], 2)
        self.assertEqual(len(data['notifications']), 2)

        # 3. Mark single notification as read
        read_res = self.client.post(reverse('udon:api_mark_notification_read', kwargs={'notification_id': n1.id}))
        self.assertEqual(read_res.status_code, 200)
        self.assertEqual(read_res.json()['unread_count'], 1)
        n1.refresh_from_db()
        self.assertTrue(n1.is_read)

        # 4. Mark all as read
        all_res = self.client.post(reverse('udon:api_mark_all_notifications_read'))
        self.assertEqual(all_res.status_code, 200)
        self.assertEqual(all_res.json()['unread_count'], 0)
        n2.refresh_from_db()
        self.assertTrue(n2.is_read)

    def test_shop_favorite_api_and_memos(self):
        # 1. Anonymous request gives 401
        url = reverse('udon:api_toggle_shop_favorite', kwargs={'shop_id': self.shop1.id})
        anon_res = self.client.post(url, data=json.dumps({'action': 'save', 'reason': '最高'}), content_type='application/json')
        self.assertEqual(anon_res.status_code, 401)

        # 2. Authenticated user saves favorite with memo
        self.client.force_login(self.user)
        save_res = self.client.post(url, data=json.dumps({'action': 'save', 'reason': 'かけうどんとゲソ天が絶品！'}), content_type='application/json')
        self.assertEqual(save_res.status_code, 200)
        data = save_res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['is_favorited'])
        self.assertEqual(data['reason'], 'かけうどんとゲソ天が絶品！')

        fav = ShopFavorite.objects.get(user=self.user, shop=self.shop1)
        self.assertEqual(fav.reason, 'かけうどんとゲソ天が絶品！')

        # 3. Update reason
        update_res = self.client.post(url, data=json.dumps({'action': 'save', 'reason': 'ひやあつが一番うまい'}), content_type='application/json')
        self.assertEqual(update_res.status_code, 200)
        fav.refresh_from_db()
        self.assertEqual(fav.reason, 'ひやあつが一番うまい')

        # 4. Delete favorite
        del_res = self.client.post(url, data=json.dumps({'action': 'delete'}), content_type='application/json')
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()['status'], 'ok')
        self.assertFalse(ShopFavorite.objects.filter(user=self.user, shop=self.shop1).exists())

    def test_shop_list_favorites_tab(self):
        self.client.force_login(self.user)
        # Create a favorite for shop2
        ShopFavorite.objects.create(user=self.user, shop=self.shop2, reason='釜玉発祥の地！')

        # Request default list (all shops)
        res_all = self.client.get(reverse('udon:shop_list'))
        self.assertEqual(res_all.status_code, 200)
        self.assertContains(res_all, self.shop1.name)
        self.assertContains(res_all, self.shop2.name)
        self.assertEqual(res_all.context['favorites_count'], 1)

        # Request favorites tab
        res_fav = self.client.get(reverse('udon:shop_list') + '?tab=favorites')
        self.assertEqual(res_fav.status_code, 200)
        self.assertContains(res_fav, self.shop2.name)
        self.assertContains(res_fav, '釜玉発祥の地！')
        self.assertNotContains(res_fav, self.shop1.name)

    def test_profile_edit_has_favorites_link_and_count(self):
        self.client.force_login(self.user)
        ShopFavorite.objects.create(user=self.user, shop=self.shop1, reason='がもう最高')
        ShopFavorite.objects.create(user=self.user, shop=self.shop2, reason='山越最高')

        res = self.client.get(reverse('udon:profile_edit'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['favorites_count'], 2)
        self.assertContains(res, 'お気に入りうどん店舗一覧')
        self.assertContains(res, 'tab=favorites')

    def test_quick_login_order_by_recent_use(self):
        from django.utils import timezone
        import datetime
        u1 = User.objects.create_user(username='recent_u1')
        p1 = UserProfile.objects.create(user=u1, nickname='一番目')
        u1.last_login = timezone.now() - datetime.timedelta(hours=2)
        u1.save()

        u2 = User.objects.create_user(username='recent_u2')
        p2 = UserProfile.objects.create(user=u2, nickname='二番目')
        u2.last_login = timezone.now() - datetime.timedelta(minutes=5)
        u2.save()

        # Login page should list u2 first, then u1
        res = self.client.get(reverse('udon:login'))
        self.assertEqual(res.status_code, 200)
        profiles = list(res.context['existing_profiles'])
        profile_users = [p.user.username for p in profiles]
        self.assertIn('recent_u2', profile_users)
        self.assertIn('recent_u1', profile_users)
        self.assertLess(profile_users.index('recent_u2'), profile_users.index('recent_u1'))





