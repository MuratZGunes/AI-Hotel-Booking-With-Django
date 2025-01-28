from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Room, Booking, Review, PromoCode
from django.utils import timezone

class BookingForm(forms.ModelForm):
    promo_code = forms.CharField(
        label='Promosyon Kodu',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Promosyon kodunuz varsa giriniz'})
    )

    class Meta:
        model = Booking
        fields = ['check_in', 'check_out']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        promo_code = cleaned_data.get('promo_code')

        if check_in and check_out:
            if check_in < timezone.now().date():
                raise forms.ValidationError("Giriş tarihi geçmiş bir tarih olamaz.")
            
            if check_out <= check_in:
                raise forms.ValidationError("Çıkış tarihiniz giriş tarihinden sonra olmalıdır.")

            # Oda müsaitlik kontrolü - self.initial'dan room'u al
            room = self.initial.get('room')
            if room and not room.is_available(check_in, check_out):
                raise forms.ValidationError(
                    "Üzgünüz, seçtiğiniz tarihler için bu oda dolu. "
                    "Lütfen takvimden müsait olan tarihleri kontrol ediniz veya "
                    "başka bir oda seçiniz."
                )

        # Promosyon kodu kontrolü
        if promo_code:
            try:
                promo = PromoCode.objects.get(code=promo_code)
                if not promo.is_valid():
                    raise forms.ValidationError("Bu promosyon kodu geçerli değil.")
                cleaned_data['promo_code'] = promo
            except PromoCode.DoesNotExist:
                raise forms.ValidationError("Geçersiz promosyon kodu.")

        return cleaned_data

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'description', 'price', 'image', 'capacity', 
                 'room_type', 'amenities', 'floor', 'has_balcony', 'has_sea_view']
        widgets = {
            'amenities': forms.CheckboxSelectMultiple(),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class RoomSearchForm(forms.Form):
    check_in = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Giriş Tarihi",
        required=True
    )
    check_out = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Çıkış Tarihi",
        required=True
    )
    room_type = forms.ChoiceField(
        choices=[('', 'Tüm Odalar')] + Room.ROOM_TYPES,
        required=False,
        label="Oda Tipi"
    )
    capacity = forms.IntegerField(
        min_value=1,
        required=False,
        label="Kişi Sayısı",
        widget=forms.NumberInput(attrs={'placeholder': 'Kişi sayısı'})
    )
    max_price = forms.DecimalField(
        required=False,
        label="Maksimum Fiyat",
        widget=forms.NumberInput(attrs={'placeholder': 'TL'})
    )
    has_balcony = forms.BooleanField(
        required=False,
        label="Balkonlu",
        initial=False
    )
    has_sea_view = forms.BooleanField(
        required=False,
        label="Deniz Manzaralı",
        initial=False
    )

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')

        if check_in and check_out:
            if check_in < timezone.now().date():
                raise forms.ValidationError("Giriş tarihi geçmiş bir tarih olamaz.")
            if check_out <= check_in:
                raise forms.ValidationError("Çıkış tarihi giriş tarihinden sonra olmalıdır.")

        return cleaned_data

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-mail")
    first_name = forms.CharField(required=True, label="İsminiz")
    last_name = forms.CharField(required=True, label="Soyisminiz")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), label="Kullanıcı Adı")
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Şifre")

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class BookingApprovalForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['status']

class SearchForm(forms.Form):
    check_in = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control rounded-pill'})
    )
    # diğer alanlar...