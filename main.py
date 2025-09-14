import os
import requests
import telebot
import subprocess
import threading
import time
import shutil
import json
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# إعدادات البوت
BOT_TOKEN = "8403108424:AAEGT-XtShnVn6_sZ_2HH_xTeGoLYyiqIB8"
GEMINI_API_KEY = "AIzaSyDTb_B7Pq3KSWWMTC1KjG4iPGqFFgLpRl8"
ADMIN_ID = 6689435577
CHANNEL_ID = -1003091756917  # إضافة علامة ناقص للقنوات

# رموز تعبيرية عشوائية
EMOJIS = ["🧤", "🩲", "🪖", "👒", "🐸", "🐝", "🪲", "🐍", "🦎", "🫎", "🦖", "🐊", "🐎", "🦚", "🦜", "🎍", "🪷", "🪸", "🪻"]

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# مجلد التخزين المؤقت
if not os.path.exists("temp_files"):
    os.makedirs("temp_files")

# قاموس لتخزين معلومات الملفات
file_storage = {}

# دالة للحصول على رمز تعبيري عشوائي
def random_emoji():
    import random
    return random.choice(EMOJIS)

# دالة لإنشاء لوحة المفاتيح الرئيسية
def create_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"{random_emoji()} بدء الإنتاج", callback_data="start_production"),
        InlineKeyboardButton(f"{random_emoji()} خيارات أكثر", callback_data="more_options")
    )
    return keyboard

# دالة لإنشاء لوحة خيارات أكثر
def create_more_options_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(f"{random_emoji()} رفع ملف جاهز", callback_data="upload_file"),
        InlineKeyboardButton(f"{random_emoji()} حذف ملف", callback_data="delete_file")
    )
    keyboard.add(
        InlineKeyboardButton(f"{random_emoji()} استبدال ملف", callback_data="replace_file"),
        InlineKeyboardButton(f"{random_emoji()} عرض الملفات", callback_data="list_files")
    )
    return keyboard

# دالة لإنشاء ملف Python باستخدام Gemini AI
def create_python_file(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"Write a complete Python Telegram bot using the pyTelegramBotAPI library. {prompt}. Provide only the Python code without any explanations or markdown formatting."
                    }
                ]
            }
        ]
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        code = result['candidates'][0]['content']['parts'][0]['text']
        return code
    else:
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
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        modified_code = result['candidates'][0]['content']['parts'][0]['text']
        return modified_code
    else:
        return None

