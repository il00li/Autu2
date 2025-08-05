import os
import re
import pickle
import logging
import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.storage import BaseStorage
from aiogram.utils.executor import start_webhook
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired,
    PhoneNumberInvalid, PhoneNumberUnoccupied, BadRequest, FloodWait
)

# تكوين السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تكوين FastAPI
app = FastAPI()

# بيانات البوت
TOKEN = os.getenv("TOKEN", "8247037355:AAH2rRm9PJCXqcVISS8g-EL1lv3tvQTXFys")
API_ID = int(os.getenv("API_ID", "23656977"))
API_HASH = os.getenv("API_HASH", "49d3f43531a92b3f5bc403766313ca1e")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://autu2.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL_FULL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# تخزين الحالة في الذاكرة (بدون aiogram.contrib)
class MemoryStorage(BaseStorage):
    def __init__(self):
        self.data = {}

    async def wait_closed(self):
        pass

    async def close(self):
        self.data.clear()

    async def get_state(self, *args, **kwargs):
        chat = kwargs.get('chat')
        user = kwargs.get('user')
        key = f"fsm:{chat}:{user}"
        return self.data.get(key, {}).get('state')

    async def get_data(self, *args, **kwargs):
        chat = kwargs.get('chat')
        user = kwargs.get('user')
        key = f"fsm:{chat}:{user}"
        return self.data.get(key, {}).get('data', {})

    async def set_state(self, *args, **kwargs):
        chat = kwargs.get('chat')
        user = kwargs.get('user')
        state = kwargs.get('state')
        key = f"fsm:{chat}:{user}"
        if key not in self.data:
            self.data[key] = {}
        self.data[key]['state'] = state

    async def set_data(self, *args, **kwargs):
        chat = kwargs.get('chat')
        user = kwargs.get('user')
        data = kwargs.get('data')
        key = f"fsm:{chat}:{user}"
        if key not in self.data:
            self.data[key] = {}
        self.data[key]['data'] = data

    async def update_data(self, *args, **kwargs):
        chat = kwargs.get('chat')
        user = kwargs.get('user')
        data = kwargs.get('data')
        key = f"fsm:{chat}:{user}"
        if key not in self.data:
            self.data[key] = {'data': {}}
        self.data[key]['data'].update(data)

    async def reset_state(self, *args, **kwargs):
        await self.set_state(state=None, *args, **kwargs)

# تكوين Aiogram
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# حالات المستخدم
class UserStates(StatesGroup):
    LOGIN_PHONE = State()
    LOGIN_CODE = State()
    LOGIN_PASSWORD = State()
    SET_MESSAGE = State()
    SET_GROUPS = State()
    SET_COUNT = State()

# تخزين بيانات المستخدمين
user_data = {}
temp_sessions = {}

# خيارات التوقيت (بالثواني)
TIMING_OPTIONS = {
    "2 دقائق": 120,
    "5 دقائق": 300,
    "10 دقائق": 600,
    "15 دقائق": 900
}

# تحميل البيانات المحفوظة
def load_data():
    global user_data
    if os.path.exists('user_data.pkl'):
        try:
            with open('user_data.pkl', 'rb') as f:
                user_data = pickle.load(f)
                logger.info("تم تحميل بيانات المستخدمين بنجاح")
        except Exception as e:
            logger.error(f"خطأ في تحميل البيانات: {e}")

# حفظ البيانات
def save_data():
    try:
        with open('user_data.pkl', 'wb') as f:
            pickle.dump(user_data, f)
            logger.info("تم حفظ بيانات المستخدمين بنجاح")
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")

# إنشاء لوحة المفاتيح الرئيسية
def main_menu_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup()
    
    if user_id not in user_data or not user_data.get(user_id, {}).get('logged_in'):
        keyboard.add(types.InlineKeyboardButton("🌱 1. تسجيل الدخول", callback_data='login'))
    else:
        keyboard.add(types.InlineKeyboardButton("📝 2. تعيين الرسالة", callback_data='set_message'))
        keyboard.add(types.InlineKeyboardButton("🌿 3. تعيين المجموعات", callback_data='set_groups'))
        keyboard.add(types.InlineKeyboardButton("🍀 4. تعيين العدد", callback_data='set_count'))
        keyboard.add(types.InlineKeyboardButton("⏱ 5. ضبط التوقيت", callback_data='set_interval'))
    
    keyboard.row(
        types.InlineKeyboardButton("🚀 بدء النشر", callback_data='start_posting'),
        types.InlineKeyboardButton("🛑 إيقاف النشر", callback_data='stop_posting')
    )
    keyboard.add(types.InlineKeyboardButton("ℹ️ حالة البوت", callback_data='bot_status'))
    
    return keyboard

