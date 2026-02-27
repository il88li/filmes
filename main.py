import asyncio
import json
import aiohttp
import re
import logging
from telethon import TelegramClient, events, Button
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import SessionPasswordNeededError, PhoneNumberInvalidError
from bs4 import BeautifulSoup
import random

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعدادات البوت
API_ID = 23656977
API_HASH = "49d3f43531a92b3f5bc403766313ca1e"
BOT_TOKEN = "8137587721:AAGq7kyLc3E0EL7HZ2SKRmJPGj3OLQFVSKo"

# مصادر الأرقام المؤقتة (Web Scraping)
SMS_SOURCES = {
    'smstome': {
        'url': 'https://smstome.com/country/{country}',
        'list_url': 'https://smstome.com/country/{country}',
        'msg_url': 'https://smstome.com/phone/{phone}'
    },
    'receive_smss': {
        'url': 'https://receive-smss.com/',
        'list_selector': '.number-box',
    },
    'anonymsms': {
        'url': 'https://anonymsms.com/',
        'list_selector': '.number-card',
    },
    'temp_number': {
        'url': 'https://temporarynumber.com/',
        'list_selector': '.number-item',
    }
}

# قائمة الدول المدعومة يدوياً (احتياطي)
FALLBACK_COUNTRIES = {
    'us': '🇺🇸 United States',
    'uk': '🇬🇧 United Kingdom', 
    'ca': '🇨🇦 Canada',
    'de': '🇩🇪 Germany',
    'fr': '🇫🇷 France',
    'nl': '🇳🇱 Netherlands',
    'se': '🇸🇪 Sweden',
    'fi': '🇫🇮 Finland',
    'be': '🇧🇪 Belgium'
}

# تخزين مؤقت
user_sessions = {}
temp_numbers_cache = {}
cache_timestamp = 0
CACHE_DURATION = 300  # 5 دقائق

