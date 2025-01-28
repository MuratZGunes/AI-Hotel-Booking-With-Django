# hotel_booking/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .api_views import RoomViewSet, BookingViewSet, ReviewViewSet, PromoCodeViewSet


router = DefaultRouter()
router.register(r'api/rooms', RoomViewSet)
router.register(r'api/bookings', BookingViewSet, basename='booking')
router.register(r'api/reviews', ReviewViewSet, basename='review')
router.register(r'api/promocodes', PromoCodeViewSet)

urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('rooms/', views.available_rooms, name='available_rooms'),
    path('book/<int:room_id>/', views.book_room, name='book_room'),
    path('booking_success/<int:booking_id>/', views.booking_success, name='booking_success'),

    # Üyelik URLS
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('profile/', views.profile, name='profile'),
    
    # Oda URLS
    path('add-room/', views.add_room, name='add_room'),
    path('edit-room/<int:id>/', views.edit_room, name='edit_room'),
    path('delete-room/<int:id>/', views.delete_room, name='delete_room'),
    path('room/<int:room_id>/', views.room_details, name='room_details'),
    
    # Admin URLS
    path('admin-home/', views.admin_home, name='admin_home'),
    path('manage-rooms/', views.manage_rooms, name='manage_rooms'),
    path('bookings/', views.view_bookings, name='view_bookings'),
    path('approve-booking/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('bookings/delete-cancelled/', views.delete_cancelled_bookings, name='delete_cancelled_bookings'),
    
    # Sezonluk Fiyat URLS
    path('seasonal-prices/', views.manage_seasonal_prices, name='manage_seasonal_prices'),
    path('seasonal-prices/<int:room_id>/', views.manage_seasonal_prices, name='manage_seasonal_prices'),
    path('seasonal-prices/delete/<int:price_id>/', views.delete_seasonal_price, name='delete_seasonal_price'),
    
    # Görünüm URLS
    path('room/<int:room_id>/review/', views.add_review, name='add_review'),
    
    # Report URLs
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/bookings/', views.booking_report, name='booking_report'),
    path('reports/revenue/', views.revenue_report, name='revenue_report'),
    path('reports/bookings/download/', views.download_booking_report, name='download_booking_report'),
    path('reports/revenue/download/', views.download_revenue_report, name='download_revenue_report'),
    
    # Diğer URLs
    path('contact/', views.contact, name='contact'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('api/chat/', views.chat_api, name='chat_api'),

    # Admin panel için URL'ler ekleyin
    path('admin/contact-messages/', views.contact_messages, name='admin_contact_messages'),
    path('admin/contact-messages/mark-read/', views.mark_messages_read, name='mark_messages_read'),
    path('admin/contact-messages/delete/', views.delete_messages, name='delete_messages'),

    path('room/<int:id>/delete/', views.delete_room, name='delete_room'),

] + router.urls + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

