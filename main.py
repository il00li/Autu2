import telebot
from telebot import types
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    PhoneNumberInvalid,
    PhoneNumberUnoccupied,
    BadRequest,
    FloodWait
)
import asyncio
import logging
import re
import os
import pickle
import time
import sys
import threading

# تكوين السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# بيانات البوت
TOKEN = "8059858208:AAEfjTIUhSiFdYLFB5B_TvGvaAXXZv5L67A "
API_ID = 23656977
API_HASH = "49d3f43531a92b3f5bc403766313ca1e"

bot = telebot.TeleBot(TOKEN)

# تخزين بيانات المستخدمين
user_data = {}
temp_sessions = {}
data_lock = threading.Lock()  # لمنع تضارب الوصول للبيانات

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
    with data_lock:
        try:
            with open('user_data.pkl', 'wb') as f:
                pickle.dump(user_data, f)
                logger.info("تم حفظ بيانات المستخدمين بنجاح")
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات: {e}")

# إنشاء لوحة المفاتيح الرئيسية
def main_menu_keyboard(user_id):
    markup = types.InlineKeyboardMarkup()
    
    if user_id not in user_data or not user_data.get(user_id, {}).get('logged_in'):
        markup.add(types.InlineKeyboardButton("🌱 1. تسجيل الدخول", callback_data='login'))
    else:
        markup.add(types.InlineKeyboardButton("📝 2. تعيين الرسالة", callback_data='set_message'))
        markup.add(types.InlineKeyboardButton("🌿 3. تعيين المجموعات", callback_data='set_groups'))
        markup.add(types.InlineKeyboardButton("🍀 4. تعيين العدد", callback_data='set_count'))
        markup.add(types.InlineKeyboardButton("⏱ 5. ضبط التوقيت", callback_data='set_interval'))
    
    markup.row(
        types.InlineKeyboardButton("🚀 بدء النشر", callback_data='start_posting'),
        types.InlineKeyboardButton("🛑 إيقاف النشر", callback_data='stop_posting')
    )
    markup.add(types.InlineKeyboardButton("ℹ️ حالة البوت", callback_data='bot_status'))
    
    return markup

# لوحة اختيار التوقيت
def timing_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⏱ كل 2 دقائق", callback_data='interval_120'))
    markup.add(types.InlineKeyboardButton("⏱ كل 5 دقائق", callback_data='interval_300'))
    markup.add(types.InlineKeyboardButton("⏱ كل 10 دقائق", callback_data='interval_600'))
    markup.add(types.InlineKeyboardButton("⏱ كل 15 دقائق", callback_data='interval_900'))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main'))
    return markup

