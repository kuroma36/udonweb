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


class FoodEntry(models.Model):
    TYPE_CHOICES = (
        ('product', '新発売・新商品'),
        ('event', 'グルメイベント・催事'),
    )

    item_type = models.CharField('情報種別', max_length=10, choices=TYPE_CHOICES, default='product', db_index=True)
    title = models.CharField('商品名 / イベント名', max_length=200)
    category = models.ForeignKey(FoodCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='entries', verbose_name='カテゴリ')
    brand = models.CharField('メーカー / ブランド / 主催', max_length=120, help_text='例: セブン-イレブン, マクドナルド, 実行委員会')
    catchphrase = models.CharField('キャッチコピー・見出し', max_length=250, blank=True, help_text='魅力が一言で伝わる短文')
    description = models.TextField('詳細・特徴説明')

    # 価格・エリア情報
    price_info = models.CharField('価格・入場料', max_length=100, blank=True, help_text='例: 380円(税込), 入場無料(飲食代別途)')
    area_info = models.CharField('販売地域 / 開催エリア', max_length=150, blank=True, help_text='例: 全国, 関東・東海限定, 東京都渋谷区')
    venue_name = models.CharField('会場名・開催場所', max_length=150, blank=True, help_text='イベントの場合の会場名（例: 代々木公園 イベント広場）')
    venue_address = models.CharField('会場住所', max_length=250, blank=True)

    # 日程情報
    start_date = models.DateField('発売日 / 開催開始日', db_index=True)
    end_date = models.DateField('販売終了予定日 / 開催終了日', null=True, blank=True, help_text='未定または通年販売の場合は空欄')
    is_period_limited = models.BooleanField('期間限定 / 数量限定', default=False)

    # メディア・外部リンク
    image = models.ImageField('アップロード画像', upload_to='food/images/%Y/%m/', blank=True, null=True)
    image_url = models.URLField('画像URL (外部参照)', blank=True, max_length=500, help_text='画像ファイルアップロードの代わりにURL直接指定も可能')
    official_url = models.URLField('公式サイト / 参照URL', blank=True, max_length=500)

    # タグ・フラグ
    tags = models.CharField('タグ (カンマ区切り)', max_length=200, blank=True, help_text='例: 秋限定, 栗, 濃厚, 話題の新作')
    is_featured = models.BooleanField('注目・ピックアップ', default=False, db_index=True)
    is_published = models.BooleanField('公開フラグ', default=True, db_index=True)

    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '食ニュース・イベント'
        verbose_name_plural = '食ニュース・イベント一覧'
        ordering = ['-is_featured', 'start_date', '-created_at']

    def __str__(self):
        type_str = '【新商品】' if self.item_type == 'product' else '【イベント】'
        return f"{type_str} {self.title} ({self.brand})"

    @property
    def effective_image_url(self):
        """画像URLを優先度順に返す"""
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
        """ステータス判定（近日、開催中/発売中、終了など）"""
        today = date.today()
        
        if self.item_type == 'event':
            if today < self.start_date:
                days = (self.start_date - today).days
                return {
                    'code': 'upcoming',
                    'label': f'あと{days}日' if days <= 7 else '近日開催',
                    'badge_class': 'badge-upcoming',
                    'color': '#3B82F6'
                }
            elif self.end_date and today > self.end_date:
                return {
                    'code': 'ended',
                    'label': '終了',
                    'badge_class': 'badge-ended',
                    'color': '#9CA3AF'
                }
            else:
                return {
                    'code': 'ongoing',
                    'label': '開催中！',
                    'badge_class': 'badge-ongoing',
                    'color': '#10B981'
                }
        else: # product
            if today < self.start_date:
                days = (self.start_date - today).days
                return {
                    'code': 'upcoming',
                    'label': f'あと{days}日発売' if days <= 7 else '近日発売',
                    'badge_class': 'badge-upcoming',
                    'color': '#F59E0B'
                }
            elif self.end_date and today > self.end_date:
                return {
                    'code': 'ended',
                    'label': '販売終了',
                    'badge_class': 'badge-ended',
                    'color': '#9CA3AF'
                }
            else:
                days_since = (today - self.start_date).days
                if days_since <= 7:
                    return {
                        'code': 'new',
                        'label': 'NEW 新発売！',
                        'badge_class': 'badge-new',
                        'color': '#EF4444'
                    }
                return {
                    'code': 'selling',
                    'label': '好評販売中',
                    'badge_class': 'badge-selling',
                    'color': '#10B981'
                }
