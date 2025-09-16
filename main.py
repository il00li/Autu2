import os
import telebot
import subprocess
import time
import logging
import requests
import json
import uuid
import re
import html
import random
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InputFile
)
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import tempfile
from flask import Flask, request

# إعدادات البوت
BOT_TOKEN = "8403108424:AAEGT-XtShnVn6_sZ_2HH_xTeGoLYyiqIB8"
ADMIN_ID = 6689435577
CHANNEL_ID = -1003091756917
STORAGE_CHANNEL_ID = -1003088700358
SUBSCRIPTION_CHANNEL = "@iIl337"
BOT_USERNAME = "@TIET6BOT"
MAX_FILES_PER_USER = 3
MAX_AI_REQUESTS = 1

# قائمة الرموز التعبيرية العشوائية
EMOJIS = ["🌴", "💐", "🐢", "🍃", "🌿", "🍾", "🐛", "🍀", "🐉", "🥑", "🥕", "🌾", "🐊", "🌳", "🌵", "🌱", "🌽", "🏕️", "🐸", "🌹", "🦎", "🦚", "🦜", "🪲", "🦠", "💐", "🌿", "☘️", "🍀", "🌱", "🪴", "🌲", "🌳", "🍃"]

# قائمة المكتبات المسبقة التجميع للتحسين
PRECOMPILED_LIBS = [
    'requests', 'numpy', 'pandas', 'matplotlib', 'scikit-learn',
    'beautifulsoup4', 'pillow', 'flask', 'django', 'tensorflow',
    'pytorch', 'keras', 'sqlalchemy', 'psycopg2', 'pymysql',
    'python-dotenv', 'openpyxl', 'xlrd', 'pdfkit', 'reportlab',
    'telebot', 'pytelegrambotapi', 'python-telegram-bot'
]

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
app = Flask(__name__)

# قاعدة بيانات بسيطة
users_data = {}
invite_codes = {}
premium_invites = {}
user_libraries = {}  # تخزين المكتبات المطلوبة لكل مستخدم

# تحميل البيانات المحفوظة
def load_data():
    global users_data, invite_codes, premium_invites, user_libraries
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
        if os.path.exists('user_libraries.json'):
            with open('user_libraries.json', 'r', encoding='utf-8') as f:
                user_libraries = json.load(f)
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        users_data = {}
        invite_codes = {}
        premium_invites = {}
        user_libraries = {}

# حفظ البيانات
def save_data():
    try:
        with open('users_data.json', 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
        with open('invite_codes.json', 'w', encoding='utf-8') as f:
            json.dump(invite_codes, f, ensure_ascii=False, indent=4)
        with open('premium_invites.json', 'w', encoding='utf-8') as f:
            json.dump(premium_invites, f, ensure_ascii=False, indent=4)
        with open('user_libraries.json', 'w', encoding='utf-8') as f:
            json.dump(user_libraries, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving data: {e}")

# الحصول على رمز تعبيري عشوائي
def get_random_emoji():
    return random.choice(EMOJIS)

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
    if str(user_id) not in user_libraries:
        user_libraries[str(user_id)] = []
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

# حفظ الملف في القناة
def save_file_to_channel(file_content, file_name, user_id):
    try:
        if check_user_files_limit(user_id):
            return False, "لقد وصلت إلى الحد الأقصى للملفات (3 ملفات). يرجى حذف بعض الملفات أولاً."
        
        temp_path = os.path.join(UPLOAD_DIR, file_name)
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        with open(temp_path, 'rb') as f:
            message = bot.send_document(CHANNEL_ID, f, caption=f"User: {user_id}\nFile: {file_name}")
        
        if str(user_id) in users_data:
            file_info = {
                'name': file_name,
                'message_id': message.message_id,
                'date': datetime.now().isoformat()
            }
            users_data[str(user_id)]['files'].append(file_info)
            save_data()
        
        os.remove(temp_path)
        
        return True, "تم حفظ الملف بنجاح"
    except Exception as e:
        logging.error(f"Error saving file to channel: {e}")
        return False, f"حدث خطأ في حفظ الملف: {str(e)}"

# إنشاء لوحة المفاتيح الرئيسية
def create_main_keyboard(user_id=None):
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if user_id and not check_subscription(user_id):
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} اشترك في القناة", url=f"https://t.me/{SUBSCRIPTION_CHANNEL[1:]}"))
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} تحقق من الاشتراك", callback_data="check_subscription"))
        return keyboard
    
    buttons = [
        InlineKeyboardButton(f"{get_random_emoji()} رفع وتشغيل ملف", callback_data="upload_and_run_file"),
        InlineKeyboardButton(f"{get_random_emoji()} خيارات أكثر", callback_data="more_options"),
        InlineKeyboardButton(f"{get_random_emoji()} إحصائياتي", callback_data="my_stats"),
        InlineKeyboardButton(f"{get_random_emoji()} رابط الدعوة", callback_data="invite_link")
    ]
    
    keyboard.add(buttons[0], buttons[1])
    keyboard.add(buttons[2], buttons[3])
    
    return keyboard

