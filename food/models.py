from django.db import models
from django.utils import timezone
from datetime import date


class FoodCategory(models.Model):
    ITEM_TYPE_CHOICES = (
        ('all', '共通'),
        ('product', '新発売・新商品'),
        ('event', 'イベント・フェス'),
    )

    name = models.CharField('カテゴリ名', max_length=50)
    slug = models.SlugField('スラッグ', max_length=50, unique=True)
    item_type = models.CharField('対象種別', max_length=10, choices=ITEM_TYPE_CHOICES, default='all')
    icon = models.CharField('アイコン（絵文字）', max_length=50, default='🍽️')
    order = models.IntegerField('表示順', default=0)

    class Meta:
        verbose_name = 'カテゴリ'
        verbose_name_plural = 'カテゴリ一覧'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.icon} {self.name}"


class FoodArticle(models.Model):
    """Webから自動収集・キュレーションした食ニュース記事"""
    CATEGORY_CHOICES = (
        ('new_product', '新商品・新発売'),
        ('sweets', 'スイーツ・アイス'),
        ('fastfood', '外食・ファストフード'),
        ('convenience', 'コンビニ'),
        ('event', 'イベント・催事・フェス'),
        ('drinks', 'カフェ・お酒・飲料'),
        ('noodle', 'ラーメン・麺類'),
        ('trend', 'トレンド・話題'),
    )

    CATEGORY_ICONS = {
        'new_product': '🍔',
        'sweets': '🍰',
        'fastfood': '🍟',
        'convenience': '🏪',
        'event': '🎪',
        'drinks': '☕',
        'noodle': '🍜',
        'trend': '💡',
    }

    title = models.CharField('記事タイトル', max_length=350)
    url = models.URLField('記事URL', max_length=1000, unique=True, db_index=True)
    source_name = models.CharField('配信元メディア', max_length=100, db_index=True)
    category = models.CharField('カテゴリ', max_length=30, choices=CATEGORY_CHOICES, default='new_product', db_index=True)
    summary = models.TextField('要約・本文抜粋', blank=True)
    image_url = models.URLField('サムネイル画像URL', max_length=1000, blank=True)
    published_at = models.DateTimeField('配信日時', db_index=True)
    keyword_query = models.CharField('収集キーワード', max_length=100, blank=True)
    is_featured = models.BooleanField('注目記事', default=False, db_index=True)
    created_at = models.DateTimeField('収集日時', auto_now_add=True)

    class Meta:
        verbose_name = 'Web収集食ニュース'
        verbose_name_plural = 'Web収集食ニュース一覧'
        ordering = ['-published_at', '-id']

    def __str__(self):
        return f"[{self.source_name}] {self.title}"

    @property
    def category_icon(self):
        return self.CATEGORY_ICONS.get(self.category, '🍽️')

    @property
    def time_ago(self):
        """配信からの経過時間を分かりやすく返す（例: 15分前, 2時間前, 1日前）"""
        now = timezone.now()
        diff = now - self.published_at
        seconds = diff.total_seconds()
        
        if seconds < 0:
            return 'たった今'
        if seconds < 3600:
            minutes = int(seconds / 60)
            return f'{max(1, minutes)}分前'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours}時間前'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days}日前'
        else:
            return self.published_at.strftime('%Y/%m/%d')


class FoodEntry(models.Model):
    """手動登録用・詳細イベントモデル（既存互換）"""
    TYPE_CHOICES = (
        ('product', '新発売・新商品'),
        ('event', 'グルメイベント・催事'),
    )

    item_type = models.CharField('情報種別', max_length=10, choices=TYPE_CHOICES, default='product', db_index=True)
    title = models.CharField('商品名 / イベント名', max_length=200)
    category = models.ForeignKey(FoodCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='entries', verbose_name='カテゴリ')
    brand = models.CharField('メーカー / ブランド / 主催', max_length=120)
    catchphrase = models.CharField('キャッチコピー・見出し', max_length=250, blank=True)
    description = models.TextField('詳細・特徴説明')

    price_info = models.CharField('価格・入場料', max_length=100, blank=True)
    area_info = models.CharField('販売地域 / 開催エリア', max_length=150, blank=True)
    venue_name = models.CharField('会場名・開催場所', max_length=150, blank=True)
    venue_address = models.CharField('会場住所', max_length=250, blank=True)

    start_date = models.DateField('発売日 / 開催開始日', db_index=True)
    end_date = models.DateField('販売終了予定日 / 開催終了日', null=True, blank=True)
    is_period_limited = models.BooleanField('期間限定 / 数量限定', default=False)

    image = models.ImageField('アップロード画像', upload_to='food/images/%Y/%m/', blank=True, null=True)
    image_url = models.URLField('画像URL (外部参照)', blank=True, max_length=500)
    official_url = models.URLField('公式サイト / 参照URL', blank=True, max_length=500)

    tags = models.CharField('タグ (カンマ区切り)', max_length=200, blank=True)
    is_featured = models.BooleanField('注目・ピックアップ', default=False, db_index=True)
    is_published = models.BooleanField('公開フラグ', default=True, db_index=True)

    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '特集・ピックアップ食情報'
        verbose_name_plural = '特集・ピックアップ食情報一覧'
        ordering = ['-is_featured', 'start_date', '-created_at']

    def __str__(self):
        type_str = '【新商品】' if self.item_type == 'product' else '【イベント】'
        return f"{type_str} {self.title} ({self.brand})"

    @property
    def effective_image_url(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return ''

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.replace('、', ',').split(',') if t.strip()]

    @property
    def status_info(self):
        today = date.today()
        if self.item_type == 'event':
            if today < self.start_date:
                days = (self.start_date - today).days
                return {'code': 'upcoming', 'label': f'あと{days}日' if days <= 7 else '近日開催', 'badge_class': 'badge-upcoming', 'color': '#3B82F6'}
            elif self.end_date and today > self.end_date:
                return {'code': 'ended', 'label': '終了', 'badge_class': 'badge-ended', 'color': '#9CA3AF'}
            else:
                return {'code': 'ongoing', 'label': '開催中！', 'badge_class': 'badge-ongoing', 'color': '#10B981'}
        else:
            if today < self.start_date:
                days = (self.start_date - today).days
                return {'code': 'upcoming', 'label': f'あと{days}日発売' if days <= 7 else '近日発売', 'badge_class': 'badge-upcoming', 'color': '#F59E0B'}
            elif self.end_date and today > self.end_date:
                return {'code': 'ended', 'label': '販売終了', 'badge_class': 'badge-ended', 'color': '#9CA3AF'}
            else:
                days_since = (today - self.start_date).days
                if days_since <= 7:
                    return {'code': 'new', 'label': 'NEW 新発売！', 'badge_class': 'badge-new', 'color': '#EF4444'}
                return {'code': 'selling', 'label': '好評販売中', 'badge_class': 'badge-selling', 'color': '#10B981'}
