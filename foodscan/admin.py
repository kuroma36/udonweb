from django.contrib import admin
from .models import FoodItem, ScanLog

@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('barcode', 'name', 'brand', 'calories', 'protein', 'fat', 'carbohydrates', 'scan_count', 'updated_at')
    search_fields = ('barcode', 'name', 'brand', 'ingredients')
    list_filter = ('source', 'updated_at')
    ordering = ('-updated_at',)

@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ('food_item', 'scanned_at', 'ip_address')
    search_fields = ('food_item__name', 'food_item__barcode', 'ip_address')
    list_filter = ('scanned_at',)
    ordering = ('-scanned_at',)
