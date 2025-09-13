import os
import random
import requests
import telebot
import threading
import time
import re
import sys
import subprocess
import signal
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# التوكنات والمفاتيح
BOT_TOKEN = "8403108424:AAHnqJdSxWdKrShCwDTsJbKeVPLp3yby3ro"
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
        
        if file_name in permanent_files:
            file_info = permanent_files[file_name]
            del permanent_files[file_name]
        elif file_name in temporary_files:
            file_info = temporary_files[file_name]
            del temporary_files[file_name]
        else:
            return False, "الملف غير موجود."
        
        try:
            bot.delete_message(CHANNEL_ID, file_info['message_id'])
        except:
            pass
        
        if file_name in active_bots:
            try:
                active_bots[file_name]['process'].terminate()
            except:
                pass
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
        
        if file_name in active_bots:
            return False, "البوت يعمل بالفعل."
        
        file_id = file_info['file_id']
        file_info_obj = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info_obj.file_path)
        
        local_path = f"bots/{file_name}"
        os.makedirs("bots", exist_ok=True)
        
        with open(local_path, 'wb') as f:
            f.write(downloaded_file)
        
        # تشغيل البوت في عملية منفصلة
        process = subprocess.Popen([sys.executable, local_path], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
        
        active_bots[file_name] = {
            'process': process,
            'started_at': datetime.now(),
            'is_permanent': is_permanent,
            'file_path': local_path
        }
        
        if is_permanent:
            return True, f"تم بدء التشغيل الدائم للبوت {file_name}."
        else:
            # بدء مؤقت للإيقاف التلقائي بعد 10 دقائق
            timer = threading.Timer(600, stop_bot, args=[file_name])
            timer.start()
            return True, f"تم بدء التشغيل المؤقت للبوت {file_name} لمدة 10 دقائق."
    except Exception as e:
        return False, f"حدث خطأ أثناء تشغيل البوت: {str(e)}"

def stop_bot(file_name):
    try:
        if file_name in active_bots:
            process = active_bots[file_name]['process']
            try:
                # إرسال إشارة إنهاء للعملية
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            except:
                pass
            
            # تنظيف الملف المحلي
            file_path = active_bots[file_name].get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            
            del active_bots[file_name]
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

def restore_files_from_channel():
    """استعادة الملفات من القناة عند بدء التشغيل"""
    try:
        # الحصول على آخر 100 رسالة من القناة
        messages = bot.get_chat_administrators(CHANNEL_ID)
        time.sleep(1)  # تجنب rate limiting
        
        # محاولة الحصول على الرسائل بطريقة أخرى
        try:
            # هذه طريقة بديلة إذا لم تعمل الطريقة الأولى
            for i in range(1, 50):
                try:
                    message = bot.get_message(CHANNEL_ID, i)
                    if message.document:
                        file_name = message.document.file_name
                        caption = message.caption if message.caption else ""
                        
                        # تحديد إذا كان الملف دائمًا أو مؤقتًا
                        is_permanent = "دائم: True" in caption
                        
                        if is_permanent:
                            permanent_files[file_name] = {
                                'file_id': message.document.file_id,
                                'message_id': message.message_id,
                                'created_at': datetime.now(),
                                'is_permanent': True
                            }
                        else:
                            temporary_files[file_name] = {
                                'file_id': message.document.file_id,
                                'message_id': message.message_id,
                                'created_at': datetime.now(),
                                'expires_at': datetime.now() + timedelta(minutes=10),
                                'is_permanent': False
                            }
                except:
                    continue
        except:
            print("تعذر استعادة الملفات من القناة. سيتم البدء بقوائم فارغة.")
        
        print(f"تم استعادة {len(permanent_files)} ملف دائم و {len(temporary_files)} ملف مؤقت من القناة.")
    except Exception as e:
        print(f"حدث خطأ أثناء استعادة الملفات من القناة: {str(e)}")

# استعادة الملفات عند بدء التشغيل
restore_files_from_channel()

# بدء ثريد لفحص الملفات المنتهية الصلاحية
cleanup_thread = threading.Thread(target=check_expired_files)
cleanup_thread.daemon = True
cleanup_thread.start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "عذرًا،你没有权限使用此机器人。")
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} بدء الانشاء", callback_data="start_creation"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} خيارات أكثر", callback_data="more_options"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} عرض الملفات", callback_data="show_files"))
    
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
    
    elif call.data == "show_files":
        show_files_menu(call.message)
    
    elif call.data.startswith("file_"):
        file_name = call.data.replace("file_", "")
        show_file_options(call.message, file_name)
    
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
    
    elif call.data == "upload_file":
        msg = bot.send_message(call.message.chat.id, "أرسل الملف الجاهز الذي تريد رفعه:")
        bot.register_next_step_handler(msg, process_upload_file)
    
    elif call.data == "create_file":
        msg = bot.send_message(call.message.chat.id, "أرسل كود الملف سطرًا سطرًا. عند الانتهاء، أرسل /don لحفظ الملف.")
        bot.register_next_step_handler(msg, process_code_input)
    
    elif call.data == "list_active_bots":
        show_active_bots_list(call.message)