# إنشاء لوحة خيارات إضافية
def create_more_options_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(f"{get_random_emoji()} رفع ملف فقط", callback_data="upload_file_only"),
        InlineKeyboardButton(f"{get_random_emoji()} حذف ملف", callback_data="delete_file"),
        InlineKeyboardButton(f"{get_random_emoji()} عرض الملفات", callback_data="list_files"),
        InlineKeyboardButton(f"{get_random_emoji()} تشغيل ملف", callback_data="run_file"),
        InlineKeyboardButton(f"{get_random_emoji()} استبدال ملف", callback_data="replace_file"),
        InlineKeyboardButton(f"{get_random_emoji()} تثبيت مكتبات", callback_data="install_libraries"),
        InlineKeyboardButton(f"{get_random_emoji()} رجوع", callback_data="main_menu")
    ]
    
    keyboard.add(buttons[0], buttons[1])
    keyboard.add(buttons[2], buttons[3])
    keyboard.add(buttons[4], buttons[5])
    keyboard.add(buttons[6])
    
    return keyboard

# إنشاء لوحة الدعوة
def create_invite_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(f"{get_random_emoji()} توليد رابط دعوة", callback_data=f"generate_invite_{user_id}"),
        InlineKeyboardButton(f"{get_random_emoji()} رجوع", callback_data="main_menu")
    )
    return keyboard

# إنشاء لوحة إدارة المدير
def create_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(f"{get_random_emoji()} إنشاء رابط نقاط", callback_data="admin_create_premium"),
        InlineKeyboardButton(f"{get_random_emoji()} إحصائيات البوت", callback_data="admin_stats"),
        InlineKeyboardButton(f"{get_random_emoji()} رجوع", callback_data="main_menu")
    ]
    
    keyboard.add(buttons[0])
    keyboard.add(buttons[1])
    keyboard.add(buttons[2])
    
    return keyboard

# استخراج المكتبات المطلوبة من ملف بايثون
def extract_required_libraries(file_content):
    libraries = []
    lines = file_content.split('\n')
    
    common_stdlibs = ['os', 'sys', 'json', 'time', 're', 'math', 'datetime', 
                     'random', 'collections', 'itertools', 'functools', 'threading',
                     'asyncio', 'hashlib', 'base64', 'csv', 'urllib', 'ssl']
    
    for line in lines:
        line = line.strip()
        
        # اكتشاف عبارات الاستيراد الأساسية
        if line.startswith('import '):
            lib = line.split('import ')[1].split()[0].split('.')[0]
            if (lib not in libraries and 
                lib not in common_stdlibs and 
                not lib.startswith('_')):
                libraries.append(lib)
        
        elif line.startswith('from '):
            parts = line.split()
            if len(parts) >= 4 and parts[0] == 'from' and parts[2] == 'import':
                lib = parts[1].split('.')[0]
                if (lib not in libraries and 
                    lib not in common_stdlibs and 
                    not lib.startswith('_')):
                    libraries.append(lib)
    
    return libraries

# التحقق مما إذا كانت المكتبة مسبقة التجميع
def is_lib_precompiled(lib_name):
    return lib_name.lower() in [lib.lower() for lib in PRECOMPILED_LIBS]

