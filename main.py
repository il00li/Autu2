import os
import telebot
import subprocess
import time
import logging
import requests
import json
import uuid
import re
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InputFile
)

# إعدادات البوت
BOT_TOKEN = "8403108424:AAEGT-XtShnVn6_sZ_2HH_xTeGoLYyiqIB8"
GEMINI_API_KEY = "AIzaSyDTb_B7Pq3KSWWMTC1KjG4iPGqFFgLpRl8"
ADMIN_ID = 6689435577
CHANNEL_ID = -1003091756917
STORAGE_CHANNEL_ID = -1003088700358
SUBSCRIPTION_CHANNEL = "@iIl337"
BOT_USERNAME = "@TIET6BOT"
MAX_FILES_PER_USER = 3  # الحد الأقصى للملفات النشطة لكل مستخدم
MAX_AI_REQUESTS = 1

# إعدادات الملفات
UPLOAD_DIR = 'uploaded_files'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# قاعدة بيانات بسيطة
users_data = {}
invite_codes = {}
premium_invites = {}  # تخزين روابط النقاط المميزة

# تحميل البيانات المحفوظة
def load_data():
    global users_data, invite_codes, premium_invites
    try:
        if os.path.exists('users_data.json'):
            with open('users_data.json', 'r', encoding='utf-8') as f:
                users_data = json.load(f)
        if os.path.exists('invite_codes.json'):
            with open('invite_codes.json', 'r', encoding='utf-8') as f:
                invite_codes = json.load(f)
        if os.path.exists('premium_invites.json'):
            with open('premium_invites.json', 'r', encoding='utf-8') as f:
                premium_invites = json.load(f)
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        users_data = {}
        invite_codes = {}
        premium_invites = {}

