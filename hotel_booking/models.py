from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class Amenity(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="Örnek, Wi-Fi", verbose_name="Özellik Adı")
    icon = models.CharField(max_length=50, verbose_name="İkon")  # FontAwesome  ikon sınıfı

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Özellikler"

class Room(models.Model):
    ROOM_TYPES = [
        ('single', 'Tek Kişilik'),
        ('double', 'Çift Kişilik'), 
        ('suite', 'Suit'),
        ('family', 'Aile'),
    ]

    name = models.CharField(max_length=100, verbose_name="Oda Adı")
    description = models.TextField(verbose_name="Açıklama")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fiyat")
    image = models.ImageField(upload_to='room_images/', blank=True, null=True, verbose_name="Resim")
    capacity = models.IntegerField(default=2, verbose_name="Kapasite")
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, verbose_name="Oda Tipi")
    amenities = models.ManyToManyField(Amenity, verbose_name="Özellikler")
    floor = models.IntegerField(verbose_name="Kat")
    has_balcony = models.BooleanField(default=False, verbose_name="Balkon")
    has_sea_view = models.BooleanField(default=False, verbose_name="Deniz Manzaralı")
    ai_analysis = models.TextField(blank=True, null=True, verbose_name="AI Yorum Analizi")
    
    def __str__(self):
        return self.name

    def is_available(self, check_in, check_out):    # Oda belirli bir tarih aralığında müsait mi?
        overlapping_bookings = self.booking_set.filter(
            check_in__lte=check_out,
            check_out__gte=check_in,
            status='confirmed'
        )
        return not overlapping_bookings.exists()   

    def get_current_price(self, date):            # Oda için belirli bir tarihte geçerli olan fiyatı döndürür
        seasonal_price = self.seasonalprice_set.filter(
            start_date__lte=date,
            end_date__gte=date
        ).first()
        return seasonal_price.price if seasonal_price else self.price
    
    class Meta:
        verbose_name_plural = "Odalar"

class SeasonalPrice(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name="Oda")
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(verbose_name="Bitiş Tarihi")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fiyat")

    def __str__(self):
        return f"{self.room.name} ({self.start_date} - {self.end_date})"
    
    class Meta:
        verbose_name_plural = "Sezon Fiyatı"

class CancellationPolicy(models.Model):
    hours_before = models.IntegerField(verbose_name="Önceki Saatler")
    refund_percentage = models.IntegerField(verbose_name="İade Yüzdesi",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    def __str__(self):
        return f"{self.hours_before}saat önce - {self.refund_percentage}% geri ödeme"

    class Meta:
        verbose_name_plural = "İptal Politikaları"

class PromoCode(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Promosyon Kodu")
    discount_percentage = models.IntegerField(verbose_name="İndirim Yüzdesi",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    valid_from = models.DateTimeField(verbose_name="Geçerli Başlangıç")
    valid_until = models.DateTimeField(verbose_name="Geçerli Bitiş")
    max_uses = models.IntegerField(verbose_name="Maksimum Kullanım")
    current_uses = models.IntegerField(default=0, verbose_name="Mevcut Kullanım")

    def __str__(self):  # Promo kodunun adını ve indirim yüzdesini döndürür
        return f"{self.code} ({self.discount_percentage}% indirim)"

    # Promo kodunun geçerli olup olmadığını kontrol eder
    def is_valid(self): 
        now = timezone.now()
        return (
            self.valid_from <= now <= self.valid_until and
            self.current_uses < self.max_uses
        )
    
    class Meta:
        verbose_name_plural = "Promo Kodları"

class Booking(models.Model):   
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('confirmed', 'Onaylandı'),
        ('cancelled', 'İptal Edildi'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name="Oda")
    check_in = models.DateField(verbose_name="Giriş Tarihi")
    check_out = models.DateField(verbose_name="Çıkış Tarihi")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Toplam Tutar")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Durum")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    promo_code = models.ForeignKey(PromoCode, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Promosyon Kodu")
    cancellation_deadline = models.DateTimeField(null=True, blank=True, verbose_name="İptal Son Tarihi")
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="İade Tutarı")

    def save(self, *args, **kwargs):
        if not self.total_cost:
            # Gün sayısını hesapla
            days = (self.check_out - self.check_in).days
            # Günlük fiyatı al
            daily_price = self.room.price
            # Toplam maliyeti hesapla
            self.total_cost = daily_price * days
            
            # Eğer promosyon kodu varsa ve geçerliyse indirim uygula
            if self.promo_code and self.promo_code.is_valid():
                discount = (self.total_cost * self.promo_code.discount_percentage) / 100
                self.total_cost -= discount
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username}'nin rezervasyonu {self.room.name}"

    @property
    def duration(self):
        return (self.check_out - self.check_in).days

    def calculate_refund(self):
        if self.status != 'onaylandı':
            return 0
        
        hours_until_checkin = (self.check_in - timezone.now().date()).days * 24
        policy = CancellationPolicy.objects.filter(
            hours_before__lte=hours_until_checkin
        ).order_by('-saat önce').first()
        
        if policy:
            return (self.total_cost * policy.refund_percentage) / 100
        return 0
    
    def get_original_cost(self):
        """İndirim uygulanmadan önceki orijinal tutarı hesaplar"""
        nights = (self.check_out - self.check_in).days
        return self.room.get_current_price(self.check_in) * nights

    def get_discount_amount(self):
        """Promosyon kodu ile kazanılan indirim tutarını hesaplar"""
        if not self.promo_code:
            return 0
        original_cost = self.get_original_cost()
        return original_cost - self.total_cost
    
    class Meta:
        verbose_name_plural = "Rezervasyonlar"

class Review(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name="Oda")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    rating = models.IntegerField(verbose_name="Puan",
        choices=[(i, i) for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(verbose_name="Yorum")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    def save(self, *args, **kwargs):
        try:
            is_new = self.pk is None
            super().save(*args, **kwargs)
            
            if is_new:  # Sadece yeni yorum eklendiğinde AI analizi güncelle
                from .utils import update_room_ai_analysis  # Circular import'u önlemek için local import
                update_room_ai_analysis(self.room)
        except Exception as e:
            print(f"Yorum kaydedilirken hata oluştu: {e}")
            raise  # Hatayı tekrar fırlat

    def __str__(self):
        return f"{self.user.username}'nin incelemesi {self.room.name}"

    class Meta:
        unique_together = ['room', 'user']
        verbose_name_plural = "İncelemeler"

class ContactMessage(models.Model):
    name = models.CharField(max_length=100, verbose_name="İsim")
    email = models.EmailField(verbose_name="E-posta")
    subject = models.CharField(max_length=200, verbose_name="Konu")
    message = models.TextField(verbose_name="Mesaj")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Gönderilme Tarihi")
    is_read = models.BooleanField(default=False, verbose_name="Okundu")
    
    class Meta:
        verbose_name = "İletişim Mesajı"
        verbose_name_plural = "İletişim Mesajları"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.subject