# تثبيت المكتبات المطلوبة
def install_required_libraries(libraries, user_id):
    installed_libs = []
    failed_libs = []
    
    for lib in libraries:
        try:
            # تخطي المكتبات الأساسية المثبتة مسبقاً
            if lib in ['telebot', 'requests', 'flask', 'json', 'time', 'os', 'sys', 'subprocess']:
                continue
            
            # تثبيت المكتبة
            install_cmd = ["pip", "install", lib]
            install_process = subprocess.Popen(
                install_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            install_stdout, install_stderr = install_process.communicate()
            
            if install_process.returncode == 0:
                installed_libs.append(lib)
                # تحديث قائمة المكتبات المثبتة للمستخدم
                if lib not in user_libraries.get(str(user_id), []):
                    user_libraries[str(user_id)].append(lib)
            else:
                failed_libs.append((lib, install_stderr))
                
        except Exception as e:
            failed_libs.append((lib, str(e)))
    
    save_data()
    return installed_libs, failed_libs

# تحسين أداء التثبيت بتجميع المكتبات
def optimize_installation(libraries):
    """
    تحسين عملية التثبيت بتجميع المكتبات
    """
    # تجميع المكتبات في أمر تثبيت واحد
    if libraries:
        install_cmd = ["pip", "install"] + libraries
        install_process = subprocess.Popen(
            install_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        install_stdout, install_stderr = install_process.communicate()
        
        return install_process.returncode == 0, install_stdout, install_stderr
    
    return True, "", ""


# تشغيل ملف بايثون مع المكتبات المثبتة
def run_python_file_with_libraries(file_path, user_id):
    try:
        # قراءة محتوى الملف لاكتشاف المكتبات المطلوبة
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # استخراج المكتبات المطلوبة
        required_libs = extract_required_libraries(file_content)
        
        # تثبيت المكتبات المطلوبة
        if required_libs:
            installed, failed = install_required_libraries(required_libs, user_id)
            
            if failed:
                error_msg = "❌ فشل في تثبيت بعض المكتبات:\n"
                for lib, error in failed:
                    error_msg += f"- {lib}: {error[:100]}...\n"
                return None, error_msg
        
        # تشغيل الملف
        start_time = time.time()
        process = subprocess.Popen(
            ['python', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # انتظار التنفيذ لمدة أقصاها 60 ثانية
        try:
            stdout, stderr = process.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return None, "❌ تجاوز وقت التنفيذ (60 ثانية)"
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        result = f"⏱ وقت التنفيذ: {execution_time:.2f} ثانية\n\n"
        
        if stdout:
            result += f"📤 الناتج:\n{stdout}\n"
        
        if stderr:
            result += f"❌ الأخطاء:\n{stderr}"
        
        if not stdout and not stderr:
            result += "✅ تم التشغيل بنجاح بدون ناتج."
        
        return result, None
        
    except Exception as e:
        return None, f"❌ حدث خطأ أثناء التشغيل: {str(e)}"

# معالجة أمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    init_user(user_id)
    
    if len(message.text.split()) > 1:
        invite_code = message.text.split()[1]
        
        if invite_code in premium_invites and not premium_invites[invite_code]['used']:
            points = premium_invites[invite_code]['points']
            users_data[str(user_id)]['ai_requests'] = users_data[str(user_id)].get('ai_requests', 0) + points
            premium_invites[invite_code]['used'] = True
            premium_invites[invite_code]['used_by'] = user_id
            premium_invites[invite_code]['used_date'] = datetime.now().isoformat()
            save_data()
            
            bot.send_message(user_id, f"🎉 لقد حصلت على {points} نقطة بفضل الرابط المميز!")
        
        else:
            for inviter_id, user_data in users_data.items():
                if user_data.get('invite_code') == invite_code and str(user_id) != inviter_id:
                    if str(user_id) not in user_data.get('invited_users', []):
                        user_data['invited_users'].append(str(user_id))
                        user_data['ai_requests'] = user_data.get('ai_requests', 0) + 1
                        user_data['invites'] = user_data.get('invites', 0) + 1
                        users_data[inviter_id] = user_data
                        
                        if str(user_id) in users_data:
                            users_data[str(user_id)]['ai_requests'] = users_data[str(user_id)].get('ai_requests', 0) + 1
                        
                        save_data()
                        bot.send_message(user_id, "🎉 لقد حصلت على طلب إضافي بفضل انضمامك عبر رابط الدعوة!")
                        break
    
    if not check_subscription(user_id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(f"{get_random_emoji()} اشترك في القناة", url=f"https://t.me/{SUBSCRIPTION_CHANNEL[1:]}"),
            InlineKeyboardButton(f"{get_random_emoji()} تحقق من الاشتراك", callback_data="check_subscription")
        )
        
        welcome_text = f"""
{get_random_emoji()} مرحباً

أنا بوت مجاني لرفع وتشغيل ملفات البايثون

للاستفادة من جميع ميزات البوت، يجب عليك الاشتراك في قناتنا أولاً
"""
        bot.send_message(user_id, welcome_text, reply_markup=keyboard)
        return
    
    welcome_text = f"""
{get_random_emoji()} مرحباً

أنا بوت مجاني لرفع وتشغيل ملفات البايثون

{get_random_emoji()} المميزات المتاحة
- رفع وتشغيل ملفات البايثون (بحد أقصى {MAX_FILES_PER_USER} ملفات نشطة)
- عرض وإدارة الملفات
- نظام دعوة للحصول على مزيد من الطلبات
- تثبيت مكتبات بايثون مخصصة
- التعرف التلقائي على المكتبات المطلوبة
- دعم معظم مكتبات بايثون الشائعة

{get_random_emoji()} المكتبات المدعومة تشمل:
- pandas, numpy, matplotlib للبيانات
- requests, beautifulsoup4 للويب
- tensorflow, pytorch, keras للذكاء الاصطناعي
- flask, django للويب
- sqlalchemy, pymysql لقواعد البيانات
- والعديد من المكتبات الأخرى

{get_random_emoji()} لبدء الاستخدام
1. اختر "رفع وتشغيل ملف" لرفع ملف بايثون وتشغيله فوراً
2. أو اختر خيارات أكثر للوصول إلى الميزات الأخرى

{get_random_emoji()} ملاحظة: يمكنك الاحتفاظ بحد أقصى {MAX_FILES_PER_USER} ملفات نشطة في نفس الوقت
"""
    bot.send_message(user_id, welcome_text, reply_markup=create_main_keyboard(user_id))

# معالجة أمر /admin
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "ليس لديك صلاحية الوصول إلى هذه الأداة")
        return
    
    admin_text = f"""
{get_random_emoji()} لوحة إدارة البوت

• عدد المستخدمين: {len(users_data)}
• إجمالي الطلبات: {sum(user.get('ai_requests', 0) for user in users_data.values())}
• الروابط المميزة: {len(premium_invites)}

اختر أحد الخيارات أدناه
"""
    
    bot.send_message(user_id, admin_text, reply_markup=create_admin_keyboard())

# معالجة الردود على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    init_user(user_id)
    
    if call.data == "admin_create_premium" and is_admin(user_id):
        msg = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{get_random_emoji()} أدخل عدد النقاط التي تريد منحها في الرابط المميز"
        )
        bot.register_next_step_handler(msg, process_premium_points)
        return
    
    elif call.data == "admin_stats" and is_admin(user_id):
        total_users = len(users_data)
        total_requests = sum(user.get('ai_requests', 0) for user in users_data.values())
        active_premium = sum(1 for invite in premium_invites.values() if not invite.get('used', False))
        
        stats_text = f"""
{get_random_emoji()} إحصائيات البوت

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
    
    if not check_subscription(user_id) and call.data not in ["check_subscription", "main_menu"]:
        bot.answer_callback_query(call.id, "يجب الاشتراك في القناة أولاً")
        return
    
    if call.data == "main_menu":
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} القائمة الرئيسية",
                reply_markup=create_main_keyboard(user_id)
            )
        except:
            bot.send_message(call.message.chat.id, f"{get_random_emoji()} القائمة الرئيسية", reply_markup=create_main_keyboard(user_id))
    
    elif call.data == "check_subscription":
        if check_subscription(user_id):
            users_data[str(user_id)]['is_subscribed'] = True
            save_data()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} شكراً للاشتراك في قناتنا. الآن يمكنك استخدام جميع ميزات البوت",
                reply_markup=create_main_keyboard(user_id)
            )
        else:
            bot.answer_callback_query(call.id, "لم تشترك بعد في القناة")
    
    elif call.data == "more_options":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{get_random_emoji()} خيارات إضافية",
            reply_markup=create_more_options_keyboard()
        )
    
    elif call.data == "upload_and_run_file":
        if users_data[str(user_id)]['ai_requests'] <= 0:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} ليس لديك نقاط كافية لتشغيل الملف\n\nقم بدعوة أصدقائك للحصول على المزيد من النقاط",
                reply_markup=create_invite_keyboard(user_id)
            )
            return
            
        if check_user_files_limit(user_id):
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} لقد وصلت إلى الحد الأقصى للملفات ({MAX_FILES_PER_USER} ملفات). يرجى حذف بعض الملفات أولاً",
                reply_markup=create_more_options_keyboard()
            )
            return
            
        msg = bot.send_message(call.message.chat.id, f"{get_random_emoji()} أرسل لي ملف بايثون لرفعه وتشغيله فوراً")
        bot.register_next_step_handler(msg, handle_document_and_run)
    
    elif call.data == "upload_file_only":
        if check_user_files_limit(user_id):
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} لقد وصلت إلى الحد الأقصى للملفات ({MAX_FILES_PER_USER} ملفات). يرجى حذف بعض الملفات أولاً",
                reply_markup=create_more_options_keyboard()
            )
            return
            
        msg = bot.send_message(call.message.chat.id, f"{get_random_emoji()} أرسل لي ملف بايثون لرفعه فقط (بدون تشغيل)")
        bot.register_next_step_handler(msg, handle_document_upload_only)
    
    elif call.data == "my_stats":
        user_stats = users_data[str(user_id)]
        user_libs = user_libraries.get(str(user_id), [])
        stats_text = f"""
{get_random_emoji()} إحصائياتك

• الطلبات المتاحة: {user_stats['ai_requests']}
• عدد الدعوات: {user_stats['invites']}
• الملفات المحفوظة: {len(user_stats.get('files', []))}/{MAX_FILES_PER_USER}
• المكتبات المثبتة: {len(user_libs)}
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
            text=f"{get_random_emoji()} رابط الدعوة الخاص بك:\n`{invite_link}`\n\nشارك هذا الرابط مع أصدقائك. عند انضمامهم ستحصل على طلب إضافي",
            parse_mode="Markdown",
            reply_markup=create_invite_keyboard(user_id)
        )
    
    elif call.data.startswith("generate_invite_"):
        target_user_id = int(call.data.split("_")[2])
        if target_user_id != user_id:
            bot.answer_callback_query(call.id, "ليس لديك صلاحية للوصول إلى هذا الرابط")
            return
            
        invite_code = users_data[str(user_id)]['invite_code']
        invite_link = f"https://t.me/{BOT_USERNAME[1:]}?start={invite_code}"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{get_random_emoji()} رابط الدعوة الخاص بك:\n`{invite_link}`\n\nشارك هذا الرابط مع أصدقائك. عند انضمامهم ستحصل على طلب إضافي",
            parse_mode="Markdown",
            reply_markup=create_invite_keyboard(user_id)
        )
    
    elif call.data == "delete_file":
        user_files = users_data[str(user_id)].get('files', [])
        if not user_files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} لا توجد ملفات لحذفها",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        keyboard = InlineKeyboardMarkup()
        for i, file_info in enumerate(user_files):
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} {i+1}. {file_info['name']}", callback_data=f"delete_{file_info['name']}"))
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} رجوع", callback_data="more_options"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{get_random_emoji()} اختر الملف الذي تريد حذفه",
            reply_markup=keyboard
        )
    
    elif call.data.startswith("delete_"):
        file_name = call.data[7:]
        user_files = users_data[str(user_id)].get('files', [])
        
        new_files = [f for f in user_files if f['name'] != file_name]
        users_data[str(user_id)]['files'] = new_files
        save_data()
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{get_random_emoji()} تم حذف الملف: {file_name}",
            reply_markup=create_more_options_keyboard()
        )
    
    elif call.data == "list_files":
        user_files = users_data[str(user_id)].get('files', [])
        if not user_files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} لا توجد ملفات مرفوعة بعد",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        files_list = "\n".join([f"{get_random_emoji()} {f['name']} ({f['date'][:10]})" for f in user_files])
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{get_random_emoji()} الملفات المرفوعة ({len(user_files)}/{MAX_FILES_PER_USER}):\n{files_list}",
            reply_markup=create_more_options_keyboard()
        )
    
    elif call.data == "run_file":
        user_files = users_data[str(user_id)].get('files', [])
        if not user_files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} لا توجد ملفات بايثون لتشغيلها",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        # التحقق من وجود نقاط كافية
        if users_data[str(user_id)]['ai_requests'] <= 0:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} ليس لديك نقاط كافية لتشغيل الملف\n\nقم بدعوة أصدقائك للحصول على المزيد من النقاط",
                reply_markup=create_invite_keyboard(user_id)
            )
            return
        
        keyboard = InlineKeyboardMarkup()
        for i, file_info in enumerate(user_files):
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} {i+1}. {file_info['name']}", callback_data=f"run_{file_info['name']}"))
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} رجوع", callback_data="more_options"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{get_random_emoji()} اختر الملف الذي تريد تشغيله",
            reply_markup=keyboard
        )
    
    elif call.data.startswith("run_"):
        file_name = call.data[4:]
        user_files = users_data[str(user_id)].get('files', [])
        
        file_info = next((f for f in user_files if f['name'] == file_name), None)
        
        if not file_info:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} الملف غير موجود",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        # خصم نقطة واحدة
        users_data[str(user_id)]['ai_requests'] -= 1
        save_data()
        
        status_msg = bot.send_message(call.message.chat.id, f"{get_random_emoji()} جاري تشغيل الملف: {file_name}...")
        
        try:
            file_message = bot.forward_message(user_id, CHANNEL_ID, file_info['message_id'])
            file_info_obj = bot.get_file(file_message.document.file_id)
            downloaded_file = bot.download_file(file_info_obj.file_path)
            
            temp_path = os.path.join(UPLOAD_DIR, file_name)
            with open(temp_path, 'wb') as f:
                f.write(downloaded_file)
            
            # تشغيل الملف مع المكتبات المثبتة
            result, error = run_python_file_with_libraries(temp_path, user_id)
            
            os.remove(temp_path)
            
            if error:
                # إرجاع النقطة في حالة الخطأ
                users_data[str(user_id)]['ai_requests'] += 1
                save_data()
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=status_msg.message_id,
                    text=f"{get_random_emoji()} خطأ في التشغيل:\n{error}\n\nتم إرجاع النقطة إليك. النقاط المتبقية: {users_data[str(user_id)]['ai_requests']}"
                )
            else:
                full_result = f"{get_random_emoji()} الملف: {file_name}\n{result}\n\nتم خصم نقطة واحدة. النقاط المتبقية: {users_data[str(user_id)]['ai_requests']}"
                
                if len(full_result) > 4000:
                    full_result = full_result[:4000] + "...\n\n(تم تقصير النتيجة بسبب الطول)"
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=status_msg.message_id,
                    text=full_result
                )
            
        except Exception as e:
            # إرجاع النقطة في حالة الخطأ
            users_data[str(user_id)]['ai_requests'] += 1
            save_data()
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=status_msg.message_id,
                text=f"{get_random_emoji()} حدث خطأ أثناء التشغيل: {str(e)}\n\nتم إرجاع النقطة إليك. النقاط المتبقية: {users_data[str(user_id)]['ai_requests']}"
            )
    
    elif call.data == "replace_file":
        user_files = users_data[str(user_id)].get('files', [])
        if not user_files:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{get_random_emoji()} لا توجد ملفات لاستبدالها",
                reply_markup=create_more_options_keyboard()
            )
            return
        
        keyboard = InlineKeyboardMarkup()
        for i, file_info in enumerate(user_files):
            keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} {i+1}. {file_info['name']}", callback_data=f"replace_{file_info['name']}"))
        keyboard.add(InlineKeyboardButton(f"{get_random_emoji()} رجوع", callback_data="more_options"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{get_random_emoji()} اختر الملف الذي تريد استبداله",
            reply_markup=keyboard
        )
    
    elif call.data.startswith("replace_"):
        file_name = call.data[8:]
        msg = bot.send_message(call.message.chat.id, f"{get_random_emoji()} أرسل لي الملف الجديد لاستبدال {file_name}")
        bot.register_next_step_handler(msg, handle_replace_file, file_name)
    
    elif call.data == "install_libraries":
        msg = bot.send_message(call.message.chat.id, f"{get_random_emoji()} أرسل أسماء المكتبات التي تريد تثبيتها مفصولة بمسافات:\n\nمثال: requests numpy pandas")
        bot.register_next_step_handler(msg, process_install_libraries)

# معالجة تثبيت المكتبات
def process_install_libraries(message):
    user_id = message.from_user.id
    libraries = message.text.split()
    
    if not libraries:
        bot.send_message(message.chat.id, f"{get_random_emoji()} لم تقم بإرسال أي مكتبات")
        return
    
    # حفظ المكتبات للمستخدم
    user_libraries[str(user_id)] = libraries
    save_data()
    
    bot.send_message(message.chat.id, f"{get_random_emoji()} تم حفظ المكتبات بنجاح: {', '.join(libraries)}\n\nسيتم تثبيت هذه المكتبات تلقائياً عند تشغيل أي ملف")

# معالجة عدد النقاط للرابط المميز
def process_premium_points(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "ليس لديك صلاحية الوصول إلى هذه الأداة")
        return
    
    try:
        points = int(message.text)
        if points <= 0:
            bot.send_message(user_id, "يجب أن يكون عدد النقاط أكبر من الصفر")
            return
        
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
            f"{get_random_emoji()} تم إنشاء الرابط المميز بنجاح!\n\n🎁 عدد النقاط: {points}\n🔗 الرابط: `{invite_link}`\n\nهذا الرابط يعمل لمرة واحدة فقط",
            parse_mode="Markdown"
        )
        
    except ValueError:
        bot.send_message(user_id, "يرجى إدخال رقم صحيح")

