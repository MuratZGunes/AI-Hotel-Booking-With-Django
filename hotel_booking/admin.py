from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.db import models
from .models import Room, Booking, Amenity, SeasonalPrice, CancellationPolicy, PromoCode, Review

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'display_icon']
    search_fields = ['name']

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }

    def display_icon(self, obj):
        return format_html('<i class="{}"></i>', obj.icon)
    display_icon.short_description = 'Simge Önizlemesi'

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'capacity', 'price', 'floor', 'has_balcony', 'has_sea_view', 'booking_count', 'average_rating']
    list_filter = ['room_type', 'capacity', 'has_balcony', 'has_sea_view', 'floor']
    search_fields = ['name', 'description']
    filter_horizontal = ['amenities']
    readonly_fields = ['booking_count', 'average_rating']

    def booking_count(self, obj):
        return obj.booking_set.count()
    booking_count.short_description = 'Toplam Rezervasyonlar'

    def average_rating(self, obj):
        avg = obj.review_set.aggregate(avg=models.Avg('rating'))['avg']
        return f"{avg:.1f} ★" if avg else "Hiçbir derecelendirme yok"
    average_rating.short_description = 'Ortalama Puan'

@admin.register(SeasonalPrice)
class SeasonalPriceAdmin(admin.ModelAdmin):
    list_display = ['room', 'start_date', 'end_date', 'price']
    list_filter = ['start_date', 'end_date']
    search_fields = ['room__name']
    date_hierarchy = 'start_date'

@admin.register(CancellationPolicy)
class CancellationPolicyAdmin(admin.ModelAdmin):
    list_display = ['hours_before', 'refund_percentage']
    list_filter = ['refund_percentage']
    ordering = ['hours_before']

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percentage', 'valid_from', 'valid_until', 'max_uses', 'current_uses', 'is_active']
    list_filter = ['valid_from', 'valid_until']
    search_fields = ['code']
    readonly_fields = ['current_uses']

    def is_active(self, obj):
        return obj.is_valid()
    is_active.boolean = True
    is_active.short_description = 'Aktif'

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'room', 'check_in', 'check_out', 'total_cost', 'status', 'created_at']
    list_filter = ['status', 'check_in', 'check_out', 'created_at']
    search_fields = ['user__username', 'user__email', 'room__name']
    readonly_fields = ['created_at', 'total_cost']
    date_hierarchy = 'check_in'
    actions = ['approve_bookings', 'cancel_bookings']

    def approve_bookings(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} Rezervasyonlar başarıyla onaylandı.')
    approve_bookings.short_description = "Seçilen rezervasyonları onayla"

    def cancel_bookings(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} rezervasyonlar iptal edildi.')
    cancel_bookings.short_description = "Seçili rezervasyonları iptal et"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'rating', 'created_at', 'short_comment']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'room__name', 'comment']
    readonly_fields = ['created_at']

    def short_comment(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    short_description = 'Yorum Önizlemesi'

# Admin site customization
admin.site.site_header = 'Otel Rezervasyon Yönetimi'
admin.site.site_title = 'Otel Rezervasyon Yöneticisi'
admin.site.index_title = 'Otel Yönetim Sistemi'
