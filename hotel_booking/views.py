from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Case, When
from django.db.models.functions import TruncMonth
from django.core.mail import send_mail
from .models import Room, Booking, Review, PromoCode, SeasonalPrice, ContactMessage
from .forms import (
    RoomForm, BookingForm, ReviewForm, RoomSearchForm,
    UserRegistrationForm, UserLoginForm, UserProfileForm,
    BookingApprovalForm
)
from django.http import HttpResponse, JsonResponse
from .utils import generate_booking_report_pdf, generate_revenue_report_pdf
from django.views.decorators.http import require_http_methods
from django.conf import settings
import google.generativeai as genai
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import models

def index(request):
    top_rated_rooms = Room.objects.annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review')
    ).order_by('-avg_rating')[:4]  # En yüksek 4 oda derecelendirmesi
    
    # Sezonluk fiyatları güncelle
    today = timezone.now().date()
    for room in top_rated_rooms:
        room.current_price = room.get_current_price(today)
    
    return render(request, 'hotel_booking/index.html', {
        'top_rated_rooms': top_rated_rooms
    })


def available_rooms(request):
    form = RoomSearchForm(request.GET)
    rooms = Room.objects.annotate(
        avg_rating=Avg('review__rating')
    ).all()

    if form.is_valid():
        check_in = form.cleaned_data.get('check_in')
        check_out = form.cleaned_data.get('check_out')
        room_type = form.cleaned_data.get('room_type')
        capacity = form.cleaned_data.get('capacity')
        has_balcony = form.cleaned_data.get('has_balcony')
        has_sea_view = form.cleaned_data.get('has_sea_view')
        max_price = form.cleaned_data.get('max_price')

        # Önce diğer filtreleri uygula
        if room_type:
            rooms = rooms.filter(room_type=room_type)
        if capacity:
            rooms = rooms.filter(capacity__gte=capacity)
        if has_balcony:
            rooms = rooms.filter(has_balcony=True)
        if has_sea_view:
            rooms = rooms.filter(has_sea_view=True)

        if check_in and check_out:
            # Çakışan rezervasyonlara sahip odaları filtreleyin
            unavailable_rooms = Booking.objects.filter(
                check_in__lte=check_out,
                check_out__gte=check_in,
                status='confirmed'
            ).values_list('room_id', flat=True)
            rooms = rooms.exclude(id__in=unavailable_rooms)

            # Her oda için sezonluk fiyatı kontrol et
            rooms = list(rooms)  # QuerySet'i listeye çevir
            for room in rooms:
                room.current_price = room.get_current_price(check_in)
                
            # Eğer max_price filtresi varsa, sezonluk fiyata göre filtrele
            if max_price:
                rooms = [room for room in rooms if room.current_price <= max_price]
    else:
        # Form geçerli değilse, her oda için bugünün fiyatını göster
        rooms = list(rooms)  # QuerySet'i listeye çevir
        for room in rooms:
            room.current_price = room.get_current_price(timezone.now().date())

    return render(request, 'hotel_booking/available_rooms.html', {
        'form': form,
        'rooms': rooms
    })

