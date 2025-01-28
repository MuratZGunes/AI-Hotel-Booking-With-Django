from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.http import HttpResponse
from io import BytesIO
import datetime
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import locale
import google.generativeai as genai
from django.db.models import Avg
from .models import Room
from reportlab.pdfbase.pdfmetrics import registerFontFamily
locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')

# Roboto fontunu kaydet
pdfmetrics.registerFont(TTFont('Roboto', 'static/fonts/Roboto-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Roboto-Bold', 'static/fonts/Roboto-Bold.ttf'))

# Stil oluştur
styles = getSampleStyleSheet()
heading1_style = ParagraphStyle(
    'CustomHeading1',
    parent=styles['Heading1'],
    fontName='Roboto-Bold',
    encoding='utf-8'
)
heading2_style = ParagraphStyle(
    'CustomHeading2',
    parent=styles['Heading2'],
    fontName='Roboto-Bold',
    encoding='utf-8'
)
normal_style = ParagraphStyle(
    'CustomNormal',
    parent=styles['Normal'],
    fontName='Roboto',
    encoding='utf-8'
)

# Stilleri stylesheet'e ekle
styles.add(heading1_style)
styles.add(heading2_style)
styles.add(normal_style)

def get_turkish_month(date):
    """Ay ismini Türkçe olarak döndürür"""
    months = {
        1: 'Ocak',
        2: 'Şubat',
        3: 'Mart',
        4: 'Nisan',
        5: 'Mayıs',
        6: 'Haziran',
        7: 'Temmuz',
        8: 'Ağustos',
        9: 'Eylül',
        10: 'Ekim',
        11: 'Kasım',
        12: 'Aralık'
    }
    return f"{months[date.month]} {date.year}"

def get_room_type_display(room_type):
    """Oda tipini Türkçe olarak döndür"""
    room_types = {
        'single': 'Tek Kişilik',
        'double': 'Çift Kişilik',
        'suite': 'Suit',
        'family': 'Aile',
        'deluxe': 'Delüks'
    }
    return room_types.get(room_type, room_type)

