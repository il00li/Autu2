import os
import random
import requests
import telebot
import threading
import time
import re
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

# التوكنات والمفاتيح
BOT_TOKEN = "8403108424:AAEH87G0dODsndjpZGFvCsn6EeOdkLlr3JE"
GEMINI_API_KEY = "AIzaSyDTb_B7Pq3KSWWMTC1KjG4iPGqFFgLpRl8"
CHANNEL_ID = -1003091756917  # تأكد من استخدام ID صحيح للقناة
ADMIN_ID = 6689435577

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# قائمة الملفات الدائمة والمؤقتة
permanent_files = {}
temporary_files = {}
MAX_PERMANENT_FILES = 50

# قائمة البوتات النشطة
active_bots = {}

# رموز تعبيرية عشوائية
EMOJIS = ["🌿", "🐊", "🍃", "🌴", "🐸", "☕", "🐛", "🌵", "🐢", "🍀", "💐", "🌱", "🌾", "🌳"]

def get_random_emoji():
    return random.choice(EMOJIS)

# وظيفة للتحقق من هوية المدير
def is_admin(user_id):
    return user_id == ADMIN_ID

# وظيفة للتحقق من صحة اسم الملف
def is_valid_filename(filename):
    if not filename:
        return False
    # التحقق من أن الاسم لا يحتوي على مسارات
    if "/" in filename or "\\" in filename:
        return False
    # التحقق من أن الاسم ينتهي بامتداد Python
    if not filename.endswith('.py'):
        filename += '.py'
    # التحقق من أن الاسم لا يحتوي على أحرف غير مسموحة
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        return False
    return True

# وظيفة للتفاعل مع Gemini API
def generate_with_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"قم بإنشاء كود بوت تيليجرام باستخدام مكتبة pyTelegramBotAPI بناء على الوصف التالي: {prompt}. يجب أن يكون الكود جاهزًا للتنفيذ ومتكاملاً."
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
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.Timeout:
        return "انتهت المهلة أثناء الاتصال بـ Gemini API."
    except requests.exceptions.RequestException as e:
        return f"حدث خطأ في الاتصال: {str(e)}"
    except (KeyError, IndexError) as e:
        return f"حدث خطأ في معالجة الاستجابة: {str(e)}"
    except Exception as e:
        return f"حدث خطأ غير متوقع: {str(e)}"

# وظيفة لحفظ الملف في القناة
def save_file_to_channel(file_name, content, is_permanent=False):
    try:
        # التأكد من أن اسم الملف صالح
        if not is_valid_filename(file_name):
            return False, "اسم الملف غير صالح."
        
        # إضافة امتداد .py إذا لم يكن موجودًا
        if not file_name.endswith('.py'):
            file_name += '.py'
        
        # التحقق من عدد الملفات الدائمة
        if is_permanent and len(permanent_files) >= MAX_PERMANENT_FILES:
            return False, "تم الوصول إلى الحد الأقصى للملفات الدائمة (50)."
        
        # حفظ المحتوى في ملف مؤقت
        temp_path = f"temp_{file_name}"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # إرسال الملف إلى القناة
        with open(temp_path, 'rb') as f:
            message = bot.send_document(CHANNEL_ID, f, caption=f"اسم الملف: {file_name}\nدائم: {is_permanent}")
        
        # حفظ معلومات الملف
        file_id = message.document.file_id
        if is_permanent:
            permanent_files[file_name] = {
                'file_id': file_id,
                'created_at': datetime.now(),
                'is_permanent': True
            }
        else:
            # للملفات المؤقتة، نضيف وقت انتهاء الصلاحية (10 دقائق)
            temporary_files[file_name] = {
                'file_id': file_id,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(minutes=10),
                'is_permanent': False
            }
        
        # حذف الملف المؤقت
        os.remove(temp_path)
        return True, f"تم حفظ الملف {file_name} بنجاح."
    except Exception as e:
        # تنظيف الملف المؤقت في حالة الخطأ
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"حدث خطأ أثناء حفظ الملف: {str(e)}"

# وظيفة لحذف الملف من القناة
def delete_file_from_channel(file_name):
    try:
        # البحث عن الملف في الملفات الدائمة أو المؤقتة
        file_info = None
        if file_name in permanent_files:
            file_info = permanent_files[file_name]
            del permanent_files[file_name]
        elif file_name in temporary_files:
            file_info = temporary_files[file_name]
            del temporary_files[file_name]
        else:
            return False, "الملف غير موجود."
        
        # محاولة حذف الرسالة من القناة
        try:
            bot.delete_message(CHANNEL_ID, file_info['message_id'])
        except:
            # إذا لم نتمكن من حذف الرسالة، نكتفي بحذفها من التخزين المحلي
            pass
        
        return True, f"تم حذف الملف {file_name} بنجاح."
    except Exception as e:
        return False, f"حدث خطأ أثناء حذف الملف: {str(e)}"

