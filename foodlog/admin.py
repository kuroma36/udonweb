from django.contrib import admin
from .models import UserProfile, DailyLog, MealEntry, MealItem, GeneralFood

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'gender', 'current_weight', 'target_calories', 'updated_at')

class MealItemInline(admin.TabularInline):
    model = MealItem
    extra = 1

@admin.register(MealEntry)
class MealEntryAdmin(admin.ModelAdmin):
    list_display = ('daily_log', 'meal_type', 'memo')
    list_filter = ('meal_type',)
    inlines = [MealItemInline]

@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'weight', 'updated_at')
    ordering = ('-date',)

@admin.register(GeneralFood)
class GeneralFoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'serving_size', 'calories', 'protein', 'fat', 'carbohydrates', 'salt')
    search_fields = ('name',)
    list_filter = ('category',)
