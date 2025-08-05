import telebot
from telebot import types
import logging
import asyncio
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired, PhoneNumberInvalid

# تكوين السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# توكن البوت
TOKEN = "8247037355:AAH2rRm9PJCXqcVISS8g-EL1lv3tvQTXFys"
API_ID = 23656977
API_HASH = "49d3f43531a92b3f5bc403766313ca1e"

bot = telebot.TeleBot(TOKEN)

# حالات المستخدم
class UserState:
    LOGIN_PHONE = 1
    LOGIN_CODE = 2
    LOGIN_PASSWORD = 3
    SET_MESSAGE = 4
    SET_GROUPS = 5
    SET_COUNT = 6
    SET_INTERVAL = 7

# تخزين بيانات المستخدمين
user_data = {}
# تخزين جلسات تسجيل الدخول المؤقتة
temp_sessions = {}

# خيارات التوقيت (بالثواني)
TIMING_OPTIONS = {
    "2 دقائق": 120,
    "5 دقائق": 300,
    "10 دقائق": 600,
    "15 دقائق": 900
}

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
    for text, seconds in TIMING_OPTIONS.items():
        markup.add(types.InlineKeyboardButton(f"⏱ {text}", callback_data=f'interval_{seconds}'))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main'))
    return markup

# بدء البوت
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    
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
        if call.data == 'login':
            msg = bot.send_message(
                chat_id,
                "📱 **الرجاء إرسال رقم هاتفك مع رمز الدولة**\n"
                "مثال: +201234567890\n\n"
                "🛑 سيتم استخدامه فقط للنشر",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_phone_step, user_id)
            
        elif call.data == 'set_message':
            msg = bot.send_message(
                chat_id,
                "📝 **أرسل الرسالة التي تريد نشرها**\n"
                "يمكنك استخدام تنسيق Markdown",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_message_step, user_id)
            
        elif call.data == 'set_groups':
            msg = bot.send_message(
                chat_id,
                "🌿 **أرسل معرفات المجموعات (مفصولة بمسافات)**\n"
                "مثال: `@group1 @group2` أو `-10012345678 -10087654321`",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_groups_step, user_id)
            
        elif call.data == 'set_count':
            msg = bot.send_message(
                chat_id,
                "🍀 **أرسل عدد مرات النشر المطلوبة**\n"
                "يجب أن يكون رقماً صحيحاً موجباً",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_count_step, user_id)
            
        elif call.data == 'set_interval':
            bot.edit_message_text(
                "⏱ **اختر الفترة بين النشرات:**",
                chat_id,
                message_id,
                reply_markup=timing_keyboard()
            )
            
        elif call.data.startswith('interval_'):
            interval = int(call.data.split('_')[1])
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]['interval'] = interval
            bot.edit_message_text(
                f"✅ تم ضبط التوقيت على كل {interval//60} دقائق",
                chat_id,
                message_id,
                reply_markup=main_menu_keyboard(user_id)
            )
            
        elif call.data == 'start_posting':
            if validate_user_settings(user_id):
                bot.answer_callback_query(call.id, "🚀 بدأ النشر التلقائي...")
                asyncio.run(start_auto_posting(user_id, chat_id))
            else:
                bot.answer_callback_query(
                    call.id,
                    "❌ يرجى إكمال جميع إعدادات البوت أولاً",
                    show_alert=True
                )
                
        elif call.data == 'stop_posting':
            # إيقاف النشر (سيتم التعامل معه في الدورة التالية)
            if user_id in user_data:
                user_data[user_id]['posting'] = False
            bot.answer_callback_query(call.id, "🛑 تم إيقاف النشر التلقائي")
            
        elif call.data == 'bot_status':
            show_bot_status(user_id, call)
            
        elif call.data == 'back_to_main':
            bot.edit_message_text(
                "🌿 **القائمة الرئيسية**",
                chat_id,
                message_id,
                reply_markup=main_menu_keyboard(user_id)
            )
            
    except Exception as e:
        logger.error(f"Error in handle_buttons: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ ما!")