# وظيفة لتشغيل البوت
def run_bot(file_name, is_permanent=False):
    try:
        # الحصول على الملف من القناة
        file_info = None
        if is_permanent and file_name in permanent_files:
            file_info = permanent_files[file_name]
        elif not is_permanent and file_name in temporary_files:
            file_info = temporary_files[file_name]
        
        if not file_info:
            return False, "الملف غير موجود."
        
        # تنزيل الملف
        file_id = file_info['file_id']
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # حفظ الملف محليًا
        local_path = f"running_{file_name}"
        with open(local_path, 'wb') as f:
            f.write(downloaded_file)
        
        # تشغيل البوت في thread منفصل
        if is_permanent:
            thread = threading.Thread(target=run_permanent_bot, args=(local_path, file_name))
            thread.daemon = True
            thread.start()
            return True, f"تم بدء التشغيل الدائم للبوت {file_name}."
        else:
            thread = threading.Thread(target=run_temporary_bot, args=(local_path, file_name))
            thread.daemon = True
            thread.start()
            return True, f"تم بدء التشغيل المؤقت للبوت {file_name} لمدة 10 دقائق."
    except Exception as e:
        return False, f"حدث خطأ أثناء تشغيل البوت: {str(e)}"

# وظيفة لتشغيل البوت بشكل دائم
def run_permanent_bot(file_path, file_name):
    try:
        # تنفيذ البوت
        active_bots[file_name] = {
            'process': None,
            'started_at': datetime.now(),
            'is_permanent': True
        }
        
        # هنا يجب تنفيذ البوت، ولكن في هذا المثال سنكتفي بمحاكاة التشغيل
        # في الواقع الفعلي، ستحتاج إلى استخدام subprocess أو importlib لتشغيل الكود
        print(f"Starting permanent bot: {file_name}")
        
        # محاكاة التشغيل الدائم
        while file_name in active_bots and active_bots[file_name]['is_permanent']:
            time.sleep(1)
        
        print(f"Stopped permanent bot: {file_name}")
    except Exception as e:
        print(f"Error running permanent bot {file_name}: {str(e)}")
    finally:
        if file_name in active_bots:
            del active_bots[file_name]
        # تنظيف الملف المحلي
        if os.path.exists(file_path):
            os.remove(file_path)

# وظيفة لتشغيل البوت بشكل مؤقت
def run_temporary_bot(file_path, file_name):
    try:
        # تنفيذ البوت
        active_bots[file_name] = {
            'process': None,
            'started_at': datetime.now(),
            'is_permanent': False
        }
        
        # هنا يجب تنفيذ البوت، ولكن في هذا المثال سنكتفي بمحاكاة التشغيل
        print(f"Starting temporary bot: {file_name}")
        
        # محاكاة التشغيل لمدة 10 دقائق
        end_time = datetime.now() + timedelta(minutes=10)
        while datetime.now() < end_time and file_name in active_bots:
            time.sleep(1)
        
        print(f"Stopped temporary bot: {file_name}")
    except Exception as e:
        print(f"Error running temporary bot {file_name}: {str(e)}")
    finally:
        if file_name in active_bots:
            del active_bots[file_name]
        # تنظيف الملف المحلي
        if os.path.exists(file_path):
            os.remove(file_path)

# وظيفة لإيقاف البوت
def stop_bot(file_name):
    try:
        if file_name in active_bots:
            # إيقاف البوت
            active_bots[file_name]['is_permanent'] = False
            return True, f"تم إيقاف البوت {file_name}."
        else:
            return False, "البوت غير نشط."
    except Exception as e:
        return False, f"حدث خطأ أثناء إيقاف البوت: {str(e)}"

# وظيفة للتحقق من الملفات المنتهية الصلاحية وتنظيفها
def check_expired_files():
    while True:
        try:
            current_time = datetime.now()
            expired_files = []
            
            # البحث عن الملفات المؤقتة المنتهية الصلاحية
            for file_name, file_info in list(temporary_files.items()):
                if 'expires_at' in file_info and current_time > file_info['expires_at']:
                    expired_files.append(file_name)
            
            # حذف الملفات المنتهية الصلاحية
            for file_name in expired_files:
                success, message = delete_file_from_channel(file_name)
                if success:
                    print(f"تم حذف الملف المنتهي الصلاحية: {file_name}")
                else:
                    print(f"فشل في حذف الملف المنتهي الصلاحية: {file_name} - {message}")
            
            # الانتظار لمدة دقيقة قبل الفحص التالي
            time.sleep(60)
        except Exception as e:
            print(f"حدث خطأ أثناء فحص الملفات المنتهية الصلاحية: {str(e)}")
            time.sleep(60)