def generate_revenue_report_pdf(monthly_revenue, room_type_revenue):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, encoding='utf-8')
    elements = []

    elements.append(Paragraph("Gelir Raporu", styles['CustomHeading1']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Aylık Gelir", styles['CustomHeading2']))
    elements.append(Spacer(1, 10))

    monthly_data = [['Ay', 'Gelir', 'Rezervasyon Sayısı']]
    total_revenue = 0
    total_bookings = 0

    for item in monthly_revenue:
        month_str = get_turkish_month(item['month'])
        monthly_data.append([
            Paragraph(month_str, styles['CustomNormal']),
            f"{item['revenue']:.2f} TL",
            str(item['booking_count'])
        ])
        total_revenue += item['revenue']
        total_bookings += item['booking_count']

    monthly_table = Table(monthly_data)
    monthly_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Roboto-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(monthly_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Özet", styles['CustomHeading2']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Toplam Gelir: {total_revenue:.2f} TL", styles['CustomNormal']))
    elements.append(Paragraph(f"Toplam Rezervasyon Sayısı: {total_bookings}", styles['CustomNormal']))
    elements.append(Paragraph(f"Rezervasyon Başına Ortalama Gelir: {(total_revenue/total_bookings if total_bookings else 0):.2f} TL", styles['CustomNormal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Oda Türüne Göre Gelir", styles['CustomHeading2']))
    elements.append(Spacer(1, 10))

    room_type_data = [['Oda Türü', 'Gelir', 'Rezervasyon Sayısı', 'Rezervasyon Başına Ortalama Gelir']]
    for item in room_type_revenue:
        avg_revenue = item['revenue'] / item['booking_count'] if item['booking_count'] else 0
        room_type = get_room_type_display(item['room__room_type'])
        room_type_data.append([
            Paragraph(room_type, styles['CustomNormal']),
            f"{item['revenue']:.2f} TL",
            str(item['booking_count']),
            f"{avg_revenue:.2f} TL"
        ])

    room_type_table = Table(room_type_data)
    room_type_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Roboto-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(room_type_table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

def send_booking_confirmation(booking):
    context = {
        'booking': booking,
        'year': timezone.now().year,
        'site_url': settings.SITE_URL,
    }

    html_message = render_to_string('hotel_booking/emails/booking_confirmation.html', context)
    plain_message = render_to_string('hotel_booking/emails/booking_confirmation.txt', context)

    send_mail(
        subject=f'Rezervasyon Onayı - {booking.room.name}',
        message=plain_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.user.email],
        fail_silently=False,
    )

def send_booking_reminder(booking):
    context = {
        'booking': booking,
        'year': timezone.now().year,
        'site_url': settings.SITE_URL,
    }

    html_message = render_to_string('hotel_booking/emails/booking_reminder.html', context)
    plain_message = render_to_string('hotel_booking/emails/booking_reminder.txt', context)

    send_mail(
        subject=f"Hatırlatma: Yarın {booking.room.name}'deki Konaklamanız",
        message=plain_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.user.email],
        fail_silently=False,
    )

def generate_booking_report_pdf(bookings, start_date=None, end_date=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, encoding='utf-8')
    elements = []

    title = "Rezervasyon Raporu"
    if start_date and end_date:
        title += f" ({start_date} - {end_date})"
    elements.append(Paragraph(title, styles['CustomHeading1']))
    elements.append(Spacer(1, 20))

    total_revenue = sum(booking.total_cost for booking in bookings)
    summary = [
        f"Toplam Rezervasyon Sayısı: {len(bookings)}",
        f"Toplam Gelir: {total_revenue:.2f} TL",
        f"Ortalama Rezervasyon Değeri: {(total_revenue/len(bookings) if bookings else 0):.2f} TL"
    ]
    for line in summary:
        elements.append(Paragraph(line, styles['CustomNormal']))
    elements.append(Spacer(1, 20))

    # Tablo sütun genişliklerini ayarla
    col_widths = [40, 80, 80, 60, 60, 60, 60]  # Toplam genişlik yaklaşık 440 birim
    data = [['No', 'Misafir', 'Oda', 'Giriş', 'Çıkış', 'Ücret', 'Durum']]
    for booking in bookings:
        data.append([
            Paragraph(str(booking.id), styles['CustomNormal']),
            Paragraph(booking.user.get_full_name(), styles['CustomNormal']),
            Paragraph(booking.room.name, styles['CustomNormal']),
            Paragraph(booking.check_in.strftime('%d-%m-%Y'), styles['CustomNormal']),
            Paragraph(booking.check_out.strftime('%d-%m-%Y'), styles['CustomNormal']),
            Paragraph(f"{booking.total_cost} TL", styles['CustomNormal']),
            Paragraph('Onaylandı' if booking.status == 'confirmed' else ('Beklemede' if booking.status == 'pending' else 'İptal'), styles['CustomNormal'])
        ])

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Roboto-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),  # Başlık font boyutu küçültüldü
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),  # İçerik font boyutu küçültüldü
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),  # Sol padding küçültüldü
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),  # Sağ padding küçültüldü
    ]))
    elements.append(table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

def update_room_ai_analysis(room):
    """
    Oda için tüm yorumları analiz eder ve AI analizi günceller
    """
    try:
        reviews = room.review_set.all()
        if not reviews.exists():
            room.ai_analysis = None
            room.save()
            return

        # Yorumları ve puanları topla
        review_texts = [f"Yorum: {review.comment}\nPuan: {review.rating}/5" for review in reviews]
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        
        # Gemini AI yapılandırması
        genai.configure(api_key=settings.GEMINI_API_SETTINGS['api_key'])
        model = genai.GenerativeModel('gemini-pro',
                                    safety_settings=settings.GEMINI_API_SETTINGS['safety_settings'],
                                    generation_config=settings.GEMINI_API_SETTINGS['generation_config'])
        
        # Prompt hazırla
        prompt = f"""
        Aşağıdaki otel odası yorumlarını analiz et ve genel bir değerlendirme yap.
        Ortalama puan: {avg_rating:.1f}/5
        
        {"\n\n".join(review_texts)}
        
        Lütfen şu konulara değinerek kısa bir analiz yap:
        1. Genel memnuniyet düzeyi
        2. Öne çıkan olumlu yönler
        3. Varsa iyileştirme gereken alanlar
        4. Genel tavsiye
        5. Varsa çok az negatif yönler
        
        Yanıtını 3-4 cümle ile sınırla.
        """
        
        try:
            # AI analizi al
            response = model.generate_content(prompt)
            if response and hasattr(response, 'text'):
                analysis = response.text
                print(f"AI Analizi başarıyla oluşturuldu: {analysis}")  # Debug için
            else:
                raise Exception("API yanıtı geçersiz format")
            
            # Analizi kaydet
            room.ai_analysis = analysis
            room.save()
            print(f"AI Analizi başarıyla kaydedildi: {room.ai_analysis}")  # Debug için
            
        except Exception as api_error:
            print(f"Gemini API hatası: {str(api_error)}")
            room.ai_analysis = None
            room.save()
            raise Exception(f"AI analizi oluşturulamadı: {str(api_error)}")
            
    except Exception as e:
        print(f"Genel hata: {str(e)}")
        room.ai_analysis = None
        room.save()
        raise
