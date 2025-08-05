import telebot
from telebot import types
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    PhoneNumberInvalid,
    PhoneNumberUnoccupied,
    BadRequest
)
import asyncio
import logging
import re
import os
import pickle
import time
import nest_asyncio
from threading import Thread

# حل مشكلة event loop
nest_asyncio.apply()

# تكوين السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# بيانات البوت
TOKEN = "8247037355:AAH2rRm9PJCXqcVISS8g-EL1lv3tvQTXFys"
API_ID = 23656977
API_HASH = "49d3f43531a92b3f5bc403766313ca1e"

bot = telebot.TeleBot(TOKEN)

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
    markup = types.InlineKeyboardMarkup()
    
    # خطوات الإعداد
    if user_id not in user_data or not user_data[user_id].get('logged_in'):
        markup.add(types.InlineKeyboardButton("🌱 1. تسجيل الدخول", callback_data='login'))
    else:
        markup.add(types.InlineKeyboardButton("📝 2. تعيين الرسالة", callback_data='set_message'))
        markup.add(types.InlineKeyboardButton("🌿 3. تعيين المجموعات", callback_data='set_groups'))
        markup.add(types.InlineKeyboardButton("🍀 4. تعيين العدد", callback_data='set_count'))
        markup.add(types.InlineKeyboardButton("⏱ 5. ضبط التوقيت", callback_data='set_interval'))
    
    # أزرار التحكم
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
    if user_id not in user_data:
        user_data[user_id] = {
            'logged_in': False,
            'posting': False,
            'groups': [],
            'count': 0,
            'interval': 300,  # 5 دقائق افتراضياً
            'message': ''
        }
        save_data()
    
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
    message_id = call.message.message_id
    
    try:
        # إنشاء بيانات المستخدم إذا لم تكن موجودة
        if user_id not in user_data:
            user_data[user_id] = {
                'logged_in': False,
                'posting': False,
                'groups': [],
                'count': 0,
                'interval': 300,
                'message': ''
            }
            save_data()
        
        # تسجيل الدخول
        if call.data == 'login':
            msg = bot.send_message(
                chat_id,
                "📱 **الرجاء إرسال رقم هاتفك مع رمز الدولة**\n"
                "مثال: +201234567890\n\n"
                "🛑 سيتم استخدامه فقط للنشر",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_phone)
        
        # تعيين الرسالة
        elif call.data == 'set_message':
            msg = bot.send_message(
                chat_id,
                "📝 **أرسل الرسالة التي تريد نشرها**\n"
                "يمكنك استخدام تنسيق Markdown",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_message)
        
        # تعيين المجموعات
        elif call.data == 'set_groups':
            msg = bot.send_message(
                chat_id,
                "🌿 **أرسل معرفات المجموعات (مفصولة بمسافات)**\n"
                "مثال: `@group1 @group2` أو `-10012345678 -10087654321`",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_groups)
        
        # تعيين العدد
        elif call.data == 'set_count':
            msg = bot.send_message(
                chat_id,
                "🍀 **أرسل عدد مرات النشر المطلوبة**\n"
                "يجب أن يكون رقماً صحيحاً موجباً",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_count)
        
        # تعيين التوقيت
        elif call.data == 'set_interval':
            bot.edit_message_text(
                "⏱ **اختر الفترة بين النشرات:**",
                chat_id,
                message_id,
                reply_markup=timing_keyboard()
            )
        
        # اختيار التوقيت
        elif call.data.startswith('interval_'):
            interval = int(call.data.split('_')[1])
            user_data[user_id]['interval'] = interval
            bot.edit_message_text(
                f"✅ تم ضبط التوقيت على كل {interval//60} دقائق",
                chat_id,
                message_id,
                reply_markup=main_menu_keyboard(user_id)
            )
            save_data()
        
        # بدء النشر
        elif call.data == 'start_posting':
            if validate_user_settings(user_id):
                user_data[user_id]['posting'] = True
                save_data()
                bot.answer_callback_query(call.id, "🚀 بدأ النشر التلقائي...")
                # بدء النشر في خلفية منفصلة
                Thread(target=start_auto_posting, args=(user_id, chat_id)).start()
            else:
                bot.answer_callback_query(
                    call.id,
                    "❌ يرجى إكمال جميع إعدادات البوت أولاً",
                    show_alert=True
                )
        
        # إيقاف النشر
        elif call.data == 'stop_posting':
            user_data[user_id]['posting'] = False
            save_data()
            bot.answer_callback_query(call.id, "🛑 تم إيقاف النشر التلقائي")
        
        # حالة البوت
        elif call.data == 'bot_status':
            show_bot_status(user_id, call)
        
        # العودة للقائمة الرئيسية
        elif call.data == 'back_to_main':
            bot.edit_message_text(
                "🌿 **القائمة الرئيسية**",
                chat_id,
                message_id,
                reply_markup=main_menu_keyboard(user_id)
            )
    
    except Exception as e:
        logger.error(f"خطأ في معالجة الأزرار: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ ما!")

