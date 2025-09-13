import os
import random
import requests
import telebot
import threading
import time
import re
import sys
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# التوكنات والمفاتيح
BOT_TOKEN = "8403108424:AAGTGpE8tHiEXid6Hr11hjNzu-PdaZx8H9w"
GEMINI_API_KEY = "AIzaSyDTb_B7Pq3KSWWMTC1KjG4iPGqFFgLpRl8"
CHANNEL_ID = -1003091756917
ADMIN_ID = 6689435577

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# قوائم الملفات والبوتات النشطة
permanent_files = {}
temporary_files = {}
active_bots = {}
MAX_PERMANENT_FILES = 50

# رموز تعبيرية عشوائية
EMOJIS = ["🌿", "🐊", "🍃", "🌴", "🐸", "☕", "🐛", "🌵", "🐢", "🍀", "💐", "🌱", "🌾", "🌳"]

def get_random_emoji():
    return random.choice(EMOJIS)

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_valid_filename(filename):
    if not filename:
        return False
    if "/" in filename or "\\" in filename:
        return False
    if not filename.endswith('.py'):
        filename += '.py'
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        return False
    return True

def generate_with_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    # تعليمات أكثر تحديدًا للحصول على كود جاهز للتشغيل بدون تعليقات زائدة
    enhanced_prompt = f"""
    قم بإنشاء كود بوت تيليجرام باستخدام مكتبة pyTelegramBotAPI بناء على الوصف التالي: {prompt}.
    
    المتطلبات:
    1. يجب أن يكون الكود جاهزًا للتنفيذ ومتكاملاً
    2. لا تضع تعليقات زائدة أو شروحات غير ضرورية
    3. تأكد من أن الكود يعمل مباشرة بدون أخطاء
    4. تأكد من تضمين جميع المكتبات المطلوبة
    5. استخدم أفضل الممارسات في كتابة الكود
    6. تأكد من أن البوت يعمل فور تشغيله
    """
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": enhanced_prompt
                    }
                ]
            }
        ]
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        # زيادة مدة الانتظار إلى 10 دقائق (600 ثانية)
        response = requests.post(url, json=payload, headers=headers, timeout=600)
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"حدث خطأ أثناء توليد الكود: {str(e)}"

def save_file_to_channel(file_name, content, is_permanent=False):
    try:
        if not is_valid_filename(file_name):
            return False, "اسم الملف غير صالح."
        
        if not file_name.endswith('.py'):
            file_name += '.py'
        
        if is_permanent and len(permanent_files) >= MAX_PERMANENT_FILES:
            return False, "تم الوصول إلى الحد الأقصى للملفات الدائمة (50)."
        
        temp_path = f"temp_{file_name}"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        with open(temp_path, 'rb') as f:
            message = bot.send_document(CHANNEL_ID, f, caption=f"اسم الملف: {file_name}\nدائم: {is_permanent}")
        
        file_id = message.document.file_id
        message_id = message.message_id
        
        if is_permanent:
            permanent_files[file_name] = {
                'file_id': file_id,
                'message_id': message_id,
                'created_at': datetime.now(),
                'is_permanent': True
            }
        else:
            temporary_files[file_name] = {
                'file_id': file_id,
                'message_id': message_id,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(minutes=10),
                'is_permanent': False
            }
        
        os.remove(temp_path)
        return True, file_name
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"حدث خطأ أثناء حفظ الملف: {str(e)}"

def delete_file_from_channel(file_name):
    try:
        file_info = None
        source = None
        
        if file_name in permanent_files:
            file_info = permanent_files[file_name]
            del permanent_files[file_name]
            source = "permanent"
        elif file_name in temporary_files:
            file_info = temporary_files[file_name]
            del temporary_files[file_name]
            source = "temporary"
        else:
            return False, "الملف غير موجود."
        
        try:
            bot.delete_message(CHANNEL_ID, file_info['message_id'])
        except:
            pass
        
        if file_name in active_bots:
            active_bots[file_name]['is_running'] = False
            del active_bots[file_name]
        
        return True, f"تم حذف الملف {file_name} بنجاح."
    except Exception as e:
        return False, f"حدث خطأ أثناء حذف الملف: {str(e)}"