# معالجة رفع الملفات وتشغيلها
def handle_document_and_run(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # التحقق من وجود نقاط كافية
    if users_data[str(user_id)]['ai_requests'] <= 0:
        bot.send_message(chat_id, f"{get_random_emoji()} ليس لديك نقاط كافية لتشغيل الملف\n\nقم بدعوة أصدقائك للحصول على المزيد من النقاط")
        return
    
    try:
        if not message.document:
            bot.send_message(chat_id, f"{get_random_emoji()} يرجى إرسال ملف بايثون صالح")
            return
        
        file_name = message.document.file_name
        if not file_name.endswith('.py'):
            bot.send_message(chat_id, f"{get_random_emoji()} يسمح فقط بملفات البايثون (.py)")
            return
        
        # خصم نقطة واحدة
        users_data[str(user_id)]['ai_requests'] -= 1
        save_data()
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_content = downloaded_file.decode('utf-8') if isinstance(downloaded_file, bytes) else downloaded_file
        success, message_text = save_file_to_channel(file_content, file_name, user_id)
        
        if not success:
            # إرجاع النقطة في حالة الخطأ
            users_data[str(user_id)]['ai_requests'] += 1
            save_data()
            
            bot.send_message(chat_id, message_text)
            return
        
        # حفظ الملف مؤقتاً للتشغيل
        temp_path = os.path.join(UPLOAD_DIR, file_name)
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        status_msg = bot.send_message(chat_id, f"{get_random_emoji()} جاري تشغيل الملف: {file_name}...")
        
        # تشغيل الملف مع المكتبات المثبتة
        result, error = run_python_file_with_libraries(temp_path, user_id)
        
        os.remove(temp_path)
        
        if error:
            # إرجاع النقطة في حالة الخطأ
            users_data[str(user_id)]['ai_requests'] += 1
            save_data()
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"{get_random_emoji()} خطأ في التشغيل:\n{error}\n\nتم إرجاع النقطة إليك. النقاط المتبقية: {users_data[str(user_id)]['ai_requests']}"
            )
        else:
            full_result = f"{get_random_emoji()} الملف: {file_name}\n{result}\n\nتم خصم نقطة واحدة. النقاط المتبقية: {users_data[str(user_id)]['ai_requests']}"
            
            if len(full_result) > 4000:
                full_result = full_result[:4000] + "...\n\n(تم تقصير النتيجة بسبب الطول)"
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=full_result
            )
        
        logging.info(f"File uploaded and run: {file_name} by user {user_id}")
    
    except Exception as e:
        # إرجاع النقطة في حالة الخطأ
        users_data[str(user_id)]['ai_requests'] += 1
        save_data()
        
        logging.error(f"Error uploading and running file: {str(e)}")
        bot.send_message(chat_id, f"{get_random_emoji()} حدث خطأ أثناء رفع وتشغيل الملف: {str(e)}\n\nتم إرجاع النقطة إليك. النقاط المتبقية: {users_data[str(user_id)]['ai_requests']}")

