import os
import requests
import telebot
import subprocess
import threading
import time
import shutil
import json
import re
import uuid
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# إعدادات البوت
BOT_TOKEN = "8403108424:AAEGT-XtShnVn6_sZ_2HH_xTeGoLYyiqIB8"
GEMINI_API_KEY = "AIzaSyDTb_B7Pq3KSWWMTC1KjG4iPGqFFgLpRl8"
ADMIN_ID = 6689435577
CHANNEL_ID = -1003091756917
STORAGE_CHANNEL_ID = -1003088700358
SUBSCRIPTION_CHANNEL = "@iIl337"
BOT_USERNAME = "@TIET6BOT"

# رموز تعبيرية عشوائية
EMOJIS = ["🧤", "🩲", "🪖", "👒", "🐸", "🐝", "🪲", "🐍", "🦎", "🫎", "🦖", "🐊", "🐎", "🦚", "🦜", "🎍", "🪷", "🪸", "🪻"]

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# مجلد التخزين المؤقت
if not os.path.exists("temp_files"):
    os.makedirs("temp_files")

# قواعد البيانات المحلية
file_storage = {}
active_processes = {}
user_data_cache = {}
invited_users = {}
banned_users = {}

# دالة لتنظيف الكود من علامات Markdown
def clean_generated_code(code):
    code = re.sub(r'^```python\s*', '', code, flags=re.IGNORECASE)
    code = re.sub(r'```\s*$', '', code)
    code = re.sub(r'^\s*`{3,}.*$', '', code, flags=re.MULTILINE)
    return code.strip()

# دالة للحصول على رمز تعبيري عشوائي
def random_emoji():
    import random
    return random.choice(EMOJIS)

# دالة للتحقق من اشتراك المستخدم في القناة
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(SUBSCRIPTION_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# دالة لتحميل البيانات من القناة عند بدء التشغيل
def load_data_from_channel():
    try:
        # جلب الرسائل من القناة
        messages = bot.get_chat(STORAGE_CHANNEL_ID)
        print("✅ تم تحميل البيانات من القناة بنجاح")
    except Exception as e:
        print(f"❌ خطأ في تحميل البيانات من القناة: {e}")

# دالة للحصول على بيانات المستخدم
def get_user_data(user_id):
    if str(user_id) in banned_users:
        return None
    
    if user_id in user_data_cache:
        return user_data_cache[user_id]
    
    user_data = {
        'user_id': user_id,
        'points': 5,
        'invited_count': 0,
        'referral_code': str(uuid.uuid4())[:8],
        'referral_link': f"https://t.me/{BOT_USERNAME[1:]}?start=ref_{user_id}",
        'banned': False
    }
    
    user_data_cache[user_id] = user_data
    return user_data

# دالة لتحديث بيانات المستخدم
def update_user_data(user_id, points=None, invited_count=None):
    if str(user_id) in banned_users:
        return None
        
    user_data = get_user_data(user_id)
    if not user_data:
        return None
    
    if points is not None:
        user_data['points'] = points
    if invited_count is not None:
        user_data['invited_count'] = invited_count
    
    user_data_cache[user_id] = user_data
    return user_data

# دالة لمعالجة روابط الدعوة
def process_referral(start_param, new_user_id):
    if start_param.startswith('ref_'):
        referrer_id = int(start_param[4:])
        
        if referrer_id == new_user_id:
            return False
            
        if str(new_user_id) in invited_users:
            return False
            
        referrer_data = get_user_data(referrer_id)
        if not referrer_data:
            return False
        
        new_invited_count = referrer_data['invited_count'] + 1
        new_points = referrer_data['points'] + 1
        
        update_user_data(referrer_id, new_points, new_invited_count)
        
        new_user_data = get_user_data(new_user_id)
        if new_user_data:
            update_user_data(new_user_id, new_user_data['points'] + 1)
        
        invited_users[str(new_user_id)] = {
            'invited_by': referrer_id,
            'invited_at': datetime.now().isoformat()
        }
        
        try:
            bot.send_message(
                new_user_id,
                f"🎉 لقد حصلت على نقطة مجانية لدخولك عبر رابط الدعوة!"
            )
        except:
            pass
            
        try:
            bot.send_message(
                referrer_id,
                f"🎊 لقد حصلت على نقطة جديدة لدعوة صديق!"
            )
        except:
            pass
        
        return True
    return False

# دالة لإنشاء Inline Keyboard للقائمة الرئيسية
def create_main_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} بدء الإنتاج", callback_data="start_production"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} خيارات أكثر", callback_data="more_options"))
    return keyboard