def run_bot(file_name, is_permanent=False):
    try:
        file_info = None
        if is_permanent and file_name in permanent_files:
            file_info = permanent_files[file_name]
        elif not is_permanent and file_name in temporary_files:
            file_info = temporary_files[file_name]
        
        if not file_info:
            return False, "الملف غير موجود."
        
        file_id = file_info['file_id']
        file_info_obj = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info_obj.file_path)
        
        local_path = f"running_{file_name}"
        with open(local_path, 'wb') as f:
            f.write(downloaded_file)
        
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

def run_permanent_bot(file_path, file_name):
    try:
        active_bots[file_name] = {
            'process': None,
            'started_at': datetime.now(),
            'is_running': True
        }
        
        print(f"Starting permanent bot: {file_name}")
        
        while file_name in active_bots and active_bots[file_name]['is_running']:
            time.sleep(1)
        
        print(f"Stopped permanent bot: {file_name}")
    except Exception as e:
        print(f"Error running permanent bot {file_name}: {str(e)}")
    finally:
        if file_name in active_bots:
            del active_bots[file_name]
        if os.path.exists(file_path):
            os.remove(file_path)

def run_temporary_bot(file_path, file_name):
    try:
        active_bots[file_name] = {
            'process': None,
            'started_at': datetime.now(),
            'is_running': True
        }
        
        print(f"Starting temporary bot: {file_name}")
        
        end_time = datetime.now() + timedelta(minutes=10)
        while datetime.now() < end_time and file_name in active_bots and active_bots[file_name]['is_running']:
            time.sleep(1)
        
        print(f"Stopped temporary bot: {file_name}")
    except Exception as e:
        print(f"Error running temporary bot {file_name}: {str(e)}")
    finally:
        if file_name in active_bots:
            del active_bots[file_name]
        if os.path.exists(file_path):
            os.remove(file_path)

def stop_bot(file_name):
    try:
        if file_name in active_bots:
            active_bots[file_name]['is_running'] = False
            return True, f"تم إيقاف البوت {file_name}."
        else:
            return False, "البوت غير نشط."
    except Exception as e:
        return False, f"حدث خطأ أثناء إيقاف البوت: {str(e)}"

def check_expired_files():
    while True:
        try:
            current_time = datetime.now()
            expired_files = []
            
            for file_name, file_info in list(temporary_files.items()):
                if 'expires_at' in file_info and current_time > file_info['expires_at']:
                    expired_files.append(file_name)
            
            for file_name in expired_files:
                success, message = delete_file_from_channel(file_name)
                if success:
                    print(f"تم حذف الملف المنتهي الصلاحية: {file_name}")
                else:
                    print(f"فشل في حذف الملف المنتهي الصلاحية: {file_name} - {message}")
            
            time.sleep(60)
        except Exception as e:
            print(f"حدث خطأ أثناء فحص الملفات المنتهية الصلاحية: {str(e)}")
            time.sleep(60)

cleanup_thread = threading.Thread(target=check_expired_files)
cleanup_thread.daemon = True
cleanup_thread.start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "عذرًا，你没有权限使用此机器人。")
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} بدء الانشاء", callback_data="start_creation"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} خيارات أكثر", callback_data="more_options"))
    
    bot.send_message(message.chat.id, "مرحبًا! أنا بوت لإنشاء بوتات تيليجرام أخرى. اختر أحد الخيارات:", reply_markup=keyboard)

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
    
    elif call.data.startswith("stop_bot_"):
        file_name = call.data.replace("stop_bot_", "")
        success, message = stop_bot(file_name)
        bot.answer_callback_query(call.id, message)
    
    elif call.data.startswith("delete_file_"):
        file_name = call.data.replace("delete_file_", "")
        success, message = delete_file_from_channel(file_name)
        bot.answer_callback_query(call.id, message)
        if success:
            bot.send_message(call.message.chat.id, message)
    
    elif call.data == "replace_file":
        msg = bot.send_message(call.message.chat.id, "أرسل اسم الملف الذي تريد استبداله:")
        bot.register_next_step_handler(msg, ask_replacement_file)
    
    elif call.data == "delete_file_menu":
        show_delete_menu(call.message)
    
    elif call.data == "upload_file":
        msg = bot.send_message(call.message.chat.id, "أرسل الملف الجاهز الذي تريد رفعه:")
        bot.register_next_step_handler(msg, process_upload_file)
    
    elif call.data == "create_file":
        msg = bot.send_message(call.message.chat.id, "أرسل كود الملف سطرًا سطرًا. عند الانتهاء، أرسل /don لحفظ الملف.")
        bot.register_next_step_handler(msg, process_code_input)
    
    elif call.data == "list_files":
        show_files_list(call.message)
    
    elif call.data == "list_active_bots":
        show_active_bots_list(call.message)

