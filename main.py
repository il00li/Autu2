import os
import re
import pickle
import logging
import asyncio
from typing import Dict, Any, Optional

from telethon import TelegramClient, events, Button, functions
from telethon.tl.types import User, Channel, PeerUser, PeerChannel
from telethon.errors import (
    SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError,
    PhoneNumberInvalidError, FloodWaitError
)

from fastapi import FastAPI, Request
from starlette.responses import Response

# --- تكوين السجل ---
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
STATE_SET_TIMING = "set_timing"

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
    buttons = []
    if user_id not in user_data or not user_data.get(user_id, {}).get('logged_in'):
        buttons.append([Button.inline("🌱 1. تسجيل الدخول", b'login')])
    else:
        buttons.append([Button.inline("📝 2. تعيين الرسالة", b'set_message')])
        buttons.append([Button.inline("🌿 3. تعيين المجموعات", b'set_groups')])
        buttons.append([Button.inline("🍀 4. تعيين العدد", b'set_count')])
        buttons.append([Button.inline("⏱ 5. ضبط التوقيت", b'set_interval')])
        buttons.append([
            Button.inline("🚀 بدء النشر", b'start_posting'),
            Button.inline("🛑 إيقاف النشر", b'stop_posting')
        ])
    buttons.append([Button.inline("ℹ️ حالة البوت", b'bot_status')])
    return buttons

def timing_keyboard():
    return [
        [Button.inline("⏱ كل 2 دقائق", b'interval_120')],
        [Button.inline("⏱ كل 5 دقائق", b'interval_300')],
        [Button.inline("⏱ كل 10 دقائق", b'interval_600')],
        [Button.inline("⏱ كل 15 دقائق", b'interval_900')],
        [Button.inline("🔙 رجوع", b'back_to_main')]
    ]

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

async def show_bot_status(user_id: int, bot_client: TelegramClient, chat_id: int):
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
async def start_autoposting(user_id: int, bot_client: TelegramClient):
    data = user_data.get(user_id, {})
    chat_id = data.get('chat_id')

    try:
        user_client = TelegramClient(
            f"user_{user_id}",
            API_ID,
            API_HASH
        )
        await user_client.start(bot_token=None, phone=lambda: data['phone_for_session'], password=lambda: None)
        await bot_client.send_message(chat_id, "🚀 بدأ النشر التلقائي...")

        for i in range(data.get('count', 0)):
            if not data.get('posting', False):
                break
            
            for group in data.get('groups', []):
                try:
                    await user_client.send_message(group, data.get('message', ''))
                    logger.info(f"تم النشر في {group} ({i+1}/{data['count']})")
                    await asyncio.sleep(2)  # تأخير بين المجموعات
                except FloodWaitError as e:
                    logger.warning(f"تم حظر الطلب مؤقتًا: انتظر {e.seconds} ثواني")
                    await asyncio.sleep(e.seconds)
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
            await user_client.disconnect()
        except:
            pass
        if user_id in user_data:
            user_data[user_id]['posting'] = False
        save_data()

# --- إعداد عميل البوت ---
app = TelegramClient(
    'bot_session',
    API_ID,
    API_HASH
).start(bot_token=TOKEN)

# --- معالجات الرسائل والأوامر ---
@app.on(events.NewMessage(pattern='/start'))
async def start_command_handler(event):
    user_id = event.sender_id
    if user_id not in user_data:
        user_data[user_id] = {
            'logged_in': False, 'posting': False, 'groups': [],
            'count': 0, 'interval': 300, 'message': '', 'chat_id': event.chat_id,
            'phone_for_session': ''
        }
    await event.reply(
        "👋 مرحبًا بك في بوت النشر التلقائي المتقدم!\n\n"
        "🌿 يرجى اتباع الخطوات بالترتيب:\n"
        "1. تسجيل الدخول بحسابك\n"
        "2. تعيين الرسالة\n"
        "3. تعيين المجموعات\n"
        "4. تعيين عدد المرات\n"
        "5. ضبط توقيت النشر\n\n"
        "استخدم الأزرار أدناه للبدء:",
        buttons=main_menu_keyboard(user_id)
    )

