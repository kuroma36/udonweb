from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from django.utils import timezone


class Shop(models.Model):
    name = models.CharField('店舗名', max_length=100)
    address = models.CharField('住所', max_length=255)
    lat = models.FloatField('緯度', default=34.3427)
    lng = models.FloatField('経度', default=134.0465)
    place_id = models.CharField('Google Place ID', max_length=150, blank=True)
    google_rating = models.FloatField('Google評価', null=True, blank=True)
    google_user_ratings_total = models.IntegerField('Google口コミ件数', default=0)
    featured_menu = models.CharField('名物メニュー', max_length=150, blank=True)
    price_range = models.CharField('価格帯', max_length=50, default='300円〜700円')
    opening_hours = models.CharField('営業時間', max_length=150, blank=True)
    photo = models.ImageField('店舗写真', upload_to='shops/', blank=True, null=True)
    photo_url = models.CharField('写真URL', max_length=500, blank=True)
    description = models.TextField('店舗紹介・メモ', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'うどん店舗'
        verbose_name_plural = 'うどん店舗一覧'
        ordering = ['name']

    def __str__(self):
        return self.name

    def sync_top_photo(self):
        """Find the newest photo from ShopPhoto or Review and set it as shop.photo."""
        latest_shop_photo = self.photos.order_by('-created_at').first()
        latest_review_photo = self.reviews.filter(
            (models.Q(photo__isnull=False) & ~models.Q(photo=''))
        ).order_by('-created_at').first()

        chosen_photo = None
        if latest_shop_photo and latest_review_photo:
            if latest_shop_photo.created_at >= latest_review_photo.created_at:
                chosen_photo = latest_shop_photo.image
            else:
                chosen_photo = latest_review_photo.photo
        elif latest_shop_photo:
            chosen_photo = latest_shop_photo.image
        elif latest_review_photo:
            chosen_photo = latest_review_photo.photo

        self.photo = chosen_photo
        if chosen_photo:
            self.photo_url = ''
        self.save(update_fields=['photo', 'photo_url'])
        return chosen_photo

    @property
    def display_photo(self):
        # 1. Shop's direct photo
        if self.photo:
            return self.photo.url

        # 2. Check if latest photo exists in ShopPhoto or Review
        latest_shop_photo = self.photos.order_by('-created_at').first()
        latest_review_with_photo = self.reviews.filter(
            (models.Q(photo__isnull=False) & ~models.Q(photo='')) |
            (models.Q(photo_url__isnull=False) & ~models.Q(photo_url=''))
        ).order_by('-created_at').first()

        if latest_shop_photo and latest_review_with_photo:
            if latest_shop_photo.created_at >= latest_review_with_photo.created_at:
                return latest_shop_photo.image.url
            else:
                if latest_review_with_photo.photo:
                    return latest_review_with_photo.photo.url
                if latest_review_with_photo.photo_url and not any(ph in latest_review_with_photo.photo_url for ph in ['no_image', 'udon_default', 'sanuki_hero']):
                    return latest_review_with_photo.photo_url
        elif latest_shop_photo:
            return latest_shop_photo.image.url
        elif latest_review_with_photo:
            if latest_review_with_photo.photo:
                return latest_review_with_photo.photo.url
            if latest_review_with_photo.photo_url and not any(ph in latest_review_with_photo.photo_url for ph in ['no_image', 'udon_default', 'sanuki_hero']):
                return latest_review_with_photo.photo_url

        # 3. Shop's custom photo_url (not a placeholder)
        if self.photo_url and not any(ph in self.photo_url for ph in ['no_image', 'udon_default', 'sanuki_hero']):
            return self.photo_url

        # 4. Default: greyed-out "No Image" placeholder
        return '/static/udon/images/no_image.svg'

    @property
    def has_photo(self):
        return self.display_photo != '/static/udon/images/no_image.svg'

    @property
    def has_reviews(self):
        return self.reviews.exists()

    def get_latest_unique_reviews(self):
        """Return list of latest review per user (deduplicated by user or author_name)."""
        all_revs = self.reviews.select_related('user', 'trip').prefetch_related('likes', 'comments__user__profile').order_by('-created_at')
        seen_keys = set()
        unique_revs = []
        for r in all_revs:
            key = f"user_{r.user_id}" if r.user_id else f"author_{r.author_name}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_revs.append(r)
        return unique_revs

    @property
    def average_score_total(self):
        unique_revs = self.get_latest_unique_reviews()
        if not unique_revs:
            return None
        total = sum(r.score_total for r in unique_revs)
        return float(round(total / len(unique_revs), 1))

    @property
    def average_scores(self):
        unique_revs = self.get_latest_unique_reviews()
        if not unique_revs:
            return {
                'noodle': 0.0,
                'soup': 0.0,
                'atmosphere': 0.0,
                'tempura': 0.0,
                'cost': 0.0,
            }
        n = len(unique_revs)
        return {
            'noodle': float(round(sum(r.score_noodle for r in unique_revs) / n, 1)),
            'soup': float(round(sum(r.score_soup for r in unique_revs) / n, 1)),
            'atmosphere': float(round(sum(r.score_atmosphere for r in unique_revs) / n, 1)),
            'tempura': float(round(sum(r.score_tempura for r in unique_revs) / n, 1)),
            'cost': float(round(sum(r.score_cost for r in unique_revs) / n, 1)),
        }

    @property
    def review_count(self):
        return len(self.get_latest_unique_reviews())


class TripQuerySet(models.QuerySet):
    def for_user(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        nickname = getattr(getattr(user, 'profile', None), 'nickname', None)
        q = models.Q(owner=user) | models.Q(members__user=user) | models.Q(members__name=user.username)
        if nickname:
            q |= models.Q(members__name=nickname)
        return self.filter(q).distinct()


class TripManager(models.Manager):
    def get_queryset(self):
        return TripQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class Trip(models.Model):
    title = models.CharField('旅行タイトル', max_length=150, default='香川うどん巡礼2026')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_trips', verbose_name='作成者')
    date = models.DateField('日程', default=timezone.now)
    start_date = models.DateField('開始日', null=True, blank=True)
    end_date = models.DateField('終了日', null=True, blank=True)
    is_public = models.BooleanField('公開設定', default=True)
    memo = models.TextField('旅行メモ', blank=True)
    created_at = models.DateTimeField('作成日', auto_now_add=True)
    updated_at = models.DateTimeField('更新日', auto_now=True)

    objects = TripManager()

    class Meta:
        verbose_name = 'うどん旅'
        verbose_name_plural = 'うどん旅一覧'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.date:
            if not self.start_date:
                self.start_date = self.date
            if not self.end_date:
                self.end_date = self.date
        elif self.start_date:
            self.date = self.start_date
        super().save(*args, **kwargs)

    @property
    def display_date(self):
        return self.date or self.start_date or self.created_at.date()

    def is_accessible_by(self, user):
        """Check if a user is the owner or a member of this trip."""
        if not user or not user.is_authenticated:
            return False
        if self.owner_id == user.id:
            return True
        nickname = getattr(getattr(user, 'profile', None), 'nickname', None)
        if self.members.filter(user=user).exists():
            return True
        if self.members.filter(name=user.username).exists():
            return True
        if nickname and self.members.filter(name=nickname).exists():
            return True
        return False

    @property
    def ordered_stops(self):
        return self.stops.select_related('shop').order_by('visit_order')

    @property
    def stops_count(self):
        return self.stops.count()

    def update_travel_times(self):
        """Recalculate realistic travel times for all stops based on coordinates."""
        stops = list(self.stops.select_related('shop').order_by('visit_order'))
        for i, stop in enumerate(stops):
            if i == 0:
                stop.travel_time_text = '出発'
            else:
                prev = stops[i - 1]
                mins = calculate_driving_minutes(prev.shop.lat, prev.shop.lng, stop.shop.lat, stop.shop.lng)
                stop.travel_time_text = f"車で{mins}分"
            stop.save()


class TripMember(models.Model):
    ROLE_CHOICES = [
        ('owner', '主催者'),
        ('member', 'メンバー'),
    ]
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='members', verbose_name='旅行')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='trip_memberships', verbose_name='ユーザー')
    name = models.CharField('メンバー名', max_length=50, default='会員さん')
    avatar_color = models.CharField('アバター背景色', max_length=20, default='#D99B26')
    avatar_icon = models.CharField('アバターアイコン', max_length=10, default='会')
    role = models.CharField('役割', max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '参加メンバー'
        verbose_name_plural = '参加メンバー一覧'

    def save(self, *args, **kwargs):
        if not self.user and self.name:
            profile = UserProfile.objects.filter(nickname=self.name).first()
            if profile:
                self.user = profile.user
                if not self.avatar_color or self.avatar_color == '#D99B26':
                    self.avatar_color = profile.avatar_color
            else:
                user_match = User.objects.filter(username=self.name).first()
                if user_match:
                    self.user = user_match
                    if hasattr(user_match, 'profile') and user_match.profile.avatar_color:
                        self.avatar_color = user_match.profile.avatar_color
        elif self.user and (not self.name or self.name == '会員さん'):
            if hasattr(self.user, 'profile') and self.user.profile.nickname:
                self.name = self.user.profile.nickname
                self.avatar_color = self.user.profile.avatar_color
            else:
                self.name = self.user.username
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.trip.title})"

    @property
    def initial(self):
        return self.name[0] if self.name else '会'

    @property
    def avatar_image(self):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.avatar_image:
            return self.user.profile.avatar_image.url
        return None