# دالة لإنشاء Inline Keyboard للخيارات الإضافية
def create_more_options_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} رفع ملف جاهز", callback_data="upload_file"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} تعديل ملف", callback_data="edit_file"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} حذف ملف", callback_data="delete_file"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} استبدال ملف", callback_data="replace_file"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} عرض الملفات", callback_data="list_files"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
    return keyboard

# دالة لإنشاء Inline Keyboard لرابط الدعوة
def create_referral_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} إنشاء رابط الدعوة", callback_data="generate_referral"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
    return keyboard

# دالة لإنشاء Inline Keyboard لإدارة المدير
def create_admin_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} إضافة نقاط", callback_data="admin_add_points"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} حظر/فك حظر", callback_data="admin_ban_user"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} إشعار عام", callback_data="admin_broadcast"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} عدد المستخدمين", callback_data="admin_user_count"))
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
    return keyboard

# دالة لإنشاء Inline Keyboard لتأكيد الحذف
def create_confirm_delete_keyboard(file_name):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ نعم، احذف", callback_data=f"delete_yes_{file_name}"))
    keyboard.add(InlineKeyboardButton("❌ إلغاء", callback_data="back_to_main"))
    return keyboard

# دالة لإنشاء ملف Python باستخدام Gemini AI
def create_python_file(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    ai_persona = """
أنت مساعد خبير في برمجة بوتات Telegram.
يجب أن تكون الأكواد التي تكتبها:
1. كاملة وجاهزة للتشغيل مباشرة
2. تدعم مكتبات telebot و telethon و python-telegram-bot و aiogram
3. تحتوي على جميع الاستيرادات الضرورية
4. تتضمن معالجة للأخطاء
5. تكون فعالة وموثوقة
6. لا تحتوي على أي علامات تنسيق
7. تدعم اللغة العربية في النصوص

الرجاء كتابة الكود فقط دون أي شرح إضافي.
"""
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{ai_persona}\n\nWrite a complete Python Telegram bot. {prompt}. Provide only the Python code without any explanations or markdown formatting."
                    }
                ]
            }
        ]
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            code = result['candidates'][0]['content']['parts'][0]['text']
            cleaned_code = clean_generated_code(code)
            return cleaned_code
        else:
            print(f"Error from Gemini API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception in create_python_file: {e}")
        return None

# دالة لتعديل ملف Python باستخدام Gemini AI
def modify_python_file(code, modification_request):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"Modify this Python code based on the following request: {modification_request}. Here is the current code:\n\n{code}\n\nProvide only the modified Python code without any explanations or markdown formatting."
                    }
                ]
            }
        ]
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            modified_code = result['candidates'][0]['content']['parts'][0]['text']
            cleaned_code = clean_generated_code(modified_code)
            return cleaned_code
        else:
            print(f"Error from Gemini API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception in modify_python_file: {e}")
        return None

