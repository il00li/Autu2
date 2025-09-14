import os
import requests
import telebot
import subprocess
import threading
import time
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

# دالة للحصول على رمز تعبيري عشوائي
def random_emoji():
    import random
    return random.choice(EMOJIS)

# دالة لتشغيل البوت لمدة 15 دقيقة
def run_bot_for_15_minutes(file_path, message):
    try:
        # تشغيل البوت
        process = subprocess.Popen(['python', file_path], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
        
        # الانتظار لمدة 15 دقيقة
        time.sleep(900)
        
        # إنهاء العملية بعد 15 دقيقة
        process.terminate()
        bot.send_message(message.chat.id, "⏰ انتهت مدة التشغيل (15 دقيقة)")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ أثناء التشغيل: {str(e)}")

# التحقق من هوية المدير
def is_admin(user_id):
    return user_id == ADMIN_ID

# معالج الأمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    emoji1 = random_emoji()
    emoji2 = random_emoji()
    emoji3 = random_emoji()
    emoji4 = random_emoji()
    
    keyboard.add(
        InlineKeyboardButton(f"{emoji1} إنشاء بوت جديد", callback_data="create_bot"),
        InlineKeyboardButton(f"{emoji2} رفع ملف جاهز", callback_data="upload_file")
    )
    keyboard.add(
        InlineKeyboardButton(f"{emoji3} حذف ملف", callback_data="delete_file"),
        InlineKeyboardButton(f"{emoji4} استبدال ملف", callback_data="replace_file")
    )
    
    bot.send_message(message.chat.id, "مرحباً! اختر أحد الخيارات:", reply_markup=keyboard)

# معالج استدعاء الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    if call.data == "create_bot":
        msg = bot.send_message(call.message.chat.id, "📝 أرسل وصفاً للبوت الذي تريد إنشاءه:")
        bot.register_next_step_handler(msg, process_bot_creation)
    
    elif call.data == "upload_file":
        msg = bot.send_message(call.message.chat.id, "📤 أرسل ملف Python الجاهز:")
        bot.register_next_step_handler(msg, process_file_upload)
    
    elif call.data == "delete_file":
        # هنا يمكن إضافة منطق لعرض الملفات المتاحة للحذف
        bot.send_message(call.message.chat.id, "⚠️ هذه الميزة قيد التطوير")
    
    elif call.data == "replace_file":
        # هنا يمكن إضافة منطق لعرض الملفات المتاحة للاستبدال
        bot.send_message(call.message.chat.id, "⚠️ هذه الميزة قيد التطوير")
    
    elif call.data.startswith("run_"):
        file_name = call.data[4:]
        file_path = f"temp_files/{file_name}"
        
        # إرسال رسالة بدء التشغيل
        bot.send_message(call.message.chat.id, "⏳ جاري تشغيل البوت لمدة 15 دقيقة...")
        
        # تشغيل البوت في thread منفصل
        thread = threading.Thread(target=run_bot_for_15_minutes, args=(file_path, call.message))
        thread.start()
    
    elif call.data.startswith("edit_"):
        file_name = call.data[5:]
        file_path = f"temp_files/{file_name}"
        
        # قراءة المحتوى الحالي
        with open(file_path, 'r') as f:
            code = f.read()
        
        # حفظ المحتوى مؤقتاً للاستخدام لاحقاً
        bot.user_data[call.from_user.id] = {"action": "editing", "file_name": file_name, "code": code}
        
        msg = bot.send_message(call.message.chat.id, "✏️ ما التعديلات التي تريد إجراؤها على الملف؟")
        bot.register_next_step_handler(msg, process_edit_request)

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
            
            bot.send_document(message.chat.id, f, caption="✅ تم إنشاء البوت بنجاح", reply_markup=keyboard)
        
        # إرسال الملف إلى القناة
        try:
            with open(file_path, 'rb') as f:
                bot.send_document(CHANNEL_ID, f, caption=f"تم إنشاء البوت بواسطة {message.from_user.first_name}")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
    else:
        bot.send_message(message.chat.id, "❌ فشل في إنشاء البوت. يرجى المحاولة مرة أخرى.")

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
            
            # إنشاء زر التشغيل
            keyboard = InlineKeyboardMarkup()
            emoji_run = random_emoji()
            emoji_edit = random_emoji()
            keyboard.add(
                InlineKeyboardButton(f"{emoji_run} تشغيل (15 دقيقة)", callback_data=f"run_{file_name}"),
                InlineKeyboardButton(f"{emoji_edit} تعديل", callback_data=f"edit_{file_name}")
            )
            
            bot.send_message(message.chat.id, "✅ تم رفع الملف بنجاح", reply_markup=keyboard)
            
            # إرسال الملف إلى القناة
            try:
                with open(file_path, 'rb') as f:
                    bot.send_document(CHANNEL_ID, f, caption=f"تم رفع الملف بواسطة {message.from_user.first_name}")
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
        else:
            bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python فقط (امتداد .py)")
    else:
        bot.send_message(message.chat.id, "❌ يرجى رفع ملف Python")

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
                
                bot.send_document(message.chat.id, f, caption="✅ تم تعديل الملف بنجاح", reply_markup=keyboard)
            
            # إرسال الملف المعدل إلى القناة
            try:
                with open(file_path, 'rb') as f:
                    bot.send_document(CHANNEL_ID, f, caption=f"تم تعديل الملف بواسطة {message.from_user.first_name}")
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ لم أتمكن من إرسال الملف إلى القناة: {str(e)}")
            
            # تنظيف البيانات المؤقتة
            del bot.user_data[user_id]
        else:
            bot.send_message(message.chat.id, "❌ فشل في تعديل الملف. يرجى المحاولة مرة أخرى.")
    else:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على بيانات التعديل. يرجى البدء من جديد.")

# بدء البوت
if __name__ == "__main__":
    print("البوت يعمل...")
    bot.infinity_polling() 