@login_required
def book_room(request, room_id):
    if not request.user.is_authenticated:
        messages.warning(request, 'Rezervasyon işlemi yapmak için önce giriş yapmalısınız.')
        return redirect('user_login')
        
    room = get_object_or_404(Room, id=room_id)
    
    # Sezonluk fiyatı kontrol et
    room.current_price = room.get_current_price(timezone.now().date())
    
    # Ortalama puanı hesapla
    reviews = room.review_set.all()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    
    if request.method == 'POST':
        form = BookingForm(request.POST, initial={'room': room})
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.room = room
            
            # Toplam maliyeti hesapla
            total_cost = 0
            current_date = booking.check_in
            
            # Konaklama süresince her gün için o günün fiyatını hesapla
            while current_date < booking.check_out:
                daily_price = room.get_current_price(current_date)
                total_cost += daily_price
                current_date += timezone.timedelta(days=1)

            # Geçerliyse promosyon kodunu uygula
            if form.cleaned_data.get('promo_code'):
                promo = form.cleaned_data['promo_code']
                discount = (total_cost * promo.discount_percentage) / 100
                booking.total_cost = total_cost - discount
                booking.promo_code = promo
                promo.current_uses += 1
                promo.save()
            else:
                booking.total_cost = total_cost

            # Zaman dilimi farkındalığıyla iptal son tarihini belirleyin
            check_in_datetime = timezone.make_aware(
                timezone.datetime.combine(booking.check_in, timezone.datetime.min.time())
            )
            booking.cancellation_deadline = check_in_datetime - timezone.timedelta(days=1)

            booking.save()
            
            try:
                # Onay e-postasını güncelle
                send_booking_confirmation(booking, room.get_current_price(booking.check_in))
            except Exception as e:
                # Hatayı kaydedin ancak rezervasyon sürecini durdurmayın
                print(f"E-posta gönderimi başarısız oldu: {e}")
            
            return redirect('booking_success', booking_id=booking.id)
    else:
        form = BookingForm(initial={'room': room})

    # Mevcut rezervasyonları al
    bookings = Booking.objects.filter(
        room=room,
        status='confirmed'
    ).values('check_in', 'check_out')
    
    # Takvim için events listesi oluştur
    events = []
    for booking in bookings:
        events.append({
            'title': 'Dolu',
            'start': booking['check_in'].strftime('%Y-%m-%d'),
            'end': booking['check_out'].strftime('%Y-%m-%d'),
            'display': 'background',
            'color': '#e9ecef'
        })
    
    # Events listesini JSON'a çevir
    bookings_json = json.dumps(events)

    return render(request, 'hotel_booking/book_room.html', {
        'form': form,
        'room': room,
        'bookings_json': bookings_json,
        'avg_rating': avg_rating,
        'reviews': reviews
    })