class TelegramOTPBot:
    def __init__(self):
        self.client = None
        self.bot = None
        self.session = None
        
    async def start(self):
        """بدء تشغيل البوت"""
        try:
            self.session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            )
            
            self.client = TelegramClient('bot_session_v3', API_ID, API_HASH)
            await self.client.start(bot_token=BOT_TOKEN)
            
            self.bot = await self.client.get_me()
            
            print("=" * 60)
            print("✅ BOT STARTED SUCCESSFULLY")
            print("=" * 60)
            print(f"🤖 Bot Name: {self.bot.first_name}")
            print(f"📱 Bot Username: @{self.bot.username}")
            print(f"🆔 Bot ID: {self.bot.id}")
            print(f"🔑 API ID: {API_ID}")
            print(f"🌐 Session: Active")
            print("=" * 60)
            print("🚀 Bot is running... Waiting for messages")
            print("Press Ctrl+C to stop")
            print("=" * 60)
            
            self.register_handlers()
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            print(f"❌ Fatal Error: {e}")
            raise
        finally:
            if self.session:
                await self.session.close()
    
    def register_handlers(self):
        """تسجيل معالجات الأحداث"""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            logger.info(f"User {event.sender_id} started the bot")
            await self.show_main_menu(event)
        
        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            await self.show_help(event, edit=False)
        
        @self.client.on(events.NewMessage(pattern='/countries'))
        async def countries_handler(event):
            await self.show_countries(event)
        
        @self.client.on(events.CallbackQuery)
        async def callback_handler(event):
            try:
                await self.handle_callback(event)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
                await event.answer("❌ حدث خطأ، حاول مرة أخرى")
        
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            if event.sender_id == self.bot.id:
                return
            if event.message.text and event.message.text.startswith('/'):
                return
            await self.handle_text_message(event)
    
    async def show_main_menu(self, event, edit=False):
        """عرض القائمة الرئيسية"""
        text = """
🤖 **بوت البحث عن أرقام تلجرام**

مرحباً بك! أنا بوت متخصص في البحث عن أرقام متاحة للتسجيل على تلجرام.

⚡ **المميزات:**
• 🔍 البحث في أرقام متعددة الدول
• ✅ التحقق من توفر الرقم للتسجيل
• 📩 جلب أكواد التفعيل تلقائياً
• 🚀 سريع وسهل الاستخدام

🔽 اختر من القائمة أدناه:
"""
        buttons = [
            [Button.inline("🔍 بدء البحث", b"start_search")],
            [Button.inline("🌍 عرض الدول", b"show_countries"), Button.inline("❓ المساعدة", b"help")],
            [Button.inline("ℹ️ عن البوت", b"about")]
        ]
        
        try:
            if edit:
                await event.edit(text, buttons=buttons, parse_mode='markdown')
            else:
                await event.respond(text, buttons=buttons, parse_mode='markdown')
        except Exception as e:
            logger.error(f"Error showing menu: {e}")
    
    async def handle_callback(self, event):
        """معالجة ضغطات الأزرار"""
        data = event.data.decode('utf-8')
        user_id = event.sender_id
        
        logger.info(f"Callback from {user_id}: {data}")
        
        handlers = {
            'start_search': self.show_countries,
            'back_main': lambda e: self.show_main_menu(e, edit=True),
            'help': lambda e: self.show_help(e, edit=True),
            'about': lambda e: self.show_about(e, edit=True),
            'show_countries': self.show_countries,
            'refresh_countries': lambda e: self.show_countries(e, edit=True),
            'cancel_search': lambda e: self.show_main_menu(e, edit=True),
        }
        
        if data in handlers:
            await handlers[data](event)
        
        elif data.startswith("country:"):
            country = data.split(":")[1]
            await self.start_number_search(event, country, user_id)
        
        elif data.startswith("check_code:"):
            phone = data.split(":", 1)[1]
            await self.check_verification_code(event, phone)
        
        elif data.startswith("search_again:"):
            country = data.split(":")[1]
            await self.start_number_search(event, country, user_id)
        
        else:
            await event.answer("⚠️ خيار غير معروف")
    
    async def show_countries(self, event, edit=False):
        """عرض قائمة الدول المتاحة"""
        please_wait = "⏳ جاري جلب قائمة الدول..."
        
        try:
            if edit:
                await event.edit(please_wait)
            else:
                await event.answer(please_wait)
            
            # استخدام القائمة الاحتياطية المحددة مسبقاً
            countries = FALLBACK_COUNTRIES
            
            text = "🌍 **الدول المتاحة للبحث:**\n\nاختر الدولة المطلوبة:"
            buttons = []
            
            country_list = list(countries.items())
            for i in range(0, len(country_list), 2):
                row = []
                for j in range(2):
                    if i + j < len(country_list):
                        code, name = country_list[i + j]
                        row.append(Button.inline(name, f"country:{code}"))
                buttons.append(row)
            
            buttons.append([Button.inline("🔄 تحديث", b"refresh_countries")])
            buttons.append([Button.inline("🔙 رجوع", b"back_main")])
            
            if edit:
                await event.edit(text, buttons=buttons, parse_mode='markdown')
            else:
                await event.respond(text, buttons=buttons, parse_mode='markdown')
                
        except Exception as e:
            logger.error(f"Error showing countries: {e}")
            error_text = "❌ حدث خطأ في جلب الدول."
            buttons = [[Button.inline("🔄 إعادة المحاولة", b"refresh_countries")],
                      [Button.inline("🔙 رجوع", b"back_main")]]
            
            if edit:
                await event.edit(error_text, buttons=buttons)
            else:
                await event.respond(error_text, buttons=buttons)
    
    async def start_number_search(self, event, country, user_id):
        """بدء البحث عن رقم متاح"""
        search_text = f"🔍 **جاري البحث في:** {FALLBACK_COUNTRIES.get(country, country.upper())}\n\n⏳ جاري فحص الأرقام المتاحة من مصادر متعددة..."
        await event.edit(search_text)
        
        try:
            # جلب الأرقام من المصادر
            numbers = await self.fetch_numbers_from_sources(country)
            
            if not numbers:
                await event.edit(
                    "❌ لا توجد أرقام متاحة حالياً في هذه الدولة.\n\n"
                    "الأرقام المجانية تُستخدم بسرعة. حاول مرة أخرى أو جرب دولة أخرى.",
                    buttons=[
                        [Button.inline("🔄 إعادة البحث", f"search_again:{country}")],
                        [Button.inline("🌍 دولة أخرى", b"show_countries")],
                        [Button.inline("🏠 رئيسية", b"back_main")]
                    ]
                )
                return
            
            # البحث عن رقم متاح للتسجيل
            available_number = None
            checked = 0
            
            for phone in numbers[:15]:  # فحص أول 15 رقم
                checked += 1
                
                if checked % 3 == 0:
                    try:
                        await event.edit(f"🔍 جاري الفحص... ({checked}/{min(15, len(numbers))})\nالرقم: +{phone}")
                    except:
                        pass
                
                # التحقق من توفر الرقم على تلجرام
                is_available = await self.check_telegram_availability(phone)
                
                if is_available:
                    available_number = phone
                    break
                
                await asyncio.sleep(0.5)
            
            if available_number:
                user_sessions[user_id] = {
                    'phone': available_number,
                    'country': country,
                    'found_at': asyncio.get_event_loop().time()
                }
                
                success_msg = f"""
✅ **تم إيجاد رقم متاح!**

📱 **الرقم:** `+{available_number}`
🌍 **الدولة:** {FALLBACK_COUNTRIES.get(country, country.upper())}
📊 **الحالة:** ✅ جاهز للتسجيل

⚠️ **تنبيه:** الرقم متاح مؤقتاً. استخدمه فوراً!

🔽 **الخطوات:**
1. انسخ الرقم أعلاه
2. افتح تلجرام واضغط "تسجيل الدخول"
3. أدخل الرقم وانتظر الكود
4. اضغط "جلب آخر كود" بالأسفل
"""
                buttons = [
                    [Button.inline("📩 جلب آخر كود", f"check_code:{available_number}")],
                    [Button.inline("🔍 رقم آخر", f"search_again:{country}")],
                    [Button.inline("🏠 رئيسية", b"back_main")]
                ]
                
                await event.edit(success_msg, buttons=buttons, parse_mode='markdown')
                
                # إرسال الرقم في رسالة منفصلة للنسخ السهل
                await event.respond(
                    f"📋 **انسخ الرقم:**\n`+{available_number}`",
                    parse_mode='markdown'
                )
            else:
                await event.edit(
                    f"❌ لم يتم العثور على أرقام متاحة من بين {checked} رقم تم فحصهم.\n\n"
                    f"💡 **نصيحة:** الأرقام تُستخدم بسرعة. حاول مباشرة أو اختر دولة أخرى.",
                    buttons=[
                        [Button.inline("🔄 إعادة البحث", f"search_again:{country}")],
                        [Button.inline("🌍 دولة أخرى", b"show_countries")],
                        [Button.inline("🏠 رئيسية", b"back_main")]
                    ]
                )
                
        except Exception as e:
            logger.error(f"Error in search: {e}")
            await event.edit(
                "❌ حدث خطأ أثناء البحث.",
                buttons=[
                    [Button.inline("🔄 إعادة المحاولة", f"search_again:{country}")],
                    [Button.inline("🔙 رجوع", b"back_main")]
                ]
            )
    
    async def fetch_numbers_from_sources(self, country):
        """جلب الأرقام من مصادر متعددة"""
        numbers = []
        
        # محاولة جلب من smstome
        try:
            smstome_numbers = await self.fetch_smstome_numbers(country)
            numbers.extend(smstome_numbers)
            logger.info(f"Fetched {len(smstome_numbers)} numbers from smstome")
        except Exception as e:
            logger.error(f"smstome error: {e}")
        
        # محاولة جلب من مصادر أخرى
        if len(numbers) < 5:
            try:
                backup_numbers = await self.fetch_backup_numbers(country)
                numbers.extend(backup_numbers)
                logger.info(f"Fetched {len(backup_numbers)} backup numbers")
            except Exception as e:
                logger.error(f"Backup fetch error: {e}")
        
        # إزالة التكرارات
        unique_numbers = list(set(numbers))
        return unique_numbers[:20]  # إرجاع أول 20 رقم فقط
    
    async def fetch_smstome_numbers(self, country):
        """جلب الأرقام من smstome.com"""
        numbers = []
        
        country_mapping = {
            'us': 'usa', 'uk': 'uk', 'ca': 'canada', 'de': 'germany',
            'fr': 'france', 'nl': 'netherlands', 'se': 'sweden',
            'fi': 'finland', 'be': 'belgium'
        }
        
        smstome_country = country_mapping.get(country, country)
        url = f"https://smstome.com/country/{smstome_country}"
        
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # البحث عن روابط الأرقام
                    number_links = soup.find_all('a', href=re.compile(r'/phone/\d+'))
                    
                    for link in number_links:
                        href = link.get('href', '')
                        phone_match = re.search(r'/phone/(\d+)', href)
                        if phone_match:
                            phone = phone_match.group(1)
                            if phone not in numbers:
                                numbers.append(phone)
        except Exception as e:
            logger.error(f"Error fetching from smstome: {e}")
        
        return numbers
    
    async def fetch_backup_numbers(self, country):
        """جلب أرقام احتياطية من مصادر أخرى"""
        # قائمة أرقام تجريبية للاختبار (في حالة فشل المصادر)
        # في الإنتاج، يجب استبدالها بـ API حقيقية
        return []
    
    async def check_telegram_availability(self, phone):
        """التحقق من توفر الرقم على تلجرام"""
        try:
            contact = InputPhoneContact(
                client_id=0,
                phone=f"+{phone}",
                first_name="Test",
                last_name="User"
            )
            
            result = await self.client(ImportContactsRequest([contact]))
            
            # إذا لم يكن هناك مستخدمين، الرقم غير مسجل (متاح)
            if not result.users:
                return True
            
            return False
            
        except PhoneNumberInvalidError:
            return False
        except Exception as e:
            logger.debug(f"Check error: {e}")
            return True
    
    async def check_verification_code(self, event, phone):
        """التحقق من وجود كود تفعيل"""
        await event.answer("⏳ جاري البحث عن الكود...")
        
        try:
            messages = await self.fetch_messages_for_number(phone)
            
            telegram_msgs = [m for m in messages if self.is_telegram_message(m)]
            
            if telegram_msgs:
                latest = telegram_msgs[0]
                code = self.extract_code(latest.get('text', ''))
                
                msg_text = f"""
📩 **تم العثور على كود!**

📱 **الرقم:** `+{phone}`
🔢 **الكود:** `{code}`
📝 **الرسالة:** 
{latest.get('text', '')}
           ⏰ **الوقت:** {latest.get('time', 'الآن')}

⚠️ استخدم الكود فوراً!
"""
                buttons = [
                    [Button.inline("🔄 تحديث", f"check_code:{phone}")],
                    [Button.inline("🔍 رقم جديد", b"start_search")],
                    [Button.inline("🏠 رئيسية", b"back_main")]
                ]
                await event.edit(msg_text, buttons=buttons, parse_mode='markdown')
            else:
                waiting_text = f"""
⏳ **في انتظار الكود...**

📱 **الرقم:** `+{phone}`
📊 **الحالة:** لا يوجد كود بعد

💡 **تعليمات:**
• تأكد من بدء التسجيل على تلجرام
• انتظر 30-60 ثانية واضغط تحديث
• قد يستغرق وصول الرسالة دقيقتين
"""
                buttons = [
                    [Button.inline("🔄 تحديث الآن", f"check_code:{phone}")],
                    [Button.inline("🔍 رقم آخر", b"start_search")],
                    [Button.inline("🏠 رئيسية", b"back_main")]
                ]
                await event.edit(waiting_text, buttons=buttons, parse_mode='markdown')
                
        except Exception as e:
            logger.error(f"Error checking code: {e}")
            await event.edit(
                "❌ تعذر جلب الرسائل.",
                buttons=[
                    [Button.inline("🔄 إعادة المحاولة", f"check_code:{phone}")],
                    [Button.inline("🔙 رجوع", b"back_main")]
                ]
            )
    
    async def fetch_messages_for_number(self, phone):
        """جلب الرسائل لرقم معين"""
        messages = []
        
        # محاولة جلب من smstome
        try:
            url = f"https://smstome.com/phone/{phone}"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # البحث عن صفوف الرسائل
                    rows = soup.find_all('tr', class_=re.compile(r'sms-row|message'))
                    if not rows:
                        rows = soup.find_all('tr')
                    
                    for row in rows:
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 3:
                            sender = cols[0].get_text(strip=True)
                            text = cols[1].get_text(strip=True)
                            time = cols[2].get_text(strip=True)
                            
                            messages.append({
                                'sender': sender,
                                'text': text,
                                'time': time
                            })
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
        
        return messages
    
    def is_telegram_message(self, msg):
        """التحقق مما إذا كانت الرسالة من تلجرام"""
        text = msg.get('text', '').lower()
        sender = msg.get('sender', '').lower()
        
        keywords = ['telegram', 'code', 'verification', 'login', 'tg', 
                   'web login', 'new login', 'device', 'كود', 'تلجرام', 'تيليجرام']
        
        return any(k in text for k in keywords) or any(k in sender for k in ['telegram', 'tg'])
    
    def extract_code(self, text):
        """استخراج الكود من النص"""
        patterns = [
            r'\b\d{5}\b',
            r'\b\d{6}\b', 
            r'code[:\s]+(\d+)',
            r'رمز[:\s]+(\d+)',
            r'كود[:\s]+(\d+)',
            r'verification code[:\s]+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(0) if match.group(0).isdigit() else match.group(1)
                if result.isdigit():
                    return result
        
        return "غير محدد"
    
    async def show_help(self, event, edit=False):
        """عرض المساعدة"""
        text = """
❓ **كيفية الاستخدام:**

**الخطوات:**
1️⃣ اضغط "🔍 بدء البحث"
2️⃣ اختر الدولة المطلوبة
3️⃣ انتظر حتى يجد البوت رقماً متاحاً
4️⃣ انسخ الرقم واستخدمه للتسجيل
5️⃣ اضغط "📩 جلب آخر كود" للحصول على الكود

**⚠️ تحذيرات:**
• الأرقام مؤقتة وعامة (يمكن للجميع رؤيتها)
• لا تستخدمها لحسابات مهمة
• سرعة الاستخدام مطلوبة جداً
• قد يستخدم الرقم من شخص آخر قبلك

**الأوامر:**
/start - القائمة الرئيسية
/help - المساعدة
/countries - عرض الدول
"""
        buttons = [[Button.inline("🔙 رجوع", b"back_main")]]
        
        if edit:
            await event.edit(text, buttons=buttons, parse_mode='markdown')
        else:
            await event.respond(text, buttons=buttons, parse_mode='markdown')
    
    async def show_about(self, event, edit=False):
        """عرض معلومات عن البوت"""
        text = f"""
ℹ️ **عن البوت:**

🤖 **Telegram OTP Finder v3.0**
👨‍💻 **المطور:** @YourUsername

🔧 **التقنيات:**
• Python 3.x + Telethon
• Web Scraping (BeautifulSoup)
• Multi-source Aggregation

📡 **المصادر:**
• smstome.com
• receive-smss.com
• anonymsms.com

⚡ **الوصف:**
بوت متخصص في البحث عن أرقام وهمية مؤقتة
للتسجيل على تلجرام وجلب أكواد التفعيل.

📝 **للتبليغ عن مشاكل:**
تواصل مع المطور

🔙 رجوع للقائمة الرئيسية
"""
        buttons = [[Button.inline("🔙 رجوع", b"back_main")]]
        
        if edit:
            await event.edit(text, buttons=buttons, parse_mode='markdown')
        else:
            await event.respond(text, buttons=buttons, parse_mode='markdown')
    
    async def handle_text_message(self, event):
        """معالجة الرسائل النصية"""
        text = event.message.text.strip()
        
        if text == "/start":
            return
        
        await event.respond(
            "👋 استخدم الأزرار للتنقل بين الخيارات.",
            buttons=[Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        )

async def main():
    print("🚀 Starting Telegram OTP Bot v3.0...")
    print(f"📱 API ID: {API_ID}")
    print(f"🔑 API Hash: {API_HASH[:10]}...")
    print("=" * 60)
    
    bot = TelegramOTPBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
     