def process_description(message):
    if not message.text or len(message.text) < 10:
        bot.send_message(message.chat.id, "الوصف очень короткий. يرجى إرسال وصف أكثر تفصيلاً.")
        return
    
    bot.send_message(message.chat.id, "جاري إنشاء البوت، يرجى الانتظار... (قد تستغرق العملية حتى 10 دقائق)")
    
    code = generate_with_gemini(message.text)
    
    if code.startswith("حدث خطأ"):
        bot.send_message(message.chat.id, f"عذرًا، {code}")
        return
    
    file_name = f"bot_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    success, result = save_file_to_channel(file_name, code, is_permanent=False)
    
    if success:
        # إرسال الملف للمدير مع أزرار التشغيل
        file_info = bot.get_file(permanent_files[file_name]['file_id'] if file_name in permanent_files else temporary_files[file_name]['file_id'])
        downloaded_file = bot.download_file(file_info.file_path)
        
        # حفظ مؤقت لإرساله للمستخدم
        temp_path = f"temp_send_{file_name}"
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file)
        
        with open(temp_path, 'rb') as f:
            # إنشاء أزرار التشغيل
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل مؤقت (10 دقائق)", callback_data=f"temporary_run_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل دائم", callback_data=f"permanent_run_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تعديل", callback_data=f"edit_file_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} إيقاف", callback_data=f"stop_bot_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف", callback_data=f"delete_file_{file_name}"))
            
            bot.send_document(message.chat.id, f, caption=f"تم إنشاء البوت بنجاح!\nاسم الملف: {file_name}", reply_markup=keyboard)
        
        os.remove(temp_path)
    else:
        bot.send_message(message.chat.id, f"عذرًا، {result}")

def show_more_options(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} استبدال ملف", callback_data="replace_file"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف ملف", callback_data="delete_file_menu"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} رفع ملف جاهز", callback_data="upload_file"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} صنع ملف", callback_data="create_file"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} عرض الملفات", callback_data="list_files"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} عرض البوتات النشطة", callback_data="list_active_bots"))
    
    bot.send_message(message.chat.id, "خيارات إضافية:", reply_markup=keyboard)

def show_delete_menu(message):
    keyboard = InlineKeyboardMarkup()
    
    # إضافة أزرار لحذف الملفات المؤقتة
    for file_name in list(temporary_files.keys())[:10]:  # عرض أول 10 ملفات فقط
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف {file_name}", callback_data=f"delete_file_{file_name}"))
    
    # إضافة أزرار لحذف الملفات الدائمة
    for file_name in list(permanent_files.keys())[:10]:  # عرض أول 10 ملفات فقط
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف {file_name}", callback_data=f"delete_file_{file_name}"))
    
    bot.send_message(message.chat.id, "اختر الملف الذي تريد حذفه:", reply_markup=keyboard)