# معالجة رفع الملفات فقط (بدون تشغيل)
def handle_document_upload_only(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        if not message.document:
            bot.send_message(chat_id, f"{get_random_emoji()} يرجى إرسال ملف")
            return
        
        file_name = message.document.file_name
        if not file_name.endswith('.py'):
            bot.send_message(chat_id, f"{get_random_emoji()} يسمح فقط بملفات البايثون (.py)")
            return
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_content = downloaded_file.decode('utf-8') if isinstance(downloaded_file, bytes) else downloaded_file
        success, message_text = save_file_to_channel(file_content, file_name, user_id)
        
        if success:
            bot.send_message(chat_id, f"{get_random_emoji()} تم رفع الملف بنجاح: {file_name}")
            logging.info(f"File uploaded: {file_name} by user {user_id}")
        else:
            bot.send_message(chat_id, message_text)
    
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")
        bot.send_message(chat_id, f"{get_random_emoji()} حدث خطأ أثناء رفع الملف: {str(e)}")

# معالجة استبدال الملف
def handle_replace_file(message, old_file_name):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        if not message.document:
            bot.send_message(chat_id, f"{get_random_emoji()} يرجى إرسال ملف")
            return
        
        file_name = message.document.file_name
        if not file_name.endswith('.py'):
            bot.send_message(chat_id, f"{get_random_emoji()} يسمح فقط بملفات البايثون (.py)")
            return
        
        user_files = users_data[str(user_id)].get('files', [])
        users_data[str(user_id)]['files'] = [f for f in user_files if f['name'] != old_file_name]
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_content = downloaded_file.decode('utf-8') if isinstance(downloaded_file, bytes) else downloaded_file
        success, message_text = save_file_to_channel(file_content, file_name, user_id)
        
        if success:
            bot.send_message(chat_id, f"{get_random_emoji()} تم استبدال الملف بنجاح: {old_file_name} → {file_name}")
            logging.info(f"File replaced: {old_file_name} with {file_name} by user {user_id}")
        else:
            bot.send_message(chat_id, message_text)
    
    except Exception as e:
        logging.error(f"Error replacing file: {str(e)}")
        bot.send_message(chat_id, f"{get_random_emoji()} حدث خطأ أثناء استبدال الملف: {str(e)}")

# معالجة أي ملف يرسله المستخدم
@bot.message_handler(content_types=['document'])
def handle_any_document(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # إذا كان المستخدم يريد رفع وتشغيل الملف مباشرة
    if users_data[str(user_id)]['ai_requests'] > 0:
        handle_document_and_run(message)
    else:
        handle_document_upload_only(message)

# ويب هووك
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Invalid content type', 403

# تشغيل البوت
if __name__ == '__main__':
    load_data()
    
    print("🤖 بوت رفع الملفات المجاني يعمل الآن...")
    
    # إعداد ويب هووك
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url='https://autu2.onrender.com/' + BOT_TOKEN)
    
    # تشغيل Flask على البورت 10000
    app.run(host='0.0.0.0', port=10000) 