# تأكيد إعدادات المستخدم
def validate_user_settings(user_id):
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
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "❌ لم يتم إعداد البوت بعد", show_alert=True)
        return
    
    data = user_data[user_id]
    status = (
        "ℹ️ **حالة البوت:**\n\n"
        f"🔹 الحساب: {'✅ مسجل' if data['logged_in'] else '❌ غير مسجل'}\n"
        f"📝 الرسالة: {'✅ معينة' if data['message'] else '❌ غير معينة'}\n"
        f"🌿 المجموعات: {len(data['groups'])} مجموعة\n"
        f"🍀 العدد: {data['count']}\n"
        f"⏱ التوقيت: كل {data['interval']//60} دقائق\n"
        f"🚀 النشر: {'✅ نشط' if data.get('posting', False) else '❌ غير نشط'}"
    )
    
    bot.answer_callback_query(call.id, status, show_alert=True)

# معالجة رقم الهاتف
def process_phone(message):
    user_id = message.from_user.id
    
    try:
        # التحقق من صحة رقم الهاتف
        phone = message.text.strip().replace(" ", "").replace("-", "")
        if not re.match(r"^\+\d{10,15}$", phone):
            bot.reply_to(message, "❌ رقم الهاتف غير صحيح. مثال صحيح: +967734763250")
            return
        
        # التحقق من وجود جلسة نشطة
        if user_id in user_data and user_data[user_id].get('logged_in'):
            bot.reply_to(message, "⚠️ لديك جلسة نشطة بالفعل!")
            return
        
        # إنشاء عميل Pyrogram
        client = Client(
            name=f"user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )
        
        # إرسال رمز التحقق
        client.connect()
        sent_code = client.send_code(phone)
        
        # حفظ الجلسة المؤقتة
        temp_sessions[user_id] = {
            'client': client,
            'phone': phone,
            'phone_code_hash': sent_code.phone_code_hash
        }
        
        # طلب رمز التحقق
        msg = bot.reply_to(
            message,
            "🔢 **تم إرسال رمز التحقق إليك.**\n"
            "الرجاء إرسال الرمز (5 أرقام):"
        )
        bot.register_next_step_handler(msg, process_code)
    
    except (PhoneNumberInvalid, PhoneNumberUnoccupied) as e:
        bot.reply_to(message, f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"خطأ في معالجة رقم الهاتف: {e}")
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

# معالجة رمز التحقق
def process_code(message):
    user_id = message.from_user.id
    code = message.text.strip()
    
    try:
        # التحقق من وجود الجلسة المؤقتة
        if user_id not in temp_sessions:
            bot.reply_to(message, "❌ انتهت الجلسة. الرجاء البدء من جديد.")
            return
        
        # استرداد بيانات الجلسة
        client = temp_sessions[user_id]['client']
        phone = temp_sessions[user_id]['phone']
        phone_code_hash = temp_sessions[user_id]['phone_code_hash']
        
        # تسجيل الدخول بالرمز
        client.sign_in(phone, phone_code_hash, code)
        
        # تخزين الجلسة
        session_string = client.export_session_string()
        user_data[user_id]['session_string'] = session_string
        user_data[user_id]['logged_in'] = True
        
        bot.reply_to(message, "✅ **تم تسجيل الدخول بنجاح!**")
        save_data()
    
    except SessionPasswordNeeded:
        # طلب كلمة المرور الثنائية
        msg = bot.reply_to(
            message,
            "🔐 **الحساب محمي بكلمة مرور ثنائية.**\n"
            "الرجاء إرسال كلمة المرور:"
        )
        bot.register_next_step_handler(msg, process_password)
    
    except (PhoneCodeInvalid, PhoneCodeExpired) as e:
        bot.reply_to(message, f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"خطأ في معالجة رمز التحقق: {e}")
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")
    finally:
        # تنظيف الجلسة المؤقتة
        if user_id in temp_sessions:
            client = temp_sessions[user_id]['client']
            client.disconnect()
            del temp_sessions[user_id]

# معالجة كلمة المرور الثنائية
def process_password(message):
    user_id = message.from_user.id
    password = message.text
    
    try:
        # التحقق من وجود الجلسة المؤقتة
        if user_id not in temp_sessions:
            bot.reply_to(message, "❌ انتهت الجلسة. الرجاء البدء من جديد.")
            return
        
        # استرداد بيانات الجلسة
        client = temp_sessions[user_id]['client']
        
        # تسجيل الدخول بكلمة المرور
        client.check_password(password=password)
        
        # تخزين الجلسة
        session_string = client.export_session_string()
        user_data[user_id]['session_string'] = session_string
        user_data[user_id]['logged_in'] = True
        
        bot.reply_to(message, "✅ **تم تسجيل الدخول بنجاح!**")
        save_data()
    
    except Exception as e:
        logger.error(f"خطأ في معالجة كلمة المرور: {e}")
        bot.reply_to(message, f"❌ كلمة المرور غير صحيحة: {str(e)}")
    finally:
        # تنظيف الجلسة المؤقتة
        if user_id in temp_sessions:
            client = temp_sessions[user_id]['client']
            client.disconnect()
            del temp_sessions[user_id]

# معالجة الرسالة
def process_message(message):
    user_id = message.from_user.id
    user_data[user_id]['message'] = message.text
    bot.reply_to(message, "✅ **تم حفظ الرسالة بنجاح!**")
    save_data()

# معالجة المجموعات
def process_groups(message):
    user_id = message.from_user.id
    groups = message.text.split()
    
    # تنظيف المعرفات
    cleaned_groups = []
    for group in groups:
        # إزالة أي رابط وتحويله إلى معرف
        if group.startswith("https://t.me/"):
            group = "@" + group.split("/")[-1]
        elif group.startswith("t.me/"):
            group = "@" + group.split("/")[-1]
        
        cleaned_groups.append(group.strip())
    
    user_data[user_id]['groups'] = cleaned_groups
    bot.reply_to(
        message, 
        f"✅ **تم حفظ {len(cleaned_groups)} مجموعة بنجاح!**"
    )
    save_data()

# معالجة العدد
def process_count(message):
    user_id = message.from_user.id
    
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
        
        user_data[user_id]['count'] = count
        bot.reply_to(message, f"✅ **تم تعيين عدد النشرات إلى {count}!**")
        save_data()
    
    except ValueError:
        bot.reply_to(message, "❌ الرجاء إدخال عدد صحيح موجب.")

# بدء النشر التلقائي (بدون async)
def start_auto_posting(user_id, chat_id):
    data = user_data[user_id]
    
    try:
        # إنشاء عميل Pyrogram
        client = Client(
            name=f"user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=data['session_string'],
            in_memory=True
        )
        
        # بدء العميل
        client.start()
        bot.send_message(chat_id, "🚀 بدأ النشر التلقائي...")
        
        # حلقة النشر
        for i in range(data['count']):
            if not data.get('posting', True):
                break
                
            for group in data['groups']:
                try:
                    client.send_message(group, data['message'])
                    logger.info(f"تم النشر في {group} ({i+1}/{data['count']})")
                    time.sleep(2)  # تأخير بين المجموعات
                except BadRequest as e:
                    logger.error(f"خطأ في النشر: {e}")
                    bot.send_message(chat_id, f"❌ خطأ في النشر في {group}: {str(e)}")
                except Exception as e:
                    logger.error(f"خطأ غير متوقع: {e}")
                    bot.send_message(chat_id, f"❌ خطأ غير متوقع في النشر: {str(e)}")
            
            # انتظار الفترة الزمنية المحددة
            if i < data['count'] - 1 and data.get('posting', True):
                time.sleep(data['interval'])
        
        bot.send_message(chat_id, "✅ تم الانتهاء من النشر!")
    
    except Exception as e:
        logger.error(f"خطأ في النشر التلقائي: {e}")
        bot.send_message(chat_id, f"❌ حدث خطأ في النشر: {str(e)}")
    finally:
        # إيقاف العميل وتحديث الحالة
        try:
            client.stop()
        except:
            pass
        user_data[user_id]['posting'] = False
        save_data()

# تشغيل البوت
if __name__ == '__main__':
    # تحميل البيانات المحفوظة
    load_data()
    
    # بدء البوت
    logger.info("جارٍ تشغيل البوت...")
    bot.polling(none_stop=True, timeout=60)
