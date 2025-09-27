import asyncio
import logging
import re
import os
import time
import json
from typing import List, Dict, Optional, Set
from datetime import datetime
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv('.env')


from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from fake_useragent import UserAgent

class iPhone17StockMonitor:
    """iPhone 17 Pro/Pro Max Stok Takip Sistemi - Playwright + Requests"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ua = UserAgent()
        
        # Telegram bot configuration
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.telegram_bot = Bot(token=self.telegram_token) if self.telegram_token else None
        
        # Playwright configuration
        self.playwright = None
        self.browser = None
        
        # Requests session configuration
        self.session = requests.Session()
        try:
            # Yeni urllib3 sürümü için
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        except TypeError:
            # Eski urllib3 sürümü için fallback
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # iPhone 17 Pro ve Pro Max URL'leri
        self.iphone_urls = {
            # iPhone 17 Pro (256 GB)
            'iPhone 17 Pro 256GB Gümüş': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-256gb-gümüş',
            'iPhone 17 Pro 256GB Kozmik Turuncu': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-256gb-kozmik-turuncu',
            'iPhone 17 Pro 256GB Abis': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-256gb-abis',
            
            # iPhone 17 Pro (512 GB)
            'iPhone 17 Pro 512GB Gümüş': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-512gb-gümüş',
            'iPhone 17 Pro 512GB Kozmik Turuncu': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-512gb-kozmik-turuncu',
            'iPhone 17 Pro 512GB Abis': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-512gb-abis',
            
            # iPhone 17 Pro (1 TB)
            'iPhone 17 Pro 1TB Gümüş': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-1tb-gümüş',
            'iPhone 17 Pro 1TB Kozmik Turuncu': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-1tb-kozmik-turuncu',
            'iPhone 17 Pro 1TB Abis': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.3-inç-ekran-1tb-abis',
            
            # iPhone 17 Pro Max (256 GB)
            'iPhone 17 Pro Max 256GB Gümüş': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-256gb-gümüş',
            'iPhone 17 Pro Max 256GB Kozmik Turuncu': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-256gb-kozmik-turuncu',
            'iPhone 17 Pro Max 256GB Abis': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-256gb-abis',
            
            # iPhone 17 Pro Max (512 GB)
            'iPhone 17 Pro Max 512GB Gümüş': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-512gb-gümüş',
            'iPhone 17 Pro Max 512GB Kozmik Turuncu': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-512gb-kozmik-turuncu',
            'iPhone 17 Pro Max 512GB Abis': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-512gb-abis',
            
            # iPhone 17 Pro Max (1 TB)
            'iPhone 17 Pro Max 1TB Gümüş': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-1tb-gümüş',
            'iPhone 17 Pro Max 1TB Kozmik Turuncu': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-1tb-kozmik-turuncu',
            'iPhone 17 Pro Max 1TB Abis': 'https://www.apple.com/tr/shop/buy-iphone/iphone-17-pro/6.9-inç-ekran-1tb-abis'
        }
        
        # Stok durumu cache'i
        self.stock_cache: Dict[str, bool] = {}
        
        # Rate limiting (sıralı çalışma için optimize edildi)
        self.request_delay = 1.0  # Her ürün arasında 1 saniye bekle
        self.cycle_delay = 5   # Her tam döngü arasında 5 saniye bekle
        
        # Context pool - performans için (sıralı çalışma için optimize edildi)
        self.context_pool = []
        self.max_contexts = 2  # Sıralı çalışma için yeterli
        
    async def _setup_playwright(self):
        """Playwright'ı başlat"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-logging',
                    '--log-level=3',
                    '--silent'
                ]
            )
    
    async def _create_context(self) -> BrowserContext:
        """Yeni browser context oluştur"""
        await self._setup_playwright()
        
        context = await self.browser.new_context(
            user_agent=self.ua.random,
            viewport={'width': 1920, 'height': 1080},
            locale='tr-TR',
            timezone_id='Europe/Istanbul',
            extra_http_headers={
                'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        # Anti-detection script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        return context
    
    async def _get_context(self) -> BrowserContext:
        """Context pool'dan context al veya yeni oluştur"""
        if self.context_pool:
            return self.context_pool.pop()
        return await self._create_context()
    
    async def _return_context(self, context: BrowserContext):
        """Context'i pool'a geri ver"""
        if len(self.context_pool) < self.max_contexts:
            # Pool'a geri ver
            self.context_pool.append(context)
        else:
            # Pool dolu, context'i kapat
            try:
                await context.close()
            except Exception:
                pass
   
    async def _cleanup_contexts(self):
        """Tüm context'leri temizle"""
        for context in self.context_pool:
            try:
                await context.close()
            except Exception:
                pass
        self.context_pool.clear()
        
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
    
    def _clean_text(self, text: str) -> str:
        """Metni temizle - non-breaking space ve diğer karakterleri kaldır"""
        if not text:
            return ""
        
        # Non-breaking space ve diğer whitespace karakterleri normalize et
        text = text.replace('\u00A0', ' ').strip()
        
        # Footnote/sup tag'lerinden gelen sayıları kaldır
        text = re.sub(r'\s*\d+\s*$', '', text)
        text = re.sub(r'^\s*\d+\s*', '', text)
        
        # Çoklu boşlukları tek boşluğa çevir
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    async def _wait_and_click(self, page: Page, selector: str, timeout: int = 10000, scroll: bool = True) -> bool:
        """Element'i bekle ve tıkla"""
        try:
            # Element'in görünür ve tıklanabilir olmasını bekle
            await page.wait_for_selector(selector, timeout=timeout, state='visible')
            
            if scroll:
                # Element'e scroll yap
                await page.locator(selector).scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
            
            # Tıklamayı dene
            await page.locator(selector).click(timeout=5000)
            return True
                
        except PlaywrightTimeoutError:
            self.logger.debug(f"Element not found or not clickable: {selector}")
            return False
        except Exception as e:
            self.logger.error(f"Click failed for selector {selector}: {e}")
            return False
    
    async def _find_availability_button(self, page: Page) -> bool:
        """Uygunluğu kontrol et butonunu bul ve tıkla"""
        # Sayfayı aşağı kaydır - buton sayfanın alt kısmında
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
        await asyncio.sleep(1)
        
        # Genişletilmiş selector'lar - daha fazla varyasyon
        selectors = [
            'button.rf-pickup-quote-overlay-trigger',
            'button[data-autom^="productLocatorTriggerLink_"]',
            'button:has-text("Uygunluğu kontrol et")',
            'button:has-text("kontrol et")',
            'button.as-buttonlink.icon.icon-after.icon-pluscircle',
            'button[class*="pickup"]',
            'button[class*="availability"]',
            'a[class*="pickup"]',
            'a:has-text("Uygunluğu kontrol et")',
        ]
        
        for selector in selectors:
            try:
                if await self._wait_and_click(page, selector, timeout=3000):
                    self.logger.info(f"Clicked availability button with: {selector}")
                    return True
            except Exception as e:
                self.logger.debug(f"Selector {selector} failed: {e}")
                continue
       
        # Eğer buton hala bulunamazsa, sayfayı daha da aşağı kaydır
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        
        # Son deneme - span text ile parent button
        try:
            span_locator = page.locator('span:text("Uygunluğu kontrol et")')
            if await span_locator.count() > 0:
                button_locator = span_locator.locator('..')
                await button_locator.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await button_locator.click()
                self.logger.info("Clicked availability button via span text")
                return True
        except Exception as e:
            self.logger.debug(f"Final attempt failed: {e}")
        
        return False
    
    async def _select_location(self, page: Page) -> bool:
        """Konum seçim işlemlerini gerçekleştir"""
        try:
            self.logger.info("Starting location selection process...")
            
            # 1. "Konum seçin" butonunu bekle ve tıkla
            self.logger.info("Step 1: Looking for 'Konum seçin' button...")
            location_selectors = [
                'button:has-text("Konum seçin")',
                'button.rf-productlocator-province-selector-button',
                'button:has-text("Konum")',
            ]
            
            location_clicked = False
            for selector in location_selectors:
                if await self._wait_and_click(page, selector, timeout=5000):
                    location_clicked = True
                    self.logger.info(f"SUCCESS: Successfully clicked location button: {selector}")
                    break
            
            if not location_clicked:
                self.logger.error("ERROR: Could not find location selection button")
                return False
            
            self.logger.info("Waiting 0.5 seconds for location options to load...")
            await asyncio.sleep(0.5)  # 1'den 0.5'e düşürüldü
            
            # 2. İSTANBUL'u seç
            self.logger.info("Step 2: Looking for 'İSTANBUL' option...")
            if not await self._wait_and_click(page, 'button:has-text("İSTANBUL")', timeout=5000):
                self.logger.error("ERROR: Could not find Istanbul option")
                return False
            
            self.logger.info("SUCCESS: Successfully selected İSTANBUL")
            self.logger.info("Waiting 0.5 seconds for district options to load...")
            await asyncio.sleep(0.5)  # 1'den 0.5'e düşürüldü
            
            # 3. KADIKÖY'ü seç
            self.logger.info("Step 3: Looking for 'KADIKÖY' option...")
            # Exact match kullan - sadece "KADIKÖY" yazan button
            kadikoy_selectors = [
                'button.rc-province-selector-option-district:has-text("KADIKÖY")',  # Class + exact text
                'button[data-province-name="KADIKÖY"]',
                'button[data-district-name="KADIKÖY"]',
                'button:text("KADIKÖY")',      # Fallback
            ]

            kadikoy_clicked = False

            # Tüm district butonlarını al ve içlerinden "KADIKÖY" olanı bul
            try:
                district_buttons = page.locator('button.rc-province-selector-option-district')
                count = await district_buttons.count()

                for i in range(count):
                    button = district_buttons.nth(i)
                    button_text = await button.text_content()
                    button_text = button_text.strip() if button_text else ""

                    if button_text == "KADIKÖY":
                        await button.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await button.click(timeout=3000)
                        kadikoy_clicked = True
                        self.logger.info("SUCCESS: Found Kadikoy by iterating district buttons")
                        break

            except Exception as e:
                self.logger.debug(f"District button iteration failed: {e}")

            # Fallback selectors
            if not kadikoy_clicked:
                for selector in kadikoy_selectors:
                    try:
                        # İlk elementi al (strict mode violation'dan kaçınmak için)
                        locator = page.locator(selector).first
                        await locator.wait_for(timeout=3000, state='visible')
                        await locator.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await locator.click(timeout=3000)
                        kadikoy_clicked = True
                        self.logger.info(f"SUCCESS: Found Kadikoy with fallback selector: {selector}")
                        break
                    except Exception as e:
                        self.logger.debug(f"Fallback selector {selector} failed: {e}")
                        continue

            if not kadikoy_clicked:
                self.logger.error("ERROR: Could not find Kadikoy option")
                return False



            
            self.logger.info("SUCCESS: Successfully selected KADIKOY")
            self.logger.info("Waiting 1 second for results to load...")
            await asyncio.sleep(1)  # 2'den 1'e düşürüldü
            
            self.logger.info("TARGET: Location selection completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"ERROR: Location selection failed: {e}")
            return False
    
    async def _check_stock_status(self, page: Page, product_name: str, url: str = "") -> Dict:
        """YENİ SISTEM: İstanbul Kadıköy seçtikten sonra input elementlerini kontrol et"""
        try:
            self.logger.info(f"Waiting for stock input elements to load for {product_name}...")
            await asyncio.sleep(1.5)  # Input'ların yüklenmesini bekle (3'ten 1.5'e düşürüldü)
            
            # Stok bilgileri
            stock_available = False
            stock_info = []
            
            self.logger.info(f"NEW SYSTEM: Checking for store input elements for {product_name}...")
            
            # YENİ SISTEM: form-selector-input class'ına sahip input'ları kontrol et
            try:
                # Farklı selector'ları dene
                selectors_to_try = [
                    'input.form-selector-input',
                    'input[type="radio"]',
                    'input[name*="store"]',
                    'input[id*="store"]',
                    '.store-availability input',
                    '.pickup-quote input'
                ]

                store_inputs = []
                for selector in selectors_to_try:
                    try:
                        inputs = await page.locator(selector).all()
                        if inputs:
                            store_inputs = inputs
                            self.logger.info(f"Found {len(store_inputs)} store input elements with selector '{selector}' for {product_name}")
                            break
                    except Exception:
                        continue

                if not store_inputs:
                    self.logger.info(f"No store input elements found with any selector for {product_name}")
                    store_inputs = []
                
                for i, input_element in enumerate(store_inputs):
                    try:
                        # Input'un label'ını bul (mağaza bilgileri burada)
                        input_id = await input_element.get_attribute('id')
                        label_id = f"{input_id}_label"
                        
                        # Label'ı bul
                        try:
                            label_element = page.locator(f'#{label_id}')
                            if await label_element.count() > 0:
                                label_text = await label_element.text_content()
                            else:
                                raise Exception("Label not found with ID")
                        except:
                            # Label bulunamazsa aria-labelledby ile dene
                            try:
                                aria_label = await input_element.get_attribute('aria-labelledby')
                                if aria_label:
                                    label_element = page.locator(f'#{aria_label}')
                                    label_text = await label_element.text_content()
                                else:
                                    raise Exception("No aria-labelledby")
                            except:
                                # Son çare: parent element'in text'ini al
                                parent = input_element.locator('..')
                                label_text = await parent.text_content()
                        
                        clean_label_text = self._clean_text(label_text or "")
                        self.logger.info(f"Store {i+1} label for {product_name}: {clean_label_text}")
                        
                        # Stok durumunu kontrol et - Selenium kodundaki mantık
                        text_lower = clean_label_text.lower()
                        
                        # Selenium kodundaki mantık: mevcut, bugün, yarın var VE gönderim, hafta yok
                        has_stock_indicators = any(keyword in text_lower for keyword in ['mevcut', 'bugün', 'yarın'])
                        no_stock_indicators = any(keyword in text_lower for keyword in ['gönderim', 'hafta'])

                        # DEBUG: Stok kontrol sonuçlarını logla
                        self.logger.info(f"STOCK CHECK for {product_name}: has_stock={has_stock_indicators}, no_stock={no_stock_indicators}, text='{clean_label_text[:100]}...'")

                        # SADECE stok varsa bildirim gönder (no_stock kontrolünü kaldır)
                        if has_stock_indicators:
                            stock_available = True

                            
                            # Mağaza ismini çıkar
                            store_name = "Unknown Store"
                            if 'apple' in clean_label_text.lower():
                                if 'bağdat' in clean_label_text.lower():
                                    store_name = "Apple Bağdat Caddesi"
                                elif 'akasya' in clean_label_text.lower():
                                    store_name = "Apple Akasya"
                                elif 'zorlu' in clean_label_text.lower():
                                    store_name = "Apple Zorlu Center"
                                else:
                                    store_name = "Apple Store"
                            
                            stock_message = f"STOK MEVCUT - {product_name} - {store_name}"
                            stock_info.append(stock_message)
                            
                            self.logger.info(f"ALERT: STOCK AVAILABLE for {product_name} at {store_name}!")
                            self.logger.info(f"Full label text: {clean_label_text}")
                            
                            # Telegram API'ye direkt HTTP request gönder (Selenium kodundaki gibi)
                            if self.telegram_token and self.telegram_chat_id:
                                try:
                                    message = f"🚨 STOK AÇILDI! 🚨\n\n"
                                    message += f"📱 {product_name}\n\n"
                                    message += f"📍 Stok Bilgileri:\n"
                                    message += f"• {stock_message}\n\n"
                                    message += f"🔗 [Satın Al]({url})\n"
                                    message += f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                                    
                                    # Direkt HTTP request ile gönder
                                    telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                                    self.logger.info(f"Using Chat ID: {self.telegram_chat_id}")
                                    
                                    payload = {
                                        'chat_id': self.telegram_chat_id,
                                        'text': message,
                                        'parse_mode': 'Markdown'
                                    }
                                    
                                    response = requests.post(telegram_url, json=payload, timeout=10)
                                    
                                    if response.status_code == 200:
                                        self.logger.info(f"🚀 TELEGRAM MESSAGE SENT for {product_name}!")
                                    else:
                                        self.logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                                    
                                except Exception as notify_e:
                                    self.logger.error(f"TELEGRAM SEND FAILED: {notify_e}")
                            else:
                                self.logger.warning(f"TELEGRAM NOT CONFIGURED - Stock found: {stock_message}")
                        
                    except Exception as e:
                        self.logger.warning(f"Error reading store input {i+1} for {product_name}: {e}")
                        
            except Exception as e:
                self.logger.info(f"No store input elements found for {product_name}: {e}")
            
            # Eğer input'lar bulunamazsa, fallback method ile "mevcut" kelimesini ara
            if not stock_info:
                self.logger.info(f"No input elements found, trying fallback method for {product_name}...")
                
                try:
                    # Daha akıllı fallback arama
                    page_text = await page.locator('body').text_content()
                    if page_text:
                        lines = page_text.split('\n')
                        for line in lines:
                            line_lower = line.lower().strip()

                            # Selenium kodundaki mantık: mevcut, bugün, yarın var VE gönderim, hafta yok
                            has_stock = any(keyword in line_lower for keyword in ['mevcut', 'bugün', 'yarın'])
                            has_no_stock = any(keyword in line_lower for keyword in ['gönderim', 'hafta'])

                            # SADECE stok varsa bildirim gönder (no_stock kontrolünü kaldır)
                            if has_stock and len(line.strip()) > 10:
                                clean_line = self._clean_text(line)
                                stock_info.append(f"FALLBACK STOCK: {clean_line}")
                                stock_available = True
                                self.logger.info(f"FALLBACK: Found stock indicator for {product_name}: {clean_line}")
                                break  # İlk bulunan stok yeterli

                except Exception as e:
                    self.logger.debug(f"Fallback text search failed for {product_name}: {e}")

            
            return {
                'stock_available': stock_available,
                'stock_info': stock_info,
                'product': product_name
            }
            
        except Exception as e:
            self.logger.error(f"Stock status check failed for {product_name}: {e}")
            return {
                'stock_available': False,
                'stock_info': [f"Error: {str(e)}"],
                'product': product_name
            }
    
    async def _log_all_buttons(self, page: Page, product_name: str):
        """Debug için sayfadaki tüm butonları logla"""
        try:
            self.logger.info(f"Logging all buttons on page for {product_name}...")
            
            buttons = await page.locator('button').all()
            self.logger.info(f"Found {len(buttons)} buttons for {product_name}")
            
            for i, button in enumerate(buttons[:10]):  # İlk 10 buton
                try:
                    button_text = self._clean_text(await button.text_content() or "")
                    button_class = await button.get_attribute('class') or 'no-class'
                    button_id = await button.get_attribute('id') or 'no-id'
                    
                    if button_text:  # Sadece text'i olan butonları logla
                        self.logger.info(f"Button {i+1} for {product_name}: text='{button_text}', class='{button_class}', id='{button_id}'")
                        
                except Exception as e:
                    self.logger.debug(f"Error logging button {i}: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Button logging failed for {product_name}: {e}")
    
    async def check_product_with_js_rendering(self, product_name: str, url: str) -> Dict:
        """Basit HTTP request ile ürün kontrolü (JS rendering olmadan)"""
        try:
            # Basit HTTP request
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # "Uygunluğu kontrol et" butonunu ara
            availability_button = soup.find('button', class_='rf-pickup-quote-overlay-trigger')
            if not availability_button:
                # Buton yoksa direkt Playwright'a geç
                return await self.check_single_product_playwright(product_name, url)
            
            # Buton varsa Playwright ile etkileşim yap
            return await self.check_single_product_playwright(product_name, url)
            
        except Exception as e:
            self.logger.error(f"HTTP request failed for {product_name}: {e}")
            # Fallback olarak Playwright'ı dene
            return await self.check_single_product_playwright(product_name, url)
    
    async def check_single_product_playwright(self, product_name: str, url: str) -> Dict:
        """Playwright ile tek bir ürünün stok durumunu kontrol et"""
        self.logger.info(f"Checking stock for: {product_name}")
        
        context = None
        try:
            # Context pool'dan context al
            context = await self._get_context()
            page = await context.new_page()
            
            # Sayfayı aç
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(0.2)  # Daha hızlı sayfa yükleme
            
            # 1. "Uygunluğu kontrol et" butonunu bul ve tıkla
            if not await self._find_availability_button(page):
                return {
                    'product': product_name,
                    'url': url,
                    'stock_available': False,
                    'error': 'Availability button not found'
                }
            
            await asyncio.sleep(1)  # Buton tıklama sonrası bekleme azaltıldı
            
            # 2. Konum seçim işlemleri
            if not await self._select_location(page):
                return {
                    'product': product_name,
                    'url': url,
                    'stock_available': False,
                    'error': 'Location selection failed'
                }
            
            # 3. Stok durumunu kontrol et
            stock_result = await self._check_stock_status(page, product_name, url)
            
            await page.close()
            return stock_result
            
        except Exception as e:
            self.logger.error(f"Error checking {product_name}: {e}")
            return {
                'product': product_name,
                'url': url,
                'stock_available': False,
                'error': str(e)
            }
        finally:
            if context:
                # Context'i pool'a geri ver (close yerine)
                await self._return_context(context)
    
    async def check_single_product(self, product_name: str, url: str) -> Dict:
        """Tek bir ürünün stok durumunu kontrol et - hibrit yaklaşım"""
        # Önce requests ile hızlı kontrol, sonra Playwright ile etkileşim
        return await self.check_product_with_js_rendering(product_name, url)
    

    async def send_telegram_notification(self, message: str):
        """Telegram'a mesaj gönder"""
        if not self.telegram_token or not self.telegram_chat_id:
            self.logger.warning("Telegram not configured. Skipping notification.")
            return
        
        try:
            # Önce bot bilgilerini kontrol et
            get_me_url = f"https://api.telegram.org/bot{self.telegram_token}/getMe"
            me_response = requests.get(get_me_url, timeout=10)
            if me_response.status_code != 200:
                self.logger.error(f"Bot token invalid: {me_response.status_code} - {me_response.text}")
                return

            # Bot bilgilerini logla
            bot_info = me_response.json()
            self.logger.info(f"Bot info: {bot_info}")

            telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }

            self.logger.info(f"Sending to chat_id: {self.telegram_chat_id}")
            response = requests.post(telegram_url, json=payload, timeout=10)

            if response.status_code == 200:
                self.logger.info("Telegram message sent successfully.")
            else:
                self.logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")

                # Chat not found ise alternatif chat ID'leri dene
                if "chat not found" in response.text.lower():
                    self.logger.info("Trying alternative chat IDs...")
                    alt_chat_ids = [
                        str(self.telegram_chat_id).replace('-100', ''),  # Grup ID'si olabilir
                        f"-{self.telegram_chat_id}",  # Farklı format
                    ]
                    for alt_id in alt_chat_ids:
                        try:
                            alt_payload = payload.copy()
                            alt_payload['chat_id'] = alt_id
                            alt_response = requests.post(telegram_url, json=alt_payload, timeout=10)
                            if alt_response.status_code == 200:
                                self.logger.info(f"Success with alternative chat_id: {alt_id}")
                                break
                        except Exception:
                            continue
            
        except Exception as e:
            self.logger.error(f"Telegram notification failed: {e}")

    async def monitor_products(self):
        """Tüm ürünleri sıralı olarak kontrol et - paralel çalışma kaldırıldı"""
        try:
            results = []
            for product_name, url in self.iphone_urls.items():
                try:
                    result = await self.check_single_product(product_name, url)
                    results.append(result)
                    # Her ürün arasında kısa bekleme
                    await asyncio.sleep(0.5)
                except Exception as e:
                    self.logger.error(f"Error checking {product_name}: {e}")
                    results.append({
                        'product': product_name,
                        'url': url,
                        'stock_available': False,
                        'error': str(e)
                    })

            for (product_name, url), result in zip(self.iphone_urls.items(), results):

                if isinstance(result, Exception):
                    self.logger.error(f"Error monitoring {product_name}: {result}")
                    continue

                if result and result.get("stock_available"):
                    stock_messages = "\n".join(result["stock_info"])
                    message = (
                        f"🚨 STOK AÇILDI! 🚨\n\n📱 {product_name}\n\n{stock_messages}"
                        f"\n\n🔗 [Satın Al]({url})\n🕐 {datetime.now().strftime('%H:%M:%S')}"
                    )
                    await self.send_telegram_notification(message)

            await asyncio.sleep(self.request_delay)
                            
        except Exception as e:
            self.logger.error(f"Monitor products loop failed: {e}")



    async def run(self):
        """Ana döngü"""
        try:
            self.logger.info("iPhone 17 stock monitor started.")
            while True:
                await self.monitor_products()
                await asyncio.sleep(self.cycle_delay)
        except KeyboardInterrupt:
            self.logger.info("Stopping due to KeyboardInterrupt.")
        except Exception as e:
            self.logger.error(f"Fatal error in run loop: {e}")
        finally:
            await self._cleanup_contexts()
            self.logger.info("Cleaned up all contexts and stopped Playwright.")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    monitor = iPhone17StockMonitor()
    asyncio.run(monitor.run())
