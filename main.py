import os
import telebot
import subprocess
import time
import logging
import requests
import json
import uuid
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)

# إعدادات البوت
BOT_TOKEN = "8403108424:AAEGT-XtShnVn6_sZ_2HH_xTeGoLYyiqIB8"
GEMINI_API_KEY = "AIzaSyDTb_B7Pq3KSWWMTC1KjG4iPGqFFgLpRl8"
ADMIN_ID = 6689435577
CHANNEL_ID = -1003091756917
STORAGE_CHANNEL_ID = -1003088700358
SUBSCRIPTION_CHANNEL = "@iIl337"
BOT_USERNAME = "@TIET6BOT"
MAX_FILES = 6
MAX_AI_REQUESTS = 1  # عدد الطلبات المسموحة لكل مستخدم

# إعدادات الملفات
UPLOAD_DIR = 'uploaded_files'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# قاعدة بيانات بسيطة (في الإصدار الحقيقي استخدم قاعدة بيانات حقيقية)
users_data = {}
invite_codes = {}

# تحميل البيانات المحفوظة
def load_data():
    global users_data, invite_codes
    try:
        if os.path.exists('users_data.json'):
            with open('users_data.json', 'r') as f:
                users_data = json.load(f)
        if os.path.exists('invite_codes.json'):
            with open('invite_codes.json', 'r') as f:
                invite_codes = json.load(f)
    except:
        pass

# حفظ البيانات
def save_data():
    with open('users_data.json', 'w') as f:
        json.dump(users_data, f)
    with open('invite_codes.json', 'w') as f:
        json.dump(invite_codes, f)

# تهيئة بيانات المستخدم إذا لم يكن موجوداً
def init_user(user_id):
    if str(user_id) not in users_data:
        users_data[str(user_id)] = {
            'ai_requests': 0,
            'invites': 0,
            'invite_code': str(uuid.uuid4())[:8],
            'invited_users': []
        }
        save_data()

# إنشاء لوحة المفاتيح الرئيسية
def create_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🛠 إنتاج ملف", callback_data="generate_file"),
        InlineKeyboardButton("⚙️ خيارات أكثر", callback_data="more_options")
    )
    return keyboard

# إنشاء لوحة خيارات إضافية
def create_more_options_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📤 رفع ملف", callback_data="upload_file"),
        InlineKeyboardButton("🗑️ حذف ملف", callback_data="delete_file"),
        InlineKeyboardButton("📂 عرض الملفات", callback_data="list_files"),
        InlineKeyboardButton("▶️ تشغيل ملف", callback_data="run_file"),
        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
    )
    return keyboard

# إنشاء لوحة الدعوة
def create_invite_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("📨 توليد رابط دعوة", callback_data=f"generate_invite_{user_id}"),
        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
    )
    return keyboard

# استخدام Gemini AI لإنشاء كود البايثون
def generate_python_code(description):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    قم بإنشاء كود بايثون لبناء بوت تلجرام بناء على الوصف التالي:
    {description}
    
    المتطلبات:
    - يجب أن يكون الكود جاهز للتشغيل
    - استخدم مكتبة telebot أو telethon
    - أضف تعليقات توضيحية بالعربية
    - تأكد من أن الكود خالٍ من الأخطاء
    - أضف وظائف أساسية مثل /start ومعالجة الرسائل
    """
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logging.error(f"Error generating code: {str(e)}")
        return None

# معالجة أمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # التحقق من وجود رابط دعوة
    if len(message.text.split()) > 1:
        invite_code = message.text.split()[1]
        for inviter_id, user_data in users_data.items():
            if user_data['invite_code'] == invite_code and str(message.from_user.id) != inviter_id:
                if str(message.from_user.id) not in user_data['invited_users']:
                    user_data['invited_users'].append(str(message.from_user.id))
                    user_data['ai_requests'] += 1
                    users_data[inviter_id] = user_data
                    save_data()
                    break
    
    init_user(message.from_user.id)
    
    welcome_text = """
مرحباً! 🤖