# دالة لتشغيل البوت لمدة 15 دقيقة
def run_bot_for_15_minutes(file_path, chat_id, file_name, user_id):
    try:
        status_msg = bot.send_message(chat_id, f"⏳ جاري تشغيل البوت: {file_name} لمدة 15 دقيقة...")
        
        process = subprocess.Popen(
            ['python', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        active_processes[file_name] = {
            'process': process,
            'start_time': time.time(),
            'status_msg_id': status_msg.message_id,
            'user_id': user_id
        }
        
        for _ in range(90):
            if process.poll() is not None:
                break
            time.sleep(10)
        
        if process.poll() is None:
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                process.kill()
        
        stdout, stderr = process.communicate()
        
        result_message = f"⏰ انتهت مدة التشغيل (15 دقيقة) للبوت: {file_name}\n\n"
        
        if stdout:
            result_message += f"📤 الناتج:\n{stdout[-1000:]}\n\n"
        
        if stderr:
            result_message += f"❌ الأخطاء:\n{stderr[-1000:]}\n\n"
        
        if not stdout and not stderr:
            result_message += "✅ تم التشغيل بنجاح بدون ناتج."
        
        has_errors = bool(stderr) or "error" in result_message.lower() or "exception" in result_message.lower()
        
        if has_errors and user_id in active_processes and user_id != ADMIN_ID:
            user_data = get_user_data(user_id)
            if user_data:
                update_user_data(user_id, user_data['points'] + 1)
                result_message += "\n\n⚠️ تم إعادة النقطة إلى رصيدك بسبب وجود أخطاء في التشغيل."
        
        try:
            bot.edit_message_text(
                result_message,
                chat_id,
                status_msg.message_id
            )
        except:
            bot.send_message(chat_id, result_message)
        
        if file_name in active_processes:
            del active_processes[file_name]
            
    except Exception as e:
        error_msg = f"❌ خطأ أثناء تشغيل البوت {file_name}: {str(e)}"
        try:
            bot.send_message(chat_id, error_msg)
        except:
            print(error_msg)
        
        if user_id in active_processes and user_id != ADMIN_ID:
            user_data = get_user_data(user_id)
            if user_data:
                update_user_data(user_id, user_data['points'] + 1)
        
        if file_name in active_processes:
            del active_processes[file_name]

# التحقق من هوية المدير
def is_admin(user_id):
    return user_id == ADMIN_ID

# معالج الأمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if str(message.from_user.id) in banned_users:
        bot.send_message(message.chat.id, "❌ تم حظرك من استخدام البوت.")
        return
    
    if not check_subscription(message.from_user.id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("✅ التحقق من الاشتراك", callback_data="check_subscription"))
        bot.send_message(
            message.chat.id, 
            f"⚠️ يجب الاشتراك في القناة {SUBSCRIPTION_CHANNEL} أولاً لاستخدام البوت.",
            reply_markup=keyboard
        )
        return
    
    if len(message.text.split()) > 1:
        start_param = message.text.split()[1]
        process_referral(start_param, message.from_user.id)
    
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "❌ حدث خطأ في تحميل بياناتك.")
        return
    
    welcome_text = f"""
مرحباً! 👋 {random_emoji()}

أنا بوت متقدم لإنشاء وتشغيل بوتات Python باستخدام الذكاء الاصطناعي.

✨ **المميزات المتاحة:**
- إنشاء بوتات Python باستخدام Gemini AI
- تشغيل البوتات لمدة 15 دقيقة على السيرفر
- تعديل البوتات باستخدام الذكاء الاصطناعي
- إدارة كاملة للملفات

⭐ **نقاطك الحالية: {user_data['points']}**
👥 **عدد المدعوين: {user_data['invited_count']}**

🚀 **لبدء الاستخدام:**
اضغط على "بدء الإنتاج" لإنشاء بوت جديد، أو "خيارات أكثر" للوصول إلى الميزات الأخرى.
"""
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_keyboard())

# معالج الأمر /admin
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية الوصول إلى لوحة الإدارة.")
        return
    
    admin_text = f"""
👑 لوحة إدارة المدير

اختر أحد الخيارات أدناه للإدارة:
"""
    bot.send_message(message.chat.id, admin_text, reply_markup=create_admin_keyboard())