@app.on(events.NewMessage(func=lambda e: user_states.get(e.sender_id) == STATE_LOGIN_PHONE))
async def handle_phone_input(event):
    user_id = event.sender_id
    phone = re.sub(r'\s+', '', event.message.message.strip())
    
    if not re.match(r'^\+\d{10,15}$', phone):
        await event.reply("❌ رقم الهاتف غير صحيح. مثال صحيح: +967734763250")
        return
    
    try:
        user_client = TelegramClient(f"user_{user_id}", API_ID, API_HASH)
        await user_client.connect()
        sent_code = await user_client.send_code_request(phone)
        
        temp_sessions[user_id] = {
            'client': user_client,
            'phone': phone,
            'sent_code': sent_code
        }
        
        user_states[user_id] = STATE_LOGIN_CODE
        await event.reply("🔢 تم إرسال رمز التحقق إليك. الرجاء إرسال الرمز:")
    except PhoneNumberInvalidError:
        await event.reply("❌ رقم الهاتف غير صالح. الرجاء التحقق وإعادة المحاولة.")
    except FloodWaitError as e:
        await event.reply(f"⏳ تم حظر الطلب مؤقتًا. الرجاء الانتظار {e.seconds} ثواني.")
    except Exception as e:
        logger.error(f"خطأ في معالجة رقم الهاتف: {e}")
        await event.reply(f"❌ حدث خطأ غير متوقع: {str(e)}")
        user_states.pop(user_id, None)

@app.on(events.NewMessage(func=lambda e: user_states.get(e.sender_id) == STATE_LOGIN_CODE))
async def handle_code_input(event):
    user_id = event.sender_id
    code = event.message.message.strip()
    
    if user_id not in temp_sessions:
        await event.reply("❌ انتهت الجلسة. الرجاء البدء من جديد.")
        user_states.pop(user_id, None)
        return
    
    session = temp_sessions[user_id]
    user_client = session['client']
    
    try:
        await user_client.sign_in(session['phone'], code=code, password=None, phone_code_hash=session['sent_code'].phone_code_hash)
        
        user_data[user_id].update({
            'logged_in': True,
            'phone_for_session': session['phone']
        })
        await event.reply("✅ تم تسجيل الدخول بنجاح!")
        save_data()
        user_states.pop(user_id, None)
    except SessionPasswordNeededError:
        user_states[user_id] = STATE_LOGIN_PASSWORD
        await event.reply("🔐 الحساب محمي بكلمة مرور ثنائية. الرجاء إرسال كلمة المرور:")
    except (PhoneCodeInvalidError, PhoneCodeExpiredError):
        await event.reply("❌ رمز التحقق غير صحيح أو منتهي الصلاحية.")
    except Exception as e:
        logger.error(f"خطأ في معالجة رمز التحقق: {e}")
        await event.reply(f"❌ فشل تسجيل الدخول: {str(e)}")
    finally:
        if 'client' in temp_sessions[user_id]:
            await temp_sessions[user_id]['client'].disconnect()
            temp_sessions.pop(user_id, None)
        
@app.on(events.NewMessage(func=lambda e: user_states.get(e.sender_id) == STATE_LOGIN_PASSWORD))
async def handle_password_input(event):
    user_id = event.sender_id
    password = event.message.message
    
    if user_id not in temp_sessions:
        await event.reply("❌ انتهت الجلسة. الرجاء البدء من جديد.")
        user_states.pop(user_id, None)
        return
    
    user_client = temp_sessions[user_id]['client']
    try:
        await user_client.sign_in(password=password)
        
        user_data[user_id].update({
            'logged_in': True,
            'phone_for_session': temp_sessions[user_id]['phone']
        })
        await event.reply("✅ تم تسجيل الدخول بنجاح!")
        save_data()
    except Exception as e:
        logger.error(f"خطأ في معالجة كلمة المرور: {e}")
        await event.reply(f"❌ كلمة المرور غير صحيحة: {str(e)}")
    finally:
        user_states.pop(user_id, None)
        if 'client' in temp_sessions[user_id]:
            await temp_sessions[user_id]['client'].disconnect()
            temp_sessions.pop(user_id, None)

@app.on(events.NewMessage(func=lambda e: user_states.get(e.sender_id) == STATE_SET_MESSAGE))
async def handle_message_input(event):
    user_id = event.sender_id
    user_data[user_id]['message'] = event.message.message
    await event.reply("✅ تم حفظ الرسالة بنجاح!")
    save_data()
    user_states.pop(user_id, None)
    await event.reply("القائمة الرئيسية:", buttons=main_menu_keyboard(user_id))