def show_files_menu(message):
    """عرض قائمة الملفات عبر inline keyboard"""
    keyboard = InlineKeyboardMarkup()
    
    # إضافة الملفات المؤقتة
    if temporary_files:
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} الملفات المؤقتة ({len(temporary_files)})", callback_data="temp_files"))
    
    # إضافة الملفات الدائمة
    if permanent_files:
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} الملفات الدائمة ({len(permanent_files)})", callback_data="perm_files"))
    
    # إضافة البوتات النشطة
    if active_bots:
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} البوتات النشطة ({len(active_bots)})", callback_data="active_bots"))
    
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} الرجوع", callback_data="more_options"))
    
    bot.send_message(message.chat.id, "اختر نوع الملفات التي تريد عرضها:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data in ["temp_files", "perm_files", "active_bots"])
def handle_files_categories(call):
    if call.data == "temp_files":
        show_files_list(call.message, "temporary")
    elif call.data == "perm_files":
        show_files_list(call.message, "permanent")
    elif call.data == "active_bots":
        show_active_bots_list(call.message)

def show_files_list(message, file_type):
    """عرض قائمة الملفات مع أزرار التحكم"""
    files = temporary_files if file_type == "temporary" else permanent_files
    
    if not files:
        bot.send_message(message.chat.id, f"لا توجد ملفات {file_type}.")
        return
    
    # تقسيم الملفات إلى صفحات إذا كان العدد كبيرًا
    files_list = list(files.keys())
    page_size = 10
    pages = [files_list[i:i + page_size] for i in range(0, len(files_list), page_size)]
    
    for page_num, page_files in enumerate(pages, 1):
        keyboard = InlineKeyboardMarkup()
        
        for file_name in page_files:
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} {file_name}", callback_data=f"file_{file_name}"))
        
        # أزرار التنقل بين الصفحات إذا كان هناك أكثر من صفحة
        if len(pages) > 1:
            nav_buttons = []
            if page_num > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{file_type}_{page_num-1}"))
            if page_num < len(pages):
                nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{file_type}_{page_num+1}"))
            keyboard.row(*nav_buttons)
        
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} الرجوع", callback_data="show_files"))
        
        bot.send_message(message.chat.id, f"الملفات {file_type} - الصفحة {page_num}/{len(pages)}:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def handle_pagination(call):
    parts = call.data.split("_")
    if len(parts) >= 3:
        file_type = parts[1]
        page_num = int(parts[2])
        show_files_page(call.message, file_type, page_num)

def show_files_page(message, file_type, page_num):
    """عرض صفحة محددة من الملفات"""
    files = temporary_files if file_type == "temporary" else permanent_files
    
    if not files:
        bot.send_message(message.chat.id, f"لا توجد ملفات {file_type}.")
        return
    
    files_list = list(files.keys())
    page_size = 10
    pages = [files_list[i:i + page_size] for i in range(0, len(files_list), page_size)]
    
    if page_num < 1 or page_num > len(pages):
        bot.send_message(message.chat.id, "رقم الصفحة غير صحيح.")
        return
    
    page_files = pages[page_num-1]
    keyboard = InlineKeyboardMarkup()
    
    for file_name in page_files:
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} {file_name}", callback_data=f"file_{file_name}"))
    
    # أزرار التنقل بين الصفحات
    nav_buttons = []
    if page_num > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{file_type}_{page_num-1}"))
    if page_num < len(pages):
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{file_type}_{page_num+1}"))
    
    if nav_buttons:
        keyboard.row(*nav_buttons)
    
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} الرجوع", callback_data="show_files"))
    
    bot.edit_message_reply_markup(
        chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=keyboard
    )

