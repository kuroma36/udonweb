import json
from datetime import date, time, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from travel.models import TravelTrip, TravelDay, TravelStop


class TravelAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.other_user = User.objects.create_user(username='other', password='password123')

        from udon.models import UserProfile
        UserProfile.objects.create(user=self.user1, nickname='たびたろう', avatar_color='#0284C7')
        UserProfile.objects.create(user=self.user2, nickname='たびじろう', avatar_color='#0D9488')

        # 3日間の旅行
        self.trip = TravelTrip.objects.create(
            title='北海道3泊4日 絶景ドライブ旅',
            destination='北海道',
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 3),
            cover_preset='hokkaido',
            description='富良野のラベンダーと美瑛の丘をめぐるドライブ旅',
            created_by=self.user1
        )
        self.trip.members.add(self.user2)
        self.trip.ensure_days()

    def test_ensure_days_creates_exact_number_of_days(self):
        """旅行期間（3日間）に応じて Day 1, Day 2, Day 3 が自動作成されること"""
        days = self.trip.days.all()
        self.assertEqual(days.count(), 3)
        self.assertEqual(days[0].day_number, 1)
        self.assertEqual(days[0].date, date(2026, 7, 1))
        self.assertEqual(days[1].day_number, 2)
        self.assertEqual(days[1].date, date(2026, 7, 2))
        self.assertEqual(days[2].day_number, 3)
        self.assertEqual(days[2].date, date(2026, 7, 3))

    def test_calculate_transport_duration(self):
        """案1: 出発時刻と到着時刻から所要時間が正しく自動計算されること"""
        day1 = self.trip.days.first()
        stop = TravelStop.objects.create(
            day=day1,
            order=1,
            name='羽田空港 第1ターミナル',
            category='transport',
            transport_mode='flight',
            transport_departure_time=time(9, 20),
            transport_arrival_time=time(10, 55),
            transport_memo='ANA 55便 24A席'
        )
        duration_text = stop.calculate_transport_duration()
        self.assertEqual(duration_text, '1時間35分')

    def test_trip_access_permissions(self):
        """作成者とメンバーは閲覧可能、第三者ユーザーは拒否されること"""
        url = reverse('travel:trip_detail', kwargs={'trip_id': self.trip.id})

        # 1. 未ログイン -> travel:login へリダイレクト (/travel/login/?next=...)
        res_anon = self.client.get(url)
        self.assertEqual(res_anon.status_code, 302)
        self.assertTrue(res_anon.headers.get('Location').startswith('/travel/login/'))

        # 2. 作成者 -> 200 OK
        self.client.force_login(self.user1)
        res_creator = self.client.get(url)
        self.assertEqual(res_creator.status_code, 200)

        # 3. 参加メンバー -> 200 OK
        self.client.force_login(self.user2)
        res_member = self.client.get(url)
        self.assertEqual(res_member.status_code, 200)

        # 4. 第三者 -> リダイレクト (エラーメッセージ付き)
        self.client.force_login(self.other_user)
        res_other = self.client.get(url)
        self.assertEqual(res_other.status_code, 302)

    def test_trip_list_and_create(self):
        """旅行一覧画面の表示と新規作成フロー"""
        self.client.force_login(self.user1)

        # 一覧画面
        res_list = self.client.get(reverse('travel:trip_list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, '北海道3泊4日 絶景ドライブ旅')

        # 新規作成画面 GET
        res_create_get = self.client.get(reverse('travel:trip_create'))
        self.assertEqual(res_create_get.status_code, 200)
        self.assertContains(res_create_get, '新しい旅を計画する')

        # 編集画面 GET
        res_edit_get = self.client.get(reverse('travel:trip_edit', kwargs={'trip_id': self.trip.id}))
        self.assertEqual(res_edit_get.status_code, 200)
        self.assertContains(res_edit_get, '旅行情報の編集')

        # 新規作成 POST
        create_data = {
            'title': '京都週末紅葉めぐり',
            'destination': '京都府',
            'start_date': '2026-11-14',
            'end_date': '2026-11-15',
            'cover_preset': 'kyoto',
            'description': '清水寺と嵐山を散策',
        }
        res_create = self.client.post(reverse('travel:trip_create'), data=create_data)
        self.assertEqual(res_create.status_code, 302)
        new_trip = TravelTrip.objects.get(title='京都週末紅葉めぐり')
        self.assertEqual(new_trip.duration_days, 2)
        self.assertEqual(new_trip.days.count(), 2)

    def test_api_add_and_delete_stop(self):
        """APIによるスポットの追加と削除"""
        self.client.force_login(self.user1)
        day1 = self.trip.days.first()

        # スポット追加
        add_url = reverse('travel:api_add_stop', kwargs={'trip_id': self.trip.id})
        add_data = {
            'day_id': day1.id,
            'name': '小樽運河',
            'category': 'sightseeing',
            'address': '北海道小樽市港町',
            'lat': '43.1907',
            'lng': '141.0021',
            'arrival_time': '14:30',
            'stay_duration': '60分',
            'memo': '夕暮れのガス灯が綺麗',
            'transport_mode': 'car',
        }
        res_add = self.client.post(add_url, data=add_data)
        self.assertEqual(res_add.status_code, 200)
        data = res_add.json()
        self.assertEqual(data['status'], 'ok')

        stop = TravelStop.objects.get(name='小樽運河')
        self.assertEqual(stop.order, 1)
        self.assertEqual(stop.arrival_time, time(14, 30))

        # スポット削除
        del_url = reverse('travel:api_delete_stop', kwargs={'trip_id': self.trip.id, 'stop_id': stop.id})
        res_del = self.client.post(del_url)
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(TravelStop.objects.filter(id=stop.id).exists())

    def test_api_add_stop_manual_name_and_fallback_day(self):
        """サジェストを使わず手動で文字入力（例: 札幌）したスポット追加やday_id省略時のフォールバック"""
        self.client.force_login(self.user1)
        add_url = reverse('travel:api_add_stop', kwargs={'trip_id': self.trip.id})

        # 1. 座標なし・day_idなしの手動テキスト「札幌」の追加
        res1 = self.client.post(add_url, data={'name': '札幌'})
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1['status'], 'ok')
        stop1 = TravelStop.objects.get(name='札幌')
        self.assertEqual(stop1.day, self.trip.days.first())
        self.assertIsNone(stop1.latitude)

        # 2. 名前未入力時のバリデーションエラーがJSONで返ること（HTML 404/500にならないこと）
        res_err = self.client.post(add_url, data={'name': ''})
        self.assertEqual(res_err.status_code, 400)
        data_err = res_err.json()
        self.assertEqual(data_err['status'], 'error')
        self.assertIn('スポット名を入力してください', data_err['message'])

    def test_api_update_transport_auto_calculates(self):
        """APIによる交通手段設定の更新と所要時間の自動計算（案1の検証）"""
        self.client.force_login(self.user1)
        day1 = self.trip.days.first()
        stop = TravelStop.objects.create(
            day=day1,
            order=1,
            name='東京駅',
            category='transport'
        )

        update_url = reverse('travel:api_update_transport', kwargs={'trip_id': self.trip.id, 'stop_id': stop.id})
        update_data = {
            'transport_mode': 'train',
            'transport_departure_time': '08:30',
            'transport_arrival_time': '10:45',
            'transport_memo': 'のぞみ15号 7号車12A',
        }
        res_update = self.client.post(update_url, data=update_data)
        self.assertEqual(res_update.status_code, 200)
        data = res_update.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['transport_time_text'], '2時間15分')
        self.assertEqual(data['transport_memo'], 'のぞみ15号 7号車12A')

        stop.refresh_from_db()
        self.assertEqual(stop.transport_time_text, '2時間15分')

    def test_trip_guide_view(self):
        """旅のしおり画面（/guide/）が正常に表示されること"""
        self.client.force_login(self.user1)
        guide_url = reverse('travel:trip_guide', kwargs={'trip_id': self.trip.id})
        res_guide = self.client.get(guide_url)
        self.assertEqual(res_guide.status_code, 200)
        self.assertContains(res_guide, '旅のしおり')
        self.assertContains(res_guide, '北海道3泊4日 絶景ドライブ旅')

    def test_travel_login_view_and_quick_login(self):
        """たびしお専用ログイン画面の表示とワンタップ即時ログイン"""
        login_url = reverse('travel:login')
        res_get = self.client.get(login_url)
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, 'たびしお')
        self.assertContains(res_get, '登録済みのトラベラー')

        # チップからのワンタップログイン
        res_quick = self.client.post(login_url, data={'user_id': self.user1.id, 'next': '/travel/trips/'})
        self.assertEqual(res_quick.status_code, 302)
        self.assertEqual(res_quick.headers.get('Location'), '/travel/trips/')

    def test_guest_mode(self):
        """ゲストモードでワンタップ体験ログイン"""
        guest_url = reverse('travel:guest_mode') + '?next=/travel/trips/'
        res_guest = self.client.get(guest_url)
        self.assertEqual(res_guest.status_code, 302)
        self.assertEqual(res_guest.headers.get('Location'), '/travel/trips/')

    def test_stop_detail_view(self):
        """スポット個別詳細画面（/stops/<id>/）の表示とGoogleレビュー枠"""
        self.client.force_login(self.user1)
        day1 = self.trip.days.first()
        stop = TravelStop.objects.create(
            day=day1,
            order=1,
            name='旭山動物園',
            category='sightseeing',
            address='北海道旭川市東旭川町倉沼',
            memo='ペンギンの散歩が名物'
        )
        url = reverse('travel:stop_detail', kwargs={'trip_id': self.trip.id, 'stop_id': stop.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '旭山動物園')
        self.assertContains(res, 'たびしお')
        self.assertContains(res, 'Google マップのクチコミ')
        self.assertContains(res, '写真ギャラリー')

    def test_stop_photo_upload_and_delete(self):
        """スポット詳細画面での写真アップロードと削除"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from travel.models import TravelStopPhoto

        self.client.force_login(self.user1)
        day1 = self.trip.days.first()
        stop = TravelStop.objects.create(
            day=day1,
            order=1,
            name='美瑛 青い池',
            category='sightseeing'
        )
        upload_url = reverse('travel:api_upload_stop_photo', kwargs={'trip_id': self.trip.id, 'stop_id': stop.id})
        
        # 1x1 GIF dummy image
        tiny_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        photo_file = SimpleUploadedFile('test_photo.gif', tiny_gif, content_type='image/gif')

        res_upload = self.client.post(upload_url, data={
            'photos': [photo_file],
            'caption': 'エメラルドグリーンの池！'
        })
        self.assertEqual(res_upload.status_code, 302)
        
        photo = TravelStopPhoto.objects.filter(stop=stop).first()
        self.assertIsNotNone(photo)
        self.assertEqual(photo.caption, 'エメラルドグリーンの池！')
        self.assertEqual(photo.user, self.user1)

        # 削除
        delete_url = reverse('travel:api_delete_stop_photo', kwargs={
            'trip_id': self.trip.id,
            'stop_id': stop.id,
            'photo_id': photo.id
        })
        res_delete = self.client.post(delete_url)
        self.assertEqual(res_delete.status_code, 302)
        self.assertFalse(TravelStopPhoto.objects.filter(id=photo.id).exists())

    def test_hotel_sync_next_day_start_and_dual_delete(self):
        """宿設定時の翌日スタート自動登録および連動削除のテスト"""
        self.client.force_login(self.user1)
        day1 = self.trip.days.get(day_number=1)
        day2 = self.trip.days.get(day_number=2)

        # Day 2 に既存スポットを事前に登録（巡回順 1, 2）
        stop_d2_1 = TravelStop.objects.create(day=day2, order=1, name='富良野ファーム', category='sightseeing')
        stop_d2_2 = TravelStop.objects.create(day=day2, order=2, name='美瑛パッチワークの路', category='sightseeing')

        # 1. Day 1 に「宿泊（ホテル・宿）」を追加（sync_next_day=true）
        add_url = reverse('travel:api_add_stop', kwargs={'trip_id': self.trip.id})
        hotel_data = {
            'day_id': day1.id,
            'name': '登別グランドホテル',
            'category': 'hotel',
            'address': '北海道登別市温泉町',
            'lat': '42.5123',
            'lng': '141.1345',
            'arrival_time': '17:00',
            'sync_next_day': 'true',
        }
        res = self.client.post(add_url, data=hotel_data)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')

        # Day 1 にホテルが追加されていること
        hotel_day1 = TravelStop.objects.get(day=day1, name='登別グランドホテル')
        self.assertEqual(hotel_day1.order, 1)

        # Day 2 の先頭（order=1）に同じホテルが自動登録されていること
        hotel_day2 = TravelStop.objects.get(day=day2, name='登別グランドホテル')
        self.assertEqual(hotel_day2.order, 1)
        self.assertEqual(hotel_day2.category, 'hotel')
        self.assertEqual(hotel_day2.address, '北海道登別市温泉町')

        # 相互に paired_stop が設定されていること
        self.assertEqual(hotel_day1.paired_stop, hotel_day2)
        self.assertEqual(hotel_day2.paired_stop, hotel_day1)

        # Day 2 の既存スポットが order=2, 3 に繰り下がっていること
        stop_d2_1.refresh_from_db()
        stop_d2_2.refresh_from_db()
        self.assertEqual(stop_d2_1.order, 2)
        self.assertEqual(stop_d2_2.order, 3)

        # 2. Day 1 のホテルを削除 -> Day 2 のホテルも連動削除され、Day 2 の order が再採番されること
        del_url = reverse('travel:api_delete_stop', kwargs={'trip_id': self.trip.id, 'stop_id': hotel_day1.id})
        res_del = self.client.post(del_url)
        self.assertEqual(res_del.status_code, 200)
        data_del = res_del.json()
        self.assertTrue(data_del['deleted_paired'])

        # 双方とも DB から削除されていること
        self.assertFalse(TravelStop.objects.filter(id=hotel_day1.id).exists())
        self.assertFalse(TravelStop.objects.filter(id=hotel_day2.id).exists())

        # Day 2 の残りのスポットが order=1, 2 に繰り上がって再採番されていること
        stop_d2_1.refresh_from_db()
        stop_d2_2.refresh_from_db()
        self.assertEqual(stop_d2_1.order, 1)
        self.assertEqual(stop_d2_2.order, 2)

    def test_hotel_delete_from_next_day_dual_deletes(self):
        """Day 2 のスタート宿側を削除した場合も連動して Day 1 の宿が削除されること"""
        self.client.force_login(self.user1)
        day1 = self.trip.days.get(day_number=1)
        day2 = self.trip.days.get(day_number=2)

        add_url = reverse('travel:api_add_stop', kwargs={'trip_id': self.trip.id})
        hotel_data = {
            'day_id': day1.id,
            'name': '札幌グランドホテル',
            'category': 'hotel',
            'sync_next_day': 'true',
        }
        res = self.client.post(add_url, data=hotel_data)
        self.assertEqual(res.status_code, 200)

        hotel_day1 = TravelStop.objects.get(day=day1, name='札幌グランドホテル')
        hotel_day2 = TravelStop.objects.get(day=day2, name='札幌グランドホテル')

        # Day 2 側から削除
        del_url = reverse('travel:api_delete_stop', kwargs={'trip_id': self.trip.id, 'stop_id': hotel_day2.id})
        res_del = self.client.post(del_url)
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()['deleted_paired'])

        self.assertFalse(TravelStop.objects.filter(id=hotel_day1.id).exists())
        self.assertFalse(TravelStop.objects.filter(id=hotel_day2.id).exists())