@app.on(events.NewMessage(func=lambda e: user_states.get(e.sender_id) == STATE_SET_GROUPS))
async def handle_groups_input(event):
    user_id = event.sender_id
    groups = event.message.message.split()
    
    user_data[user_id]['groups'] = groups
    await event.reply(f"✅ تم حفظ {len(groups)} مجموعة بنجاح!")
    save_data()
    user_states.pop(user_id, None)
    await event.reply("القائمة الرئيسية:", buttons=main_menu_keyboard(user_id))

@app.on(events.NewMessage(func=lambda e: user_states.get(e.sender_id) == STATE_SET_COUNT))
async def handle_count_input(event):
    user_id = event.sender_id
    try:
        count = int(event.message.message)
        if count <= 0:
            raise ValueError
        
        user_data[user_id]['count'] = count
        await event.reply(f"✅ تم تعيين عدد النشرات إلى {count}!")
        save_data()
    except ValueError:
        await event.reply("❌ الرجاء إدخال عدد صحيح موجب.")
    finally:
        user_states.pop(user_id, None)
        await event.reply("القائمة الرئيسية:", buttons=main_menu_keyboard(user_id))

@app.on(events.CallbackQuery())
async def callback_handler(event):
    user_id = event.sender_id
    data = event.data
    
    if data == b'login':
        if user_data.get(user_id, {}).get('logged_in'):
            await event.answer("⚠️ لديك جلسة نشطة بالفعل!", alert=True)
            return
        user_states[user_id] = STATE_LOGIN_PHONE
        await event.edit("📱 الرجاء إرسال رقم هاتفك مع رمز الدولة\n"
                         "مثال: +201234567890")

    elif data == b'set_message':
        user_states[user_id] = STATE_SET_MESSAGE
        await event.edit("📝 أرسل الرسالة التي تريد نشرها.")
    
    elif data == b'set_groups':
        user_states[user_id] = STATE_SET_GROUPS
        await event.edit("🌿 أرسل معرفات المجموعات (مفصولة بمسافات).")
    
    elif data == b'set_count':
        user_states[user_id] = STATE_SET_COUNT
        await event.edit("🍀 أرسل عدد مرات النشر المطلوبة.")
    
    elif data == b'set_interval':
        await event.edit("⏱ اختر الفترة بين النشرات:", buttons=timing_keyboard())

    elif data.startswith(b'interval_'):
        interval = int(data.split(b'_')[1].decode())
        user_data[user_id]['interval'] = interval
        save_data()
        await event.edit(
            f"✅ تم ضبط التوقيت على كل {interval//60} دقائق",
            buttons=main_menu_keyboard(user_id)
        )

    elif data == b'start_posting':
        if await validate_user_settings(user_id):
            user_data[user_id]['posting'] = True
            save_data()
            await event.answer("🚀 بدأ النشر التلقائي...", alert=True)
            asyncio.create_task(start_autoposting(user_id, app))
        else:
            await event.answer("❌ يرجى إكمال جميع إعدادات البوت أولاً", alert=True)
    
    elif data == b'stop_posting':
        user_data[user_id]['posting'] = False
        save_data()
        await event.answer("🛑 تم إيقاف النشر التلقائي", alert=True)
        await event.edit("🌿 القائمة الرئيسية", buttons=main_menu_keyboard(user_id))

    elif data == b'bot_status':
        await event.answer("جارٍ إعداد الحالة...", alert=False)
        await show_bot_status(user_id, app, event.chat_id)
    
    elif data == b'back_to_main':
        await event.edit("🌿 القائمة الرئيسية", buttons=main_menu_keyboard(user_id))

# --- إعداد FastAPI للويب هوك ---
api = FastAPI()

@api.on_event("startup")
async def startup_event():
    load_data()
    await app.start()
    await app(functions.bots.SetWebhookRequest(
        url=WEBHOOK_URL_FULL,
        max_connections=40,
        drop_pending_updates=True
    ))
    logger.info(f"تم إعداد الويب هوك بنجاح على {WEBHOOK_URL_FULL}")
    logger.info("البوت يعمل بنجاح!")

@api.on_event("shutdown")
async def shutdown_event():
    save_data()
    await app.run_until_disconnected()
    await app.disconnect()
    logger.info("إيقاف البوت...")

@api.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update = await request.body()
    update_dict = await app.to_json(update)
    await app.process_updates(update_dict)
    return Response(status_code=200)

