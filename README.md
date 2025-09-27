# iPhone 17 Stock Monitor

iPhone 17 Pro/Pro Max stok takip sistemi - Playwright ile otomatik stok kontrolü ve Telegram bildirimleri.

## Özellikler

- 🚀 **Playwright** ile hızlı ve güvenilir web scraping
- 📱 **iPhone 17 Pro/Pro Max** tüm modeller için stok takibi
- 📍 **İstanbul Kadıköy** mağaza stok kontrolü
- 📢 **Telegram** bildirimleri
- 🔄 **Otomatik** sürekli stok kontrolü
- 🛡️ **Anti-detection** özellikleri

## Desteklenen Modeller

### iPhone 17 Pro (6.3 inç)
- 256GB Gümüş
- 256GB Kozmik Turuncu  
- 256GB Abis
- 512GB Gümüş
- 512GB Kozmik Turuncu
- 512GB Abis
- 1TB Gümüş
- 1TB Kozmik Turuncu
- 1TB Abis

### iPhone 17 Pro Max (6.9 inç)
- 256GB Gümüş
- 256GB Kozmik Turuncu
- 256GB Abis
- 512GB Gümüş
- 512GB Kozmik Turuncu
- 512GB Abis
- 1TB Gümüş
- 1TB Kozmik Turuncu
- 1TB Abis

## Kurulum

### 1. Gereksinimler
```bash
pip install playwright requests beautifulsoup4 python-telegram-bot fake-useragent python-dotenv
```

### 2. Playwright Browser Kurulumu
```bash
playwright install chromium
```

### 3. Environment Variables
`.env` dosyası oluşturun:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 4. Telegram Bot Kurulumu
1. [@BotFather](https://t.me/botfather) ile bot oluşturun
2. Bot token'ını alın
3. Bot'a mesaj atın ve chat ID'nizi alın

## Kullanım

```bash
python iphone17.py
```

## Nasıl Çalışır

1. **Sayfa Yükleme**: Apple Store sayfasını açar
2. **Stok Kontrolü**: "Uygunluğu kontrol et" butonuna tıklar
3. **Konum Seçimi**: İstanbul > Kadıköy seçer
4. **Stok Analizi**: Mağaza stok durumlarını kontrol eder
5. **Bildirim**: Stok bulunursa Telegram'a mesaj gönderir

## Stok Tespit Mantığı

- ✅ **Stok Var**: "Mevcut", "Bugün", "Yarın" kelimeleri
- ❌ **Stok Yok**: "Gönderim", "Hafta", "Şu anda kullanılamıyor"

## Mağazalar

- Apple Bağdat Caddesi
- Apple Akasya
- Apple Zorlu Center

## Teknik Detaylar

- **Framework**: Playwright (Chromium)
- **Language**: Python 3.8+
- **Async**: Asyncio ile performanslı çalışma
- **Rate Limiting**: 1 saniye ürün arası bekleme
- **Context Pool**: Browser context'leri yeniden kullanma

## Loglar

Tüm işlemler detaylı loglarla takip edilir:
- Stok kontrol sonuçları
- Mağaza bilgileri
- Telegram bildirim durumu
- Hata mesajları

## Lisans

MIT License
