from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime


class TravelTrip(models.Model):
    """旅行全体の基本情報・日程・共同メンバー"""
    PRESET_COVERS = [
        ('hokkaido', '北海道・自然'),
        ('kyoto', '京都・古都'),
        ('okinawa', '沖縄・リゾートビーチ'),
        ('tokyo', '東京・アーバン夜景'),
        ('fuji', '富士山・温泉'),
    ]

    title = models.CharField('旅行タイトル', max_length=120)
    destination = models.CharField('主な旅行先・エリア', max_length=120, blank=True)
    start_date = models.DateField('開始日', default=timezone.now)
    end_date = models.DateField('終了日', default=timezone.now)
    cover_image = models.ImageField('カバー写真', upload_to='travel/covers/', blank=True, null=True)
    cover_preset = models.CharField('プリセット写真', max_length=50, choices=PRESET_COVERS, default='hokkaido')
    description = models.TextField('旅行のテーマ・メモ', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_travel_trips', verbose_name='作成者')
    members = models.ManyToManyField(User, related_name='travel_trips', blank=True, verbose_name='参加メンバー')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '旅行'
        verbose_name_plural = '旅行一覧'
        ordering = ['-start_date', '-created_at']

    def __str__(self):
        return self.title

    @property
    def duration_days(self):
        """旅行の日数を計算"""
        if self.start_date and self.end_date and self.end_date >= self.start_date:
            return (self.end_date - self.start_date).days + 1
        return 1

    def is_accessible_by(self, user):
        """指定ユーザーが閲覧・編集可能かを判定"""
        if not user.is_authenticated:
            return False
        if user == self.created_by or user.is_staff or user.is_superuser:
            return True
        return self.members.filter(id=user.id).exists()

    def ensure_days(self):
        """旅行の開始日〜終了日に基づいて TravelDay を自動生成・同期"""
        days_count = self.duration_days
        current_days = {day.day_number: day for day in self.days.all()}

        for i in range(1, days_count + 1):
            day_date = self.start_date + timedelta(days=i - 1) if self.start_date else None
            if i in current_days:
                day = current_days[i]
                if day.date != day_date:
                    day.date = day_date
                    day.save()
            else:
                TravelDay.objects.create(
                    trip=self,
                    day_number=i,
                    date=day_date,
                    title=f'Day {i}'
                )

        # 期間短縮等で余分になった日のストップは最終日にマージするか保持
        # ここでは余分な空の日のみ削除
        for num, day in current_days.items():
            if num > days_count and not day.stops.exists():
                day.delete()


class TravelDay(models.Model):
    """旅行内の日別スケジュール（Day 1, Day 2...）"""
    trip = models.ForeignKey(TravelTrip, on_delete=models.CASCADE, related_name='days', verbose_name='旅行')
    day_number = models.PositiveIntegerField('日程番号', default=1)
    date = models.DateField('日付', null=True, blank=True)
    title = models.CharField('日程タイトル・テーマ', max_length=120, blank=True)
    memo = models.TextField('その日のメモ', blank=True)

    class Meta:
        verbose_name = '日程'
        verbose_name_plural = '日程一覧'
        ordering = ['day_number']
        unique_together = ('trip', 'day_number')

    def __str__(self):
        date_str = f" ({self.date.strftime('%m/%d')})" if self.date else ""
        return f"{self.trip.title} - Day {self.day_number}{date_str}"

    @property
    def ordered_stops(self):
        return self.stops.all().order_by('order', 'id')


class TravelStop(models.Model):
    """各日程における立ち寄りスポット＆次スポットへの移動ダイヤ情報"""
    CATEGORY_CHOICES = [
        ('sightseeing', '観光・絶景'),
        ('gourmet', 'グルメ・カフェ'),
        ('hotel', '宿泊（ホテル・宿）'),
        ('activity', 'アクティビティ・体験'),
        ('transport', '交通拠点（駅・空港・港）'),
        ('other', 'その他スポット'),
    ]

    TRANSPORT_CHOICES = [
        ('car', '🚗 車 / レンタカー'),
        ('train', '🚃 電車 / 新幹線'),
        ('flight', '✈️ 飛行機'),
        ('bus', '🚌 バス'),
        ('walk', '🚶 徒歩'),
        ('boat', '🚢 船・フェリー'),
    ]

    day = models.ForeignKey(TravelDay, on_delete=models.CASCADE, related_name='stops', verbose_name='日程')
    order = models.PositiveIntegerField('巡回順', default=1)
    name = models.CharField('スポット名', max_length=200)
    category = models.CharField('カテゴリ', max_length=30, choices=CATEGORY_CHOICES, default='sightseeing')
    address = models.CharField('住所', max_length=300, blank=True)
    latitude = models.FloatField('緯度', null=True, blank=True)
    longitude = models.FloatField('経度', null=True, blank=True)
    google_place_id = models.CharField('Google Place ID', max_length=200, blank=True)
    photo_url = models.URLField('写真URL', max_length=1000, blank=True)
    photo_image = models.ImageField('アップロード写真', upload_to='travel/stops/', blank=True, null=True)

    # 滞在予定・時間
    arrival_time = models.TimeField('到着予定時刻', null=True, blank=True)
    departure_time = models.TimeField('出発予定時刻', null=True, blank=True)
    stay_duration = models.CharField('滞在予定時間', max_length=50, blank=True)
    memo = models.TextField('スポットメモ・予約情報', blank=True)

    # 次のスポットへの移動手段情報（案1）
    transport_mode = models.CharField('次のスポットへの移動手段', max_length=20, choices=TRANSPORT_CHOICES, default='car')
    transport_departure_time = models.TimeField('移動出発時刻', null=True, blank=True)
    transport_arrival_time = models.TimeField('移動到着時刻', null=True, blank=True)
    transport_time_text = models.CharField('所要時間目安', max_length=100, blank=True)
    transport_memo = models.CharField('便名・列車名・座席メモ', max_length=300, blank=True)

    # 宿泊連動スポット（前日・翌日の宿泊スタート連動）
    paired_stop = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='paired_from', verbose_name='連動スポット')

    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '立ち寄りスポット'
        verbose_name_plural = '立ち寄りスポット一覧'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.day} - {self.order}. {self.name}"

    def calculate_transport_duration(self):
        """出発時刻と到着時刻から所要時間テキストを自動計算"""
        if self.transport_departure_time and self.transport_arrival_time:
            t1 = datetime.combine(timezone.now().date(), self.transport_departure_time)
            t2 = datetime.combine(timezone.now().date(), self.transport_arrival_time)
            if t2 < t1:  # 日跨ぎの場合
                t2 += timedelta(days=1)
            diff_minutes = int((t2 - t1).total_seconds() / 60)
            hours = diff_minutes // 60
            minutes = diff_minutes % 60
            if hours > 0 and minutes > 0:
                return f"{hours}時間{minutes}分"
            elif hours > 0:
                return f"{hours}時間"
            else:
                return f"{minutes}分"
        return self.transport_time_text or ''


