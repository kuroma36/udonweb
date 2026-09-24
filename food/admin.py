from django.contrib import admin
from django.utils.html import format_html
from .models import FoodCategory, FoodEntry


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

    fieldsets = (
        ('基本情報', {
            'fields': ('item_type', 'title', 'catchphrase', 'category', 'brand', 'description')
        }),
        ('価格・エリア / 会場', {
            'fields': ('price_info', 'area_info', 'venue_name', 'venue_address')
        }),
        ('日程・掲載設定', {
            'fields': ('start_date', 'end_date', 'is_period_limited', 'is_featured', 'is_published')
        }),
        ('画像・メディア', {
            'fields': ('image', 'image_url', 'thumbnail_large_preview', 'official_url', 'tags')
        }),
        ('システム情報', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

    def thumbnail_preview(self, obj):
        url = obj.effective_image_url
        if url:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);" />',
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
