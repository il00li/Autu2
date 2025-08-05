import telebot
from telebot import types
import logging
import time
from pyrogram import Client
import asyncio

# تكوين السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# بيانات البوت
TOKEN = "8247037355:AAH2rRm9PJCXqcVISS8g-EL1lv3tvQTXFys"
API_ID = 23656977
API_HASH = "49d3f43531a92b3f5bc403766313ca1e"

bot = telebot.TeleBot(TOKEN)

# حالات المستخدم
class UserState:
    LOGIN_PHONE = 1
    LOGIN_CODE = 2
    SET_MESSAGE = 3
    SET_GROUPS = 4
    SET_COUNT = 5
    SET_INTERVAL = 6

# تخزين بيانات المستخدمين
user_data = {}

# خيارات التوقيت
TIMING_OPTIONS = {
    "2 دقائق": 120,
    "5 دقائق": 300,
    "10 دقائق": 600,
    "15 دقائق": 900
}

# إنشاء لوحة المفاتيح الرئيسية
def main_menu_keyboard(user_id=None):
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
    
    try:
        if call.data == 'login':
            msg = bot.send_message(
                chat_id,
                "📱 **الرجاء إرسال رقم هاتفك مع رمز الدولة**\n"
                "مثال: +201234567890\n\n"
                "🛑 سيتم استخدامه فقط للنشر",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_phone_step)
            
        elif call.data == 'set_message':
            msg = bot.send_message(
                chat_id,
                "📝 **أرسل الرسالة التي تريد نشرها**\n"
                "يمكنك استخدام تنسيق Markdown",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_message_step)
            
        elif call.data == 'set_interval':
            bot.edit_message_text(
                "⏱ **اختر الفترة بين النشرات:**",
                chat_id,
                call.message.message_id,
                reply_markup=timing_keyboard()
            )
            
        elif call.data.startswith('interval_'):
            interval = int(call.data.split('_')[1])
            user_data[user_id]['interval'] = interval
            bot.send_message(
                chat_id,
                f"✅ تم ضبط التوقيت على كل {interval//60} دقائق",
                reply_markup=main_menu_keyboard(user_id)
            )
            
        elif call.data == 'start_posting':
            if validate_user_settings(user_id):
                start_auto_posting(user_id, chat_id)
            else:
                bot.answer_callback_query(
                    call.id,
                    "❌ يرجى إكمال جميع إعدادات البوت أولاً",
                    show_alert=True
                )
                
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
    required = ['logged_in', 'message', 'groups', 'count', 'interval']
    return all(key in user_data.get(user_id, {}) for key in required)

# عرض حالة البوت
def show_bot_status(user_id, call):
    status = "ℹ️ **حالة البوت:**\n\n"
    
    if user_id in user_data:
        data = user_data[user_id]
        status += f"🔹 الحساب: {'✅ مسجل' if data.get('logged_in') else '❌ غير مسجل'}\n"
        status += f"📝 الرسالة: {'✅ معينة' if 'message' in data else '❌ غير معينة'}\n"
        status += f"🌿 المجموعات: {len(data.get('groups', []))}\n"
        status += f"🍀 العدد: {data.get('count', '❌ غير معين')}\n"
        status += f"⏱ التوقيت: كل {data.get('interval', 0)//60} دقائق\n"
    else:
        status += "❌ لم يتم إعداد البوت بعد"
    
    bot.answer_callback_query(call.id, status, show_alert=True)

# بدء النشر التلقائي
def start_auto_posting(user_id, chat_id):
    data = user_data[user_id]
    bot.send_message(chat_id, "🚀 بدأ النشر التلقائي...")
    
    for i in range(data['count']):
        for group in data['groups']:
            try:
                # هنا يتم إرسال الرسالة باستخدام Pyrogram
                asyncio.run(send_via_pyrogram(user_id, group, data['message']))
                logger.info(f"تم النشر في {group} (المحاولة {i+1})")
            except Exception as e:
                logger.error(f"خطأ في النشر: {e}")
        
        if i < data['count'] - 1:
            time.sleep(data['interval'])
    
    bot.send_message(chat_id, "✅ تم الانتهاء من النشر!")

# إرسال الرسالة عبر Pyrogram
async def send_via_pyrogram(user_id, chat_id, text):
    client = Client(
        f"user_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=user_data[user_id]['session_string']
    )
    
    async with client:
        await client.send_message(chat_id, text)

# تشغيل البوت
if __name__ == '__main__':
    logger.info("Starting bot...")
    bot.infinity_polling()