# لوحة اختيار التوقيت
def timing_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("⏱ كل 2 دقائق", callback_data='interval_120'))
    keyboard.add(types.InlineKeyboardButton("⏱ كل 5 دقائق", callback_data='interval_300'))
    keyboard.add(types.InlineKeyboardButton("⏱ كل 10 دقائق", callback_data='interval_600'))
    keyboard.add(types.InlineKeyboardButton("⏱ كل 15 دقائق", callback_data='interval_900'))
    keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main'))
    return keyboard

# بدء البوت
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {
            'logged_in': False,
            'posting': False,
            'groups': [],
            'count': 0,
            'interval': 300,
            'message': ''
        }
    
    await message.reply(
        "👋 **مرحبًا بك في بوت النشر التلقائي المتقدم!**\n\n"
        "🌿 يرجى اتباع الخطوات بالترتيب:\n"
        "1. تسجيل الدخول بحسابك\n"
        "2. تعيين الرسالة\n"
        "3. تعيين المجموعات\n"
        "4. تعيين عدد المرات\n"
        "5. ضبط توقيت النشر\n\n"
        "استخدم الأزرار أدناه للبدء:",
        reply_markup=main_menu_keyboard(user_id),
        parse_mode='Markdown'
    )

# معالجة الأزرار
@dp.callback_query_handler()
async def handle_buttons(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    
    try:
        if callback_query.data == 'login':
            await UserStates.LOGIN_PHONE.set()
            await bot.send_message(
                chat_id,
                "📱 **الرجاء إرسال رقم هاتفك مع رمز الدولة**\n"
                "مثال: +201234567890\n\n"
                "🛑 سيتم استخدامه فقط للنشر",
                parse_mode='Markdown'
            )
            
        elif callback_query.data == 'set_message':
            await UserStates.SET_MESSAGE.set()
            await bot.send_message(
                chat_id,
                "📝 **أرسل الرسالة التي تريد نشرها**\n"
                "يمكنك استخدام تنسيق Markdown",
                parse_mode='Markdown'
            )
            
        elif callback_query.data == 'set_groups':
            await UserStates.SET_GROUPS.set()
            await bot.send_message(
                chat_id,
                "🌿 **أرسل معرفات المجموعات (مفصولة بمسافات)**\n"
                "مثال: `@group1 @group2` أو `-10012345678 -10087654321`",
                parse_mode='Markdown'
            )
            
        elif callback_query.data == 'set_count':
            await UserStates.SET_COUNT.set()
            await bot.send_message(
                chat_id,
                "🍀 **أرسل عدد مرات النشر المطلوبة**\n"
                "يجب أن يكون رقماً صحيحاً موجباً",
                parse_mode='Markdown'
            )
            
        elif callback_query.data == 'set_interval':
            await callback_query.message.edit_text(
                "⏱ **اختر الفترة بين النشرات:**",
                reply_markup=timing_keyboard()
            )
            
        elif callback_query.data.startswith('interval_'):
            interval = int(callback_query.data.split('_')[1])
            user_data[user_id]['interval'] = interval
            await bot.send_message(
                chat_id,
                f"✅ تم ضبط التوقيت على كل {interval//60} دقائق",
                reply_markup=main_menu_keyboard(user_id)
            )
            save_data()
            
        elif callback_query.data == 'start_posting':
            if await validate_user_settings(user_id):
                user_data[user_id]['posting'] = True
                await callback_query.answer("🚀 بدأ النشر التلقائي...")
                asyncio.create_task(start_auto_posting(user_id, chat_id))
            else:
                await callback_query.answer(
                    "❌ يرجى إكمال جميع إعدادات البوت أولاً",
                    show_alert=True
                )
                
        elif callback_query.data == 'stop_posting':
            user_data[user_id]['posting'] = False
            await callback_query.answer("🛑 تم إيقاف النشر التلقائي")
            
        elif callback_query.data == 'bot_status':
            await show_bot_status(user_id, callback_query)
            
        elif callback_query.data == 'back_to_main':
            await callback_query.message.edit_text(
                "🌿 **القائمة الرئيسية**",
                reply_markup=main_menu_keyboard(user_id)
            )
            
    except Exception as e:
        logger.error(f"Error in handle_buttons: {e}")
        await callback_query.answer("❌ حدث خطأ ما!")

# تأكيد إعدادات المستخدم
async def validate_user_settings(user_id):
    if user_id not in user_data:
        return False
    
    data = user_data[user_id]
    required = [
        data.get('logged_in', False),
        data.get('message', ''),
        len(data.get('groups', [])) > 0,
        data.get('count', 0) > 0,
        data.get('interval', 0) > 0
    ]
    
    return all(required)

# عرض حالة البوت
async def show_bot_status(user_id, callback_query: types.CallbackQuery):
    status = "ℹ️ **حالة البوت:**\n\n"
    
    if user_id in user_data:
        data = user_data[user_id]
        status += f"🔹 الحساب: {'✅ مسجل' if data.get('logged_in') else '❌ غير مسجل'}\n"
        status += f"📝 الرسالة: {'✅ معينة' if data.get('message') else '❌ غير معينة'}\n"
        status += f"🌿 المجموعات: {len(data.get('groups', []))}\n"
        status += f"🍀 العدد: {data.get('count', '❌ غير معين')}\n"
        status += f"⏱ التوقيت: كل {data.get('interval', 0)//60} دقائق\n"
        status += f"🚀 النشر: {'✅ نشط' if data.get('posting', False) else '❌ غير نشط'}\n"
    else:
        status += "❌ لم يتم إعداد البوت بعد"
    
    await callback_query.answer(status, show_alert=True)

# معالجة رقم الهاتف
@dp.message_handler(state=UserStates.LOGIN_PHONE)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        # تنظيف الرقم وإزالة المسافات
        phone = re.sub(r'\s+', '', message.text.strip())
        
        # التحقق من صحة الرقم
        if not re.match(r'^\+\d{10,15}$', phone):
            await message.reply("❌ رقم الهاتف غير صحيح. مثال صحيح: +967734763250")
            return
        
        # التحقق من وجود جلسة نشطة
        if user_id in user_data and user_data[user_id].get('logged_in'):
            await message.reply("⚠️ لديك جلسة نشطة بالفعل!")
            await state.finish()
            return
        
        # إنشاء عميل Pyrogram
        client = Client(
            f"user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            phone_number=phone,
            in_memory=True
        )
        
        # الاتصال وإرسال رمز التحقق
        await client.connect()
        sent_code = await client.send_code(phone)
        
        # حفظ الجلسة المؤقتة
        temp_sessions[user_id] = {
            'client': client,
            'phone': phone,
            'phone_code_hash': sent_code.phone_code_hash
        }
        
        await message.reply(
            "🔢 **تم إرسال رمز التحقق إليك.**\n"
            "الرجاء إرسال الرمز (5 أرقام):"
        )
        await UserStates.LOGIN_CODE.set()
    
    except PhoneNumberInvalid:
        await message.reply("❌ رقم الهاتف غير صالح. الرجاء التحقق وإعادة المحاولة.")
    except PhoneNumberUnoccupied:
        await message.reply("❌ رقم الهاتف غير مسجل في Telegram.")
    except FloodWait as e:
        await message.reply(f"⏳ تم حظر الطلب مؤقتًا. الرجاء الانتظار {e.x} ثواني قبل المحاولة مرة أخرى.")
    except Exception as e:
        logger.error(f"Error in process_phone: {e}")
        await message.reply(f"❌ حدث خطأ غير متوقع: {str(e)}")
    finally:
        await state.finish()

# معالجة رمز التحقق
@dp.message_handler(state=UserStates.LOGIN_CODE)
async def process_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip()
    
    try:
        if user_id not in temp_sessions:
            await message.reply("❌ انتهت الجلسة. الرجاء البدء من جديد.")
            return
        
        client = temp_sessions[user_id]['client']
        phone = temp_sessions[user_id]['phone']
        phone_code_hash = temp_sessions[user_id]['phone_code_hash']
        
        # تسجيل الدخول بالرمز
        await client.sign_in(phone, phone_code_hash, code)
        
        # تخزين الجلسة
        session_string = await client.export_session_string()
        user_data[user_id] = {
            'session_string': session_string,
            'logged_in': True,
            'posting': False,
            'groups': [],
            'count': 0,
            'interval': 300,
            'message': ''
        }
        
        await message.reply("✅ **تم تسجيل الدخول بنجاح!**")
        save_data()
    
    except SessionPasswordNeeded:
        await message.reply(
            "🔐 **الحساب محمي بكلمة مرور ثنائية.**\n"
            "الرجاء إرسال كلمة المرور:"
        )
        await UserStates.LOGIN_PASSWORD.set()
    except (PhoneCodeInvalid, PhoneCodeExpired):
        await message.reply("❌ رمز التحقق غير صحيح أو منتهي الصلاحية.")
    except Exception as e:
        logger.error(f"Error in process_code: {e}")
        await message.reply(f"❌ فشل تسجيل الدخول: {str(e)}")
    finally:
        if user_id in temp_sessions:
            try:
                await temp_sessions[user_id]['client'].disconnect()
                del temp_sessions[user_id]
            except:
                pass
        await state.finish()

# معالجة كلمة المرور الثنائية
@dp.message_handler(state=UserStates.LOGIN_PASSWORD)
async def process_password(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    password = message.text
    
    try:
        if user_id not in temp_sessions:
            await message.reply("❌ انتهت الجلسة. الرجاء البدء من جديد.")
            return
        
        client = temp_sessions[user_id]['client']
        
        # تسجيل الدخول بكلمة المرور
        await client.check_password(password=password)
        
        # تخزين الجلسة
        session_string = await client.export_session_string()
        user_data[user_id] = {
            'session_string': session_string,
            'logged_in': True,
            'posting': False,
            'groups': [],
            'count': 0,
            'interval': 300,
            'message': ''
        }
        
        await message.reply("✅ **تم تسجيل الدخول بنجاح!**")
        save_data()
    
    except Exception as e:
        logger.error(f"Error in process_password: {e}")
        await message.reply(f"❌ كلمة المرور غير صحيحة: {str(e)}")
    finally:
        if user_id in temp_sessions:
            try:
                await temp_sessions[user_id]['client'].disconnect()
                del temp_sessions[user_id]
            except:
                pass
        await state.finish()

# معالجة الرسالة
@dp.message_handler(state=UserStates.SET_MESSAGE)
async def process_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data[user_id]['message'] = message.text
    await message.reply("✅ **تم حفظ الرسالة بنجاح!**")
    save_data()
    await state.finish()

# معالجة المجموعات
@dp.message_handler(state=UserStates.SET_GROUPS)
async def process_groups(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    groups = []
    
    for group in message.text.split():
        if group.startswith("https://t.me/"):
            group = "@" + group.split("/")[-1]
        elif group.startswith("t.me/"):
            group = "@" + group.split("/")[-1]
        elif group.startswith("https://telegram.me/"):
            group = "@" + group.split("/")[-1]
        groups.append(group.strip())
    
    user_data[user_id]['groups'] = groups
    await message.reply(f"✅ **تم حفظ {len(groups)} مجموعة بنجاح!**")
    save_data()
    await state.finish()

# معالجة العدد
@dp.message_handler(state=UserStates.SET_COUNT)
async def process_count(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
        
        user_data[user_id]['count'] = count
        await message.reply(f"✅ **تم تعيين عدد النشرات إلى {count}!**")
        save_data()
    
    except ValueError:
        await message.reply("❌ الرجاء إدخال عدد صحيح موجب.")
    finally:
        await state.finish()

# بدء النشر التلقائي
async def start_auto_posting(user_id, chat_id):
    data = user_data.get(user_id, {})
    
    try:
        client = Client(
            f"user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=data.get('session_string', ''),
            in_memory=True
        )
        
        # بدء العميل
        await client.start()
        await bot.send_message(chat_id, "🚀 بدأ النشر التلقائي...")
        
        # حلقة النشر
        for i in range(data.get('count', 0)):
            if not data.get('posting', True):
                break
            
            for group in data.get('groups', []):
                try:
                    # إرسال الرسالة
                    await client.send_message(group, data.get('message', ''))
                    logger.info(f"تم النشر في {group} ({i+1}/{data['count']})")
                    await asyncio.sleep(2)  # تأخير بين المجموعات
                except BadRequest as e:
                    logger.error(f"خطأ في النشر: {e}")
                    await bot.send_message(chat_id, f"❌ خطأ في النشر في {group}: {str(e)}")
                except FloodWait as e:
                    logger.warning(f"تم حظر الطلب مؤقتًا: انتظر {e.x} ثواني")
                    await asyncio.sleep(e.x)
                except Exception as e:
                    logger.error(f"خطأ غير متوقع: {e}")
                    await bot.send_message(chat_id, f"❌ خطأ غير متوقع في النشر: {str(e)}")
            
            # انتظار الفترة الزمنية المحددة
            if i < data.get('count', 0) - 1:
                interval = data.get('interval', 300)
                await asyncio.sleep(interval)
        
        await bot.send_message(chat_id, "✅ تم الانتهاء من النشر!")
    
    except Exception as e:
        logger.error(f"Error in start_auto_posting: {e}")
        await bot.send_message(chat_id, f"❌ حدث خطأ في النشر: {str(e)}")
    finally:
        try:
            await client.stop()
        except:
            pass
        if user_id in user_data:
            user_data[user_id]['posting'] = False
        save_data()

# Webhook الإعدادات
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL_FULL)
    load_data()
    logger.info("البوت يعمل!")

async def on_shutdown(dp):
    await bot.delete_webhook()
    logger.info("إيقاف البوت...")

# تكوين FastAPI للتعامل مع webhook
@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update = await request.json()
    update = types.Update(**update)
    await dp.process_update(update)
    return {"status": "ok"}

# نقطة الدخول الرئيسية
if __name__ == '__main__':
    # للتشغيل المحلي
    from aiogram.utils.executor import start_polling
    load_data()
    start_polling(dp, on_startup=on_startup, skip_updates=True)
else:
    # للتشغيل على Render
    @app.on_event("startup")
    async def startup():
        await on_startup(dp)
    
    @app.on_event("shutdown")
    async def shutdown():
        await on_shutdown(dp)
