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
CHANNEL_ID = -1003091756917  # قناة تخزين الملفات
STORAGE_CHANNEL_ID = -1003088700358  # قناة تخزين بيانات المستخدمين
SUBSCRIPTION_CHANNEL = "@iIl337"  # قناة الاشتراك الإجباري
BOT_USERNAME = "@TIET6BOT"  # اسم المستخدم للبوت

# رموز تعبيرية عشوائية
EMOJIS = ["🧤", "🩲", "🪖", "👒", "🐸", "🐝", "🪲", "🐍", "🦎", "🫎", "🦖", "🐊", "🐎", "🦚", "🦜", "🎍", "🪷", "🪸", "🪻"]

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# مجلد التخزين المؤقت
if not os.path.exists("temp_files"):
    os.makedirs("temp_files")

# قاموس لتخزين معلومات الملفات
file_storage = {}
# قاموس لتخزين العمليات النشطة
active_processes = {}
# قاموس مؤقت لتخزين بيانات المستخدمين
user_data_cache = {}
# قاموس لتخزين المدعويين (لمنع الدعوة المزدوجة)
invited_users = {}
# قاموس للمستخدمين المحظورين
banned_users = {}

# دالة لتنظيف الكود من علامات Markdown
def clean_generated_code(code):
    # إزالة ```python و ``` من بداية ونهاية الكود
    code = re.sub(r'^```python\s*', '', code, flags=re.IGNORECASE)
    code = re.sub(r'```\s*$', '', code)
    
    # إزالة أي علامات Markdown أخرى
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

# دالة للتحميل التلقائي للبيانات
def load_all_data():
    load_file_list()
    load_banned_users()
    load_invited_users()
    load_user_data_from_channel()