@login_required
def add_review(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    # Check if user has stayed in this room
    has_stayed = Booking.objects.filter(
        user=request.user,
        room=room,
        status='confirmed',
        check_out__lt=timezone.now()
    ).exists()
    
    if not has_stayed:
        messages.warning(request, 'Sadece konakladığınız odaları inceleyebilirsiniz.')
        return redirect('room_details', room_id=room_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                review = form.save(commit=False)
                review.user = request.user
                review.room = room
                review.save()  # Bu save işlemi otomatik olarak AI analizini güncelleyecek
                messages.success(request, 'Yorumunuz için teşekkür ederiz!')
                return redirect('room_details', room_id=room_id)
            except Exception as e:
                print(f"Yorum kaydedilirken hata oluştu: {str(e)}")
                messages.warning(request, 'Yorumunuz kaydedilirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.')
    else:
        form = ReviewForm()

    return render(request, 'hotel_booking/add_review.html', {
        'form': form,
        'room': room
    })

def room_details(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    reviews = room.review_set.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    
    # Sezonluk fiyatı kontrol et
    room.current_price = room.get_current_price(timezone.now().date())
    
    # Oda için rezervasyonları al
    bookings = Booking.objects.filter(
        room=room,
        status='confirmed'
    ).values('check_in', 'check_out')
    
    # Takvim için events listesi oluştur
    events = []
    for booking in bookings:
        events.append({
            'title': 'Dolu',
            'start': booking['check_in'].strftime('%Y-%m-%d'),
            'end': booking['check_out'].strftime('%Y-%m-%d'),
            'extendedProps': {
                'status': 'booked'
            }
        })
    
    # Events listesini JSON'a çevir
    bookings_json = json.dumps(events)

    return render(request, 'hotel_booking/room_details.html', {
        'room': room,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'ai_analysis': room.ai_analysis,
        'bookings_json': bookings_json
    })

# Rezervasyon onay e-postaları göndermek için yardımcı fonksiyon
def send_booking_confirmation(booking, current_price):
    subject = f'Booking Confirmation - {booking.room.name}'
    
    # Günlük fiyat bilgisi
    daily_price_info = ""
    if current_price != booking.room.price:
        if current_price < booking.room.price:
            daily_price_info = f"(Sezon indirimi: {booking.room.price} TL yerine {current_price} TL)"
        else:
            daily_price_info = f"(Sezon fiyatı: {current_price} TL)"
    
    message = f"""
    Merhaba {booking.user.get_full_name()},

    Rezervasyonunuz onaylanmıştır!

    Oda Bilgileri:
    - Oda Adı: {booking.room.name}
    - Giriş Tarihi: {booking.check_in}
    - Çıkış Tarihi: {booking.check_out}
    - Günlük Fiyat: {current_price} TL {daily_price_info}
    - Toplam Ücret: {booking.total_cost} TL

    Bizi tercih ettiğiniz için teşekkür ederiz. Size keyifli bir konaklama dileriz!

    Saygılarımızla,  
    Otel Ekibi
    """
    send_mail(
        subject,
        message,
        'from@example.com',
        [booking.user.email],
        fail_silently=False,
    )

# Admin Görünüm: Tüm Odaları Yönet
@staff_member_required
def manage_rooms(request):
    all_rooms = Room.objects.all().order_by('name')  # Sidebar için tüm odalar
    rooms = Room.objects.annotate(
        active_bookings=Count(
            'booking',
            filter=models.Q(
                booking__status='confirmed',
                booking__check_in__lte=timezone.now().date(),
                booking__check_out__gte=timezone.now().date()
            )
        )
    ).all().order_by('name')
    
    for room in rooms:
        room.status = 'dolu' if room.active_bookings > 0 else 'müsait'
        
    return render(request, 'hotel_booking/manage_rooms.html', {
        'rooms': rooms,
        'all_rooms': all_rooms,  # Sidebar için eklendi
        'section': 'manage_rooms'
    })

# Admin görünümü: Rezervasyonu Onayla veya Reddet
@login_required
def approve_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    action = request.GET.get('action')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if action == 'approve':
        booking.status = 'confirmed'
        booking.save()
        if is_ajax:
            return JsonResponse({
                'status': 'success',
                'message': 'Rezervasyon onaylandı.',
                'new_status': 'confirmed',
                'new_status_text': 'Onaylandı',
                'new_status_class': 'bg-success'
            })
        messages.success(request, 'Rezervasyon onaylandı.')
    elif action == 'reject':
        booking.status = 'cancelled'
        booking.save()
        if is_ajax:
            return JsonResponse({
                'status': 'success',
                'message': 'Rezervasyon reddedildi.',
                'new_status': 'cancelled',
                'new_status_text': 'İptal Edildi',
                'new_status_class': 'bg-danger'
            })
        messages.success(request, 'Rezervasyon reddedildi.')
    elif action == 'pending':
        booking.status = 'pending'
        booking.save()
        if is_ajax:
            return JsonResponse({
                'status': 'success',
                'message': 'Rezervasyon askıya alındı.',
                'new_status': 'pending',
                'new_status_text': 'Beklemede',
                'new_status_class': 'bg-warning'
            })
        messages.success(request, 'Rezervasyon askıya alındı.')

    if is_ajax:
        return JsonResponse({'status': 'error', 'message': 'Geçersiz işlem.'})
    return render(request, 'hotel_booking/approve_booking.html', {'booking': booking})

# Admin görünümü : Tüm Rezervasyonları Görüntüle
@staff_member_required
def view_bookings(request):
    all_rooms = Room.objects.all().order_by('name')  # Sidebar için tüm odalar
    bookings = Booking.objects.all().order_by('-created_at')
    return render(request, 'hotel_booking/view_bookings.html', {
        'bookings': bookings,
        'all_rooms': all_rooms,  # Sidebar için eklendi
        'section': 'bookings'
    })

@login_required
def admin_home(request):
    today = timezone.now().date()
    
    # Tüm odaları al
    all_rooms = Room.objects.all().order_by('name')
    rooms = Room.objects.all()
    
    # Sadece onaylanmış rezervasyonları al
    bookings = Booking.objects.filter(status='confirmed').order_by('-created_at')
    
    # İstatistikler için gerekli veriler
    active_bookings_count = Booking.objects.filter(
        status='confirmed',
        check_in__lte=today,
        check_out__gte=today
    ).count()
    
    # Bugünkü giriş ve çıkışları al
    todays_checkins = Booking.objects.filter(
        status='confirmed',
        check_in=today
    ).select_related('user', 'room').order_by('check_in')
    
    # Çıkış yapacaklar için tarihi düzelt
    todays_checkouts = Booking.objects.filter(
        status='confirmed',
        check_out=today  # Bu tarih kontrolü doğru
    ).select_related('user', 'room').order_by('check_out')
    
    context = {
        'rooms': rooms,
        'bookings': bookings,
        'all_rooms': all_rooms,
        'active_bookings_count': active_bookings_count,
        'today_checkins': todays_checkins.count(),
        'today_checkouts': todays_checkouts.count(),
        'todays_checkins': todays_checkins,
        'todays_checkouts': todays_checkouts,
        'section': 'dashboard',
        'today': today,
    }
    
    return render(request, 'hotel_booking/admin_home.html', context)

@staff_member_required
@require_POST
def delete_room(request, id):
    room = get_object_or_404(Room, id=id)
    try:
        room.delete()
        messages.success(request, f'{room.name} başarıyla silindi.')
    except Exception as e:
        messages.warning(request, f'Oda silinirken bir hata oluştu: {str(e)}')
    return redirect('manage_rooms')

def home(request):
    return render(request, 'hotel_booking/home.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Kayıt başarılı!')
            return redirect('index')
    else:
        form = UserRegistrationForm()
    return render(request, 'hotel_booking/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Giriş başarılı!')
            return redirect('index')
    else:
        form = UserLoginForm()
    return render(request, 'hotel_booking/login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'Oturumunuz kapatıldı.')
    return redirect('index')

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil başarıyla güncellendi!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'hotel_booking/profile.html', {'form': form})

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.status == 'pending':
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Rezervasyon başarıyla iptal edildi.')
    else:
        messages.warning(request, 'Bu rezervasyon iptal edilemez.')
    return redirect('profile')


@staff_member_required
def reports_dashboard(request):
    # Genel istatistikler
    total_bookings = Booking.objects.count()
    total_revenue = Booking.objects.filter(status='confirmed').aggregate(
        total=Sum('total_cost'))['total'] or 0
    avg_rating = Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Aylık gelir raporu
    monthly_revenue = Booking.objects.filter(
        status='confirmed'
    ).annotate(
        month=TruncMonth('check_in')
    ).values('month').annotate(
        revenue=Sum('total_cost')
    ).order_by('month')

    # En popüler odalar
    popular_rooms = Room.objects.annotate(
        booking_count=Count('booking'),
        avg_rating=Avg('review__rating'),
        total_revenue=Sum(
            Case(
                When(booking__status='confirmed', then='booking__total_cost'),
                default=0,
                output_field=models.DecimalField(),
            )
        )
    ).order_by('-booking_count')[:5]

    # Doluluk oranı hesaplama
    total_rooms = Room.objects.count()
    today = timezone.now().date()
    
    # Son 30 günlük doluluk oranı hesaplama
    thirty_days_ago = today - timezone.timedelta(days=30)
    
    # Her gün için dolu oda sayısını hesapla
    daily_occupancy = []
    current_date = thirty_days_ago
    
    while current_date <= today:
        occupied_rooms = Booking.objects.filter(
            status='confirmed',
            check_in__lte=current_date,
            check_out__gt=current_date
        ).count()
        
        daily_occupancy.append(occupied_rooms)
        current_date += timezone.timedelta(days=1)
    
    # Ortalama doluluk oranını hesapla
    if total_rooms > 0 and daily_occupancy:
        avg_occupied_rooms = sum(daily_occupancy) / len(daily_occupancy)
        occupancy_rate = (avg_occupied_rooms / total_rooms) * 100
    else:
        occupancy_rate = 0

    context = {
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'avg_rating': avg_rating,
        'monthly_revenue': monthly_revenue,
        'popular_rooms': popular_rooms,
        'occupancy_rate': occupancy_rate,
    }
    
    return render(request, 'hotel_booking/reports/dashboard.html', context)

@staff_member_required
def booking_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    
    bookings = Booking.objects.all().order_by('-created_at')
    
    if start_date:
        bookings = bookings.filter(check_in__gte=start_date)
    if end_date:
        bookings = bookings.filter(check_out__lte=end_date)
    if status:
        bookings = bookings.filter(status=status)
    
    total_revenue = bookings.aggregate(total=Sum('total_cost'))['total'] or 0
    booking_count = bookings.count()
    average_revenue = total_revenue / booking_count if booking_count > 0 else 0
    
    context = {
        'bookings': bookings,
        'total_revenue': total_revenue,
        'booking_count': booking_count,
        'average_revenue': average_revenue,
    }
    
    return render(request, 'hotel_booking/reports/booking_report.html', context)

@staff_member_required
def revenue_report(request):
    # Aylık gelir raporu
    monthly_revenue = Booking.objects.filter(
        status='confirmed'
    ).annotate(
        month=TruncMonth('check_in')
    ).values('month').annotate(
        revenue=Sum('total_cost'),
        booking_count=Count('id')
    ).order_by('month')
    
    # Oda tipine göre gelir
    room_type_revenue = Booking.objects.filter(
        status='confirmed'
    ).values(
        'room__room_type'
    ).annotate(
        revenue=Sum('total_cost'),
        booking_count=Count('id')
    ).order_by('-revenue')
    
    context = {
        'monthly_revenue': monthly_revenue,
        'room_type_revenue': room_type_revenue,
    }
    
    return render(request, 'hotel_booking/reports/revenue_report.html', context)

@staff_member_required
def download_booking_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    
    bookings = Booking.objects.all().order_by('-created_at')
    if start_date:
        bookings = bookings.filter(check_in__gte=start_date)
    if end_date:
        bookings = bookings.filter(check_out__lte=end_date)
    if status:
        bookings = bookings.filter(status=status)

    pdf = generate_booking_report_pdf(bookings, start_date, end_date)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="booking_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    response.write(pdf)
    return response

@staff_member_required
def download_revenue_report(request):
    # Aylık gelir raporu
    monthly_revenue = Booking.objects.filter(
        status='confirmed'
    ).annotate(
        month=TruncMonth('check_in')
    ).values('month').annotate(
        revenue=Sum('total_cost'),
        booking_count=Count('id')
    ).order_by('month')
    
    # Oda tipine göre gelir
    room_type_revenue = Booking.objects.filter(
        status='confirmed'
    ).values(
        'room__room_type'
    ).annotate(
        revenue=Sum('total_cost'),
        booking_count=Count('id')
    ).order_by('-revenue')

    pdf = generate_revenue_report_pdf(monthly_revenue, room_type_revenue)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="revenue_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    response.write(pdf)
    return response

@login_required
def booking_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Konaklama süresince günlük fiyatları hesapla
    daily_prices = []
    total_cost = 0
    current_date = booking.check_in
    
    while current_date < booking.check_out:
        daily_price = booking.room.get_current_price(current_date)
        daily_prices.append({
            'date': current_date,
            'price': daily_price,
            'is_seasonal': daily_price != booking.room.price
        })
        total_cost += daily_price
        current_date += timezone.timedelta(days=1)
    
    # Promosyon kodu varsa indirim uygula
    original_total = total_cost
    if booking.promo_code:
        discount = (total_cost * booking.promo_code.discount_percentage) / 100
        total_cost -= discount
    
    # Toplam tutarı güncelle
    booking.total_cost = total_cost
    booking.save()
    
    return render(request, 'hotel_booking/booking_success.html', {
        'booking': booking,
        'daily_prices': daily_prices,
        'original_total': original_total
    })

@staff_member_required
def add_room(request):
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES)
        if form.is_valid():
            room = form.save()
            messages.success(request, 'Oda başarıyla eklendi!')
            return redirect('manage_rooms')
    else:
        form = RoomForm()
    
    return render(request, 'hotel_booking/add_room.html', {
        'form': form,
        'title': 'Add New Room'
    })

@staff_member_required
def edit_room(request, id):
    room = get_object_or_404(Room, id=id)
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oda başarıyla güncellendi!')
            return redirect('manage_rooms')
    else:
        form = RoomForm(instance=room)
    
    return render(request, 'hotel_booking/add_room.html', {
        'form': form,
        'title': 'Edit Room',
        'room': room
    })

@require_http_methods(["POST"])
@csrf_exempt
def chat_api(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Mesaj boş olamaz'}, status=400)

        # Mevcut odaları al
        rooms = Room.objects.all()
        room_details = []
        
        for room in rooms:
            try:
                room_info = {
                    'name': room.name,
                    'type': room.get_room_type_display(),
                    'price': float(room.price),
                    'current_price': float(room.get_current_price(timezone.now().date())),
                    'capacity': room.capacity,
                    'has_balcony': room.has_balcony,
                    'has_sea_view': room.has_sea_view,
                    'booking_url': f'/hotel_booking/room/{room.id}',
                    'description': room.description,
                    'rating': room.review_set.aggregate(Avg('rating'))['rating__avg']
                }
                room_details.append(room_info)
            except Exception as e:
                print(f"Oda bilgileri alınırken hata: {str(e)}")
                continue

        # Oda bilgilerini JSON formatına çevir
        rooms_json = json.dumps(room_details, ensure_ascii=False)

        try:
            genai.configure(api_key=settings.GEMINI_API_SETTINGS['api_key'])
            
            model = genai.GenerativeModel(
                model_name='gemini-pro',
                safety_settings=settings.GEMINI_API_SETTINGS['safety_settings'],
                generation_config={
                    'temperature': 0.9,
                    'top_p': 1,
                    'top_k': 40,
                    'max_output_tokens': 2048,  # Maksimum çıktı uzunluğunu artırdım
                    'stop_sequences': []
                }
            )
            
            prompt = f"""Sen bir otel asistanısın. Aşağıdaki soruya kısa ve öz bir şekilde Türkçe yanıt ver:

            Soru: {user_message}

            Yanıtın profesyonel, kısa, öz ve net olmalı. Her cevap en fazla 2-3 cümle olmalı.
            Otel hizmetleri, rezervasyonlar, odalar ve genel bilgiler hakkında kısa bilgi verebilirsin.
            Eğer Otel hizmetleri dışında bilgi isteniyorsa "Üzgünüm, yalnızca otel hakkında bilgi verebilirim." yaz.

            Mevcut odalarımız:
            {rooms_json}

            Eğer belirli bir oda tipi veya özellik hakkında sorarsa, sadece en uygun 1-2 odayı öner.
            Odaları önerirken şu formatta yanıt ver:
            "Size uygun odalarımız:
            - [Oda adı] - [Fiyat] TL <link>/hotel_booking/room/[oda_id]</link>
            [Kısa özellik açıklaması]"

            Tüm odaları göstermek istediğinde:
            "Tüm odalarımızı görmek için tıklayın: <link></link>"

            İletişim için:
            "İletişim: <link>/hotel_booking/contact</link>"

            Kayıt için:
            "<link>/hotel_booking/register</link>"

            Giriş için:
            "<link>/hotel_booking/login</link>"

            NOT: Yanıtında sadece metin ve <link> etiketlerini kullan. Her yanıt kısa ve öz olmalı.
            """
            
            response = model.generate_content(prompt)
            
            if response and hasattr(response, 'text'):
                # Link formatını HTML'e çevir
                processed_response = response.text.replace(
                    '<link>', '<a href="'
                ).replace(
                    '</link>', '/" class="btn btn-brown btn-sm" style="background-color: #8B4513; color: white;">Tıkla</a>'
                )
                return JsonResponse({'response': processed_response})
            else:
                raise Exception('API geçerli bir yanıt vermedi')

        except Exception as api_error:
            print(f"API Hatası: {str(api_error)}")
            return JsonResponse({
                'error': f'API hatası: {str(api_error)}',
                'status': 'error'
            }, status=500)
            
    except json.JSONDecodeError as e:
        print(f"JSON Decode Hatası: {str(e)}")
        return JsonResponse({
            'error': 'Geçersiz JSON formatı',
            'status': 'error'
        }, status=400)

@require_http_methods(["GET", "POST"])
def contact(request):
    if request.method == "POST":
        try:
            # JSON verilerini al
            data = json.loads(request.body)
            
            # Verileri kontrol et
            name = data.get('name')
            email = data.get('email')
            subject = data.get('subject')
            message = data.get('message')
            
            # Debug için
            print(f"Gelen veriler: {name}, {email}, {subject}, {message}")
            
            # Veri doğrulama
            if not all([name, email, subject, message]):
                return JsonResponse({
                    'success': False,
                    'error': 'Tüm alanları doldurunuz.'
                })
            
            # Mesajı kaydet
            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Mesajınız başarıyla gönderildi.'
            })
            
        except json.JSONDecodeError as e:
            print(f"JSON decode hatası: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Geçersiz veri formatı.'
            }, status=400)
            
        except Exception as e:
            print(f"Genel hata: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return render(request, 'hotel_booking/contact.html')

@staff_member_required
def contact_messages(request):
    # Django mesajlarını temizle
    storage = messages.get_messages(request)
    storage.used = True  # Tüm mesajları kullanılmış olarak işaretle
    
    contact_messages = ContactMessage.objects.all().order_by('-created_at')
    return render(request, 'hotel_booking/admin/contact_messages.html', {
        'messages': contact_messages,
        'hide_django_messages': True
    })

@staff_member_required
@require_POST
def mark_messages_read(request):
    data = json.loads(request.body)
    message_ids = data.get('ids', [])
    
    ContactMessage.objects.filter(id__in=message_ids).update(is_read=True)
    return JsonResponse({'success': True})

@staff_member_required
@require_POST
def delete_messages(request):
    data = json.loads(request.body)
    message_ids = data.get('ids', [])
    
    ContactMessage.objects.filter(id__in=message_ids).delete()
    return JsonResponse({'success': True})

@staff_member_required
def manage_seasonal_prices(request, room_id=None):
    if room_id:
        room = get_object_or_404(Room, id=room_id)
        seasonal_prices = SeasonalPrice.objects.filter(room=room).order_by('start_date')
    else:
        room = None
        seasonal_prices = SeasonalPrice.objects.all().order_by('start_date')
    
    # Tüm odaları ortalama puanlarıyla birlikte al
    rooms = Room.objects.annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review')
    ).all()
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        price = request.POST.get('price')
        room_id = request.POST.get('room')
        
        if all([start_date, end_date, price, room_id]):
            room = Room.objects.get(id=room_id)
            SeasonalPrice.objects.create(
                room=room,
                start_date=start_date,
                end_date=end_date,
                price=price
            )
            messages.success(request, 'Sezonluk fiyat başarıyla eklendi.')
            return redirect('manage_seasonal_prices', room_id=room_id)
        else:
            messages.error(request, 'Lütfen tüm alanları doldurun.')
    
    return render(request, 'hotel_booking/manage_seasonal_prices.html', {
        'rooms': rooms,
        'selected_room': room,
        'seasonal_prices': seasonal_prices
    })

@staff_member_required
@require_POST
def delete_seasonal_price(request, price_id):
    seasonal_price = get_object_or_404(SeasonalPrice, id=price_id)
    room_id = seasonal_price.room.id
    seasonal_price.delete()
    messages.success(request, 'Sezonluk fiyat başarıyla silindi.')
    return redirect('manage_seasonal_prices', room_id=room_id)

@login_required
@staff_member_required
def delete_cancelled_bookings(request):
    """İptal edilen tüm rezervasyonları siler."""
    cancelled_bookings = Booking.objects.filter(status='cancelled')
    count = cancelled_bookings.count()
    cancelled_bookings.delete()
    
    messages.success(request, f'{count} iptal edilmiş rezervasyon başarıyla silindi.')
    return redirect('view_bookings')

