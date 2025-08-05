import os
import re
import pickle
import logging
import asyncio
from typing import Dict, Any, Optional

from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Update
)
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired,
    PhoneNumberInvalid, PhoneNumberUnoccupied, BadRequest, FloodWait
)
from pyrogram.enums import ParseMode

from fastapi import FastAPI, Request
from starlette.responses import Response

# تكوين السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- إعدادات البوت والويب هوك ---
TOKEN = os.getenv("TOKEN", "8247037355:AAH2rRm9PJCXqcVISS8g-EL1lv3tvQTXFys")
API_ID = int(os.getenv("APIID", "23656977"))
API_HASH = os.getenv("APIHASH", "49d3f43531a92b3f5bc403766313ca1e")
WEBHOOK_URL = os.getenv("WEBHOOKURL", "https://autu2.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL_FULL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# --- تخزين البيانات ---
user_data: Dict[int, Dict[str, Any]] = {}
temp_sessions: Dict[int, Dict[str, Any]] = {}

# --- حالة المستخدم (FSM) ---
user_states: Dict[int, str] = {}
STATE_LOGIN_PHONE = "login_phone"
STATE_LOGIN_CODE = "login_code"
STATE_LOGIN_PASSWORD = "login_password"
STATE_SET_MESSAGE = "set_message"
STATE_SET_GROUPS = "set_groups"
STATE_SET_COUNT = "set_count"

# --- تحميل وحفظ البيانات ---
DATA_FILE = 'user_data.pkl'

def load_data():
    global user_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                user_data = pickle.load(f)
                logger.info("تم تحميل بيانات المستخدمين بنجاح.")
        except Exception as e:
            logger.error(f"خطأ في تحميل البيانات: {e}")

def save_data():
    try:
        with open(DATA_FILE, 'wb') as f:
            pickle.dump(user_data, f)
            logger.info("تم حفظ بيانات المستخدمين بنجاح.")
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")

# --- لوحات المفاتيح ---
def main_menu_keyboard(user_id: int):
    keyboard = []
    if user_id not in user_data or not user_data.get(user_id, {}).get('logged_in'):
        keyboard.append([InlineKeyboardButton("🌱 1. تسجيل الدخول", callback_data='login')])
    else:
        keyboard.append([InlineKeyboardButton("📝 2. تعيين الرسالة", callback_data='set_message')])
        keyboard.append([InlineKeyboardButton("🌿 3. تعيين المجموعات", callback_data='set_groups')])
        keyboard.append([InlineKeyboardButton("🍀 4. تعيين العدد", callback_data='set_count')])
        keyboard.append([InlineKeyboardButton("⏱ 5. ضبط التوقيت", callback_data='set_interval')])
        keyboard.append([
            InlineKeyboardButton("🚀 بدء النشر", callback_data='start_posting'),
            InlineKeyboardButton("🛑 إيقاف النشر", callback_data='stop_posting')
        ])
    keyboard.append([InlineKeyboardButton("ℹ️ حالة البوت", callback_data='bot_status')])
    return InlineKeyboardMarkup(keyboard)

def timing_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏱ كل 2 دقائق", callback_data='interval_120')],
        [InlineKeyboardButton("⏱ كل 5 دقائق", callback_data='interval_300')],
        [InlineKeyboardButton("⏱ كل 10 دقائق", callback_data='interval_600')],
        [InlineKeyboardButton("⏱ كل 15 دقائق", callback_data='interval_900')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- دوال مساعدة ---
async def validate_user_settings(user_id: int):
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

async def show_bot_status(user_id: int, bot_client: Client, chat_id: int):
    status = "ℹ️ حالة البوت:\n\n"
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
    await bot_client.send_message(chat_id, status)

# --- معالج النشر التلقائي ---
async def start_autoposting(user_id: int, bot_client: Client):
    data = user_data.get(user_id, {})
    chat_id = data.get('chat_id')

    try:
        user_client = Client(
            name=f"user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=data.get('session_string', ''),
            in_memory=True
        )
        await user_client.start()
        await bot_client.send_message(chat_id, "🚀 بدأ النشر التلقائي...")

        for i in range(data.get('count', 0)):
            if not data.get('posting', False):
                break
            
            for group in data.get('groups', []):
                try:
                    await user_client.send_message(group, data.get('message', ''))
                    logger.info(f"تم النشر في {group} ({i+1}/{data['count']})")
                    await asyncio.sleep(2)
                except BadRequest as e:
                    logger.error(f"خطأ في النشر: {e}")
                    await bot_client.send_message(chat_id, f"❌ خطأ في النشر في {group}: {str(e)}")
                except FloodWait as e:
                    logger.warning(f"تم حظر الطلب مؤقتًا: انتظر {e.value} ثواني")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    logger.error(f"خطأ غير متوقع: {e}")
                    await bot_client.send_message(chat_id, f"❌ خطأ غير متوقع في النشر: {str(e)}")
            
            if i < data.get('count', 0) - 1:
                interval = data.get('interval', 300)
                await asyncio.sleep(interval)
        
        await bot_client.send_message(chat_id, "✅ تم الانتهاء من النشر!")
    
    except Exception as e:
        logger.error(f"Error in start_autoposting: {e}")
        await bot_client.send_message(chat_id, f"❌ حدث خطأ في النشر: {str(e)}")
    finally:
        try:
            await user_client.stop()
        except:
            pass
        if user_id in user_data:
            user_data[user_id]['posting'] = False
        save_data()

# --- إعداد عميل البوت ---
app = Client(
    name="my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TOKEN,
    in_memory=True
)

@app.on_message(filters.command("start"))
async def start_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {
            'logged_in': False, 'posting': False, 'groups': [],
            'count': 0, 'interval': 300, 'message': '', 'chat_id': message.chat.id
        }
    await message.reply(
        "👋 مرحبًا بك في بوت النشر التلقائي المتقدم!\n\n"
        "🌿 يرجى اتباع الخطوات بالترتيب:\n"
        "1. تسجيل الدخول بحسابك\n"
        "2. تعيين الرسالة\n"
        "3. تعيين المجموعات\n"
        "4. تعيين عدد المرات\n"
        "5. ضبط توقيت النشر\n\n"
        "استخدم الأزرار أدناه للبدء:",
        reply_markup=main_menu_keyboard(user_id)
    )

@app.on_message(filters.text & filters.private & filters.create(lambda _, __, m: user_states.get(m.from_user.id) == STATE_LOGIN_PHONE))
async def handle_phone_input(client: Client, message: Message):
    user_id = message.from_user.id
    phone = re.sub(r'\s+', '', message.text.strip())
    
    if not re.match(r'^\+\d{10,15}$', phone):
        await message.reply("❌ رقم الهاتف غير صحيح. مثال صحيح: +967734763250")
        return
    
    try:
        user_client = Client(f"user_{user_id}", API_ID, API_HASH, in_memory=True)
        await user_client.connect()
        sent_code = await user_client.send_code(phone)
        
        temp_sessions[user_id] = {
            'client': user_client,
            'phone': phone,
            'phone_code_hash': sent_code.phone_code_hash
        }
        
        user_states[user_id] = STATE_LOGIN_CODE
        await message.reply("🔢 تم إرسال رمز التحقق إليك. الرجاء إرسال الرمز:")
    except PhoneNumberInvalid:
        await message.reply("❌ رقم الهاتف غير صالح. الرجاء التحقق وإعادة المحاولة.")
    except PhoneNumberUnoccupied:
        await message.reply("❌ رقم الهاتف غير مسجل في Telegram.")
    except FloodWait as e:
        await message.reply(f"⏳ تم حظر الطلب مؤقتًا. الرجاء الانتظار {e.value} ثواني.")
    except Exception as e:
        logger.error(f"خطأ في معالجة رقم الهاتف: {e}")
        await message.reply(f"❌ حدث خطأ غير متوقع: {str(e)}")

@app.on_message(filters.text & filters.private & filters.create(lambda _, __, m: user_states.get(m.from_user.id) == STATE_LOGIN_CODE))
async def handle_code_input(client: Client, message: Message):
    user_id = message.from_user.id
    code = message.text.strip()
    
    if user_id not in temp_sessions:
        await message.reply("❌ انتهت الجلسة. الرجاء البدء من جديد.")
        user_states.pop(user_id, None)
        return
    
    session = temp_sessions[user_id]
    user_client = session['client']
    
    try:
        await user_client.sign_in(session['phone'], session['phone_code_hash'], code)
        session_string = await user_client.export_session_string()
        user_data[user_id].update({
            'session_string': session_string,
            'logged_in': True,
        })
        await message.reply("✅ تم تسجيل الدخول بنجاح!")
        save_data()
        user_states.pop(user_id, None)
    except SessionPasswordNeeded:
        user_states[user_id] = STATE_LOGIN_PASSWORD
        await message.reply("🔐 الحساب محمي بكلمة مرور ثنائية. الرجاء إرسال كلمة المرور:")
    except (PhoneCodeInvalid, PhoneCodeExpired):
        await message.reply("❌ رمز التحقق غير صحيح أو منتهي الصلاحية.")
    except Exception as e:
        logger.error(f"خطأ في معالجة رمز التحقق: {e}")
        await message.reply(f"❌ فشل تسجيل الدخول: {str(e)}")
    finally:
        if 'client' in temp_sessions.get(user_id, {}):
            await temp_sessions[user_id]['client'].stop()
            temp_sessions.pop(user_id, None)

@app.on_message(filters.text & filters.private & filters.create(lambda _, __, m: user_states.get(m.from_user.id) == STATE_LOGIN_PASSWORD))
async def handle_password_input(client: Client, message: Message):
    user_id = message.from_user.id
    password = message.text
    
    if user_id not in temp_sessions:
        await message.reply("❌ انتهت الجلسة. الرجاء البدء من جديد.")
        user_states.pop(user_id, None)
        return
    
    user_client = temp_sessions[user_id]['client']
    try:
        await user_client.check_password(password=password)
        session_string = await user_client.export_session_string()
        user_data[user_id].update({
            'session_string': session_string,
            'logged_in': True,
        })
        await message.reply("✅ تم تسجيل الدخول بنجاح!")
        save_data()
    except Exception as e:
        logger.error(f"خطأ في معالجة كلمة المرور: {e}")
        await message.reply(f"❌ كلمة المرور غير صحيحة: {str(e)}")
    finally:
        user_states.pop(user_id, None)
        if 'client' in temp_sessions.get(user_id, {}):
            await temp_sessions[user_id]['client'].stop()
            temp_sessions.pop(user_id, None)

@app.on_message(filters.text & filters.private & filters.create(lambda _, __, m: user_states.get(m.from_user.id) == STATE_SET_MESSAGE))
async def handle_message_input(client: Client, message: Message):
    user_id = message.from_user.id
    user_data[user_id]['message'] = message.text
    await message.reply("✅ تم حفظ الرسالة بنجاح!")
    save_data()
    user_states.pop(user_id, None)
    await message.reply("القائمة الرئيسية:", reply_markup=main_menu_keyboard(user_id))

@app.on_message(filters.text & filters.private & filters.create(lambda _, __, m: user_states.get(m.from_user.id) == STATE_SET_GROUPS))
async def handle_groups_input(client: Client, message: Message):
    user_id = message.from_user.id
    groups = message.text.split()
    
    user_data[user_id]['groups'] = groups
    await message.reply(f"✅ تم حفظ {len(groups)} مجموعة بنجاح!")
    save_data()
    user_states.pop(user_id, None)
    await message.reply("القائمة الرئيسية:", reply_markup=main_menu_keyboard(user_id))

@app.on_message(filters.text & filters.private & filters.create(lambda _, __, m: user_states.get(m.from_user.id) == STATE_SET_COUNT))
async def handle_count_input(client: Client, message: Message):
    user_id = message.from_user.id
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
        
        user_data[user_id]['count'] = count
        await message.reply(f"✅ تم تعيين عدد النشرات إلى {count}!")
        save_data()
    except ValueError:
        await message.reply("❌ الرجاء إدخال عدد صحيح موجب.")
    finally:
        user_states.pop(user_id, None)
        await message.reply("القائمة الرئيسية:", reply_markup=main_menu_keyboard(user_id))

@app.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if data == 'login':
        if user_data.get(user_id, {}).get('logged_in'):
            await query.answer("⚠️ لديك جلسة نشطة بالفعل!", show_alert=True)
            return
        user_states[user_id] = STATE_LOGIN_PHONE
        await query.message.edit_text(
            "📱 الرجاء إرسال رقم هاتفك مع رمز الدولة\n"
            "مثال: +201234567890",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == 'set_message':
        user_states[user_id] = STATE_SET_MESSAGE
        await query.message.edit_text("📝 أرسل الرسالة التي تريد نشرها.")
    
    elif data == 'set_groups':
        user_states[user_id] = STATE_SET_GROUPS
        await query.message.edit_text("🌿 أرسل معرفات المجموعات (مفصولة بمسافات).")
    
    elif data == 'set_count':
        user_states[user_id] = STATE_SET_COUNT
        await query.message.edit_text("🍀 أرسل عدد مرات النشر المطلوبة.")
    
    elif data == 'set_interval':
        await query.message.edit_text("⏱ اختر الفترة بين النشرات:", reply_markup=timing_keyboard())

    elif data.startswith('interval_'):
        interval = int(data.split('_')[1])
        user_data[user_id]['interval'] = interval
        save_data()
        await query.message.edit_text(
            f"✅ تم ضبط التوقيت على كل {interval//60} دقائق",
            reply_markup=main_menu_keyboard(user_id)
        )

    elif data == 'start_posting':
        if await validate_user_settings(user_id):
            user_data[user_id]['posting'] = True
            user_data[user_id]['chat_id'] = query.message.chat.id
            save_data()
            await query.answer("🚀 بدأ النشر التلقائي...", show_alert=True)
            asyncio.create_task(start_autoposting(user_id, app))
        else:
            await query.answer("❌ يرجى إكمال جميع إعدادات البوت أولاً", show_alert=True)
    
    elif data == 'stop_posting':
        user_data[user_id]['posting'] = False
        save_data()
        await query.answer("🛑 تم إيقاف النشر التلقائي", show_alert=True)
        await query.message.edit_text("🌿 القائمة الرئيسية", reply_markup=main_menu_keyboard(user_id))

    elif data == 'bot_status':
        await show_bot_status(user_id, client, query.message.chat.id)
        await query.answer()

    elif data == 'back_to_main':
        await query.message.edit_text("🌿 القائمة الرئيسية", reply_markup=main_menu_keyboard(user_id))

# --- إعداد FastAPI للويب هوك ---
api = FastAPI()

@api.on_event("startup")
async def startup_event():
    load_data()
    # هنا لا نستخدم app.set_webhook()
    await app.start()
    await app.set_webhook(WEBHOOK_URL_FULL)
    logger.info(f"تم إعداد الويب هوك بنجاح على {WEBHOOK_URL_FULL}")
    logger.info("البوت يعمل بنجاح!")

@api.on_event("shutdown")
async def shutdown_event():
    save_data()
    await app.stop()
    await app.set_webhook(None) # تعطيل الويب هوك عند إيقاف التشغيل
    logger.info("إيقاف البوت...")

@api.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update = Update.parse_raw(await request.body())
    await app.process_update(update)
    return Response(status_code=200)