def show_files_list(message):
    files_text = "📁 الملفات المؤقتة:\n"
    
    if temporary_files:
        for file_name, file_info in temporary_files.items():
            files_text += f"• {file_name} (ينتهي: {file_info['expires_at'].strftime('%Y-%m-%d %H:%M')})\n"
    else:
        files_text += "لا توجد ملفات مؤقتة\n"
    
    files_text += "\n📁 الملفات الدائمة:\n"
    
    if permanent_files:
        for file_name, file_info in permanent_files.items():
            files_text += f"• {file_name} (أنشئ: {file_info['created_at'].strftime('%Y-%m-%d %H:%M')})\n"
    else:
        files_text += "لا توجد ملفات دائمة\n"
    
    bot.send_message(message.chat.id, files_text)

def show_active_bots_list(message):
    if not active_bots:
        bot.send_message(message.chat.id, "لا توجد بوتات نشطة حالياً.")
        return
    
    bots_text = "🤖 البوتات النشطة:\n"
    
    for file_name, bot_info in active_bots.items():
        bot_type = "دائم" if bot_info.get('is_permanent', False) else "مؤقت"
        bots_text += f"• {file_name} ({bot_type}) - يعمل منذ: {bot_info['started_at'].strftime('%Y-%m-%d %H:%M')}\n"
    
    bot.send_message(message.chat.id, bots_text)

