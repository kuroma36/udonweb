from django.contrib import admin
from .models import Shop, Trip, TripMember, TripStop, Review, ShopPhoto, ReviewLike, ReviewComment, Notification, ShopFavorite


class TripStopInline(admin.TabularInline):
    model = TripStop
    extra = 1


class TripMemberInline(admin.TabularInline):
    model = TripMember
    extra = 1


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'price_range', 'featured_menu', 'average_score_total']
    search_fields = ['name', 'address', 'featured_menu']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'start_date', 'end_date', 'stops_count', 'is_public']
    inlines = [TripMemberInline, TripStopInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['shop', 'author_name', 'score_total', 'score_noodle', 'score_soup', 'score_cost', 'created_at']
    list_filter = ['shop', 'stamp_type']


@admin.register(ShopPhoto)
class ShopPhotoAdmin(admin.ModelAdmin):
    list_display = ['shop', 'author_name', 'caption', 'created_at']
    list_filter = ['shop']


@admin.register(ReviewLike)
class ReviewLikeAdmin(admin.ModelAdmin):
    list_display = ['review', 'user', 'created_at']


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ['review', 'author_name', 'content', 'created_at']
    search_fields = ['author_name', 'content']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'sender', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['recipient__username', 'sender__username', 'message']


@admin.register(ShopFavorite)
class ShopFavoriteAdmin(admin.ModelAdmin):
    list_display = ['shop', 'user', 'reason', 'created_at', 'updated_at']
    search_fields = ['shop__name', 'user__username', 'reason']