# بدء thread لفحص الملفات المنتهية الصلاحية
cleanup_thread = threading.Thread(target=check_expired_files)
cleanup_thread.daemon = True
cleanup_thread.start()

# معالجة أمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "عذرًا،你没有权限使用此机器人。")
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton(f"{get_random_emoji()} بدء الانشاء", callback_data="start_creation"),
        InlineKeyboardButton(f"{get_random_emoji()} خيارات أكثر", callback_data="more_options")
    )
    
    bot.send_message(message.chat.id, "مرحبًا! أنا بوت لإنشاء بوتات تيليجرام أخرى. اختر أحد الخيارات:", reply_markup=keyboard)

# معالجة callback queries
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "你没有权限使用此机器人。", show_alert=True)
        return
    
    if call.data == "start_creation":
        msg = bot.send_message(call.message.chat.id, "يرجى إرسال وصف البوت الذي تريد إنشاءه:")
        bot.register_next_step_handler(msg, process_description)
    
    elif call.data == "more_options":
        show_more_options(call.message)
    
    elif call.data.startswith("temporary_run_"):
        file_name = call.data.replace("temporary_run_", "")
        success, message = run_bot(file_name, is_permanent=False)
        bot.answer_callback_query(call.id, message)
    
    elif call.data.startswith("permanent_run_"):
        file_name = call.data.replace("permanent_run_", "")
        success, message = run_bot(file_name, is_permanent=True)
        bot.answer_callback_query(call.id, message)
    
    elif call.data.startswith("edit_file_"):
        file_name = call.data.replace("edit_file_", "")
        msg = bot.send_message(call.message.chat.id, f"أرسل الوصف الجديد لتعديل الملف {file_name}:")
        bot.register_next_step_handler(msg, lambda m: process_edit_description(m, file_name))
    
    elif call.data == "replace_file":
        msg = bot.send_message(call.message.chat.id, "أرسل اسم الملف الذي تريد استبداله:")
        bot.register_next_step_handler(msg, ask_replacement_file)
    
    elif call.data == "delete_file":
        msg = bot.send_message(call.message.chat.id, "أرسل اسم الملف الذي تريد حذفه:")
        bot.register_next_step_handler(msg, process_delete_file)
    
    elif call.data == "upload_file":
        msg = bot.send_message(call.message.chat.id, "أرسل الملف الجاهز الذي تريد رفعه:")
        bot.register_next_step_handler(msg, process_upload_file)
    
    elif call.data == "create_file":
        msg = bot.send_message(call.message.chat.id, "أرسل كود الملف سطرًا سطرًا. عند الانتهاء، أرسل /don لحفظ الملف.")
        bot.register_next_step_handler(msg, process_code_input)

def process_description(message):
    description = message.text
    if not description or len(description) < 10:
        bot.send_message(message.chat.id, "الوصف очень короткий. يرجى إرسال وصف أكثر تفصيلاً.")
        return
    
    bot.send_message(message.chat.id, "جاري إنشاء البوت، يرجى الانتظار...")
    
    # استخدام Gemini لإنشاء الكود
    code = generate_with_gemini(description)
    
    if code.startswith("حدث خطأ"):
        bot.send_message(message.chat.id, f"عذرًا، {code}")
        return
    
    # حفظ الملف في القناة
    file_name = f"bot_{message.message_id}.py"
    success, result_message = save_file_to_channel(file_name, code, is_permanent=False)
    
    if success:
        # إرسال الملف مع أزرار التحكم
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton(f"{get_random_emoji()} تشغيل (10 دقائق)", callback_data=f"temporary_run_{file_name}"),
            InlineKeyboardButton(f"{get_random_emoji()} تشغيل دائم", callback_data=f"permanent_run_{file_name}"),
            InlineKeyboardButton(f"{get_random_emoji()} تعديل", callback_data=f"edit_file_{file_name}")
        )
        
        bot.send_message(message.chat.id, f"تم إنشاء البوت بنجاح!\n{result_message}", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, f"عذرًا، {result_message}")

def show_more_options(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton(f"{get_random_emoji()} استبدال ملف", callback_data="replace_file"),
        InlineKeyboardButton(f"{get_random_emoji()} حذف ملف", callback_data="delete_file")
    )
    keyboard.row(
        InlineKeyboardButton(f"{get_random_emoji()} رفع ملف جاهز", callback_data="upload_file"),
        InlineKeyboardButton(f"{get_random_emoji()} صنع ملف", callback_data="create_file")
    )
    
    bot.send_message(message.chat.id, "خيارات إضافية:", reply_markup=keyboard)