# دالة لتشغيل البوت لمدة 15 دقيقة
def run_bot_for_15_minutes(file_path, chat_id, file_name):
    try:
        # إرسال رسالة بدء التشغيل
        bot.send_message(chat_id, f"⏳ جاري تشغيل البوت: {file_name} لمدة 15 دقيقة...")
        
        # تشغيل البوت
        process = subprocess.Popen(['python', file_path], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
        
        # الانتظار لمدة 15 دقيقة
        time.sleep(900)
        
        # إنهاء العملية بعد 15 دقيقة
        process.terminate()
        try:
            bot.send_message(chat_id, f"⏰ انتهت مدة التشغيل (15 دقيقة) للبوت: {file_name}")
        except:
            pass
        
    except Exception as e:
        try:
            bot.send_message(chat_id, f"❌ خطأ أثناء تشغيل البوت {file_name}: {str(e)}")
        except:
            pass

# التحقق من هوية المدير
def is_admin(user_id):
    return user_id == ADMIN_ID

# دالة لتحميل قائمة الملفات
def load_file_list():
    global file_storage
    if os.path.exists("file_storage.json"):
        try:
            with open("file_storage.json", "r") as f:
                file_storage = json.load(f)
        except:
            file_storage = {}

# دالة لحفظ قائمة الملفات
def save_file_list():
    try:
        with open("file_storage.json", "w") as f:
            json.dump(file_storage, f)
    except:
        pass

# دالة لعرض قائمة الملفات
def show_file_list(chat_id, action, message_text="📁 اختر ملف من القائمة:"):
    if not file_storage:
        bot.send_message(chat_id, "❌ لا توجد ملفات مخزنة")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for file_name in file_storage.keys():
        emoji = random_emoji()
        keyboard.add(InlineKeyboardButton(f"{emoji} {file_name}", callback_data=f"{action}_{file_name}"))
    
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
    
    bot.send_message(chat_id, message_text, reply_markup=keyboard)

# دالة لحذف ملف
def delete_file(file_name, chat_id):
    if file_name in file_storage:
        file_path = file_storage[file_name]["path"]
        
        # حذف الملف من النظام
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # حذف الملف من القناة (إذا كان معروفًا)
        try:
            message_id = file_storage[file_name].get("message_id")
            if message_id:
                bot.delete_message(CHANNEL_ID, message_id)
        except:
            pass
        
        # حذف الملف من التخزين
        del file_storage[file_name]
        save_file_list()
        
        bot.send_message(chat_id, f"✅ تم حذف الملف: {file_name}", reply_markup=create_main_keyboard())
    else:
        bot.send_message(chat_id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())

# دالة لاستبدال ملف
def replace_file(old_file_name, new_file_path, chat_id, user_id):
    if old_file_name in file_storage:
        # قراءة المحتوى الجديد
        with open(new_file_path, 'r') as f:
            new_content = f.read()
        
        # تحديث المسار
        old_path = file_storage[old_file_name]["path"]
        if os.path.exists(old_path):
            os.remove(old_path)
        
        # نقل الملف الجديد
        shutil.move(new_file_path, old_path)
        
        # تحديث التخزين
        file_storage[old_file_name]["path"] = old_path
        file_storage[old_file_name]["content"] = new_content
        file_storage[old_file_name]["updated_at"] = datetime.now().isoformat()
        file_storage[old_file_name]["updated_by"] = user_id
        
        save_file_list()
        
        # تحديث الملف في القناة
        try:
            message_id = file_storage[old_file_name].get("message_id")
            if message_id:
                bot.delete_message(CHANNEL_ID, message_id)
                
            with open(old_path, 'rb') as f:
                sent_message = bot.send_document(CHANNEL_ID, f, caption=f"تم تحديث الملف: {old_file_name}")
                file_storage[old_file_name]["message_id"] = sent_message.message_id
                save_file_list()
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ تم الاستبدال ولكن حدث خطأ في القناة: {str(e)}")
        
        # إرسال التأكيد للمستخدم
        keyboard = InlineKeyboardMarkup()
        emoji_run = random_emoji()
        emoji_edit = random_emoji()
        keyboard.add(
            InlineKeyboardButton(f"{emoji_run} تشغيل (15 دقيقة)", callback_data=f"run_{old_file_name}"),
            InlineKeyboardButton(f"{emoji_edit} تعديل", callback_data=f"edit_{old_file_name}")
        )
        keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
        
        bot.send_message(chat_id, f"✅ تم استبدال الملف: {old_file_name}", reply_markup=keyboard)
    else:
        bot.send_message(chat_id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())

# معالج الأمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    load_file_list()
    
    welcome_text = f"""
مرحباً يا مدير! 👑 {random_emoji()}

أنا بوت متقدم لإنشاء وتشغيل بوتات Python باستخدام الذكاء الاصطناعي.

✨ **المميزات المتاحة:**
- إنشاء بوتات Python باستخدام Gemini AI
- تشغيل البوتات لمدة 15 دقيقة على السيرفر
- تعديل البوتات باستخدام الذكاء الاصطناعي
- إدارة كاملة للملفات (رفع، حذف، استبدال)
- تخزين الملفات في قناة خاصة

🚀 **لبدء الاستخدام:**
اضغط على "بدء الإنتاج" لإنشاء بوت جديد، أو "خيارات أكثر" للوصول إلى الميزات الأخرى.
"""
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_keyboard())