# معالج استدعاء الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if str(call.from_user.id) in banned_users:
        bot.answer_callback_query(call.id, "❌ تم حظرك من استخدام البوت.")
        return
    
    if not call.data.startswith("admin_") and not check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ يجب الاشتراك في القناة أولاً")
        return
    
    if call.data == "check_subscription":
        if check_subscription(call.from_user.id):
            bot.send_message(call.message.chat.id, "✅ تم الاشتراك بنجاح! يمكنك الآن استخدام البوت.", reply_markup=create_main_keyboard())
        else:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("📢 انضم إلى القناة", url=f"https://t.me/{SUBSCRIPTION_CHANNEL[1:]}"))
            keyboard.add(InlineKeyboardButton("✅ التحقق من الاشتراك", callback_data="check_subscription"))
            bot.edit_message_text(
                f"⚠️ لم تشترك بعد في القناة {SUBSCRIPTION_CHANNEL}. يرجى الاشتراك ثم الضغط على التحقق.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )
        return
    
    if call.data == "back_to_main":
        bot.edit_message_text("🏠 القائمة الرئيسية", call.message.chat.id, call.message.message_id, reply_markup=create_main_keyboard())
        return
    
    user_data = get_user_data(call.from_user.id)
    if not user_data:
        bot.answer_callback_query(call.id, "❌ حدث خطأ في تحميل بياناتك.")
        return
    
    if is_admin(call.from_user.id):
        user_data['points'] = float('inf')
    
    if call.data == "start_production":
        if user_data['points'] <= 0 and not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ ليس لديك نقاط كافية")
            bot.send_message(
                call.message.chat.id,
                f"❌ ليس لديك نقاط كافية. نقاطك الحالية: {user_data['points']}\n\n📣 قم بدعوة أصدقائك للحصول على المزيد من النقاط.",
                reply_markup=create_referral_keyboard()
            )
            return
        
        msg = bot.send_message(call.message.chat.id, "📝 أرسل وصفاً للبوت الذي تريد إنشاءه:")
        bot.register_next_step_handler(msg, process_bot_creation)
    
    elif call.data == "generate_referral":
        user_data = get_user_data(call.from_user.id)
        referral_text = f"""
📣 رابط الدعوة الخاص بك:

{user_data['referral_link']}

👥 لكل شخص يدخل عبر هذا الرابط:
⭐ تحصل على نقطة واحدة
👤 يحصل هو على نقطة مجانية

🔗 شارك الرابط مع أصدقائك للحصول على نقاط مجانية!
        """
        bot.send_message(call.message.chat.id, referral_text, reply_markup=create_main_keyboard())
    
    elif call.data == "more_options":
        bot.edit_message_text("🔧 اختر أحد الخيارات:", call.message.chat.id, call.message.message_id, reply_markup=create_more_options_keyboard())
    
    elif call.data == "upload_file":
        msg = bot.send_message(call.message.chat.id, "📤 أرسل ملف Python الجاهز:")
        bot.register_next_step_handler(msg, process_file_upload)
    
    elif call.data == "edit_file":
        if not file_storage:
            bot.send_message(call.message.chat.id, "❌ لا توجد ملفات مخزنة", reply_markup=create_main_keyboard())
            return
        
        keyboard = InlineKeyboardMarkup()
        for file_name in file_storage.keys():
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} {file_name}", callback_data=f"edit_{file_name}"))
        
        keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
        
        bot.send_message(call.message.chat.id, "📝 اختر الملف الذي تريد تعديله:", reply_markup=keyboard)
    
    elif call.data.startswith("edit_"):
        file_name = call.data[5:]
        if file_name in file_storage:
            file_path = file_storage[file_name]["path"]
            
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            bot.user_data[call.from_user.id] = {"action": "editing", "file_name": file_name, "code": code}
            
            msg = bot.send_message(call.message.chat.id, "✏️ ما التعديلات التي تريد إجراؤها على الملف؟")
            bot.register_next_step_handler(msg, process_edit_request)
        else:
            bot.send_message(call.message.chat.id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())
    
    elif call.data == "delete_file":
        if not file_storage:
            bot.send_message(call.message.chat.id, "❌ لا توجد ملفات مخزنة", reply_markup=create_main_keyboard())
            return
        
        keyboard = InlineKeyboardMarkup()
        for file_name in file_storage.keys():
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} {file_name}", callback_data=f"confirm_delete_{file_name}"))
        
        keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
        
        bot.send_message(call.message.chat.id, "🗑️ اختر الملف الذي تريد حذفه:", reply_markup=keyboard)
    
    elif call.data.startswith("confirm_delete_"):
        file_name = call.data[15:]
        bot.send_message(call.message.chat.id, f"⚠️ هل أنت متأكد من حذف الملف: {file_name}؟", reply_markup=create_confirm_delete_keyboard(file_name))
    
    elif call.data.startswith("delete_yes_"):
        file_name = call.data[11:]
        if file_name in file_storage:
            file_path = file_storage[file_name]["path"]
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            del file_storage[file_name]
            
            bot.send_message(call.message.chat.id, f"✅ تم حذف الملف: {file_name}", reply_markup=create_main_keyboard())
        else:
            bot.send_message(call.message.chat.id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())
    
    elif call.data == "replace_file":
        if not file_storage:
            bot.send_message(call.message.chat.id, "❌ لا توجد ملفات مخزنة", reply_markup=create_main_keyboard())
            return
        
        keyboard = InlineKeyboardMarkup()
        for file_name in file_storage.keys():
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} {file_name}", callback_data=f"select_replace_{file_name}"))
        
        keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
        
        bot.send_message(call.message.chat.id, "🔄 اختر الملف الذي تريد استبداله:", reply_markup=keyboard)
    
    elif call.data.startswith("select_replace_"):
        file_name = call.data[15:]
        msg = bot.send_message(call.message.chat.id, f"📤 أرسل الملف الجديد ليحل محل: {file_name}")
        bot.register_next_step_handler(msg, process_replace_file, file_name)
    
    elif call.data == "list_files":
        if not file_storage:
            bot.send_message(call.message.chat.id, "❌ لا توجد ملفات مخزنة", reply_markup=create_main_keyboard())
            return
        
        files_list = "\n".join([f"📄 {name}" for name in file_storage.keys()])
        bot.send_message(call.message.chat.id, f"📂 الملفات المخزنة ({len(file_storage)}):\n\n{files_list}", reply_markup=create_main_keyboard())
    
    elif call.data.startswith("run_"):
        file_name = call.data[4:]
        if file_name in file_storage:
            file_path = file_storage[file_name]["path"]
            
            if file_name in active_processes:
                bot.answer_callback_query(call.id, "⏳ البوت قيد التشغيل بالفعل")
                return
            
            thread = threading.Thread(target=run_bot_for_15_minutes, args=(file_path, call.message.chat.id, file_name, call.from_user.id))
            thread.daemon = True
            thread.start()
            
            bot.answer_callback_query(call.id, "⏳ بدأ تشغيل البوت لمدة 15 دقيقة")
        else:
            bot.send_message(call.message.chat.id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())
    
    elif call.data.startswith("admin_"):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول إلى لوحة الإدارة.")
            return
            
        if call.data == "admin_add_points":
            msg = bot.send_message(call.message.chat.id, "🔢 أرسل معرف المستخدم وعدد النقاط بالشكل: user_id points")
            bot.register_next_step_handler(msg, process_admin_add_points)
            
        elif call.data == "admin_ban_user":
            msg = bot.send_message(call.message.chat.id, "🔒 أرسل معرف المستخدم لحظره/فك حظره:")
            bot.register_next_step_handler(msg, process_admin_ban_user)
            
        elif call.data == "admin_broadcast":
            msg = bot.send_message(call.message.chat.id, "📢 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين:")
            bot.register_next_step_handler(msg, process_admin_broadcast)
            
        elif call.data == "admin_user_count":
            user_count = len(user_data_cache)
            bot.send_message(call.message.chat.id, f"👥 عدد المستخدمين: {user_count}")