class TravelStopPhoto(models.Model):
    """各スポットに投稿された思い出写真"""
    stop = models.ForeignKey(TravelStop, on_delete=models.CASCADE, related_name='photos', verbose_name='対象スポット')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='travel_stop_photos', verbose_name='投稿者')
    image = models.ImageField('写真', upload_to='travel/stop_photos/')
    caption = models.CharField('写真のメモ・キャプション', max_length=200, blank=True)
    created_at = models.DateTimeField('投稿日時', auto_now_add=True)

    class Meta:
        verbose_name = 'スポット写真'
        verbose_name_plural = 'スポット写真一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.stop.name} - {self.user.username} ({self.created_at.strftime('%Y/%m/%d')})"


class TravelProfile(models.Model):
    """たびしお（旅ナビ）専用のユーザープロフィール"""
    AVATAR_ICON_CHOICES = [
        ('traveler', 'バックパッカー'),
        ('camera', 'フォトグラファー'),
        ('plane', 'ジェットセッター'),
        ('car', 'ロードトリッパー'),
        ('train', '鉄道マニア'),
        ('camp', 'キャンパー'),
        ('food', 'グルメ探訪家'),
        ('relax', '温泉・癒やし'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='travel_profile', verbose_name='ユーザー')
    nickname = models.CharField('ニックネーム', max_length=50)
    avatar_color = models.CharField('アバター色', max_length=20, default='#0284C7')
    avatar_icon = models.CharField('アバターアイコン', max_length=30, choices=AVATAR_ICON_CHOICES, default='traveler')
    bio = models.TextField('自己紹介・旅スタイル', blank=True)
    is_email_verified = models.BooleanField('メール認証完了', default=False)
    email_verified_at = models.DateTimeField('認証完了日時', null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = 'たびしおプロフィール'
        verbose_name_plural = 'たびしおプロフィール一覧'

    def __str__(self):
        status = '✓認証済' if self.is_email_verified else '⏳未認証'
        return f"{self.nickname} ({self.user.email or self.user.username}) [{status}]"