# معالج استدعاء الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    if call.data == "start_production":
        msg = bot.send_message(call.message.chat.id, "📝 أرسل وصفاً للبوت الذي تريد إنشاءه:")
        bot.register_next_step_handler(msg, process_bot_creation)
    
    elif call.data == "more_options":
        bot.edit_message_text("🔧 اختر أحد الخيارات:", call.message.chat.id, call.message.message_id, reply_markup=create_more_options_keyboard())
    
    elif call.data == "back_to_main":
        bot.edit_message_text("🏠 القائمة الرئيسية", call.message.chat.id, call.message.message_id, reply_markup=create_main_keyboard())
    
    elif call.data == "upload_file":
        msg = bot.send_message(call.message.chat.id, "📤 أرسل ملف Python الجاهز:")
        bot.register_next_step_handler(msg, process_file_upload)
    
    elif call.data == "delete_file":
        show_file_list(call.message.chat.id, "confirm_delete", "🗑️ اختر الملف الذي تريد حذفه:")
    
    elif call.data == "replace_file":
        show_file_list(call.message.chat.id, "select_replace", "🔄 اختر الملف الذي تريد استبداله:")
    
    elif call.data == "list_files":
        if not file_storage:
            bot.send_message(call.message.chat.id, "❌ لا توجد ملفات مخزنة", reply_markup=create_main_keyboard())
            return
        
        files_list = "\n".join([f"📄 {name} (أنشئ في: {file_storage[name]['created_at']})" for name in file_storage.keys()])
        bot.send_message(call.message.chat.id, f"📂 الملفات المخزنة ({len(file_storage)}):\n\n{files_list}", reply_markup=create_main_keyboard())
    
    elif call.data.startswith("confirm_delete_"):
        file_name = call.data[15:]
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("✅ نعم، احذف", callback_data=f"delete_yes_{file_name}"),
            InlineKeyboardButton("❌ إلغاء", callback_data="back_to_main")
        )
        bot.send_message(call.message.chat.id, f"⚠️ هل أنت متأكد من حذف الملف: {file_name}؟", reply_markup=keyboard)
    
    elif call.data.startswith("delete_yes_"):
        file_name = call.data[11:]
        delete_file(file_name, call.message.chat.id)
    
    elif call.data.startswith("select_replace_"):
        file_name = call.data[15:]
        msg = bot.send_message(call.message.chat.id, f"📤 أرسل الملف الجديد ليحل محل: {file_name}")
        bot.register_next_step_handler(msg, process_replace_file, file_name)
    
    elif call.data.startswith("run_"):
        file_name = call.data[4:]
        if file_name in file_storage:
            file_path = file_storage[file_name]["path"]
            
            # تشغيل البوت في thread منفصل
            thread = threading.Thread(target=run_bot_for_15_minutes, args=(file_path, call.message.chat.id, file_name))
            thread.start()
            
            bot.answer_callback_query(call.id, "⏳ بدأ تشغيل البوت لمدة 15 دقيقة")
        else:
            bot.send_message(call.message.chat.id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())
    
    elif call.data.startswith("edit_"):
        file_name = call.data[5:]
        if file_name in file_storage:
            file_path = file_storage[file_name]["path"]
            
            # قراءة المحتوى الحالي
            with open(file_path, 'r') as f:
                code = f.read()
            
            # حفظ المحتوى مؤقتاً للاستخدام لاحقاً
            bot.user_data[call.from_user.id] = {"action": "editing", "file_name": file_name, "code": code}
            
            msg = bot.send_message(call.message.chat.id, "✏️ ما التعديلات التي تريد إجراؤها على الملف؟")
            bot.register_next_step_handler(msg, process_edit_request)
        else:
            bot.send_message(call.message.chat.id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())

# معالج إنشاء البوت
def process_bot_creation(message):
    prompt = message.text
    bot.send_message(message.chat.id, "⏳ جاري إنشاء البوت باستخدام الذكاء الاصطناعي...")
    
    # إنشاء الكود باستخدام Gemini AI
    code = create_python_file(prompt)
    
    if code:
        # حفظ الملف مؤقتاً
        timestamp = int(time.time())
        file_name = f"bot_{timestamp}.py"
        file_path = f"temp_files/{file_name}"
        
        with open(file_path, 'w') as f:
            f.write(code)
        
        # حفظ المعلومات في التخزين
        file_storage[file_name] = {
            "path": file_path,
            "content": code,
            "created_at": datetime.now().isoformat(),
            "created_by": message.from_user.id
        }
        save_file_list()
        
        # إرسال الملف كمستند
        with open(file_path, 'rb') as f:
            # إنشاء زر التشغيل
            keyboard = InlineKeyboardMarkup()
            emoji_run = random_emoji()
            emoji_edit = random_emoji()
            keyboard.add(
                InlineKeyboardButton(f"{emoji_run} تشغيل (15 دقيقة)", callback_data=f"run_{file_name}"),
                InlineKeyboardButton(f"{emoji_edit} تعديل", callback_data=f"edit_{file_name}")
            )
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
            
            sent_message = bot.send_document(message.chat.id, f, caption="✅ تم إنشاء البوت بنجاح", reply_markup=keyboard)
        
        # إرسال الملف إلى القناة
        try:
            with open(file_path, 'rb') as f:
                channel_message = bot.send_document(CHANNEL_ID, f, caption=f"تم إنشاء البوت: {file_name} بواسطة {message.from_user.first_name}")
                file_storage[file_name]["message_id"] = channel_message.message_id
                save_file_list()
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
    else:
        bot.send_message(message.chat.id, "❌ فشل في إنشاء البوت. يرجى المحاولة مرة أخرى.", reply_markup=create_main_keyboard())