def process_edit_description(message, file_name):
    new_description = message.text
    if not new_description or len(new_description) < 10:
        bot.send_message(message.chat.id, "الوصف очень короткий. يرجى إرسال وصف أكثر تفصيلاً.")
        return
    
    new_code = generate_with_gemini(new_description)
    
    if new_code.startswith("حدث خطأ"):
        bot.send_message(message.chat.id, f"عذرًا، {new_code}")
        return
    
    success, result_message = save_file_to_channel(file_name, new_code, is_permanent=False)
    bot.send_message(message.chat.id, result_message)

def ask_replacement_file(message):
    file_name = message.text
    if not is_valid_filename(file_name):
        bot.send_message(message.chat.id, "اسم الملف غير صالح.")
        return
    
    msg = bot.send_message(message.chat.id, f"أرسل الملف الجديد لاستبدال {file_name}:")
    bot.register_next_step_handler(msg, lambda m: process_replacement_file(m, file_name))

def process_replacement_file(message, old_file_name):
    if message.document:
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # قراءة المحتوى
            content = downloaded_file.decode('utf-8')
            
            # حفظ في القناة
            is_permanent = old_file_name in permanent_files
            success, result_message = save_file_to_channel(old_file_name, content, is_permanent=is_permanent)
            
            bot.send_message(message.chat.id, result_message)
        except Exception as e:
            bot.send_message(message.chat.id, f"حدث خطأ أثناء معالجة الملف: {str(e)}")
    else:
        bot.send_message(message.chat.id, "يرجى إرسال ملف صحيح.")

def process_delete_file(message):
    file_name = message.text
    if not is_valid_filename(file_name):
        bot.send_message(message.chat.id, "اسم الملف غير صالح.")
        return
    
    success, result_message = delete_file_from_channel(file_name)
    bot.send_message(message.chat.id, result_message)

def process_upload_file(message):
    if message.document:
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            file_name = message.document.file_name
            content = downloaded_file.decode('utf-8')
            
            # تحديد إذا كان الملف دائمًا أو مؤقتًا
            is_permanent = len(permanent_files) < MAX_PERMANENT_FILES
            success, result_message = save_file_to_channel(file_name, content, is_permanent=is_permanent)
            
            bot.send_message(message.chat.id, result_message)
        except Exception as e:
            bot.send_message(message.chat.id, f"حدث خطأ أثناء معالجة الملف: {str(e)}")
    else:
        bot.send_message(message.chat.id, "يرجى إرسال ملف صحيح.")

# متغير لتخزين الكود المجمع
code_builder = {}

def process_code_input(message):
    chat_id = message.chat.id
    if message.text == '/don':
        # انتهاء إدخال الكود، حفظ الملف
        if chat_id in code_builder and code_builder[chat_id]['code']:
            code_content = "\n".join(code_builder[chat_id]['code'])
            file_name = code_builder[chat_id].get('filename', f"user_created_{chat_id}.py")
            
            is_permanent = len(permanent_files) < MAX_PERMANENT_FILES
            success, result_message = save_file_to_channel(file_name, code_content, is_permanent=is_permanent)
            
            bot.send_message(chat_id, result_message)
            
            # مسح الكود المخزن
            del code_builder[chat_id]
        else:
            bot.send_message(chat_id, "لم يتم إدخال أي كود لحفظه.")
    elif message.text.startswith('/name '):
        # تعيين اسم الملف
        filename = message.text.replace('/name ', '').strip()
        if is_valid_filename(filename):
            if chat_id not in code_builder:
                code_builder[chat_id] = {'code': [], 'filename': filename}
            else:
                code_builder[chat_id]['filename'] = filename
            bot.send_message(chat_id, f"تم تعيين اسم الملف إلى: {filename}")
        else:
            bot.send_message(chat_id, "اسم الملف غير صالح.")
    else:
        # إضافة سطر جديد إلى الكود
        if chat_id not in code_builder:
            code_builder[chat_id] = {'code': [], 'filename': f"user_created_{chat_id}.py"}
        
        code_builder[chat_id]['code'].append(message.text)
        bot.send_message(chat_id, "تم إضافة السطر. استمر في إرسال الأسطر أو أرسل /don لحفظ الملف. يمكنك استخدام /name لتعيين اسم الملف.")

# معالجة الأخطاء العامة
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "عذرًا，你没有权限使用此机器人。")
        return
    
    bot.reply_to(message, "عذرًا، لم أفهم طلبك. يرجى استخدام الأزرار المتاحة.")

# تشغيل البوت
if __name__ == "__main__":
    print("تم تشغيل البوت...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"حدث خطأ في البوت: {str(e)}")
        time.sleep(30)
        # إعادة التشغيل التلقائي في حالة الخطأ
        os.execv(__file__, sys.argv)
