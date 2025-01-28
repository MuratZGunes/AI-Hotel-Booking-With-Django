# Yapay Zekâ ile Otel Rezervasyonu
[![English](https://img.shields.io/badge/Language-English-blue)](https://github.com/MuratZGunes/HotelBookingWithAi/blob/main/README.md)
## Proje Hakkında

HotelBookingWithAI, otel rezervasyon sürecini hızlandırmak, kolaylaştırmak ve kişiselleştirilmiş bir deneyim sunmak için geliştirilmiş yenilikçi bir web uygulamasıdır. Django framework'ü üzerine inşa edilen bu sistem, kullanıcı dostu bir arayüz aracılığıyla otel odalarını görüntüleme, rezervasyon işlemlerini yönetme ve kullanıcı profillerini düzenleme işlevlerini etkin bir şekilde sunar.

Bu proje, kullanıcıların konaklama deneyimlerini iyileştirmekle kalmayıp, aynı zamanda otel yöneticilerine verimli ve işlevsel bir altyapı sağlamayı hedefler. Kapsamlı özellikleri ile hem kullanıcı hem de işletme ihtiyaçlarını karşılayan modern bir çözüm olarak tasarlanmıştır.

![Web Sitesi Arayüzü](https://github.com/user-attachments/assets/14441e35-f6fd-4fa2-b74b-5c1306eed466)

## Temel Özellikler

- **Yapay Zekâ Destekli Asistan:** Kullanıcı tercihlerini analiz ederek kişiselleştirilmiş öneriler sunar ve anlık destek sağlar.
- **Kullanıcı Dostu Arayüz:** Tüm cihazlarda sorunsuz kullanım için duyarlı ve sezgisel bir tasarım.
- **Oda Arama ve Rezervasyon:** Kolayca oda arama, uygunluğu kontrol etme ve rezervasyon yapma imkanı.
- **Promosyon Kodu Sistemi:** Rezervasyon sırasında indirim kodları kullanabilme.
- **E-posta Entegrasyonu:** Otomatik rezervasyon onayları ve güncellemeler gönderir.
- **Yorum ve Geri Bildirim Analizi:** Yapay zekâ ile yorumları analiz eder ve faydalı içgörüler sunar.
- **Yönetici Paneli:** Otel yöneticileri için rezervasyon yönetimi, detaylı raporlar ve müşteri geri bildirimlerini analiz etme.
- **Detaylı Raporlama:** Rezervasyon trendleri, doluluk oranları ve gelirle ilgili grafik ve istatistiksel analizler sunar.

## Yapay Zekâ Destekli Özellikler

- **Kişiselleştirilmiş Öneriler:** Kullanıcı tercihlerini ve oda yorumlarını analiz ederek en uygun seçenekleri önerir.
- **Yorum Duygu Analizi:** Kullanıcı geri bildirimlerini özetler ve geliştirilmesi gereken alanları belirler.

Yapay zekâ çözümleri **Gemini.ai** araçları ile sağlanmıştır. Sohbet robotu ve yorum duygu analizi bu sistemle gerçekleştirilmiştir.

## Teknoloji Yığını

- **Backend:** Python, Django
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Veritabanı:** SQLite (veya Django ORM ile uyumlu herhangi bir veritabanı)
- **Yapay Zekâ Araçları:** Gemini.ai ile yorum analizi ve sohbet robotu

## Kurulum

1. Reponun bir kopyasını klonlayın:
   ```bash
   git clone https://github.com/MuratZGunes/HotelBookingWithAi.git
   ```
2. Proje dizinine gidin:
   ```bash
   cd HotelBookingWithAi
   ```
3. Gerekli bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
4. Veritabanı migrasyonlarını uygulayın:
   ```bash
   python manage.py migrate
   ```
5. Geliştirme sunucusunu çalıştırın:
   ```bash
   python manage.py runserver
   ```
6. Uygulamaya `http://127.0.0.1:8000/` adresinden erişin.

## Kullanım

### Kullanıcı Rolleri:
- **Misafirler:** Oda arayabilir, rezervasyon yapabilir ve geri bildirim sağlayabilir.
- **Yöneticiler:** Rezervasyonları yönetebilir, kullanıcı geri bildirimlerini analiz edebilir ve rapor oluşturabilir.

## Ekran Görüntüleri

### Yapay Zekâ Sohbet Asistanı
<img src="https://github.com/user-attachments/assets/4d2a7ea8-a1f0-40a8-b41d-75a9c5a52311" alt="Yapay Zekâ Sohbet Asistanı Görseli" width="250"/>

### Yapay Zekâ Yorum Analizi
<img src="https://github.com/user-attachments/assets/2cecabe8-83a2-4b7a-a179-9bb8beca55a5" alt="Yapay Zekâ Yorum Analizi Görseli" width="700"/>

### Web Odalar Sayfası
![Web Odalar Sayfası](https://github.com/user-attachments/assets/dcc2d37b-7228-41f3-8f94-ce8d770cb60c)

### Web Admin Arayüzü
![Web Admin Paneli](https://github.com/user-attachments/assets/37dea45f-b76b-4f98-bd50-b692d3bd5ea1)

## Katkıda Bulunma

Katkılar memnuniyetle karşılanır! Bir özellik eklemeden veya bir hata düzeltmeden önce bir konu açarak tartışınız.

## Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Daha fazla bilgi için LICENSE dosyasına bakabilirsiniz.

## İletişim
**Proje Sahibi:** Murat S. Güneş  
- **GitHub:** [MuratZGunes](https://github.com/MuratZGunes)  
- **E-posta:** muratsegunes@gmail.com

---