# معالج رفع الملف الجاهز
def process_file_upload(message):
    if message.document:
        file_name = message.document.file_name
        
        if file_name.endswith('.py'):
            # تنزيل الملف
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # حفظ الملف
            file_path = f"temp_files/{file_name}"
            with open(file_path, 'wb') as f:
                f.write(downloaded_file)
            
            # قراءة المحتوى
            with open(file_path, 'r') as f:
                content = f.read()
            
            # حفظ المعلومات في التخزين
            file_storage[file_name] = {
                "path": file_path,
                "content": content,
                "created_at": datetime.now().isoformat(),
                "created_by": message.from_user.id
            }
            save_file_list()
            
            # إنشاء زر التشغيل
            keyboard = InlineKeyboardMarkup()
            emoji_run = random_emoji()
            emoji_edit = random_emoji()
            keyboard.add(
                InlineKeyboardButton(f"{emoji_run} تشغيل (15 دقيقة)", callback_data=f"run_{file_name}"),
                InlineKeyboardButton(f"{emoji_edit} تعديل", callback_data=f"edit_{file_name}")
            )
            keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
            
            bot.send_message(message.chat.id, "✅ تم رفع الملف بنجاح", reply_markup=keyboard)
            
            # إرسال الملف إلى القناة
            try:
                with open(file_path, 'rb') as f:
                    channel_message = bot.send_document(CHANNEL_ID, f, caption=f"تم رفع الملف: {file_name} بواسطة {message.from_user.first_name}")
                    file_storage[file_name]["message_id"] = channel_message.message_id
                    save_file_list()
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
        else:
            bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python فقط (امتداد .py)", reply_markup=create_main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python", reply_markup=create_main_keyboard())

# معالج استبدال الملف
def process_replace_file(message, old_file_name):
    if message.document:
        file_name = message.document.file_name
        
        if file_name.endswith('.py'):
            # تنزيل الملف الجديد
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # حفظ الملف الجديد مؤقتاً
            temp_path = f"temp_files/temp_{file_name}"
            with open(temp_path, 'wb') as f:
                f.write(downloaded_file)
            
            # استبدال الملف
            replace_file(old_file_name, temp_path, message.chat.id, message.from_user.id)
        else:
            bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python فقط (امتداد .py)", reply_markup=create_main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python", reply_markup=create_main_keyboard())

# معالج طلب التعديل
def process_edit_request(message):
    user_id = message.from_user.id
    if user_id in bot.user_data and "action" in bot.user_data[user_id] and bot.user_data[user_id]["action"] == "editing":
        modification_request = message.text
        code = bot.user_data[user_id]["code"]
        original_file_name = bot.user_data[user_id]["file_name"]
        
        bot.send_message(message.chat.id, "⏳ جاري تعديل الملف باستخدام الذكاء الاصطناعي...")
        
        # تعديل الكود باستخدام Gemini AI
        modified_code = modify_python_file(code, modification_request)
        
        if modified_code:
            # حفظ الملف المعدل
            timestamp = int(time.time())
            new_file_name = f"modified_{timestamp}.py"
            file_path = f"temp_files/{new_file_name}"
            
            with open(file_path, 'w') as f:
                f.write(modified_code)
            
            # حفظ المعلومات في التخزين
            file_storage[new_file_name] = {
                "path": file_path,
                "content": modified_code,
                "created_at": datetime.now().isoformat(),
                "created_by": message.from_user.id,
                "modified_from": original_file_name
            }
            save_file_list()
            
            # إرسال الملف المعدل
            with open(file_path, 'rb') as f:
                # إنشاء أزرار التشغيل والتعديل
                keyboard = InlineKeyboardMarkup()
                emoji_run = random_emoji()
                emoji_edit = random_emoji()
                keyboard.add(
                    InlineKeyboardButton(f"{emoji_run} تشغيل (15 دقيقة)", callback_data=f"run_{new_file_name}"),
                    InlineKeyboardButton(f"{emoji_edit} تعديل", callback_data=f"edit_{new_file_name}")
                )
                keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
                
                sent_message = bot.send_document(message.chat.id, f, caption="✅ تم تعديل الملف بنجاح", reply_markup=keyboard)
            
            # إرسال الملف المعدل إلى القناة
            try:
                with open(file_path, 'rb') as f:
                    channel_message = bot.send_document(CHANNEL_ID, f, caption=f"تم تعديل الملف: {new_file_name} من {original_file_name} بواسطة {message.from_user.first_name}")
                    file_storage[new_file_name]["message_id"] = channel_message.message_id
                    save_file_list()
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
            
            # تنظيف البيانات المؤقتة
            del bot.user_data[user_id]
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعديل الملف. يرجى المحاولة مرة أخرى.", reply_markup=create_main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على بيانات التعديل. يرجى البدء من جديد.", reply_markup=create_main_keyboard())

# بدء البوت
if __name__ == "__main__":
    # تحميل قائمة الملفات عند البدء
    load_file_list()
    print("🤖 البوت النهائي يعمل الآن...")
    bot.infinity_polling()