# معالج إنشاء البوت
def process_bot_creation(message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "❌ حدث خطأ في تحميل بياناتك.")
        return
    
    if not is_admin(message.from_user.id):
        update_user_data(message.from_user.id, user_data['points'] - 1)
    
    prompt = message.text
    bot.send_message(message.chat.id, "⏳ جاري إنشاء البوت باستخدام الذكاء الاصطناعي...")
    
    code = create_python_file(prompt)
    
    if code:
        timestamp = int(time.time())
        file_name = f"bot_{timestamp}.py"
        file_path = f"temp_files/{file_name}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        file_storage[file_name] = {
            "path": file_path,
            "content": code,
            "created_at": datetime.now().isoformat(),
            "created_by": message.from_user.id
        }
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(f"{random_emoji()} تشغيل (15 دقيقة)", callback_data=f"run_{file_name}"))
        keyboard.add(InlineKeyboardButton(f"{random_emoji()} تعديل", callback_data=f"edit_{file_name}"))
        keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
        
        with open(file_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم إنشاء البوت بنجاح", reply_markup=keyboard)
        
        try:
            with open(file_path, 'rb') as f:
                bot.send_document(CHANNEL_ID, f, caption=f"تم إنشاء البوت: {file_name}")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
    else:
        if not is_admin(message.from_user.id):
            update_user_data(message.from_user.id, user_data['points'])
        bot.send_message(message.chat.id, "❌ فشل في إنشاء البوت. تم إعادة النقطة إلى رصيدك. يرجى المحاولة مرة أخرى.", reply_markup=create_main_keyboard())

# معالج رفع الملف الجاهز
def process_file_upload(message):
    if message.document:
        file_name = message.document.file_name
        
        if file_name.endswith('.py'):
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            file_path = f"temp_files/{file_name}"
            with open(file_path, 'wb') as f:
                f.write(downloaded_file)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_storage[file_name] = {
                "path": file_path,
                "content": content,
                "created_at": datetime.now().isoformat(),
                "created_by": message.from_user.id
            }
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} تشغيل (15 دقيقة)", callback_data=f"run_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} تعديل", callback_data=f"edit_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
            
            bot.send_message(message.chat.id, "✅ تم رفع الملف بنجاح", reply_markup=keyboard)
            
            try:
                with open(file_path, 'rb') as f:
                    bot.send_document(CHANNEL_ID, f, caption=f"تم رفع الملف: {file_name}")
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
        else:
            bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python فقط", reply_markup=create_main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python", reply_markup=create_main_keyboard())