# بدء البوت
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    with data_lock:
        if user_id not in user_data:
            user_data[user_id] = {
                'logged_in': False,
                'posting': False,
                'groups': [],
                'count': 0,
                'interval': 300,
                'message': ''
            }
    
    bot.send_message(
        message.chat.id,
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
@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    try:
        with data_lock:
            if user_id not in user_data:
                user_data[user_id] = {
                    'logged_in': False,
                    'posting': False,
                    'groups': [],
                    'count': 0,
                    'interval': 300,
                    'message': ''
                }
        
        if call.data == 'login':
            msg = bot.send_message(
                chat_id,
                "📱 **الرجاء إرسال رقم هاتفك مع رمز الدولة**\n"
                "مثال: +201234567890\n\n"
                "🛑 سيتم استخدامه فقط للنشر",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_phone)
            
        elif call.data == 'set_message':
            msg = bot.send_message(
                chat_id,
                "📝 **أرسل الرسالة التي تريد نشرها**\n"
                "يمكنك استخدام تنسيق Markdown",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_message)
            
        elif call.data == 'set_groups':
            msg = bot.send_message(
                chat_id,
                "🌿 **أرسل معرفات المجموعات (مفصولة بمسافات)**\n"
                "مثال: `@group1 @group2` أو `-10012345678 -10087654321`",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_groups)
            
        elif call.data == 'set_count':
            msg = bot.send_message(
                chat_id,
                "🍀 **أرسل عدد مرات النشر المطلوبة**\n"
                "يجب أن يكون رقماً صحيحاً موجباً",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_count)
            
        elif call.data == 'set_interval':
            bot.edit_message_text(
                "⏱ **اختر الفترة بين النشرات:**",
                chat_id,
                call.message.message_id,
                reply_markup=timing_keyboard()
            )
            
        elif call.data.startswith('interval_'):
            interval = int(call.data.split('_')[1])
            with data_lock:
                user_data[user_id]['interval'] = interval
            bot.send_message(
                chat_id,
                f"✅ تم ضبط التوقيت على كل {interval//60} دقائق",
                reply_markup=main_menu_keyboard(user_id)
            )
            save_data()
            
        elif call.data == 'start_posting':
            if validate_user_settings(user_id):
                with data_lock:
                    user_data[user_id]['posting'] = True
                save_data()
                bot.answer_callback_query(call.id, "🚀 بدأ النشر التلقائي...")
                threading.Thread(target=start_auto_posting, args=(user_id, chat_id)).start()
            else:
                bot.answer_callback_query(
                    call.id,
                    "❌ يرجى إكمال جميع إعدادات البوت أولاً",
                    show_alert=True
                )
                
        elif call.data == 'stop_posting':
            with data_lock:
                user_data[user_id]['posting'] = False
            save_data()
            bot.answer_callback_query(call.id, "🛑 تم إيقاف النشر التلقائي")
            
        elif call.data == 'bot_status':
            show_bot_status(user_id, call)
            
        elif call.data == 'back_to_main':
            bot.edit_message_text(
                "🌿 **القائمة الرئيسية**",
                chat_id,
                call.message.message_id,
                reply_markup=main_menu_keyboard(user_id)
            )
            
    except Exception as e:
        logger.error(f"Error in handle_buttons: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ ما!")

# تأكيد إعدادات المستخدم
def validate_user_settings(user_id):
    with data_lock:
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
def show_bot_status(user_id, call):
    with data_lock:
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
        
        bot.answer_callback_query(call.id, status, show_alert=True)

# معالجة رقم الهاتف
def process_phone(message):
    user_id = message.from_user.id
    
    try:
        # تنظيف الرقم وإزالة المسافات
        phone = re.sub(r'\s+', '', message.text.strip())
        
        # التحقق من صحة الرقم
        if not re.match(r'^\+\d{10,15}$', phone):
            bot.reply_to(message, "❌ رقم الهاتف غير صحيح. مثال صحيح: +967734763250")
            return
        
        # التحقق من وجود جلسة نشطة
        with data_lock:
            if user_id in user_data and user_data[user_id].get('logged_in'):
                bot.reply_to(message, "⚠️ لديك جلسة نشطة بالفعل!")
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
        client.connect()
        sent_code = client.send_code(phone)
        
        # حفظ الجلسة المؤقتة
        temp_sessions[user_id] = {
            'client': client,
            'phone': phone,
            'phone_code_hash': sent_code.phone_code_hash
        }
        
        msg = bot.reply_to(
            message,
            "🔢 **تم إرسال رمز التحقق إليك.**\n"
            "الرجاء إرسال الرمز (5 أرقام):"
        )
        bot.register_next_step_handler(msg, process_code)
    
    except PhoneNumberInvalid:
        bot.reply_to(message, "❌ رقم الهاتف غير صالح. الرجاء التحقق وإعادة المحاولة.")
    except PhoneNumberUnoccupied:
        bot.reply_to(message, "❌ رقم الهاتف غير مسجل في Telegram.")
    except FloodWait as e:
        bot.reply_to(message, f"⏳ تم حظر الطلب مؤقتًا. الرجاء الانتظار {e.x} ثواني قبل المحاولة مرة أخرى.")
    except Exception as e:
        logger.error(f"Error in process_phone: {e}")
        bot.reply_to(message, f"❌ حدث خطأ غير متوقع: {str(e)}")

# معالجة رمز التحقق
def process_code(message):
    user_id = message.from_user.id
    code = message.text.strip()
    
    try:
        if user_id not in temp_sessions:
            bot.reply_to(message, "❌ انتهت الجلسة. الرجاء البدء من جديد.")
            return
        
        client = temp_sessions[user_id]['client']
        phone = temp_sessions[user_id]['phone']
        phone_code_hash = temp_sessions[user_id]['phone_code_hash']
        
        # تسجيل الدخول بالرمز
        client.sign_in(phone, phone_code_hash, code)
        
        # تخزين الجلسة
        session_string = client.export_session_string()
        with data_lock:
            user_data[user_id]['session_string'] = session_string
            user_data[user_id]['logged_in'] = True
        
        bot.reply_to(message, "✅ **تم تسجيل الدخول بنجاح!**")
        save_data()
    
    except SessionPasswordNeeded:
        msg = bot.reply_to(
            message,
            "🔐 **الحساب محمي بكلمة مرور ثنائية.**\n"
            "الرجاء إرسال كلمة المرور:"
        )
        bot.register_next_step_handler(msg, process_password)
    except (PhoneCodeInvalid, PhoneCodeExpired):
        bot.reply_to(message, "❌ رمز التحقق غير صحيح أو منتهي الصلاحية.")
    except Exception as e:
        logger.error(f"Error in process_code: {e}")
        bot.reply_to(message, f"❌ فشل تسجيل الدخول: {str(e)}")
    finally:
        if user_id in temp_sessions:
            try:
                temp_sessions[user_id]['client'].disconnect()
                del temp_sessions[user_id]
            except:
                pass

# معالجة كلمة المرور الثنائية
def process_password(message):
    user_id = message.from_user.id
    password = message.text
    
    try:
        if user_id not in temp_sessions:
            bot.reply_to(message, "❌ انتهت الجلسة. الرجاء البدء من جديد.")
            return
        
        client = temp_sessions[user_id]['client']
        
        # تسجيل الدخول بكلمة المرور
        client.check_password(password=password)
        
        # تخزين الجلسة
        session_string = client.export_session_string()
        with data_lock:
            user_data[user_id]['session_string'] = session_string
            user_data[user_id]['logged_in'] = True
        
        bot.reply_to(message, "✅ **تم تسجيل الدخول بنجاح!**")
        save_data()
    
    except Exception as e:
        logger.error(f"Error in process_password: {e}")
        bot.reply_to(message, f"❌ كلمة المرور غير صحيحة: {str(e)}")
    finally:
        if user_id in temp_sessions:
            try:
                temp_sessions[user_id]['client'].disconnect()
                del temp_sessions[user_id]
            except:
                pass

# معالجة الرسالة
def process_message(message):
    user_id = message.from_user.id
    with data_lock:
        user_data[user_id]['message'] = message.text
    bot.reply_to(message, "✅ **تم حفظ الرسالة بنجاح!**")
    save_data()

# معالجة المجموعات
def process_groups(message):
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
    
    with data_lock:
        user_data[user_id]['groups'] = groups
    bot.reply_to(message, f"✅ **تم حفظ {len(groups)} مجموعة بنجاح!**")
    save_data()

# معالجة العدد
def process_count(message):
    user_id = message.from_user.id
    
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
        
        with data_lock:
            user_data[user_id]['count'] = count
        bot.reply_to(message, f"✅ **تم تعيين عدد النشرات إلى {count}!**")
        save_data()
    
    except ValueError:
        bot.reply_to(message, "❌ الرجاء إدخال عدد صحيح موجب.")

# بدء النشر التلقائي (بدون asyncio)
def start_auto_posting(user_id, chat_id):
    with data_lock:
        data = user_data.get(user_id, {})
        if not data:
            bot.send_message(chat_id, "❌ بيانات المستخدم غير موجودة!")
            return
    
    try:
        client = Client(
            f"user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=data.get('session_string', ''),
            in_memory=True
        )
        
        # بدء العميل بشكل متزامن
        client.start()
        bot.send_message(chat_id, "🚀 بدأ النشر التلقائي...")
        
        # حلقة النشر
        for i in range(data.get('count', 0)):
            with data_lock:
                if not user_data.get(user_id, {}).get('posting', True):
                    break
            
            for group in data.get('groups', []):
                try:
                    # إرسال الرسالة
                    client.send_message(group, data.get('message', ''))
                    logger.info(f"تم النشر في {group} ({i+1}/{data['count']})")
                    time.sleep(2)  # تأخير بين المجموعات
                except BadRequest as e:
                    logger.error(f"خطأ في النشر: {e}")
                    bot.send_message(chat_id, f"❌ خطأ في النشر في {group}: {str(e)}")
                except FloodWait as e:
                    logger.warning(f"تم حظر الطلب مؤقتًا: انتظر {e.x} ثواني")
                    time.sleep(e.x)
                except Exception as e:
                    logger.error(f"خطأ غير متوقع: {e}")
                    bot.send_message(chat_id, f"❌ خطأ غير متوقع في النشر: {str(e)}")
            
            # انتظار الفترة الزمنية المحددة
            if i < data.get('count', 0) - 1:
                interval = data.get('interval', 300)
                start_time = time.time()
                while time.time() - start_time < interval:
                    with data_lock:
                        if not user_data.get(user_id, {}).get('posting', True):
                            break
                    time.sleep(1)
        
        bot.send_message(chat_id, "✅ تم الانتهاء من النشر!")
    
    except Exception as e:
        logger.error(f"Error in start_auto_posting: {e}")
        bot.send_message(chat_id, f"❌ حدث خطأ في النشر: {str(e)}")
    finally:
        try:
            client.stop()
        except:
            pass
        with data_lock:
            if user_id in user_data:
                user_data[user_id]['posting'] = False
        save_data()

# إيقاف عمليات البوت السابقة
def stop_previous_instances():
    try:
        if sys.platform == 'win32':
            os.system('taskkill /f /im python.exe')
        else:
            os.system('pkill -f "python.*bot.py"')
        time.sleep(2)
    except Exception as e:
        print(f"Warning: {e}")

# تشغيل البوت
if __name__ == '__main__':
    # إيقاف أي عمليات سابقة
    stop_previous_instances()
    
    # تحميل البيانات المحفوظة
    load_data()
    
    # بدء البوت مع إعادة المحاولة عند الفشل
    logger.info("جارٍ تشغيل البوت...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=30)
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
            time.sleep(5)