# معالجة رقم الهاتف
def process_phone_step(message, user_id):
    phone_number = message.text
    try:
        # إنشاء عميل Pyrogram
        client = Client(
            name=f"user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )
        
        # إرسال رمز التحقق
        client.connect()
        sent_code = client.send_code(phone_number)
        
        # حفظ الجلسة المؤقتة
        temp_sessions[user_id] = {
            'client': client,
            'phone': phone_number,
            'phone_code_hash': sent_code.phone_code_hash
        }
        
        # طلب رمز التحقق
        msg = bot.send_message(
            message.chat.id,
            "🔢 **تم إرسال رمز التحقق إليك.**\n"
            "الرجاء إرسال الرمز (5 أرقام):"
        )
        bot.register_next_step_handler(msg, process_code_step, user_id)
        
    except PhoneNumberInvalid:
        bot.send_message(message.chat.id, "❌ رقم الهاتف غير صحيح. الرجاء المحاولة مرة أخرى.")
    except Exception as e:
        logger.error(f"Error in process_phone_step: {e}")
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")

# معالجة رمز التحقق
def process_code_step(message, user_id):
    code = message.text.strip()
    if user_id not in temp_sessions:
        bot.send_message(message.chat.id, "❌ انتهت الجلسة. الرجاء البدء من جديد.")
        return
    
    client = temp_sessions[user_id]['client']
    phone = temp_sessions[user_id]['phone']
    phone_code_hash = temp_sessions[user_id]['phone_code_hash']
    
    try:
        client.sign_in(phone, phone_code_hash, code)
        
        # تسجيل الدخول ناجح
        session_string = client.export_session_string()
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id].update({
            'session_string': session_string,
            'logged_in': True,
            'client': client  # يمكن تخزين العميل إذا أردنا استخدامه لاحقًا
        })
        
        bot.send_message(message.chat.id, "✅ **تم تسجيل الدخول بنجاح!**")
        
    except SessionPasswordNeeded:
        msg = bot.send_message(
            message.chat.id,
            "🔐 **الحساب محمي بكلمة مرور ثنائية.**\n"
            "الرجاء إرسال كلمة المرور:"
        )
        bot.register_next_step_handler(msg, process_password_step, user_id)
    except (PhoneCodeInvalid, PhoneCodeExpired):
        bot.send_message(message.chat.id, "❌ رمز التحقق غير صحيح أو منتهي الصلاحية.")
    except Exception as e:
        logger.error(f"Error in process_code_step: {e}")
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")
    finally:
        # تنظيف الجلسة المؤقتة
        if user_id in temp_sessions:
            del temp_sessions[user_id]

# معالجة كلمة المرور
def process_password_step(message, user_id):
    password = message.text
    if user_id not in temp_sessions:
        bot.send_message(message.chat.id, "❌ انتهت الجلسة. الرجاء البدء من جديد.")
        return
    
    client = temp_sessions[user_id]['client']
    
    try:
        client.check_password(password=password)
        session_string = client.export_session_string()
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id].update({
            'session_string': session_string,
            'logged_in': True,
            'client': client
        })
        
        bot.send_message(message.chat.id, "✅ **تم تسجيل الدخول بنجاح!**")
        
    except Exception as e:
        logger.error(f"Error in process_password_step: {e}")
        bot.send_message(message.chat.id, f"❌ كلمة المرور غير صحيحة: {str(e)}")
    finally:
        if user_id in temp_sessions:
            del temp_sessions[user_id]

# تأكيد إعدادات المستخدم
def validate_user_settings(user_id):
    if user_id not in user_data:
        return False
    required = ['logged_in', 'message', 'groups', 'count', 'interval']
    return all(key in user_data.get(user_id, {}) for key in required)

# عرض حالة البوت
def show_bot_status(user_id, call):
    status = "ℹ️ **حالة البوت:**\n\n"
    
    if user_id in user_data:
        data = user_data[user_id]
        status += f"🔹 الحساب: {'✅ مسجل' if data.get('logged_in') else '❌ غير مسجل'}\n"
        status += f"📝 الرسالة: {'✅ معينة' if 'message' in data else '❌ غير معينة'}\n"
        status += f"🌿 المجموعات: {len(data.get('groups', []))} مجموعة\n"
        status += f"🍀 العدد: {data.get('count', '❌ غير معين')}\n"
        status += f"⏱ التوقيت: كل {data.get('interval', 0)//60} دقائق\n"
    else:
        status += "❌ لم يتم إعداد البوت بعد"
    
    bot.answer_callback_query(call.id, status, show_alert=True)

# بدء النشر التلقائي
async def start_auto_posting(user_id, chat_id):
    data = user_data[user_id]
    data['posting'] = True
    
    # إنشاء عميل Pyrogram من سلسلة الجلسة
    client = Client(
        name=f"user_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=data['session_string'],
        in_memory=True
    )
    
    try:
        await client.start()
        bot.send_message(chat_id, "🚀 بدأ النشر التلقائي...")
        
        for i in range(data['count']):
            if not data.get('posting', True):
                break
                
            for group in data['groups']:
                try:
                    await client.send_message(group, data['message'])
                    logger.info(f"تم النشر في {group} (المحاولة {i+1})")
                except Exception as e:
                    logger.error(f"خطأ في النشر: {e}")
                    bot.send_message(chat_id, f"❌ خطأ في النشر في {group}: {str(e)}")
            
            # انتظار الفترة الزمنية المحددة
            if i < data['count'] - 1:
                await asyncio.sleep(data['interval'])
        
        bot.send_message(chat_id, "✅ تم الانتهاء من النشر!")
        
    except Exception as e:
        logger.error(f"خطأ في النشر التلقائي: {e}")
        bot.send_message(chat_id, f"❌ حدث خطأ في النشر: {str(e)}")
    finally:
        await client.stop()
        data['posting'] = False

# تشغيل البوت
if __name__ == '__main__':
    logger.info("Starting bot...")
    bot.infinity_polling()
