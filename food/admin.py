from django.contrib import admin
from django.utils.html import format_html
from .models import FoodCategory, FoodEntry, FoodArticle


@admin.register(FoodArticle)
class FoodArticleAdmin(admin.ModelAdmin):
    list_display = (
        'title_preview',
        'source_name',
        'category_badge',
        'published_at',
        'time_ago',
        'open_link',
    )
    list_filter = ('category', 'source_name', 'published_at')
    search_fields = ('title', 'source_name', 'summary', 'keyword_query')
    date_hierarchy = 'published_at'
    readonly_fields = ('created_at',)

    def title_preview(self, obj):
        return obj.title[:50] + ('...' if len(obj.title) > 50 else '')
    title_preview.short_description = '記事タイトル'

    def category_badge(self, obj):
        return f"{obj.category_icon} {obj.get_category_display()}"
    category_badge.short_description = 'カテゴリ'

    def open_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">元記事を開く ↗</a>', obj.url)
    open_link.short_description = '外部リンク'


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'slug', 'item_type', 'order')
    list_display_links = ('name',)
    list_editable = ('order', 'icon')
    search_fields = ('name', 'slug')
    list_filter = ('item_type',)
    ordering = ('order', 'id')


@admin.register(FoodEntry)
class FoodEntryAdmin(admin.ModelAdmin):
    list_display = (
        'thumbnail_preview',
        'title',
        'item_type',
        'category',
        'brand',
        'price_info',
        'start_date',
        'status_badge',
        'is_featured',
        'is_published',
    )
    list_display_links = ('thumbnail_preview', 'title')
    list_filter = ('item_type', 'is_published', 'is_featured', 'category', 'is_period_limited', 'start_date')
    search_fields = ('title', 'brand', 'catchphrase', 'description', 'tags', 'venue_name', 'area_info')
    list_editable = ('is_featured', 'is_published')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at', 'thumbnail_large_preview')

    def thumbnail_preview(self, obj):
        url = obj.effective_image_url
        if url:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px;" />',
                url
            )
        icon = '🍔' if obj.item_type == 'product' else '🎪'
        return format_html('<span style="font-size: 26px;">{}</span>', icon)
    thumbnail_preview.short_description = 'サムネイル'

    def thumbnail_large_preview(self, obj):
        url = obj.effective_image_url
        if url:
            return format_html('<img src="{}" style="max-width: 320px; max-height: 240px; border-radius: 8px; border: 1px solid #ddd;" />', url)
        return '画像未設定'
    thumbnail_large_preview.short_description = '現在設定中の画像'

    def status_badge(self, obj):
        st = obj.status_info
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            st['color'],
            st['label']
        )
    status_badge.short_description = 'ステータス'