def show_file_options(message, file_name):
    """عرض خيارات ملف معين"""
    # التحقق من وجود الملف
    file_info = None
    if file_name in permanent_files:
        file_info = permanent_files[file_name]
    elif file_name in temporary_files:
        file_info = temporary_files[file_name]
    else:
        bot.send_message(message.chat.id, "الملف غير موجود.")
        return
    
    is_running = file_name in active_bots
    
    keyboard = InlineKeyboardMarkup()
    
    if not is_running:
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل مؤقت (10 دقائق)", callback_data=f"temporary_run_{file_name}"))
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تشغيل دائم", callback_data=f"permanent_run_{file_name}"))
    else:
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} إيقاف التشغيل", callback_data=f"stop_bot_{file_name}"))
    
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تعديل", callback_data=f"edit_file_{file_name}"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف", callback_data=f"delete_file_{file_name}"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} الرجوع", callback_data="show_files"))
    
    status = "نشط" if is_running else "غير نشط"
    bot.send_message(message.chat.id, f"خيارات الملف: {file_name}\nالحالة: {status}", reply_markup=keyboard)

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
        send_file_to_user(message.chat.id, file_name, "تم إنشاء البوت بنجاح!")
    else:
        bot.send_message(message.chat.id, f"عذرًا، {result}")

def send_file_to_user(chat_id, file_name, caption):
    """إرسال ملف للمستخدم مع أزرار التحكم"""
    try:
        file_info = None
        if file_name in permanent_files:
            file_info = permanent_files[file_name]
        elif file_name in temporary_files:
            file_info = temporary_files[file_name]
        else:
            bot.send_message(chat_id, "الملف غير موجود.")
            return
        
        file_id = file_info['file_id']
        file_info_obj = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info_obj.file_path)
        
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
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف", callback_data=f"delete_file_{file_name}"))
            
            bot.send_document(chat_id, f, caption=f"{caption}\nاسم الملف: {file_name}", reply_markup=keyboard)
        
        os.remove(temp_path)
    except Exception as e:
        bot.send_message(chat_id, f"حدث خطأ أثناء إرسال الملف: {str(e)}")

def show_more_options(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} استبدال ملف", callback_data="replace_file"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} حذف ملف", callback_data="show_files"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} رفع ملف جاهز", callback_data="upload_file"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} صنع ملف", callback_data="create_file"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} عرض الملفات", callback_data="show_files"))
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} عرض البوتات النشطة", callback_data="list_active_bots"))
    
    bot.send_message(message.chat.id, "خيارات إضافية:", reply_markup=keyboard)

def show_active_bots_list(message):
    if not active_bots:
        bot.send_message(message.chat.id, "لا توجد بوتات نشطة حالياً.")
        return
    
    keyboard = InlineKeyboardMarkup()
    
    for file_name, bot_info in active_bots.items():
        bot_type = "دائم" if bot_info.get('is_permanent', False) else "مؤقت"
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} {file_name} ({bot_type})", callback_data=f"file_{file_name}"))
    
    keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} الرجوع", callback_data="more_options"))
    
    bot.send_message(message.chat.id, "البوتات النشطة:", reply_markup=keyboard)

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
        send_file_to_user(message.chat.id, file_name, "تم تعديل البوت بنجاح!")
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
                send_file_to_user(message.chat.id, old_file_name, "تم استبدال الملف بنجاح!")
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
                send_file_to_user(message.chat.id, file_name, "تم رفع الملف بنجاح!")
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
                send_file_to_user(chat_id, file_name, "تم حفظ الملف بنجاح!")
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