# حفظ البيانات
def save_data():
    try:
        with open('users_data.json', 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
        with open('invite_codes.json', 'w', encoding='utf-8') as f:
            json.dump(invite_codes, f, ensure_ascii=False, indent=4)
        with open('premium_invites.json', 'w', encoding='utf-8') as f:
            json.dump(premium_invites, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving data: {e}")

# تهيئة بيانات المستخدم إذا لم يكن موجوداً
def init_user(user_id):
    if str(user_id) not in users_data:
        users_data[str(user_id)] = {
            'ai_requests': MAX_AI_REQUESTS,
            'invites': 0,
            'invite_code': str(uuid.uuid4())[:8].upper(),
            'invited_users': [],
            'files': [],
            'joined_date': datetime.now().isoformat(),
            'is_subscribed': False
        }
        save_data()

# التحقق من عدد الملفات للمستخدم
def check_user_files_limit(user_id):
    user_files = users_data.get(str(user_id), {}).get('files', [])
    return len(user_files) >= MAX_FILES_PER_USER

# التحقق من اشتراك المستخدم في القناة
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(SUBSCRIPTION_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return False

# التحقق من هوية المدير
def is_admin(user_id):
    return user_id == ADMIN_ID

# إنشاء لوحة المفاتيح الرئيسية
def create_main_keyboard(user_id=None):
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if user_id and not check_subscription(user_id):
        keyboard.add(InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{SUBSCRIPTION_CHANNEL[1:]}"))
        keyboard.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription"))
        return keyboard
    
    buttons = [
        InlineKeyboardButton("🛠 إنتاج ملف", callback_data="generate_file"),
        InlineKeyboardButton("⚙️ خيارات أكثر", callback_data="more_options"),
        InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
        InlineKeyboardButton("📨 رابط الدعوة", callback_data="invite_link")
    ]
    
    keyboard.add(buttons[0], buttons[1])
    keyboard.add(buttons[2], buttons[3])
    
    return keyboard

# إنشاء لوحة خيارات إضافية
def create_more_options_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("📤 رفع ملف", callback_data="upload_file"),
        InlineKeyboardButton("🗑️ حذف ملف", callback_data="delete_file"),
        InlineKeyboardButton("📂 عرض الملفات", callback_data="list_files"),
        InlineKeyboardButton("▶️ تشغيل ملف", callback_data="run_file"),
        InlineKeyboardButton("🔄 استبدال ملف", callback_data="replace_file"),
        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
    ]
    
    keyboard.add(buttons[0], buttons[1])
    keyboard.add(buttons[2], buttons[3])
    keyboard.add(buttons[4])
    keyboard.add(buttons[5])
    
    return keyboard

# إنشاء لوحة الدعوة
def create_invite_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("📨 توليد رابط دعوة", callback_data=f"generate_invite_{user_id}"),
        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
    )
    return keyboard

# إنشاء لوحة إدارة المدير
def create_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("🎁 إنشاء رابط نقاط", callback_data="admin_create_premium"),
        InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats"),
        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
    ]
    
    keyboard.add(buttons[0])
    keyboard.add(buttons[1])
    keyboard.add(buttons[2])
    
    return keyboard

# استخدام Gemini AI لإنشاء كود البايثون بدون تعليقات
def generate_python_code(description):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    
    prompt = f"""
    أنت مساعد خبير في برمجة بوتات التلجرام. قم بإنشاء كود بايثون كامل وجاهز للتشغيل بناء على الوصف التالي:
    
    {description}
    
    المتطلبات الأساسية:
    1. استخدم مكتبة pyTelegramBotAPI (telebot) بشكل أساسي
    2. تأكد من أن الكود خالٍ تمامًا من الأخطاء وجاهز للتشغيل
    3. لا تضف أي تعليقات أو شروحات داخل الكود
    4. لا تستخدم علامات الـ markdown مثل ```python
    5. أضف وظائف أساسية مثل أمر /start ومعالجة الرسائل النصية
    6. تأكد من تضمين التعامل مع الأخطاء بشكل صحيح
    7. الكود يجب أن يكون متكاملاً ولا ينقصه أي شيء
    
    قدم لي الكود النهائي فقط بدون أي إضافات.
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
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 2048,
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        logging.info(f"Gemini API response: {json.dumps(result, ensure_ascii=False)}")
        
        if 'candidates' in result and len(result['candidates']) > 0:
            code = result['candidates'][0]['content']['parts'][0]['text']
            
            # تنظيف الكود من أي علامات أو تعليقات
            code = re.sub(r'```(?:python)?\s*', '', code)  # إزالة علامات ```
            code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)  # إزالة التعليقات
            code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)  # إزالة التعليقات متعددة الأسطر
            code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)  # إزالة التعليقات متعددة الأسطر
            
            # إزالة أي نص غير بايثون
            lines = code.split('\n')
            python_lines = []
            in_code = False
            
            for line in lines:
                # تخطي الأسطر التي تحتوي على نصوص غير بايثون
                if re.match(r'^(import|from|def|class|@|if|else|for|while|try|except|async|await)', line.strip()):
                    in_code = True
                
                if in_code or line.strip().startswith(('import ', 'from ', 'def ', 'class ', '@', 'if ', 'else:', 'for ', 'while ', 'try:', 'except ', 'async ', 'await ')):
                    python_lines.append(line)
            
            code = '\n'.join(python_lines).strip()
            
            # التأكد من أن الكود يحتوي على import telebot
            if 'import telebot' not in code and 'import telebot as' not in code:
                code = "import telebot\n\n" + code
                
            return code
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            logging.error(f"Gemini API error: {error_msg}")
            return None
    except Exception as e:
        logging.error(f"Error generating code: {str(e)}")
        return None

# حفظ الملف في القناة
def save_file_to_channel(file_content, file_name, user_id):
    try:
        # التحقق من حد الملفات
        if check_user_files_limit(user_id):
            return False, "❌ لقد وصلت إلى الحد الأقصى للملفات (3 ملفات). يرجى حذف بعض الملفات أولاً."
        
        # حفظ الملف مؤقتاً
        temp_path = os.path.join(UPLOAD_DIR, file_name)
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        # إرسال الملف إلى القناة
        with open(temp_path, 'rb') as f:
            message = bot.send_document(CHANNEL_ID, f, caption=f"User: {user_id}\nFile: {file_name}")
        
        # حفظ معلومات الملف في بيانات المستخدم
        if str(user_id) in users_data:
            file_info = {
                'name': file_name,
                'message_id': message.message_id,
                'date': datetime.now().isoformat()
            }
            users_data[str(user_id)]['files'].append(file_info)
            save_data()
        
        # حذف الملف المؤقت
        os.remove(temp_path)
        
        return True, "✅ تم حفظ الملف بنجاح"
    except Exception as e:
        logging.error(f"Error saving file to channel: {e}")
        return False, f"❌ حدث خطأ في حفظ الملف: {str(e)}"

# معالجة أمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    init_user(user_id)
    
    # التحقق من وجود رابط دعوة
    if len(message.text.split()) > 1:
        invite_code = message.text.split()[1]
        
        # التحقق من روابط النقاط المميزة أولاً
        if invite_code in premium_invites and not premium_invites[invite_code]['used']:
            # منح النقاط للمستخدم من الرابط المميز
            points = premium_invites[invite_code]['points']
            users_data[str(user_id)]['ai_requests'] = users_data[str(user_id)].get('ai_requests', 0) + points
            premium_invites[invite_code]['used'] = True
            premium_invites[invite_code]['used_by'] = user_id
            premium_invites[invite_code]['used_date'] = datetime.now().isoformat()
            save_data()
            
            bot.send_message(user_id, f"🎉 لقد حصلت على {points} نقطة بفضل الرابط المميز!")
        
        # التحقق من روابط الدعوة العادية
        else:
            for inviter_id, user_data in users_data.items():
                if user_data.get('invite_code') == invite_code and str(user_id) != inviter_id:
                    if str(user_id) not in user_data.get('invited_users', []):
                        user_data['invited_users'].append(str(user_id))
                        user_data['ai_requests'] = user_data.get('ai_requests', 0) + 1
                        user_data['invites'] = user_data.get('invites', 0) + 1
                        users_data[inviter_id] = user_data
                        
                        # منح المستخدم الجديد طلب إضافي أيضاً
                        if str(user_id) in users_data:
                            users_data[str(user_id)]['ai_requests'] = users_data[str(user_id)].get('ai_requests', 0) + 1
                        
                        save_data()
                        bot.send_message(user_id, "🎉 لقد حصلت على طلب إضافي بفضل انضمامك عبر رابط الدعوة!")
                        break
    
    # التحقق من الاشتراك في القناة
    if not check_subscription(user_id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{SUBSCRIPTION_CHANNEL[1:]}"),
            InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")
        )
        
        welcome_text = """
مرحباً! 🤖

أنا بوت مجاني لرفع وتشغيل ملفات البايثون وإنشاء بوتات تلجرام تلقائياً.

⭕️ للاستفادة من جميع ميزات البوت، يجب عليك الاشتراك في قناتنا أولاً:
"""
        bot.send_message(user_id, welcome_text, reply_markup=keyboard)
        return
    
    welcome_text = f"""
مرحباً! 🤖

أنا بوت مجاني لرفع وتشغيل ملفات البايثون وإنشاء بوتات تلجرام تلقائياً.

📝 **المميزات المتاحة:**
- إنشاء بوتات تلجرام باستخدام الذكاء الاصطناعي
- رفع وتشغيل ملفات البايثون (بحد أقصى {MAX_FILES_PER_USER} ملفات نشطة)
- عرض وإدارة الملفات
- نظام دعوة للحصول على مزيد من الطلبات

🛠 **لبدء الاستخدام:**
1. اختر "إنتاج ملف" لإنشاء بوت باستخدام الذكاء الاصطناعي
2. أو اختر "خيارات أكثر" للوصول إلى الميزات الأخرى

📊 **ملاحظة:** يمكنك الاحتفاظ بحد أقصى {MAX_FILES_PER_USER} ملفات نشطة في نفس الوقت.
"""
    bot.send_message(user_id, welcome_text, reply_markup=create_main_keyboard(user_id))

# معالجة أمر /admin
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ ليس لديك صلاحية الوصول إلى هذه الأداة.")
        return
    
    admin_text = """
👑 لوحة إدارة البوت

• عدد المستخدمين: {}
• إجمالي الطلبات: {}
• الروابط المميزة: {}

اختر أحد الخيارات أدناه:
""".format(
        len(users_data),
        sum(user.get('ai_requests', 0) for user in users_data.values()),
        len(premium_invites)
    )
    
    bot.send_message(user_id, admin_text, reply_markup=create_admin_keyboard())

# معالجة الردود على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    init_user(user_id)
    
    # معالجة أوامر المدير
    if call.data == "admin_create_premium" and is_admin(user_id):
        msg = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎁 أدخل عدد النقاط التي تريد منحها في الرابط المميز:"
        )
        bot.register_next_step_handler(msg, process_premium_points)
        return
    
    elif call.data == "admin_stats" and is_admin(user_id):
        total_users = len(users_data)
        total_requests = sum(user.get('ai_requests', 0) for user in users_data.values())
        active_premium = sum(1 for invite in premium_invites.values() if not invite.get('used', False))
        
        stats_text = f"""
📊 إحصائيات البوت:

• إجمالي المستخدمين: {total_users}
• إجمالي الطلبات: {total_requests}
• الروابط المميزة النشطة: {active_premium}
• الروابط المميزة المستخدمة: {len(premium_invites) - active_premium}
"""
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=stats_text,
            reply_markup=create_admin_keyboard()
        )
        return
    
    # التحقق من الاشتراك أولاً
    if not check_subscription(user_id) and call.data not in ["check_subscription", "main_menu"]:
        bot.answer_callback_query(call.id, "⭕️ يجب الاشتراك في القناة أولاً")
        return
    
    if call.data == "main_menu":
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="القائمة الرئيسية:",
                reply_markup=create_main_keyboard(user_id)
            )
        except:
            bot.send_message(call.message.chat.id, "القائمة الرئيسية:", reply_markup=create_main_keyboard(user_id))
    
    elif call.data == "check_subscription":
        if check_subscription(user_id):
            users_data[str(user_id)]['is_subscribed'] = True
            save_data()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="مرحباً! 🤖\n\nشكراً للاشتراك في قناتنا. الآن يمكنك استخدام جميع ميزات البوت.",
                reply_markup=create_main_keyboard(user_id)
            )
        else:
            bot.answer_callback_query(call.id, "⭕️ لم تشترك بعد في القناة")
    
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
            # التحقق من حد الملفات
            if check_user_files_limit(user_id):
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"❌ لقد وصلت إلى الحد الأقصى للملفات ({MAX_FILES_PER_USER} ملفات). يرجى حذف بعض الملفات أولاً.",
                    reply_markup=create_more_options_keyboard()
                )
                return
                
            msg = bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🛠 يرجى إرسال وصف للبوت الذي تريد إنشاءه:\n\nمثال: 'بوت لادارة مجموعة مع خاصية حظر المستخدمين وإرسال الترحيب'"
            )
            bot.register_next_step_handler(msg, process_bot_description)
    
    elif call.data == "my_stats":
        user_stats = users_data[str(user_id)]
        stats_text = f"""
📊 إحصائياتك:

• الطلبات المتاحة: {user_stats['ai_requests']}
• عدد الدعوات: {user_stats['invites']}
• الملفات المحفوظة: {len(user_stats.get('files', []))}/{MAX_FILES_PER_USER}
• تاريخ الانضمام: {user_stats['joined_date'][:10]}
"""
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=stats_text,
            reply_markup=create_main_keyboard(user_id)
        )
    
    elif call.data == "invite_link":
        invite_code = users_data[str(user_id)]['invite_code']
        invite_link = f"https://t.me/{BOT_USERNAME[1:]}?start={invite_code}"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📨 رابط الدعوة الخاص بك:\n`{invite_link}`\n\nشارك هذا الرابط مع أصدقائك. عند انضمامهم ستحصل على طلب إضافي للذكاء الاصطناعي.",
            parse_mode="Markdown",
            reply_markup=create_invite_keyboard(user_id)
        )
    
    elif call.data.startswith("generate_invite_"):
        target_user_id = int(call.data.split("_")[2])
        if target_user_id != user_id:
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية للوصول إلى هذا الرابط")
            return
            
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
        # التحقق من حد الملفات
        if check_user_files_limit(user_id):
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ لقد وصلت إلى الحد الأقصى للملفات ({MAX_FILES_PER_USER} ملفات). يرجى حذف بعض الملفات أولاً.",
                reply_markup=create_more_options_keyboard()
            )
            return
            
        msg = bot.send_message(call.message.chat.id, "📤 أرسل لي ملف بايثون (.py) لرفعه")
        bot.register_next_step_handler(msg, handle_document)
    
    elif call.data == "delete_file":
        user_files = users_data[str(user_id)].get('files', [])
        if not user_files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ لا توجد ملفات لحذفها.",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        keyboard = InlineKeyboardMarkup()
        for i, file_info in enumerate(user_files):
            keyboard.add(InlineKeyboardButton(f"{i+1}. {file_info['name']}", callback_data=f"delete_{file_info['name']}"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="more_options"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📂 اختر الملف الذي تريد حذفه:",
            reply_markup=keyboard
        )
    
    elif call.data.startswith("delete_"):
        file_name = call.data[7:]
        user_files = users_data[str(user_id)].get('files', [])
        
        # البحث عن الملف وحذفه
        new_files = [f for f in user_files if f['name'] != file_name]
        users_data[str(user_id)]['files'] = new_files
        save_data()
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ تم حذف الملف: {file_name}",
            reply_markup=create_more_options_keyboard()
        )
    
    elif call.data == "list_files":
        user_files = users_data[str(user_id)].get('files', [])
        if not user_files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ لا توجد ملفات مرفوعة بعد.",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        files_list = "\n".join([f"📄 {f['name']} ({f['date'][:10]})" for f in user_files])
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📂 الملفات المرفوعة ({len(user_files)}/{MAX_FILES_PER_USER}):\n{files_list}",
            reply_markup=create_more_options_keyboard()
        )
    
    elif call.data == "run_file":
        user_files = users_data[str(user_id)].get('files', [])
        if not user_files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ لا توجد ملفات بايثون لتشغيلها.",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        keyboard = InlineKeyboardMarkup()
        for i, file_info in enumerate(user_files):
            keyboard.add(InlineKeyboardButton(f"{i+1}. {file_info['name']}", callback_data=f"run_{file_info['name']}"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="more_options"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🐍 اختر الملف الذي تريد تشغيله:",
            reply_markup=keyboard
        )
    
    elif call.data.startswith("run_"):
        file_name = call.data[4:]
        user_files = users_data[str(user_id)].get('files', [])
        
        # البحث عن الملف في القناة
        file_info = next((f for f in user_files if f['name'] == file_name), None)
        
        if not file_info:
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
            # تحميل الملف من القناة
            file_message = bot.forward_message(user_id, CHANNEL_ID, file_info['message_id'])
            file_info_obj = bot.get_file(file_message.document.file_id)
            downloaded_file = bot.download_file(file_info_obj.file_path)
            
            # حفظ الملف مؤقتاً
            temp_path = os.path.join(UPLOAD_DIR, file_name)
            with open(temp_path, 'wb') as f:
                f.write(downloaded_file)
            
            # بدء قياس الوقت
            start_time = time.time()
            
            # تشغيل الملف
            process = subprocess.Popen(
                ['python', temp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # انتظار انتهاء التنفيذ
            stdout, stderr = process.communicate()
            end_time = time.time()
            
            # تنظيف الملف المؤقت
            os.remove(temp_path)
            
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
    
    elif call.data == "replace_file":
        user_files = users_data[str(user_id)].get('files', [])
        if not user_files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ لا توجد ملفات لاستبدالها.",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        keyboard = InlineKeyboardMarkup()
        for i, file_info in enumerate(user_files):
            keyboard.add(InlineKeyboardButton(f"{i+1}. {file_info['name']}", callback_data=f"replace_{file_info['name']}"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="more_options"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📂 اختر الملف الذي تريد استبداله:",
            reply_markup=keyboard
        )
    
    elif call.data.startswith("replace_"):
        file_name = call.data[8:]
        msg = bot.send_message(call.message.chat.id, f"📤 أرسل لي الملف الجديد لاستبدال {file_name}")
        bot.register_next_step_handler(msg, handle_replace_file, file_name)

# معالجة عدد النقاط للرابط المميز
def process_premium_points(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ ليس لديك صلاحية الوصول إلى هذه الأداة.")
        return
    
    try:
        points = int(message.text)
        if points <= 0:
            bot.send_message(user_id, "❌ يجب أن يكون عدد النقاط أكبر من الصفر.")
            return
        
        # إنشاء رابط مميز
        invite_code = str(uuid.uuid4())[:12].upper()
        premium_invites[invite_code] = {
            'points': points,
            'created_by': user_id,
            'created_date': datetime.now().isoformat(),
            'used': False
        }
        save_data()
        
        invite_link = f"https://t.me/{BOT_USERNAME[1:]}?start={invite_code}"
        
        bot.send_message(
            user_id, 
            f"✅ تم إنشاء الرابط المميز بنجاح!\n\n🎁 عدد النقاط: {points}\n🔗 الرابط: `{invite_link}`\n\nهذا الرابط يعمل لمرة واحدة فقط.",
            parse_mode="Markdown"
        )
        
    except ValueError:
        bot.send_message(user_id, "❌ يرجى إدخال رقم صحيح.")

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
        
        # حفظ الملف في القناة
        success, message_text = save_file_to_channel(code, file_name, user_id)
        
        if success:
            # إرسال الملف للمستخدم
            try:
                # حفظ مؤقت وإرسال
                temp_path = os.path.join(UPLOAD_DIR, file_name)
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                with open(temp_path, 'rb') as f:
                    bot.send_document(
                        message.chat.id,
                        f,
                        caption=f"✅ تم إنشاء البوت بنجاح!\n\n📁 اسم الملف: {file_name}\n🔄 الطلبات المتبقية: {users_data[str(user_id)]['ai_requests']}\n\n📝 يمكنك الآن تشغيل الملف من خلال خيار 'تشغيل ملف' في القائمة."
                    )
                
                # حذف الملف المؤقت
                os.remove(temp_path)
            except Exception as e:
                logging.error(f"Error sending file: {e}")
                bot.send_message(message.chat.id, f"✅ تم إنشاء البوت بنجاح ولكن حدث خطأ في إرسال الملف: {str(e)}")
        else:
            bot.send_message(message.chat.id, message_text)
        
        # حذف رسالة الانتظار
        try:
            bot.delete_message(message.chat.id, wait_msg.message_id)
        except:
            pass
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
    user_id = message.from_user.id
    
    try:
        # التحقق من صيغة الملف
        if not message.document.file_name.endswith('.py'):
            bot.send_message(chat_id, "❌ يسمح فقط بملفات البايثون (.py)")
            return
        
        # تحميل الملف
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = message.document.file_name
        
        # حفظ الملف في القناة
        file_content = downloaded_file.decode('utf-8') if isinstance(downloaded_file, bytes) else downloaded_file
        success, message_text = save_file_to_channel(file_content, file_name, user_id)
        
        if success:
            bot.send_message(chat_id, f"✅ تم رفع الملف بنجاح: {file_name}")
            logging.info(f"File uploaded: {file_name} by user {user_id}")
        else:
            bot.send_message(chat_id, message_text)
    
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء رفع الملف: {str(e)}")

# معالجة استبدال الملف
def handle_replace_file(message, old_file_name):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        # التحقق من صيغة الملف
        if not message.document.file_name.endswith('.py'):
            bot.send_message(chat_id, "❌ يسمح فقط بملفات البايثون (.py)")
            return
        
        # حذف الملف القديم
        user_files = users_data[str(user_id)].get('files', [])
        users_data[str(user_id)]['files'] = [f for f in user_files if f['name'] != old_file_name]
        
        # تحميل الملف الجديد
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = message.document.file_name
        
        # حفظ الملف في القناة
        file_content = downloaded_file.decode('utf-8') if isinstance(downloaded_file, bytes) else downloaded_file
        success, message_text = save_file_to_channel(file_content, file_name, user_id)
        
        if success:
            bot.send_message(chat_id, f"✅ تم استبدال الملف بنجاح: {old_file_name} → {file_name}")
            logging.info(f"File replaced: {old_file_name} with {file_name} by user {user_id}")
        else:
            bot.send_message(chat_id, message_text)
    
    except Exception as e:
        logging.error(f"Error replacing file: {str(e)}")
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء استبدال الملف: {str(e)}")

# تشغيل البوت
if __name__ == '__main__':
    # تحميل البيانات المحفوظة
    load_data()
    
    print("🤖 بوت رفع الملفات المجاني يعمل الآن...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ حدث خطأ: {e}") 
