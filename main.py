import asyncio
import json
import aiohttp
import re
import logging
from telethon import TelegramClient, events, Button
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import SessionPasswordNeededError, PhoneNumberInvalidError

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

# روابط API
OTP_API_BASE = "https://otp-api.shelex.dev/api"
COUNTRIES_ENDPOINT = f"{OTP_API_BASE}/countries"
LIST_ENDPOINT = f"{OTP_API_BASE}/list"
MESSAGES_ENDPOINT = f"{OTP_API_BASE}"

# تخزين مؤقت للمستخدمين
user_sessions = {}

class TelegramOTPBot:
    def __init__(self):
        self.client = None
        self.bot = None
        
    async def start(self):
        """بدء تشغيل البوت"""
        try:
            # إنشاء العميل
            self.client = TelegramClient('bot_session_v2', API_ID, API_HASH)
            
            # بدء الجلسة
            await self.client.start(bot_token=BOT_TOKEN)
            
            # الحصول على معلومات البوت
            self.bot = await self.client.get_me()
            
            print("=" * 50)
            print("✅ BOT STARTED SUCCESSFULLY")
            print("=" * 50)
            print(f"🤖 Bot Name: {self.bot.first_name}")
            print(f"📱 Bot Username: @{self.bot.username}")
            print(f"🆔 Bot ID: {self.bot.id}")
            print(f"🔑 API ID: {API_ID}")
            print("=" * 50)
            
            # تسجيل المعالجات
            self.register_handlers()
            
            print("🚀 Bot is running... Waiting for messages")
            print("Press Ctrl+C to stop")
            print("=" * 50)
            
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            print(f"❌ Error: {e}")
            raise
    
    def register_handlers(self):
        """تسجيل معالجات الأحداث"""
        
        # معالج /start
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            logger.info(f"User {event.sender_id} started the bot")
            await self.show_main_menu(event)
        
        # معالج /help
        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            await self.show_help(event, edit=False)
        
        # معالج الأزرار
        @self.client.on(events.CallbackQuery)
        async def callback_handler(event):
            try:
                await self.handle_callback(event)
            except Exception as e:
                logger.error(f"Error in callback handler: {e}")
                await event.answer("❌ حدث خطأ، حاول مرة أخرى")
        
        # معالج الرسائل النصية العادية
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            # تجاهل الرسائل من البوت نفسه
            if event.sender_id == self.bot.id:
                return
            
            # تجاهل الأوامر المعروفة
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
            [Button.inline("❓ كيفية الاستخدام", b"help"), Button.inline("ℹ️ عن البوت", b"about")]
        ]
        
        try:
            if edit and hasattr(event, 'edit'):
                await event.edit(text, buttons=buttons, parse_mode='markdown')
            else:
                await event.respond(text, buttons=buttons, parse_mode='markdown')
        except Exception as e:
            logger.error(f"Error showing main menu: {e}")
    
    async def handle_callback(self, event):
        """معالجة ضغطات الأزرار"""
        data = event.data.decode('utf-8')
        user_id = event.sender_id
        
        logger.info(f"User {user_id} clicked: {data}")
        
        if data == "start_search":
            await self.show_countries(event)
        
        elif data == "back_main":
            await self.show_main_menu(event, edit=True)
        
        elif data == "help":
            await self.show_help(event, edit=True)
        
        elif data == "about":
            await self.show_about(event, edit=True)
        
        elif data.startswith("country:"):
            country = data.split(":")[1]
            await self.start_number_search(event, country, user_id)
        
        elif data == "refresh_countries":
            await self.show_countries(event, edit=True)
        
        elif data.startswith("check_code:"):
            phone = data.split(":", 1)[1]
            await self.check_verification_code(event, phone)
        
        elif data == "cancel_search":
            if user_id in user_sessions:
                del user_sessions[user_id]
            await self.show_main_menu(event, edit=True)
        
        else:
            await event.answer("⚠️ خيار غير معروف")
    
    async def show_countries(self, event, edit=False):
        """عرض قائمة الدول المتاحة"""
        please_wait_text = "⏳ جاري جلب قائمة الدول المتاحة..."
        
        try:
            if edit:
                await event.edit(please_wait_text)
            else:
                await event.answer(please_wait_text)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(COUNTRIES_ENDPOINT, timeout=15) as response:
                    if response.status == 200:
                        countries = await response.json()
                        
                        if not countries:
                            raise Exception("No countries returned")
                        
                        text = "🌍 **الدول المتاحة للبحث:**\n\nاختر الدولة المطلوبة:"
                        buttons = []
                        
                        # تقسيم الدول إلى صفوف (زرين في كل صف)
                        country_list = sorted(countries.items(), key=lambda x: x[1])
                        
                        for i in range(0, len(country_list), 2):
                            row = []
                            for j in range(2):
                                if i + j < len(country_list):
                                    code, name = country_list[i + j]
                                    flag = self.get_country_flag(code)
                                    row.append(Button.inline(f"{flag} {name}", f"country:{code}"))
                            buttons.append(row)
                        
                        buttons.append([Button.inline("🔄 تحديث القائمة", b"refresh_countries")])
                        buttons.append([Button.inline("🔙 رجوع للرئيسية", b"back_main")])
                        
                        if edit:
                            await event.edit(text, buttons=buttons, parse_mode='markdown')
                        else:
                            await event.respond(text, buttons=buttons, parse_mode='markdown')
                    else:
                        raise Exception(f"Status code: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error fetching countries: {e}")
            error_text = "❌ تعذر جلب قائمة الدول. حاول مرة أخرى."
            buttons = [
                [Button.inline("🔄 إعادة المحاولة", b"refresh_countries")],
                [Button.inline("🔙 رجوع", b"back_main")]
            ]
            
            if edit:
                await event.edit(error_text, buttons=buttons)
            else:
                await event.respond(error_text, buttons=buttons)
    
    def get_country_flag(self, country_code):
        """إرجاع علم الدولة"""
        flags = {
            'us': '🇺🇸', 'gb': '🇬🇧', 'de': '🇩🇪', 'fr': '🇫🇷', 
            'it': '🇮🇹', 'es': '🇪🇸', 'ru': '🇷🇺', 'cn': '🇨🇳',
            'in': '🇮🇳', 'jp': '🇯🇵', 'br': '🇧🇷', 'ca': '🇨🇦',
            'au': '🇦🇺', 'mx': '🇲🇽', 'kr': '🇰🇷', 'nl': '🇳🇱',
            'se': '🇸🇪', 'no': '🇳🇴', 'fi': '🇫🇮', 'dk': '🇩🇰',
            'pl': '🇵🇱', 'tr': '🇹🇷', 'id': '🇮🇩', 'sa': '🇸🇦',
            'ae': '🇦🇪', 'eg': '🇪🇬', 'za': '🇿🇦', 'ng': '🇳🇬'
        }
        return flags.get(country_code.lower(), '🌍')
    
    async def start_number_search(self, event, country, user_id):
        """بدء البحث عن رقم متاح"""
        search_text = f"🔍 **جاري البحث في دولة: {country.upper()}**\n\n⏳ الرجاء الانتظار جارٍ فحص الأرقام المتاحة..."
        await event.edit(search_text)
        
        try:
            async with aiohttp.ClientSession() as session:
                list_url = f"{LIST_ENDPOINT}/{country}"
                async with session.get(list_url, timeout=20) as response:
                    if response.status != 200:
                        raise Exception("Failed to fetch numbers")
                    
                    numbers_data = await response.json()
                    
                    if not numbers_data:
                        raise Exception("No numbers available")
                    
                    # البحث عن رقم متاح
                    available_number = None
                    total_numbers = len(numbers_data)
                    checked_count = 0
                    
                    for idx, phone_info in enumerate(numbers_data[:20]):  # فحص أول 20 رقم
                        phone = phone_info.get('phone') or phone_info.get('number')
                        if not phone:
                            continue
                        
                        # تنظيف الرقم
                        phone = str(phone).replace('+', '').replace(' ', '').replace('-', '').strip()
                        
                        if not phone.isdigit():
                            continue
                        
                        checked_count += 1
                        
                        # تحديث حالة البحث كل 3 أرقام
                        if checked_count % 3 == 0:
                            progress_text = f"🔍 **جاري الفحص...**\n\nالدولة: {country.upper()}\nالرقم الحالي: +{phone}\nالتقدم: {checked_count}/{min(20, total_numbers)}"
                            try:
                                await event.edit(progress_text)
                            except:
                                pass
                        
                        # التحقق من توفر الرقم
                        is_available = await self.check_telegram_availability(phone)
                        
                        if is_available:
                            available_number = phone
                            break
                        
                        await asyncio.sleep(0.3)
                    
                    if available_number:
                        # حفظ الجلسة
                        user_sessions[user_id] = {
                            'phone': available_number,
                            'country': country,
                            'status': 'found',
                            'timestamp': asyncio.get_event_loop().time()
                        }
                        
                        success_text = f"""
✅ **تم إيجاد رقم متاح للتسجيل!**

📱 **الرقم:** `+{available_number}`
🌍 **الدولة:** {country.upper()}
📊 **الحالة:** ✅ جاهز للتسجيل
⏱ **ملاحظة:** الرقم متاح لفترة محدودة

⚠️ **خطوات التسجيل:**
1️⃣ انسخ الرقم أعلاه
2️⃣ افتح تلجرام واضغط "تسجيل الدخول"
3️⃣ أدخل الرقم وانتظر الكود
4️⃣ اضغط على "جلب آخر كود" بالأسفل

🔽 اختر الإجراء المطلوب:
"""
                        buttons = [
                            [Button.inline("📩 جلب آخر كود", f"check_code:{available_number}")],
                            [Button.inline("🔍 البحث عن رقم آخر", f"country:{country}")],
                            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
                        ]
                        await event.edit(success_text, buttons=buttons, parse_mode='markdown')
                        
                        # إرسال الرقم في رسالة منفصلة للنسخ السهل
                        await event.respond(
                            f"📋 **انسخ الرقم:**\n`+{available_number}`\n\n"
                            f"⚡ استخدمه الآن للتسجيل على تلجرام",
                            parse_mode='markdown'
                        )
                    else:
                        no_result_text = "❌ لم يتم العثور على أرقام متاحة للتسجيل حالياً.\n\nالأرقام تُستخدم بسرعة، حاول مرة أخرى."
                        buttons = [
                            [Button.inline("🔄 إعادة البحث", f"country:{country}")],
                            [Button.inline("🌍 دولة أخرى", b"start_search")],
                            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
                        ]
                        await event.edit(no_result_text, buttons=buttons)
                        
        except Exception as e:
            logger.error(f"Error searching number: {e}")
            error_text = "❌ حدث خطأ أثناء البحث عن الأرقام."
            buttons = [
                [Button.inline("🔄 إعادة المحاولة", f"country:{country}")],
                [Button.inline("🔙 رجوع", b"back_main")]
            ]
            await event.edit(error_text, buttons=buttons)
    
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
            logger.debug(f"Check error for {phone}: {e}")
            # في حالة الشك، نفترض أنه متاح
            return True
    
    async def check_verification_code(self, event, phone):
        """التحقق من وجود كود تفعيل"""
        await event.answer("⏳ جاري البحث عن الكود...")
        
        try:
            # تحديد كود الدولة
            country_code = self.extract_country_code(phone)
            
            async with aiohttp.ClientSession() as session:
                messages_url = f"{MESSAGES_ENDPOINT}/{country_code}/{phone}"
                async with session.get(messages_url, timeout=15) as response:
                    if response.status != 200:
                        raise Exception("Failed to fetch messages")
                    
                    messages = await response.json()
                    
                    if not messages:
                        raise Exception("No messages found")
                    
                    # البحث عن رسائل تلجرام
                    telegram_codes = []
                    for msg in messages:
                        text = msg.get('text', '')
                        sender = msg.get('sender', '')
                        
                        if self.is_telegram_message(text, sender):
                            telegram_codes.append(msg)
                    
                    if telegram_codes:
                        latest_msg = telegram_codes[0]
                        code_text = latest_msg.get('text', '')
                        
                        # استخراج الكود
                        extracted_code = self.extract_code(code_text)
                        
                        result_text = f"""
📩 **تم العثور على كود التفعيل!**

📱 **الرقم:** `+{phone}`
🔢 **الكود:** `{extracted_code}`
📝 **نص الرسالة الكامل:**
{code_text}
⏰ **الوقت:** {latest_msg.get('time', 'غير معروف')}

⚠️ **تنبيه:** استخدم الكود فوراً! صلاحيته محدودة.
"""
                        buttons = [
                            [Button.inline("🔄 تحديث (كود جديد)", f"check_code:{phone}")],
                            [Button.inline("🔍 رقم جديد", b"start_search")],
                            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
                        ]
                        await event.edit(result_text, buttons=buttons, parse_mode='markdown')
                    else:
                        waiting_text = f"""
⏳ **في انتظار وصول الكود...**

📱 **الرقم:** `+{phone}`
📊 **الحالة:** لا يوجد كود بعد

💡 **تعليمات:**
• تأكد من بدء التسجيل على تلجرام
• اضغط على "تحديث" بعد 30-60 ثانية
• قد يستغرق وصول الرسالة دقيقتين

⚠️ **تنبيه:** إذا تأخر الكود، قد يكون الرقم قد استُخدم من شخص آخر.
"""
                        buttons = [
                            [Button.inline("🔄 تحديث الآن", f"check_code:{phone}")],
                            [Button.inline("🔍 رقم آخر", b"start_search")],
                            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
                        ]
                        await event.edit(waiting_text, buttons=buttons, parse_mode='markdown')
                        
        except Exception as e:
            logger.error(f"Error checking code: {e}")
            error_text = "❌ تعذر جلب الرسائل. حاول مرة أخرى."
            buttons = [
                [Button.inline("🔄 إعادة المحاولة", f"check_code:{phone}")],
                [Button.inline("🔙 رجوع", b"back_main")]
            ]
            await event.edit(error_text, buttons=buttons)
    
    def extract_country_code(self, phone):
        """استخراج كود الدولة من الرقم"""
        codes = ['1', '44', '49', '33', '39', '34', '7', '86', '91', '81', '61', '55', '52', '82', '31']
        for code in codes:
            if phone.startswith(code):
                return code
        return phone[:2] if len(phone) > 2 else phone[:1]
    
    def is_telegram_message(self, text, sender):
        """التحقق مما إذا كانت الرسالة من تلجرام"""
        text_lower = text.lower()
        sender_lower = sender.lower()
        
        telegram_keywords = [
            'telegram', 'code', 'verification', 'login', 'tg', 
            'web login', 'new login', 'device', 'telegram code',
            'كود', 'تلجرام', 'تيليجرام', 'رمز', 'تحقق'
        ]
        
        return any(keyword in text_lower for keyword in telegram_keywords) or \
               any(keyword in sender_lower for keyword in ['telegram', 'tg'])
    
    def extract_code(self, text):
        """استخراج الكود من النص"""
        # البحث عن أرقام مكونة من 5-6 أرقام
        patterns = [
            r'\b\d{5}\b',
            r'\b\d{6}\b',
            r'code[:\s]+(\d+)',
            r'رمز[:\s]+(\d+)',
            r'كود[:\s]+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0) if match.group(0).isdigit() else match.group(1)
        
        return "غير محدد"
    
    async def show_help(self, event, edit=False):
        """عرض تعليمات الاستخدام"""
        text = """
❓ **كيفية استخدام البوت:**

**الخطوات:**
1️⃣ اضغط على "🔍 بدء البحث"
2️⃣ اختر الدولة المطلوبة
3️⃣ انتظر حتى يجد البوت رقماً متاحاً
4️⃣ انسخ الرقم واستخدمه للتسجيل على تلجرام
5️⃣ اضغط على "📩 جلب آخر كود" للحصول على الكود

**⚠️ تحذيرات مهمة:**
• الأرقام مؤقتة وعامة (يمكن للجميع رؤيتها)
• لا تستخدمها لحسابات مهمة أو شخصية
• سرعة الاستخدام مطلوبة جداً
• قد يستخدم الرقم من شخص آخر قبلك

**🔒 الأمان:**
• هذا البوت للاختبار والتعلم فقط
• لا تُدخل معلومات شخصية حقيقية
"""
        buttons = [[Button.inline("🔙 رجوع للرئيسية", b"back_main")]]
        
        if edit:
            await event.edit(text, buttons=buttons, parse_mode='markdown')
        else:
            await event.respond(text, buttons=buttons, parse_mode='markdown')
    
    async def show_about(self, event, edit=False):
        """عرض معلومات عن البوت"""
        text = f"""
ℹ️ **عن البوت:**

🤖 **اسم البوت:** Telegram OTP Finder
📌 **الإصدار:** 2.0
👨‍💻 **المطور:** @YourUsername

🔧 **التقنيات المستخدمة:**
• Python 3.x
• Telethon Library
• Free-OTP-API (Shelex)

📡 **مصدر الأرقام:**
`github.com/Shelex/free-otp-api`

⚡ **الوصف:**
بوت متخصص في البحث عن أرقام وهمية مؤقتة
للتسجيل على تلجرام وجلب أكواد التفعيل.

📝 **للتبليغ عن مشاكل:**
تواصل مع المطور

🔙 اضغط على زر الرجوع للعودة للقائمة الرئيسية
"""
        buttons = [[Button.inline("🔙 رجوع للرئيسية", b"back_main")]]
        
        if edit:
            await event.edit(text, buttons=buttons, parse_mode='markdown')
        else:
            await event.respond(text, buttons=buttons, parse_mode='markdown')
    
    async def handle_text_message(self, event):
        """معالجة الرسائل النصية العادية"""
        text = event.message.text.strip()
        
        # إذا كانت الرسالة تحتوي على أمر غير معروف
        if text.startswith('/'):
            await event.respond(
                "⚠️ الأمر غير معروف. استخدم /start للقائمة الرئيسية",
                buttons=[Button.inline("🏠 القائمة الرئيسية", b"back_main")]
            )
            return
        
        # أي رسالة أخرى
        await event.respond(
            "👋 مرحباً! استخدم الأزرار للتنقل",
            buttons=[Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        )

# تشغيل البوت
async def main():
    """الدالة الرئيسية"""
    print("🚀 Starting Telegram OTP Bot...")
    print(f"📱 API ID: {API_ID}")
    print(f"🔑 API Hash: {API_HASH[:10]}...")
    print("=" * 50)
    
    bot = TelegramOTPBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise

if __name__ == "__main__":
    # تشغيل البوت
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Failed to start: {e}")
