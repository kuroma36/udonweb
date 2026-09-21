from django.contrib import admin
from .models import TravelTrip, TravelDay, TravelStop


class TravelStopInline(admin.TabularInline):
    model = TravelStop
    extra = 1
    fields = ('order', 'name', 'category', 'arrival_time', 'transport_mode', 'transport_time_text')


class TravelDayInline(admin.StackedInline):
    model = TravelDay
    extra = 0


@admin.register(TravelTrip)
class TravelTripAdmin(admin.ModelAdmin):
    list_display = ('title', 'destination', 'start_date', 'end_date', 'created_by', 'created_at')
    list_filter = ('start_date', 'created_by')
    search_fields = ('title', 'destination', 'description')
    inlines = [TravelDayInline]


@admin.register(TravelDay)
class TravelDayAdmin(admin.ModelAdmin):
    list_display = ('trip', 'day_number', 'date', 'title')
    list_filter = ('trip',)
    inlines = [TravelStopInline]


@admin.register(TravelStop)
class TravelStopAdmin(admin.ModelAdmin):
    list_display = ('day', 'order', 'name', 'category', 'arrival_time', 'transport_mode')
    list_filter = ('category', 'transport_mode')
    search_fields = ('name', 'address', 'memo', 'transport_memo')