# معالج طلب التعديل
def process_edit_request(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        bot.send_message(message.chat.id, "❌ حدث خطأ في تحميل بياناتك.")
        return
    
    if user_data['points'] <= 0 and not is_admin(user_id):
        bot.send_message(
            message.chat.id,
            f"❌ ليس لديك نقاط كافية. نقاطك الحالية: {user_data['points']}",
            reply_markup=create_referral_keyboard()
        )
        return
    
    if not is_admin(user_id):
        update_user_data(user_id, user_data['points'] - 1)
    
    if user_id in bot.user_data and "action" in bot.user_data[user_id] and bot.user_data[user_id]["action"] == "editing":
        modification_request = message.text
        code = bot.user_data[user_id]["code"]
        original_file_name = bot.user_data[user_id]["file_name"]
        
        bot.send_message(message.chat.id, "⏳ جاري تعديل الملف باستخدام الذكاء الاصطناعي...")
        
        modified_code = modify_python_file(code, modification_request)
        
        if modified_code:
            timestamp = int(time.time())
            new_file_name = f"modified_{timestamp}.py"
            file_path = f"temp_files/{new_file_name}"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_code)
            
            file_storage[new_file_name] = {
                "path": file_path,
                "content": modified_code,
                "created_at": datetime.now().isoformat(),
                "created_by": message.from_user.id,
                "modified_from": original_file_name
            }
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} تشغيل (15 دقيقة)", callback_data=f"run_{new_file_name}"))
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} تعديل", callback_data=f"edit_{new_file_name}"))
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
            
            with open(file_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ تم تعديل الملف بنجاح", reply_markup=keyboard)
            
            try:
                with open(file_path, 'rb') as f:
                    bot.send_document(CHANNEL_ID, f, caption=f"تم تعديل الملف: {new_file_name}")
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
            
            del bot.user_data[user_id]
        else:
            if not is_admin(user_id):
                update_user_data(user_id, user_data['points'])
            bot.send_message(message.chat.id, "❌ فشل في تعديل الملف. تم إعادة النقطة إلى رصيدك. يرجى المحاولة مرة أخرى.", reply_markup=create_main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على بيانات التعديل. يرجى البدء من جديد.", reply_markup=create_main_keyboard())

# معالج استبدال الملف
def process_replace_file(message, old_file_name):
    if message.document:
        file_name = message.document.file_name
        
        if file_name.endswith('.py'):
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            temp_path = f"temp_files/temp_{file_name}"
            with open(temp_path, 'wb') as f:
                f.write(downloaded_file)
            
            if old_file_name in file_storage:
                old_path = file_storage[old_file_name]["path"]
                if os.path.exists(old_path):
                    os.remove(old_path)
                
                shutil.move(temp_path, old_path)
                
                with open(old_path, 'r', encoding='utf-8') as f:
                    new_content = f.read()
                
                file_storage[old_file_name]["content"] = new_content
                file_storage[old_file_name]["updated_at"] = datetime.now().isoformat()
                file_storage[old_file_name]["updated_by"] = message.from_user.id
                
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton(f"{random_emoji()} تشغيل (15 دقيقة)", callback_data=f"run_{old_file_name}"))
                keyboard.add(InlineKeyboardButton(f"{random_emoji()} تعديل", callback_data=f"edit_{old_file_name}"))
                keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
                
                bot.send_message(message.chat.id, f"✅ تم استبدال الملف: {old_file_name}", reply_markup=keyboard)
                
                try:
                    with open(old_path, 'rb') as f:
                        bot.send_document(CHANNEL_ID, f, caption=f"تم تحديث الملف: {old_file_name}")
                except Exception as e:
                    bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
            else:
                bot.send_message(message.chat.id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python فقط", reply_markup=create_main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python", reply_markup=create_main_keyboard())

# معالجات لوحة الإدارة
def process_admin_add_points(message):
    if not is_admin(message.from_user.id):
        return
        
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ الصيغة غير صحيحة. استخدم: user_id points")
            return
            
        user_id = int(parts[0])
        points = int(parts[1])
        
        user_data = get_user_data(user_id)
        if not user_data:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود.")
            return
            
        new_points = user_data['points'] + points
        update_user_data(user_id, new_points)
        
        bot.send_message(message.chat.id, f"✅ تم إضافة {points} نقطة إلى المستخدم {user_id}. النقاط الجديدة: {new_points}")
        
        try:
            bot.send_message(user_id, f"🎉 لقد حصلت على {points} نقطة من المدير! نقاطك الآن: {new_points}")
        except:
            pass
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ القيم المدخلة غير صحيحة. تأكد من أن user_id و points أرقام صحيحة.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")

def process_admin_ban_user(message):
    if not is_admin(message.from_user.id):
        return
        
    try:
        user_id = int(message.text)
        
        if str(user_id) in banned_users:
            del banned_users[str(user_id)]
            bot.send_message(message.chat.id, f"✅ تم فك حظر المستخدم {user_id}.")
            
            try:
                bot.send_message(user_id, "✅ تم فك حظرك من البوت. يمكنك الآن استخدامه مرة أخرى.")
            except:
                pass
        else:
            banned_users[str(user_id)] = {
                'banned_by': message.from_user.id,
                'banned_at': datetime.now().isoformat()
            }
            bot.send_message(message.chat.id, f"✅ تم حظر المستخدم {user_id}.")
            
            try:
                bot.send_message(user_id, "❌ تم حظرك من استخدام البوت.")
            except:
                pass
    except ValueError:
        bot.send_message(message.chat.id, "❌ user_id يجب أن يكون رقماً صحيحاً.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")

def process_admin_broadcast(message):
    if not is_admin(message.from_user.id):
        return
        
    broadcast_text = f"""
📢 إشعار عام من الإدارة:

{message.text}
"""
    
    sent_count = 0
    for user_id in user_data_cache:
        try:
            bot.send_message(user_id, broadcast_text)
            sent_count += 1
        except:
            continue
    
    bot.send_message(message.chat.id, f"✅ تم إرسال الإشعار إلى {sent_count} مستخدم.")

# بدء البوت
if __name__ == "__main__":
    load_data_from_channel()
    print("🤖 البوت النهائي مع Inline Keyboard يعمل الآن...")
    bot.infinity_polling()