def process_edit_description(message, file_name):
    if not message.text or len(message.text) < 10:
        bot.send_message(message.chat.id, "الوصف очень короткий. يرجى إرسال وصف أكثر تفصيلاً.")
        return
    
    new_code = generate_with_gemini(message.text)
    
    if new_code.startswith("حدث خطأ"):
        bot.send_message(message.chat.id, f"عذرًا، {new_code}")
        return
    
    is_permanent = file_name in permanent_files
    success, result = save_file_to_channel(file_name, new_code, is_permanent=is_permanent)
    
    if success:
        # إرسال الملف المعدل للمدير
        file_info = bot.get_file(permanent_files[file_name]['file_id'] if file_name in permanent_files else temporary_files[file_name]['file_id'])
        downloaded_file = bot.download_file(file_info.file_path)
        
        temp_path = f"temp_send_{file_name}"
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file)
        
        with open(temp_path, 'rb') as f:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل مؤقت (10 دقائق)", callback_data=f"temporary_run_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل دائم", callback_data=f"permanent_run_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تعديل", callback_data=f"edit_file_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} إيقاف", callback_data=f"stop_bot_{file_name}"))
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف", callback_data=f"delete_file_{file_name}"))
            
            bot.send_document(message.chat.id, f, caption=f"تم تعديل البوت بنجاح!\nاسم الملف: {file_name}", reply_markup=keyboard)
        
        os.remove(temp_path)
    else:
        bot.send_message(message.chat.id, result)

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
            
            content = downloaded_file.decode('utf-8')
            
            is_permanent = old_file_name in permanent_files
            success, result = save_file_to_channel(old_file_name, content, is_permanent=is_permanent)
            
            if success:
                # إرسال الملف المستبدل للمدير
                file_info = bot.get_file(permanent_files[old_file_name]['file_id'] if old_file_name in permanent_files else temporary_files[old_file_name]['file_id'])
                downloaded_file = bot.download_file(file_info.file_path)
                
                temp_path = f"temp_send_{old_file_name}"
                with open(temp_path, 'wb') as f:
                    f.write(downloaded_file)
                
                with open(temp_path, 'rb') as f:
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل مؤقت (10 دقائق)", callback_data=f"temporary_run_{old_file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل دائم", callback_data=f"permanent_run_{old_file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تعديل", callback_data=f"edit_file_{old_file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} إيقاف", callback_data=f"stop_bot_{old_file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف", callback_data=f"delete_file_{old_file_name}"))
                    
                    bot.send_document(message.chat.id, f, caption=f"تم استبدال الملف بنجاح!\nاسم الملف: {old_file_name}", reply_markup=keyboard)
                
                os.remove(temp_path)
            else:
                bot.send_message(message.chat.id, result)
        except Exception as e:
            bot.send_message(message.chat.id, f"حدث خطأ أثناء معالجة الملف: {str(e)}")
    else:
        bot.send_message(message.chat.id, "يرجى إرسال ملف صحيح.")

def process_upload_file(message):
    if message.document:
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            file_name = message.document.file_name
            content = downloaded_file.decode('utf-8')
            
            is_permanent = len(permanent_files) < MAX_PERMANENT_FILES
            success, result = save_file_to_channel(file_name, content, is_permanent=is_permanent)
            
            if success:
                # إرسال الملف المرفوع للمدير
                file_info = bot.get_file(permanent_files[file_name]['file_id'] if file_name in permanent_files else temporary_files[file_name]['file_id'])
                downloaded_file = bot.download_file(file_info.file_path)
                
                temp_path = f"temp_send_{file_name}"
                with open(temp_path, 'wb') as f:
                    f.write(downloaded_file)
                
                with open(temp_path, 'rb') as f:
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل مؤقت (10 دقائق)", callback_data=f"temporary_run_{file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل دائم", callback_data=f"permanent_run_{file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تعديل", callback_data=f"edit_file_{file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} إيقاف", callback_data=f"stop_bot_{file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف", callback_data=f"delete_file_{file_name}"))
                    
                    bot.send_document(message.chat.id, f, caption=f"تم رفع الملف بنجاح!\nاسم الملف: {file_name}", reply_markup=keyboard)
                
                os.remove(temp_path)
            else:
                bot.send_message(message.chat.id, result)
        except Exception as e:
            bot.send_message(message.chat.id, f"حدث خطأ أثناء معالجة الملف: {str(e)}")
    else:
        bot.send_message(message.chat.id, "يرجى إرسال ملف صحيح.")

code_builder = {}

def process_code_input(message):
    chat_id = message.chat.id
    if message.text == '/don':
        if chat_id in code_builder and code_builder[chat_id]['code']:
            code_content = "\n".join(code_builder[chat_id]['code'])
            file_name = code_builder[chat_id].get('filename', f"user_created_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
            
            is_permanent = len(permanent_files) < MAX_PERMANENT_FILES
            success, result = save_file_to_channel(file_name, code_content, is_permanent=is_permanent)
            
            if success:
                # إرسال الملف المحفوظ للمدير
                file_info = bot.get_file(permanent_files[file_name]['file_id'] if file_name in permanent_files else temporary_files[file_name]['file_id'])
                downloaded_file = bot.download_file(file_info.file_path)
                
                temp_path = f"temp_send_{file_name}"
                with open(temp_path, 'wb') as f:
                    f.write(downloaded_file)
                
                with open(temp_path, 'rb') as f:
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل مؤقت (10 دقائق)", callback_data=f"temporary_run_{file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل دائم", callback_data=f"permanent_run_{file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تعديل", callback_data=f"edit_file_{file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} إيقاف", callback_data=f"stop_bot_{file_name}"))
                    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف", callback_data=f"delete_file_{file_name}"))
                    
                    bot.send_document(chat_id, f, caption=f"تم حفظ الملف بنجاح!\nاسم الملف: {file_name}", reply_markup=keyboard)
                
                os.remove(temp_path)
            else:
                bot.send_message(chat_id, result)
            
            del code_builder[chat_id]
        else:
            bot.send_message(chat_id, "لم يتم إدخال أي كود لحفظه.")
    elif message.text.startswith('/name '):
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
        if chat_id not in code_builder:
            code_builder[chat_id] = {'code': [], 'filename': f"user_created_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"}
        
        code_builder[chat_id]['code'].append(message.text)
        bot.send_message(chat_id, "تم إضافة السطر. استمر في إرسال الأسطر أو أرسل /don لحفظ الملف. يمكنك استخدام /name لتعيين اسم الملف.")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "عذرًا，你没有权限使用此机器人。")
        return
    
    bot.reply_to(message, "عذرًا، لم أفهم طلبك. يرجى استخدام الأزرار المتاحة.")

if __name__ == "__main__":
    print("تم تشغيل البوت...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"حدث خطأ في البوت: {str(e)}")
        time.sleep(30)
        os.execv(__file__, sys.argv) 