# دالة لحفظ المستخدمين المحظورين
def save_banned_users():
    try:
        with open("banned_users.json", "w", encoding='utf-8') as f:
            json.dump(banned_users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving banned users: {e}")

# دالة لتحميل المستخدمين المحظورين
def load_banned_users():
    global banned_users
    if os.path.exists("banned_users.json"):
        try:
            with open("banned_users.json", "r", encoding='utf-8') as f:
                banned_users = json.load(f)
        except Exception as e:
            print(f"Error loading banned users: {e}")
            banned_users = {}
    else:
        banned_users = {}

# دالة لحفظ المدعويين
def save_invited_users():
    try:
        with open("invited_users.json", "w", encoding='utf-8') as f:
            json.dump(invited_users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving invited users: {e}")

# دالة لتحميل المدعويين
def load_invited_users():
    global invited_users
    if os.path.exists("invited_users.json"):
        try:
            with open("invited_users.json", "r", encoding='utf-8') as f:
                invited_users = json.load(f)
        except Exception as e:
            print(f"Error loading invited users: {e}")
            invited_users = {}
    else:
        invited_users = {}

# دالة لتحميل بيانات المستخدمين من القناة
def load_user_data_from_channel():
    try:
        # جلب آخر 100 رسالة من القناة
        messages = bot.get_chat(STORAGE_CHANNEL_ID)
        
        # في التطبيق الحقيقي، سنحتاج إلى جلب الرسائل بطريقة مختلفة
        # لأن get_chat لا يعيد الرسائل، لكننا سنستخدم طريقة بديلة
        print("✅ تم تحميل بيانات المستخدمين من القناة (محاكاة)")
    except Exception as e:
        print(f"❌ خطأ في تحميل بيانات المستخدمين من القناة: {e}")

# دالة للحصول على بيانات المستخدم من قناة التخزين
def get_user_data(user_id):
    if str(user_id) in banned_users:
        return None
    
    if user_id in user_data_cache:
        return user_data_cache[user_id]
    
    try:
        # محاكاة جلب البيانات من القناة
        # في التطبيق الحقيقي، سيتم البحث في رسائل القناة عن بيانات المستخدم
        user_data = {
            'user_id': user_id,
            'points': 5,  # نقاط مجانية عند التسجيل
            'invited_count': 0,
            'referral_code': str(uuid.uuid4())[:8],
            'referral_link': f"https://t.me/{BOT_USERNAME[1:]}?start=ref_{user_id}",
            'message_id': None,
            'banned': False
        }
        
        # تخزين في الكاش
        user_data_cache[user_id] = user_data
        
        # حفظ البيانات في القناة
        save_user_data_to_channel(user_data)
        
        return user_data
        
    except Exception as e:
        print(f"Error getting user data: {e}")
        # إرجاع بيانات افتراضية في حالة الخطأ
        return {
            'user_id': user_id,
            'points': 5,
            'invited_count': 0,
            'referral_code': str(uuid.uuid4())[:8],
            'referral_link': f"https://t.me/{BOT_USERNAME[1:]}?start=ref_{user_id}",
            'message_id': None,
            'banned': False
        }

# دالة لحفظ بيانات المستخدم في قناة التخزين
def save_user_data_to_channel(user_data):
    try:
        user_message = f"""
👤 بيانات المستخدم:
🆔 ID: {user_data['user_id']}
⭐ النقاط: {user_data['points']}
👥 عدد المدعوين: {user_data['invited_count']}
🔗 رابط الدعوة: {user_data['referral_link']}
📅 آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        if user_data.get('message_id'):
            # تحديث الرسالة الموجودة
            bot.edit_message_text(
                user_message, 
                STORAGE_CHANNEL_ID, 
                user_data['message_id']
            )
        else:
            # إنشاء رسالة جديدة
            sent_message = bot.send_message(STORAGE_CHANNEL_ID, user_message)
            user_data['message_id'] = sent_message.message_id
            user_data_cache[user_data['user_id']] = user_data
            
        return True
    except Exception as e:
        print(f"Error saving user data to channel: {e}")
        return False

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
    
    # حفظ البيانات في القناة
    save_user_data_to_channel(user_data)
    
    # تحديث الكاش
    user_data_cache[user_id] = user_data
    return user_data

# دالة لمعالجة روابط الدعوة
def process_referral(start_param, new_user_id):
    if start_param.startswith('ref_'):
        referrer_id = int(start_param[4:])
        
        # التحقق من أن المستخدم لا يدعو نفسه
        if referrer_id == new_user_id:
            return False
            
        # التحقق من أن المستخدم الجديد لم يتم دعوته من قبل
        if str(new_user_id) in invited_users:
            return False
            
        referrer_data = get_user_data(referrer_id)
        if not referrer_data:
            return False
        
        # زيادة عدد المدعوين ونقاط المُدعِي
        new_invited_count = referrer_data['invited_count'] + 1
        new_points = referrer_data['points'] + 1
        
        update_user_data(referrer_id, new_points, new_invited_count)
        
        # منح النقطة المجانية للمستخدم الجديد
        new_user_data = get_user_data(new_user_id)
        if new_user_data:
            update_user_data(new_user_id, new_user_data['points'] + 1)
        
        # حفظ أن هذا المستخدم تم دعوته
        invited_users[str(new_user_id)] = {
            'invited_by': referrer_id,
            'invited_at': datetime.now().isoformat()
        }
        save_invited_users()
        
        # إرسال إشعار للمدعو
        try:
            bot.send_message(
                new_user_id,
                f"🎉 لقد حصلت على نقطة مجانية لدخولك عبر رابط الدعوة! نقاطك الآن: {new_user_data['points'] + 1}"
            )
        except:
            pass
            
        # إرسال إشعار للداعي
        try:
            bot.send_message(
                referrer_id,
                f"🎊 لقد حصلت على نقطة جديدة لدعوة صديق! نقاطك الآن: {new_points}، عدد المدعوين: {new_invited_count}"
            )
        except:
            pass
        
        return True
    return False

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
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
    return keyboard

# دالة لإنشاء لوحة رابط الدعوة
def create_referral_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(f"{random_emoji()} إنشاء رابط الدعوة", callback_data="generate_referral"),
        InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main")
    )
    return keyboard

# دالة لإنشاء لوحة إدارة المدير
def create_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(f"{random_emoji()} إضافة نقاط", callback_data="admin_add_points"),
        InlineKeyboardButton(f"{random_emoji()} حظر/فك حظر", callback_data="admin_ban_user")
    )
    keyboard.add(
        InlineKeyboardButton(f"{random_emoji()} إشعار عام", callback_data="admin_broadcast"),
        InlineKeyboardButton(f"{random_emoji()} عدد المستخدمين", callback_data="admin_user_count")
    )
    keyboard.add(InlineKeyboardButton(f"{random_emoji()} رجوع", callback_data="back_to_main"))
    return keyboard

# دالة لإنشاء ملف Python باستخدام Gemini AI
def create_python_file(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    # وصف شخصية الذكاء الاصطناعي لتحسين جودة الأكواد
    ai_persona = """
أنت مساعد خبير في برمجة بوتات Telegram باستخدام مكتبة pyTelegramBotAPI.
يجب أن تكون الأكواد التي تكتبها:
1. كاملة وجاهزة للتشغيل مباشرة دون أي علامات تنسيق
2. تحتوي على جميع الاستيرادات الضرورية
3. تتضمن معالجة للأخطاء
4. تستخدم أحدث ممارسات البرمجة
5. تكون فعالة وموثوقة
6. لا تحتوي على أي علامات تنسيق مثل ```python أو ```
7. تدعم اللغة العربية في النصوص عند الحاجة

الرجاء كتابة الكود فقط دون أي شرح إضافي أو علامات تنسيق.
"""
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{ai_persona}\n\nWrite a complete Python Telegram bot using the pyTelegramBotAPI library. {prompt}. Provide only the Python code without any explanations or markdown formatting."
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
            # تنظيف الكود من علامات التنسيق
            cleaned_code = clean_generated_code(code)
            return cleaned_code
        else:
            print(f"Error from Gemini API: {response.status_code} - {response.text}")
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
            # تنظيف الكود من علامات التنسيق
            cleaned_code = clean_generated_code(modified_code)
            return cleaned_code
        else:
            print(f"Error from Gemini API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception in modify_python_file: {e}")
        return None

# دالة لتشغيل البوت لمدة 15 دقيقة
def run_bot_for_15_minutes(file_path, chat_id, file_name, user_id):
    try:
        # إرسال رسالة بدء التشغيل
        status_msg = bot.send_message(chat_id, f"⏳ جاري تشغيل البوت: {file_name} لمدة 15 دقيقة...")
        
        # تشغيل البوت
        process = subprocess.Popen(
            ['python', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # تخزين معلومات العملية
        active_processes[file_name] = {
            'process': process,
            'start_time': time.time(),
            'status_msg_id': status_msg.message_id,
            'user_id': user_id
        }
        
        # الانتظار لمدة 15 دقيقة مع التحقق من العملية بانتظام
        for _ in range(90):  # 90 مرة كل 10 ثوان = 15 دقيقة
            if process.poll() is not None:  # إذا انتهت العملية
                break
            time.sleep(10)  # الانتظار 10 ثوان بين كل فحص
        
        # إنهاء العملية إذا كانت لا تزال تعمل
        if process.poll() is None:
            process.terminate()
            time.sleep(2)  # انتظار قليل للإنهاء
            if process.poll() is None:  # إذا لم تنته بعد
                process.kill()  # إجبار الإنهاء
        
        # جمع النتائج
        stdout, stderr = process.communicate()
        
        # إعداد رسالة النتيجة
        result_message = f"⏰ انتهت مدة التشغيل (15 دقيقة) للبوت: {file_name}\n\n"
        
        if stdout:
            result_message += f"📤 الناتج:\n{stdout[-1000:]}\n\n"  # آخر 1000 حرف فقط
        
        if stderr:
            result_message += f"❌ الأخطاء:\n{stderr[-1000:]}\n\n"  # آخر 1000 حرف فقط
        
        if not stdout and not stderr:
            result_message += "✅ تم التشغيل بنجاح بدون ناتج."
        
        # التحقق مما إذا كان هناك أخطاء في التشغيل
        has_errors = bool(stderr) or "error" in result_message.lower() or "exception" in result_message.lower()
        
        # إذا كان هناك أخطاء، إعادة النقطة للمستخدم (ما عدا المدير)
        if has_errors and user_id in active_processes and user_id != ADMIN_ID:
            user_data = get_user_data(user_id)
            if user_data:
                update_user_data(user_id, user_data['points'] + 1)
                result_message += "\n\n⚠️ تم إعادة النقطة إلى رصيدك بسبب وجود أخطاء في التشغيل."
        
        # إرسال النتيجة
        try:
            bot.edit_message_text(
                result_message,
                chat_id,
                status_msg.message_id
            )
        except:
            # إذا فشل التعديل، أرسل رسالة جديدة
            bot.send_message(chat_id, result_message)
        
        # إزالة العملية من القائمة النشطة
        if file_name in active_processes:
            del active_processes[file_name]
            
    except Exception as e:
        error_msg = f"❌ خطأ أثناء تشغيل البوت {file_name}: {str(e)}"
        try:
            bot.send_message(chat_id, error_msg)
        except:
            print(error_msg)
        
        # إعادة النقطة للمستخدم في حالة الخطأ (ما عدا المدير)
        if user_id in active_processes and user_id != ADMIN_ID:
            user_data = get_user_data(user_id)
            if user_data:
                update_user_data(user_id, user_data['points'] + 1)
        
        # إزالة العملية من القائمة النشطة في حالة الخطأ
        if file_name in active_processes:
            del active_processes[file_name]

# التحقق من هوية المدير
def is_admin(user_id):
    return user_id == ADMIN_ID

# دالة لتحميل قائمة الملفات
def load_file_list():
    global file_storage
    if os.path.exists("file_storage.json"):
        try:
            with open("file_storage.json", "r", encoding='utf-8') as f:
                file_storage = json.load(f)
        except Exception as e:
            print(f"Error loading file storage: {e}")
            file_storage = {}
    else:
        file_storage = {}

# دالة لحفظ قائمة الملفات
def save_file_list():
    try:
        with open("file_storage.json", "w", encoding='utf-8') as f:
            json.dump(file_storage, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving file storage: {e}")

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
        with open(new_file_path, 'r', encoding='utf-8') as f:
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
    # التحقق من الحظر
    if str(message.from_user.id) in banned_users:
        bot.send_message(message.chat.id, "❌ تم حظرك من استخدام البوت.")
        return
    
    # التحقق من الاشترак في القناة
    if not check_subscription(message.from_user.id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("✅ التحقق من الاشتراك", callback_data="check_subscription"))
        bot.send_message(
            message.chat.id, 
            f"⚠️ يجب الاشتراك في القناة {SUBSCRIPTION_CHANNEL} أولاً لاستخدام البوت.",
            reply_markup=keyboard
        )
        return
    
    # معالجة روابط الدعوة
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
- إدارة كاملة للملفات (رفع، حذف، استبدال)
- تخزين الملفات في قناة خاصة

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
    # التحقق من الحظر
    if str(call.from_user.id) in banned_users:
        bot.answer_callback_query(call.id, "❌ تم حظرك من استخدام البوت.")
        return
    
    # التحقق من الاشتراك في القناة (ما عدا أزرار المدير)
    if not call.data.startswith("admin_") and not check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ يجب الاشتراك في القناة أولاً")
        return
    
    # معالجة أزرار المدير
    if call.data.startswith("admin_"):
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
            # حساب عدد المستخدمين الفريدين
            user_count = len(user_data_cache)
            bot.send_message(call.message.chat.id, f"👥 عدد المستخدمين: {user_count}")
            
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
    
    user_data = get_user_data(call.from_user.id)
    if not user_data:
        bot.answer_callback_query(call.id, "❌ حدث خطأ في تحميل بياناتك.")
        return
    
    # للمدير، نقاط لا نهائية
    if is_admin(call.from_user.id):
        user_data['points'] = float('inf')
    
    if call.data == "start_production":
        if user_data['points'] <= 0 and not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ ليس لديك نقاط كافية")
            bot.send_message(
                call.message.chat.id,
                f"❌ ليس لديك نقاط كافية. نقاطك الحالية: {user_data['points']}\n\n📣 قم بدعوة أصدقائك للحصول على المزيد من النقاط.",
                reply_markup=create_referral_keyboard(call.from_user.id)
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
        
        files_list = "\n".join([f"📄 {name} (أنشئ في: {datetime.fromisoformat(file_storage[name]['created_at']).strftime('%Y-%m-%d %H:%M')})" for name in file_storage.keys()])
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
            
            # التحقق مما إذا كان الملف قيد التشغيل بالفعل
            if file_name in active_processes:
                bot.answer_callback_query(call.id, "⏳ البوت قيد التشغيل بالفعل")
                return
            
            # تشغيل البوت في thread منفصل
            thread = threading.Thread(target=run_bot_for_15_minutes, args=(file_path, call.message.chat.id, file_name, call.from_user.id))
            thread.daemon = True  # لجعل الخيط ينتهي مع انتهاء البرنامج الرئيسي
            thread.start()
            
            bot.answer_callback_query(call.id, "⏳ بدأ تشغيل البوت لمدة 15 دقيقة")
        else:
            bot.send_message(call.message.chat.id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())
    
    elif call.data.startswith("edit_"):
        file_name = call.data[5:]
        if file_name in file_storage:
            file_path = file_storage[file_name]["path"]
            
            # قراءة المحتوى الحالي
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # حفظ المحتوى مؤقتاً للاستخدام لاحقاً
            bot.user_data[call.from_user.id] = {"action": "editing", "file_name": file_name, "code": code}
            
            msg = bot.send_message(call.message.chat.id, "✏️ ما التعديلات التي تريد إجراؤها على الملف؟")
            bot.register_next_step_handler(msg, process_edit_request)
        else:
            bot.send_message(call.message.chat.id, "❌ الملف غير موجود", reply_markup=create_main_keyboard())

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
        
        # إرسال إشعار للمستخدم
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
            # فك الحظر
            del banned_users[str(user_id)]
            save_banned_users()
            bot.send_message(message.chat.id, f"✅ تم فك حظر المستخدم {user_id}.")
            
            # إرسال إشعار للمستخدم
            try:
                bot.send_message(user_id, "✅ تم فك حظرك من البوت. يمكنك الآن استخدامه مرة أخرى.")
            except:
                pass
        else:
            # الحظر
            banned_users[str(user_id)] = {
                'banned_by': message.from_user.id,
                'banned_at': datetime.now().isoformat()
            }
            save_banned_users()
            bot.send_message(message.chat.id, f"✅ تم حظر المستخدم {user_id}.")
            
            # إرسال إشعار للمستخدم
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
        
    # هذه دالة مبسطة للإشعار العام
    # في التطبيق الحقيقي، تحتاج إلى جلب جميع مستخدمي البوت وإرسال الرسالة لكل منهم
    broadcast_text = f"""
📢 إشعار عام من الإدارة:

{message.text}

---
هذا إشعام自动ي من بوت {BOT_USERNAME}
    """
    
    # إرسال الإشعار للمدير أولاً للمراجعة
    preview_msg = bot.send_message(message.chat.id, f"📋 معاينة الإشعار:\n\n{broadcast_text}")
    
    # طلب التأكيد
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ نعم، أرسل الإشعار", callback_data=f"confirm_broadcast_{preview_msg.message_id}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="back_to_main")
    )
    
    bot.send_message(message.chat.id, "⚠️ هل تريد إرسال هذا الإشعار لجميع المستخدمين؟", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_broadcast_'))
def confirm_broadcast(call):
    if not is_admin(call.from_user.id):
        return
        
    try:
        message_id = int(call.data[16:])
        original_message = bot.send_message(call.message.chat.id, "⏳ جاري إرسال الإشعار...")
        
        # محاكاة إرسال الإشعار لجميع المستخدمين
        # في التطبيق الحقيقي، سيتم إرساله لجميع المستخدمين في user_data_cache
        sent_count = 0
        for user_id in user_data_cache:
            try:
                bot.send_message(user_id, original_message.text)
                sent_count += 1
            except:
                continue
        
        bot.edit_message_text(
            f"✅ تم إرسال الإشعار إلى {sent_count} مستخدم.",
            call.message.chat.id,
            call.message.message_id
        )
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ حدث خطأ أثناء إرسال الإشعار: {str(e)}")

# معالج إنشاء البوت
def process_bot_creation(message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "❌ حدث خطأ في تحميل بياناتك.")
        return
    
    # للمدير، نقاط لا نهائية
    if not is_admin(message.from_user.id):
        # خصم نقطة من رصيد المستخدم
        update_user_data(message.from_user.id, user_data['points'] - 1)
    
    prompt = message.text
    bot.send_message(message.chat.id, "⏳ جاري إنشاء البوت باستخدام الذكاء الاصطناعي...")
    
    # إنشاء الكود باستخدام Gemini AI
    code = create_python_file(prompt)
    
    if code:
        # حفظ الملف مؤقتاً
        timestamp = int(time.time())
        file_name = f"bot_{timestamp}.py"
        file_path = f"temp_files/{file_name}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
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
        # إذا فشل إنشاء البوت، إعادة النقطة للمستخدم (ما عدا المدير)
        if not is_admin(message.from_user.id):
            update_user_data(message.from_user.id, user_data['points'])
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
            with open(file_path, 'r', encoding='utf-8') as f:
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
    user_data = get_user_data(user_id)
    if not user_data:
        bot.send_message(message.chat.id, "❌ حدث خطأ في تحميل بياناتك.")
        return
    
    # التحقق من وجود نقاط كافية (ما عدا المدير)
    if user_data['points'] <= 0 and not is_admin(user_id):
        bot.send_message(
            message.chat.id,
            f"❌ ليس لديك نقاط كافية. نقاطك الحالية: {user_data['points']}\n\n📣 قم بدعوة أصدقائك للحصول على المزيد من النقاط.",
            reply_markup=create_referral_keyboard(user_id)
        )
        return
    
    # خصم نقطة من رصيد المستخدم (ما عدا المدير)
    if not is_admin(user_id):
        update_user_data(user_id, user_data['points'] - 1)
    
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
            
            with open(file_path, 'w', encoding='utf-8') as f:
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
            # إذا فشل التعديل، إعادة النقطة للمستخدم (ما عدا المدير)
            if not is_admin(user_id):
                update_user_data(user_id, user_data['points'])
            bot.send_message(message.chat.id, "❌ فشل في تعديل الملف. يرجى المحاولة مرة أخرى.", reply_markup=create_main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على بيانات التعديل. يرجى البدء من جديد.", reply_markup=create_main_keyboard())

# بدء البوت
if __name__ == "__main__":
    # تحميل جميع البيانات عند البدء
    load_all_data()
    print("🤖 البوت النهائي مع نظام النقاط ولوحة الإدارة يعمل الآن...")
    bot.infinity_polling() 