أنا بوت مجاني لرفع وتشغيل ملفات البايثون وإنشاء بوتات تلجرام تلقائياً.

📝 **المميزات المتاحة:**
- إنشاء بوتات تلجرام باستخدام الذكاء الاصطناعي
- رفع وتشغيل ملفات البايثون
- عرض وإدارة الملفات
- نظام دعوة للحصول على مزيد من الطلبات

🛠 **لبدء الاستخدام:**
1. اختر "إنتاج ملف" لإنشاء بوت باستخدام الذكاء الاصطناعي
2. أو اختر "خيارات أكثر" للوصول إلى الميزات الأخرى
"""
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_keyboard())

# معالجة الردود على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    init_user(user_id)
    
    if call.data == "main_menu":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="القائمة الرئيسية:",
            reply_markup=create_main_keyboard()
        )
    
    elif call.data == "more_options":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="خيارات إضافية:",
            reply_markup=create_more_options_keyboard()
        )
    
    elif call.data == "generate_file":
        # التحقق من عدد الطلبات المتاحة
        if users_data[str(user_id)]['ai_requests'] <= 0:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ لا تملك طلبات كافية لاستخدام الذكاء الاصطناعي.\n\n📨 قم بدعوة أصدقائك للحصول على المزيد من الطلبات.",
                reply_markup=create_invite_keyboard(user_id)
            )
        else:
            msg = bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🛠 يرجى إرسال وصف للبوت الذي تريد إنشاءه:\n\nمثال: 'بوت لادارة مجموعة مع خاصية حظر المستخدمين وإرسال الترحيب'"
            )
            bot.register_next_step_handler(msg, process_bot_description)
    
    elif call.data.startswith("generate_invite_"):
        user_id = int(call.data.split("_")[2])
        init_user(user_id)
        invite_code = users_data[str(user_id)]['invite_code']
        invite_link = f"https://t.me/{BOT_USERNAME[1:]}?start={invite_code}"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📨 رابط الدعوة الخاص بك:\n`{invite_link}`\n\nشارك هذا الرابط مع أصدقائك. عند انضمامهم ستحصل على طلب إضافي للذكاء الاصطناعي.",
            parse_mode="Markdown",
            reply_markup=create_invite_keyboard(user_id)
        )
    
    elif call.data == "upload_file":
        msg = bot.send_message(call.message.chat.id, "📤 أرسل لي ملف بايثون (.py) لرفعه")
        bot.register_next_step_handler(msg, handle_document)
    
    elif call.data == "delete_file":
        files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.py')]
        if not files:
            bot.send_message(call.message.chat.id, "❌ لا توجد ملفات لحذفها.")
            return
        
        keyboard = InlineKeyboardMarkup()
        for i, file in enumerate(files):
            keyboard.add(InlineKeyboardButton(f"{i+1}. {file}", callback_data=f"delete_{file}"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="more_options"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📂 اختر الملف الذي تريد حذفه:",
            reply_markup=keyboard
        )
    
    elif call.data.startswith("delete_"):
        file_name = call.data[7:]
        file_path = os.path.join(UPLOAD_DIR, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ تم حذف الملف: {file_name}",
                reply_markup=create_more_options_keyboard()
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ الملف غير موجود.",
                reply_markup=create_more_options_keyboard()
            )
    
    elif call.data == "list_files":
        files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.py')]
        if not files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ لا توجد ملفات مرفوعة بعد.",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        files_list = "\n".join([f"📄 {f}" for f in files])
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📂 الملفات المرفوعة ({len(files)}/{MAX_FILES}):\n{files_list}",
            reply_markup=create_more_options_keyboard()
        )
    
    elif call.data == "run_file":
        files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.py')]
        if not files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ لا توجد ملفات بايثون لتشغيلها.",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        keyboard = InlineKeyboardMarkup()
        for i, file in enumerate(files):
            keyboard.add(InlineKeyboardButton(f"{i+1}. {file}", callback_data=f"run_{file}"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="more_options"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🐍 اختر الملف الذي تريد تشغيله:",
            reply_markup=keyboard
        )
    
    elif call.data.startswith("run_"):
        file_name = call.data[4:]
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        if not os.path.exists(file_path):
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ الملف غير موجود.",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        # إرسال رسالة بدء التشغيل
        status_msg = bot.send_message(call.message.chat.id, f"⏳ جاري تشغيل الملف: {file_name}...")
        
        try:
            # بدء قياس الوقت
            start_time = time.time()
            
            # تشغيل الملف
            process = subprocess.Popen(
                ['python', file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # انتظار انتهاء التنفيذ
            stdout, stderr = process.communicate()
            end_time = time.time()
            
            # إعداد النتيجة
            execution_time = end_time - start_time
            result = f"📄 الملف: {file_name}\n"
            result += f"⏱ وقت التنفيذ: {execution_time:.2f} ثانية\n\n"
            
            if stdout:
                result += f"📤 الناتج:\n{stdout}\n"
            
            if stderr:
                result += f"❌ الأخطاء:\n{stderr}"
            
            if not stdout and not stderr:
                result += "✅ تم التشغيل بنجاح بدون ناتج."
            
            # إرسال النتيجة (مقتطعة إذا كانت طويلة)
            if len(result) > 4000:
                result = result[:4000] + "...\n\n(تم تقصير النتيجة بسبب الطول)"
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=status_msg.message_id,
                text=result
            )
            
        except Exception as e:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=status_msg.message_id,
                text=f"❌ حدث خطأ أثناء التشغيل: {str(e)}"
            )

# معالجة وصف البوت
def process_bot_description(message):
    user_id = message.from_user.id
    description = message.text
    
    # خصم طلب من رصيد المستخدم
    users_data[str(user_id)]['ai_requests'] -= 1
    save_data()
    
    # إرسال رسالة الانتظار
    wait_msg = bot.send_message(message.chat.id, "⏳ جاري إنشاء البوت باستخدام الذكاء الاصطناعي...")
    
    # إنشاء الكود باستخدام Gemini AI
    code = generate_python_code(description)
    
    if code:
        # حفظ الكود في ملف
        file_name = f"bot_{user_id}_{int(time.time())}.py"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # إرسال الملف للمستخدم
        with open(file_path, 'rb') as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"✅ تم إنشاء البوت بنجاح!\n\n📁 اسم الملف: {file_name}\n\n📝 يمكنك الآن تشغيل الملف من خلال خيار 'تشغيل ملف' في القائمة."
            )
        
        # حذف رسالة الانتظار
        bot.delete_message(message.chat.id, wait_msg.message_id)
    else:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
            text="❌ حدث خطأ أثناء إنشاء البوت. يرجى المحاولة مرة أخرى لاحقاً."
        )

# معالجة رفع الملفات
@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    
    try:
        # التحقق من صيغة الملف
        if not message.document.file_name.endswith('.py'):
            bot.send_message(chat_id, "❌ يسمح فقط بملفات البايثون (.py)")
            return
        
        # التحقق من عدد الملفات
        files_count = len([f for f in os.listdir(UPLOAD_DIR) if f.endswith('.py')])
        if files_count >= MAX_FILES:
            bot.send_message(chat_id, f"❌ وصلت للحد الأقصى للملفات ({MAX_FILES}). يرجى حذف بعض الملفات أولاً.")
            return
        
        # تحميل الملف
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = message.document.file_name
        
        # حفظ الملف
        file_path = os.path.join(UPLOAD_DIR, file_name)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # حساب حجم الملف
        file_size = len(downloaded_file) / (1024 * 1024)  # MB
        
        bot.send_message(chat_id, f"✅ تم رفع الملف بنجاح: {file_name} ({file_size:.2f} MB)")
        logging.info(f"File uploaded: {file_name} ({file_size:.2f} MB) by user {message.from_user.id}")
    
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء رفع الملف: {str(e)}")

# تشغيل البوت
if __name__ == '__main__':
    # تحميل البيانات المحفوظة
    load_data()
    
    print("🤖 بوت رفع الملفات المجاني يعمل الآن...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ حدث خطأ: {e}") 