def calculate_driving_minutes(lat1, lng1, lat2, lng2):
    """Calculate realistic driving minutes based on geodesic distance & Kagawa road factors."""
    import math
    if not lat1 or not lng1 or not lat2 or not lng2:
        return 18
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_km = R * c
    
    # In Kagawa: road winding factor ~1.35x, average speed ~35km/h
    road_km = dist_km * 1.35
    minutes = round((road_km / 35.0) * 60)
    return max(5, minutes)


class TripStop(models.Model):
    STATUS_CHOICES = [
        ('planned', '予定'),
        ('visited', '訪問済'),
        ('skipped', 'スキップ'),
    ]
    COLOR_BADGES = [
        ('#1E2B37', 'ネイビー'),
        ('#D99B26', '山吹ゴールド'),
        ('#C84B31', '朱色レッド'),
        ('#2E7D5B', '抹茶グリーン'),
        ('#8E44AD', '紫'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stops', verbose_name='旅行')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='trip_stops', verbose_name='店舗')
    visit_order = models.PositiveIntegerField('巡回順', default=1)
    scheduled_time = models.TimeField('予定時間', null=True, blank=True)
    travel_time_text = models.CharField('所要時間・ステータス', max_length=50, default='車で18分')
    status = models.CharField('訪問ステータス', max_length=20, choices=STATUS_CHOICES, default='planned')
    notes = models.TextField('備考・注文予定', blank=True)

    class Meta:
        verbose_name = '巡回ストップ'
        verbose_name_plural = '巡回ストップ一覧'
        ordering = ['visit_order']
        unique_together = ['trip', 'visit_order']

    def __str__(self):
        return f"{self.visit_order}. {self.shop.name} ({self.trip.title})"

    @property
    def badge_color(self):
        # Rotate colors based on order
        colors = ['#1E2B37', '#D99B26', '#C84B31', '#2E7D5B', '#6C5CE7', '#E17055']
        idx = (self.visit_order - 1) % len(colors)
        return colors[idx]



class Review(models.Model):
    STAMP_CHOICES = [
        ('香川人選', '香川人選'),
        ('名店認定', '名店認定'),
        ('巡礼完了', '巡礼完了'),
        ('絶品百選', '絶品百選'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews', verbose_name='うどん旅')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='reviews', verbose_name='対象店舗')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews', verbose_name='投稿者')
    author_name = models.CharField('投稿者名', max_length=50, default='会員さん')
    author_avatar_color = models.CharField('アバター色', max_length=20, default='#D99B26')
    author_avatar_icon = models.CharField('アバターアイコン', max_length=10, default='会')

    # 5-Axis Score (1 to 10)
    score_noodle = models.PositiveSmallIntegerField('麺のコシ・喉ごし', default=8, validators=[MinValueValidator(1), MaxValueValidator(10)])
    score_soup = models.PositiveSmallIntegerField('出汁の風味・旨味', default=8, validators=[MinValueValidator(1), MaxValueValidator(10)])
    score_atmosphere = models.PositiveSmallIntegerField('店の雰囲気・情緒', default=8, validators=[MinValueValidator(1), MaxValueValidator(10)])
    score_tempura = models.PositiveSmallIntegerField('天ぷらのサクサク度', default=8, validators=[MinValueValidator(1), MaxValueValidator(10)])
    score_cost = models.PositiveSmallIntegerField('コスパ・満足度', default=9, validators=[MinValueValidator(1), MaxValueValidator(10)])

    # Overall Star Score (1.0 to 5.0)
    score_total = models.DecimalField('総合評価', max_digits=3, decimal_places=1, default=4.8, validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])

    comment = models.TextField('レビューコメント', blank=True)
    photo = models.ImageField('レビュー写真', upload_to='reviews/', blank=True, null=True)
    photo_url = models.CharField('写真URL', max_length=500, blank=True)
    stamp_type = models.CharField('認定スタンプ', max_length=30, choices=STAMP_CHOICES, default='香川人選')
    created_at = models.DateTimeField('投稿日', auto_now_add=True)

    class Meta:
        verbose_name = 'うどんレビュー'
        verbose_name_plural = 'うどんレビュー一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.shop.name} - {self.author_name} ({self.score_total}★)"

    def save(self, *args, **kwargs):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.nickname:
            if not self.author_name or self.author_name.startswith('udon_') or self.author_name == self.user.username or self.author_name == '会員さん':
                self.author_name = self.user.profile.nickname
            if self.user.profile.avatar_color:
                self.author_avatar_color = self.user.profile.avatar_color
        super().save(*args, **kwargs)

        # When a review with a photo is saved, update the shop's photo so it immediately becomes the shop's top photo
        if self.photo and self.shop_id:
            Shop.objects.filter(id=self.shop_id).update(photo=self.photo, photo_url='')

    @property
    def display_author_name(self):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.nickname:
            return self.user.profile.nickname
        return self.author_name

    @property
    def display_photo(self):
        if self.photo:
            return self.photo.url
        if self.photo_url and not any(ph in self.photo_url for ph in ['no_image', 'udon_default', 'sanuki_hero']):
            return self.photo_url
        return self.shop.display_photo

    @property
    def initial(self):
        name = self.display_author_name
        return name[0] if name else 'う'

    @property
    def author_avatar_image(self):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.avatar_image:
            return self.user.profile.avatar_image.url
        return None

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        if hasattr(self, '_prefetched_objects_cache') and 'likes' in self._prefetched_objects_cache:
            return any(l.user_id == user.id for l in self.likes.all())
        return self.likes.filter(user=user).exists()


class ReviewLike(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='likes', verbose_name='対象レビュー')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_likes', verbose_name='ユーザー')
    created_at = models.DateTimeField('いいね日時', auto_now_add=True)

    class Meta:
        verbose_name = 'レビューいいね'
        verbose_name_plural = 'レビューいいね一覧'
        unique_together = ['review', 'user']

    def __str__(self):
        return f"{self.user.username} liked {self.review}"


class ReviewComment(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments', verbose_name='対象レビュー')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_comments', verbose_name='投稿者')
    author_name = models.CharField('投稿者名', max_length=50, default='会員さん')
    content = models.TextField('コメント内容')
    created_at = models.DateTimeField('投稿日時', auto_now_add=True)

    class Meta:
        verbose_name = 'レビューコメント'
        verbose_name_plural = 'レビューコメント一覧'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author_name} on {self.review.shop.name}: {self.content[:20]}"

    def save(self, *args, **kwargs):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.nickname:
            if not self.author_name or self.author_name.startswith('udon_') or self.author_name == self.user.username or self.author_name == '会員さん':
                self.author_name = self.user.profile.nickname
        super().save(*args, **kwargs)

    @property
    def display_author_name(self):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.nickname:
            return self.user.profile.nickname
        return self.author_name

    @property
    def initial(self):
        name = self.display_author_name
        return name[0] if name else 'う'

    @property
    def author_avatar_color(self):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.avatar_color:
            return self.user.profile.avatar_color
        return '#D99B26'

    @property
    def author_avatar_image(self):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.avatar_image:
            return self.user.profile.avatar_image.url
        return None


class ShopPhoto(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='photos', verbose_name='対象店舗')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='shop_photos', verbose_name='投稿者')
    author_name = models.CharField('投稿者名', max_length=50, default='会員さん')
    image = models.ImageField('店舗写真', upload_to='shop_photos/')
    caption = models.CharField('写真メモ・説明', max_length=150, blank=True)
    created_at = models.DateTimeField('投稿日', auto_now_add=True)

    class Meta:
        verbose_name = '店舗写真'
        verbose_name_plural = '店舗写真一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.shop.name} - {self.author_name} ({self.created_at.strftime('%Y-%m-%d') if self.created_at else ''})"

    def save(self, *args, **kwargs):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.nickname:
            if not self.author_name or self.author_name.startswith('udon_') or self.author_name == self.user.username or self.author_name == '会員さん':
                self.author_name = self.user.profile.nickname
        super().save(*args, **kwargs)

        # When a photo is uploaded, update the shop's top photo
        if self.image and self.shop_id:
            Shop.objects.filter(id=self.shop_id).update(photo=self.image, photo_url='')

    @property
    def display_author_name(self):
        if self.user and hasattr(self.user, 'profile') and self.user.profile.nickname:
            return self.user.profile.nickname
        return self.author_name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='ユーザー')
    nickname = models.CharField('ニックネーム', max_length=50)
    avatar_image = models.ImageField('プロフィール画像', upload_to='avatars/', blank=True, null=True)
    avatar_color = models.CharField('アバターカラー', max_length=20, default='#E67E22')
    avatar_icon = models.CharField('アバタータイプ', max_length=50, default='udonchu')
    favorite_udon = models.CharField('好みのうどん', max_length=50, default='釜玉うどん')
    level_title = models.CharField('うどん人称号', max_length=50, default='見習いうどん人')
    bio = models.TextField('自己紹介', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'うどん人プロフィール'
        verbose_name_plural = 'うどん人プロフィール一覧'

    def __str__(self):
        return f"{self.nickname}（{self.level_title}）"

    @property
    def initial(self):
        return self.nickname[0] if self.nickname else (self.user.username[0] if self.user.username else 'う')

    @property
    def display_avatar(self):
        if self.avatar_image:
            return self.avatar_image.url
        return None


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'いいね'),
        ('comment', 'コメント'),
    )

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='受信者')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', verbose_name='送信者')
    notification_type = models.CharField('通知種別', max_length=20, choices=NOTIFICATION_TYPES)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True, verbose_name='対象レビュー')
    comment = models.ForeignKey(ReviewComment, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True, verbose_name='対象コメント')
    message = models.CharField('メッセージ', max_length=255, blank=True)
    is_read = models.BooleanField('既読', default=False)
    created_at = models.DateTimeField('通知日時', auto_now_add=True)

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username} ({self.notification_type}): {self.message[:20]}"

    @property
    def sender_name(self):
        if hasattr(self.sender, 'profile') and self.sender.profile.nickname:
            return self.sender.profile.nickname
        return self.sender.username

    @property
    def sender_avatar_image(self):
        if hasattr(self.sender, 'profile') and self.sender.profile.avatar_image:
            return self.sender.profile.avatar_image.url
        return None

    @property
    def sender_avatar_color(self):
        if hasattr(self.sender, 'profile') and self.sender.profile.avatar_color:
            return self.sender.profile.avatar_color
        return '#E67E22'

    @property
    def sender_initial(self):
        name = self.sender_name
        return name[0] if name else 'う'

    @property
    def target_url(self):
        if self.review:
            from django.urls import reverse
            return f"{reverse('udon:shop_detail', kwargs={'shop_id': self.review.shop_id})}#review-card-{self.review_id}"
        return '#'

    @property
    def time_ago_str(self):
        now = timezone.now()
        diff = now - self.created_at
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return 'たった今'
        minutes = seconds // 60
        if minutes < 60:
            return f'{minutes}分前'
        hours = minutes // 60
        if hours < 24:
            return f'{hours}時間前'
        days = hours // 24
        if days < 7:
            return f'{days}日前'
        return self.created_at.strftime('%m/%d %H:%M')


class ShopFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shop_favorites', verbose_name='ユーザー')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='店舗')
    reason = models.TextField('お気に入りの理由・メモ', blank=True)
    created_at = models.DateTimeField('登録日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = 'お気に入り店舗'
        verbose_name_plural = 'お気に入り店舗一覧'
        unique_together = ['user', 'shop']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} ★ {self.shop.name}"



