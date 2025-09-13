import os
import logging
import json
import requests
import subprocess
import threading
import time
import re
import asyncio
import random
import sqlite3
import tempfile
from datetime import datetime, timedelta
import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup

# توكنات API
TELEGRAM_BOT_TOKEN = "8403108424:AAHnOZp4bsQjlCB4tf2LUl0JbprYvrVESmw"
GEMINI_API_KEY = "AIzaSyA6GqakCMC7zZohjXfUH-pfTB3dmL2F5to"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# إعدادات القناة الخاصة
CHANNEL_ID = -1003091756917  # ايدي القناة الخاصة
ADMIN_ID = 6689435577  # ايدي المدير

# حالات المحادثة
class BotStates(StatesGroup):
    DESCRIPTION = State()
    EDITING = State()
    WAITING_CODE = State()
    WAITING_FILE = State()
    WAITING_NEW_CODE = State()
    WAITING_RUN_MODE = State()

# تخزين العمليات النشطة
active_processes = {}
user_files = {}

# الرموز التعبيرية العشوائية
EMOJIS = ["🍃", "🍀", "🌱", "🌿", "💐", "🌴", "🌾", "🌳", "🐢", "🐉", "🐸", "🐊", "🌵", "🐛", "🌹"]

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# إنشاء البوت مع حالة التخزين
storage = StateMemoryStorage()
bot = AsyncTeleBot(TELEGRAM_BOT_TOKEN, state_storage=storage)

# إعداد قاعدة البيانات
def setup_database():
    conn = sqlite3.connect('bot_files.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_files (
            user_id INTEGER,
            file_name TEXT,
            file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, file_name)
        )
    ''')
    conn.commit()
    conn.close()

def get_random_emoji():
    """إرجاع رمز تعبيري عشوائي"""
    return random.choice(EMOJIS)

@bot.message_handler(commands=['start'])
async def start(message):
    """بدء المحادثة مع أزرار إنشاء البوت والخيارات"""
    emoji1 = get_random_emoji()
    emoji2 = get_random_emoji()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"{emoji1} إنشاء بوت بالذكاء الاصطناعي", callback_data='create_bot'))
    keyboard.add(types.InlineKeyboardButton(f"{emoji2} خيارات مفيدة", callback_data='useful_options'))
    
    await bot.send_message(
        message.chat.id,
        "مرحباً أنا بوت لإنشاء بوتات تلجرام متطورة\n\n"
        "يمكنك إنشاء بوتات باستخدام الذكاء الاصطناعي أو استخدام الخيارات المتقدمة",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'create_bot')
async def handle_create_bot(call):
    """بدء عملية إنشاء البوت بالذكاء الاصطناعي"""
    await bot.answer_callback_query(call.id)
    await bot.set_state(call.from_user.id, BotStates.DESCRIPTION, call.message.chat.id)
    
    await bot.edit_message_text(
        "يرجى وصف البوت الذي تريد إنشاءه بالتفصيل، وتأكد من تضمين\n"
        "• الوظائف المطلوبة\n"
        "• التوكن إذا كان لديك (أو اكتب أحتاج توكن وسأساعدك)\n"
        "• أي متطلبات خاصة\n\n"
        "مثال: أريد بوت لإدارة مجموعة مع خاصية الترحيب بالأعضاء الجدد، وحذف الرسائل غير المرغوب فيها، وتوكن البوت هو: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == 'useful_options')
async def handle_useful_options(call):
    """عرض خيارات مفيدة"""
    await bot.answer_callback_query(call.id)
    
    emoji1 = get_random_emoji()
    emoji2 = get_random_emoji()
    emoji3 = get_random_emoji()
    emoji4 = get_random_emoji()
    emoji5 = get_random_emoji()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"{emoji1} رفع ملف جاهز", callback_data='upload_file'))
    keyboard.add(types.InlineKeyboardButton(f"{emoji2} إنشاء ملف", callback_data='create_file'))
    keyboard.add(types.InlineKeyboardButton(f"{emoji3} حذف ملف", callback_data='delete_file'))
    keyboard.add(types.InlineKeyboardButton(f"{emoji4} استبدال ملف", callback_data='replace_file'))
    keyboard.add(types.InlineKeyboardButton(f"{emoji5} الرجوع للقائمة الرئيسية", callback_data='back_to_main'))
    
    await bot.edit_message_text(
        "خيارات مفيدة\n\n"
        "اختر أحد الخيارات التالية:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
async def handle_back_to_main(call):
    """العودة إلى القائمة الرئيسية"""
    await bot.answer_callback_query(call.id)
    
    emoji1 = get_random_emoji()
    emoji2 = get_random_emoji()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"{emoji1} إنشاء بوت بالذكاء الاصطناعي", callback_data='create_bot'))
    keyboard.add(types.InlineKeyboardButton(f"{emoji2} خيارات مفيدة", callback_data='useful_options'))
    
    await bot.edit_message_text(
        "مرحباً أنا بوت لإنشاء بوتات تلجرام متطورة\n\n"
        "يمكنك إنشاء بوتات باستخدام الذكاء الاصطناعي أو استخدام الخيارات المتقدمة",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'upload_file')
async def handle_upload_file(call):
    """معالجة رفع ملف جاهز"""
    await bot.answer_callback_query(call.id)
    await bot.set_state(call.from_user.id, BotStates.WAITING_FILE, call.message.chat.id)
    
    await bot.edit_message_text(
        "يرجى إرسال ملف Python الذي تريد رفعه:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == 'create_file')
async def handle_create_file(call):
    """بدء عملية إنشاء ملف"""
    await bot.answer_callback_query(call.id)
    await bot.set_state(call.from_user.id, BotStates.WAITING_CODE, call.message.chat.id)
    
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['code_parts'] = []
    
    await bot.edit_message_text(
        "يرجى إرسال كود Python الذي تريد حفظه في ملف.\n"
        "يمكنك إرسال الكود على عدة رسائل، وعند الانتهاء ارسل done",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(state=BotStates.WAITING_CODE, content_types=['text'])
async def handle_code_input(message):
    """معالجة إدخال الكود"""
    code_part = message.text
    
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if 'code_parts' not in data:
            data['code_parts'] = []
        data['code_parts'].append(code_part)
    
    await bot.send_message(message.chat.id, "تم حفظ جزء الكود. استمر في إرسال الأجزاء أو ارسل done عند الانتهاء")

@bot.message_handler(state=BotStates.WAITING_CODE, func=lambda message: message.text.lower() == 'done')
async def handle_done_code(message):
    """إنهاء عملية إنشاء الملف"""
    user_id = message.from_user.id
    
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        code_parts = data.get('code_parts', [])
    
    if not code_parts:
        await bot.send_message(message.chat.id, "لم يتم إرسال أي كود. يرجى المحاولة مرة أخرى.")
        await bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    # جمع جميع أجزاء الكود
    full_code = "\n".join(code_parts)
    
    # حفظ الكود في ملف مؤقت
    temp_filename = f"temp_{user_id}_{int(time.time())}.py"
    with open(temp_filename, 'w', encoding='utf-8') as f:
        f.write(full_code)
    
    # رفع الملف إلى القناة الخاصة
    try:
        with open(temp_filename, 'rb') as f:
            sent_message = await bot.send_document(
                CHANNEL_ID,
                f,
                caption=f"ملف المستخدم: {user_id}"
            )
        
        file_id = sent_message.document.file_id
        final_filename = f"user_{user_id}_{int(time.time())}.py"
        
        # حفظ معلومات الملف في قاعدة البيانات
        conn = sqlite3.connect('bot_files.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_files (user_id, file_name, file_id) VALUES (?, ?, ?)",
            (user_id, final_filename, file_id)
        )
        conn.commit()
        conn.close()
        
        # تحديث قائمة الملفات المحلية
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append(final_filename)
        
        # إرسال الملف مع أزرار التشغيل
        emoji1 = get_random_emoji()
        emoji2 = get_random_emoji()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{emoji1} تشغيل الملف", callback_data=f'run_file:{final_filename}'))
        keyboard.add(types.InlineKeyboardButton(f"{emoji2} حذف الملف", callback_data=f'delete_file:{final_filename}'))
        
        # إرسال الملف للمستخدم
        await bot.send_document(
            message.chat.id,
            file_id,
            caption="تم حفظ الملف بنجاح",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error uploading file to channel: {e}")
        await bot.send_message(message.chat.id, "حدث خطأ أثناء حفظ الملف")
    
    finally:
        # حذف الملف المؤقت
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    
    await bot.delete_state(message.from_user.id, message.chat.id)

@bot.message_handler(state=BotStates.WAITING_FILE, content_types=['document'])
async def handle_file_upload(message):
    """معالجة رفع الملف"""
    user_id = message.from_user.id
    document = message.document
    
    if not document.file_name.endswith('.py'):
        await bot.send_message(message.chat.id, "يرجى رفع ملف Python فقط (امتداد .py)")
        await bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    try:
        # تحميل الملف
        file_info = await bot.get_file(document.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        temp_filename = f"temp_{user_id}_{document.file_name}"
        
        with open(temp_filename, 'wb') as f:
            f.write(downloaded_file)
        
        # رفع الملف إلى القناة الخاصة
        with open(temp_filename, 'rb') as f:
            sent_message = await bot.send_document(
                CHANNEL_ID,
                f,
                caption=f"ملف المستخدم: {user_id}"
            )
        
        file_id = sent_message.document.file_id
        final_filename = f"user_{user_id}_{document.file_name}"
        
        # حفظ معلومات الملف في قاعدة البيانات
        conn = sqlite3.connect('bot_files.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_files (user_id, file_name, file_id) VALUES (?, ?, ?)",
            (user_id, final_filename, file_id)
        )
        conn.commit()
        conn.close()
        
        # تحديث قائمة الملفات المحلية
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append(final_filename)
        
        # إرسال أزرار التشغيل
        emoji1 = get_random_emoji()
        emoji2 = get_random_emoji()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{emoji1} تشغيل الملف", callback_data=f'run_file:{final_filename}'))
        keyboard.add(types.InlineKeyboardButton(f"{emoji2} حذف الملف", callback_data=f'delete_file:{final_filename}'))
        
        await bot.send_message(
            message.chat.id,
            f"تم رفع الملف بنجاح: {document.file_name}",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error handling file upload: {e}")
        await bot.send_message(message.chat.id, "حدث خطأ أثناء رفع الملف")
    
    finally:
        # حذف الملف المؤقت
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    
    await bot.delete_state(message.from_user.id, message.chat.id)

async def load_user_files(user_id):
    """تحميل ملفات المستخدم من قاعدة البيانات"""
    try:
        conn = sqlite3.connect('bot_files.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_name FROM user_files WHERE user_id = ?",
            (user_id,)
        )
        files = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].extend(files)
        
        return files
    except Exception as e:
        logger.error(f"Error loading user files: {e}")
        return []

@bot.callback_query_handler(func=lambda call: call.data == 'delete_file')
async def handle_delete_file(call):
    """عرض قائمة الملفات للحذف"""
    await bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    files = await load_user_files(user_id)
    
    if not files:
        await bot.edit_message_text(
            "لا توجد ملفات لحذفها",
            call.message.chat.id,
            call.message.message_id
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for filename in files:
        short_name = os.path.basename(filename)
        emoji = get_random_emoji()
        keyboard.add(types.InlineKeyboardButton(f"{emoji} {short_name}", callback_data=f'confirm_delete:{filename}'))
    
    emoji_back = get_random_emoji()
    keyboard.add(types.InlineKeyboardButton(f"{emoji_back} الرجوع", callback_data='useful_options'))
    
    await bot.edit_message_text(
        "اختر الملف الذي تريد حذفه",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete:'))
async def handle_confirm_delete(call):
    """تأكيد حذف الملف"""
    await bot.answer_callback_query(call.id)
    
    filename = call.data.split(':', 1)[1]
    user_id = call.from_user.id
    
    try:
        # حذف من قاعدة البيانات
        conn = sqlite3.connect('bot_files.db')
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_files WHERE user_id = ? AND file_name = ?",
            (user_id, filename)
        )
        conn.commit()
        conn.close()
        
        # حذف من القائمة المحلية
        if user_id in user_files and filename in user_files[user_id]:
            user_files[user_id].remove(filename)
        
        await bot.edit_message_text(
            "تم حذف الملف بنجاح",
            call.message.chat.id,
            call.message.message_id
        )
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        await bot.edit_message_text(
            "حدث خطأ أثناء حذف الملف",
            call.message.chat.id,
            call.message.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data == 'replace_file')
async def handle_replace_file(call):
    """عرض قائمة الملفات للاستبدال"""
    await bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    files = await load_user_files(user_id)
    
    if not files:
        await bot.edit_message_text(
            "لا توجد ملفات لاستبدالها",
            call.message.chat.id,
            call.message.message_id
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for filename in files:
        short_name = os.path.basename(filename)
        emoji = get_random_emoji()
        keyboard.add(types.InlineKeyboardButton(f"{emoji} {short_name}", callback_data=f'select_replace:{filename}'))
    
    emoji_back = get_random_emoji()
    keyboard.add(types.InlineKeyboardButton(f"{emoji_back} الرجوع", callback_data='useful_options'))
    
    await bot.edit_message_text(
        "اختر الملف الذي تريد استبداله",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_replace:'))
async def handle_select_replace(call):
    """اختيار الملف للاستبدال"""
    await bot.answer_callback_query(call.id)
    
    filename = call.data.split(':', 1)[1]
    
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['replace_filename'] = filename
    
    await bot.set_state(call.from_user.id, BotStates.WAITING_NEW_CODE, call.message.chat.id)
    
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['code_parts'] = []
    
    await bot.edit_message_text(
        f"يرجى إرسال الكود الجديد لملف {os.path.basename(filename)}.\n"
        "يمكنك إرسال الكود على عدة رسائل، وعند الانتهاء ارسل done",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(state=BotStates.WAITING_NEW_CODE, content_types=['text'])
async def handle_new_code_input(message):
    """معالجة إدخال الكود الجديد"""
    code_part = message.text
    
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if 'code_parts' not in data:
            data['code_parts'] = []
        data['code_parts'].append(code_part)
    
    await bot.send_message(message.chat.id, "تم حفظ جزء الكود. استمر في إرسال الأجزاء أو ارسل done عند الانتهاء")

@bot.message_handler(state=BotStates.WAITING_NEW_CODE, func=lambda message: message.text.lower() == 'done')
async def handle_done_new_code(message):
    """إنهاء عملية استبدال الملف"""
    user_id = message.from_user.id
    
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        code_parts = data.get('code_parts', [])
        filename = data.get('replace_filename')
    
    if not code_parts or not filename:
        await bot.send_message(message.chat.id, "لم يتم إرسال أي كود أو لم يتم تحديد ملف. يرجى المحاولة مرة أخرى")
        await bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    # جمع جميع أجزاء الكود
    full_code = "\n".join(code_parts)
    
    # حفظ الكود في ملف مؤقت
    temp_filename = f"temp_{user_id}_{int(time.time())}.py"
    with open(temp_filename, 'w', encoding='utf-8') as f:
        f.write(full_code)
    
    try:
        # رفع الملف الجديد إلى القناة الخاصة
        with open(temp_filename, 'rb') as f:
            sent_message = await bot.send_document(
                CHANNEL_ID,
                f,
                caption=f"ملف مستبدل للمستخدم: {user_id}"
            )
        
        file_id = sent_message.document.file_id
        
        # تحديث معلومات الملف في قاعدة البيانات
        conn = sqlite3.connect('bot_files.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_files SET file_id = ? WHERE user_id = ? AND file_name = ?",
            (file_id, user_id, filename)
        )
        conn.commit()
        conn.close()
        
        # إرسال الملف مع أزرار التشغيل
        emoji1 = get_random_emoji()
        emoji2 = get_random_emoji()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{emoji1} تشغيل الملف", callback_data=f'run_file:{filename}'))
        keyboard.add(types.InlineKeyboardButton(f"{emoji2} حذف الملف", callback_data=f'delete_file:{filename}'))
        
        # إرسال الملف للمستخدم
        await bot.send_document(
            message.chat.id,
            file_id,
            caption="تم استبدال الملف بنجاح",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error replacing file: {e}")
        await bot.send_message(message.chat.id, "حدث خطأ أثناء استبدال الملف")
    
    finally:
        # حذف الملف المؤقت
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    
    await bot.delete_state(message.from_user.id, message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_file:'))
async def handle_run_file(call):
    """طلب وضع التشغيل للملف"""
    await bot.answer_callback_query(call.id)
    
    filename = call.data.split(':', 1)[1]
    
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['selected_file'] = filename
    
    await bot.set_state(call.from_user.id, BotStates.WAITING_RUN_MODE, call.message.chat.id)
    
    emoji1 = get_random_emoji()
    emoji2 = get_random_emoji()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"{emoji1} التشغيل الدائم", callback_data='run_permanent'))
    keyboard.add(types.InlineKeyboardButton(f"{emoji2} التشغيل للتطوير (10 دقائق)", callback_data='run_development'))
    
    await bot.edit_message_text(
        "اختر وضع التشغيل:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(state=BotStates.WAITING_RUN_MODE, func=lambda call: call.data in ['run_permanent', 'run_development'])
async def handle_run_mode(call):
    """معالجة اختيار وضع التشغيل"""
    await bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        filename = data.get('selected_file')
    
    mode = call.data
    
    if not filename:
        await bot.edit_message_text(
            "لم يتم تحديد ملف للتشغيل",
            call.message.chat.id,
            call.message.message_id
        )
        await bot.delete_state(user_id, call.message.chat.id)
        return
    
    # جلب file_id من قاعدة البيانات
    conn = sqlite3.connect('bot_files.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT file_id FROM user_files WHERE user_id = ? AND file_name = ?",
        (user_id, filename)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await bot.edit_message_text(
            "الملف غير موجود",
            call.message.chat.id,
            call.message.message_id
        )
        await bot.delete_state(user_id, call.message.chat.id)
        return
    
    file_id = result[0]
    
    # تحميل الملف من القناة
    try:
        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        local_filename = f"run_{user_id}_{os.path.basename(filename)}"
        
        with open(local_filename, 'wb') as f:
            f.write(downloaded_file)
        
        # تشغيل الملف حسب الوضع المختار
        if mode == 'run_permanent':
            await run_file_permanent(call, local_filename, user_id)
        else:  # run_development
            await run_file_development(call, local_filename, user_id)
            
    except Exception as e:
        logger.error(f"Error running file: {e}")
        await bot.edit_message_text(
            "حدث خطأ أثناء تشغيل الملف",
            call.message.chat.id,
            call.message.message_id
        )
    
    await bot.delete_state(user_id, call.message.chat.id)

async def run_file_permanent(call, filename, user_id):
    """تشغيل الملف بشكل دائم"""
    await bot.edit_message_text(
        "جاري التشغيل الدائم للملف...",
        call.message.chat.id,
        call.message.message_id
    )
    
    try:
        # تشغيل الملف في عملية منفصلة
        process = subprocess.Popen(
            ["python", filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # تخزين المعلومات حول العملية
        active_processes[user_id] = {
            'process': process,
            'filename': filename,
            'mode': 'permanent',
            'start_time': datetime.now()
        }
        
        # إنشاء أزرار للتحكم
        emoji1 = get_random_emoji()
        emoji2 = get_random_emoji()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{emoji1} إيقاف التشغيل", callback_data=f'stop_process:{filename}'))
        keyboard.add(types.InlineKeyboardButton(f"{emoji2} عرض السجلات", callback_data=f'show_logs:{filename}'))
        
        await bot.edit_message_text(
            "تم تشغيل الملف بشكل دائم",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in permanent run: {e}")
        await bot.edit_message_text(
            "حدث خطأ أثناء التشغيل الدائم للملف",
            call.message.chat.id,
            call.message.message_id
        )

async def run_file_development(call, filename, user_id):
    """تشغيل الملف لوضع التطوير (10 دقائق)"""
    await bot.edit_message_text(
        "جاري تشغيل الملف لوضع التطوير (10 دقائق)...",
        call.message.chat.id,
        call.message.message_id
    )
    
    try:
        # تشغيل الملف في عملية منفصلة
        process = subprocess.Popen(
            ["python", filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # تخزين المعلومات حول العملية
        end_time = datetime.now() + timedelta(minutes=10)
        active_processes[user_id] = {
            'process': process,
            'end_time': end_time,
            'filename': filename,
            'mode': 'development',
            'start_time': datetime.now()
        }
        
        # إنشاء مؤقت لإنهاء العملية بعد 10 دقائق
        def stop_process(user_id):
            time.sleep(600)  # 10 دقائق
            if user_id in active_processes:
                try:
                    active_processes[user_id]['process'].terminate()
                    active_processes[user_id]['process'].wait(timeout=5)
                except:
                    try:
                        active_processes[user_id]['process'].kill()
                    except:
                        pass
                finally:
                    if user_id in active_processes:
                        del active_processes[user_id]
        
        threading.Thread(target=stop_process, args=(user_id,), daemon=True).start()
        
        # إنشاء أزرار للتحكم
        emoji1 = get_random_emoji()
        emoji2 = get_random_emoji()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{emoji1} إيقاف التشغيل", callback_data=f'stop_process:{filename}'))
        keyboard.add(types.InlineKeyboardButton(f"{emoji2} عرض السجلات", callback_data=f'show_logs:{filename}'))
        
        await bot.edit_message_text(
            f"تم تشغيل الملف لوضع التطوير وسيعمل حتى: {end_time.strftime('%H:%M:%S')}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in development run: {e}")
        await bot.edit_message_text(
            "حدث خطأ أثناء تشغيل الملف لوضع التطوير",
            call.message.chat.id,
            call.message.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_process:'))
async def handle_stop_process(call):
    """إيقاف عملية التشغيل"""
    await bot.answer_callback_query(call.id)
    
    filename = call.data.split(':', 1)[1]
    user_id = call.from_user.id
    
    if user_id in active_processes and active_processes[user_id]['filename'] == filename:
        try:
            active_processes[user_id]['process'].terminate()
            active_processes[user_id]['process'].wait(timeout=5)
        except:
            try:
                active_processes[user_id]['process'].kill()
            except:
                pass
        finally:
            if user_id in active_processes:
                del active_processes[user_id]
        
        await bot.edit_message_text(
            "تم إيقاف التشغيل بنجاح",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        await bot.edit_message_text(
            "لا توجد عملية نشطة لهذا الملف",
            call.message.chat.id,
            call.message.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_logs:'))
async def handle_show_logs(call):
    """عرض سجلات التشغيل"""
    await bot.answer_callback_query(call.id)
    
    filename = call.data.split(':', 1)[1]
    user_id = call.from_user.id
    
    if user_id in active_processes and active_processes[user_id]['filename'] == filename:
        process = active_processes[user_id]['process']
        try:
            # محاولة قراءة السجلات بدون انتظار
            stdout, stderr = process.communicate(timeout=1)
            logs = f"سجلات الملف:\n\nstdout:\n{stdout}\n\nstderr:\n{stderr}"
            
            if len(logs) > 4000:
                logs = logs[:4000] + "... (السجلات طويلة جداً)"
                
            await bot.edit_message_text(
                logs,
                call.message.chat.id,
                call.message.message_id
            )
        except subprocess.TimeoutExpired:
            # العملية لا تزال تعمل، لا توجد سجلات جديدة
            await bot.edit_message_text(
                "الملف لا يزال يعمل ولم تظهر سجلات جديدة بعد",
                call.message.chat.id,
                call.message.message_id
            )
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            await bot.edit_message_text(
                "حدث خطأ أثناء قراءة السجلات",
                call.message.chat.id,
                call.message.message_id
            )
    else:
        await bot.edit_message_text(
            "لا توجد عملية نشطة لهذا الملف",
            call.message.chat.id,
            call.message.message_id
        )

@bot.message_handler(state=BotStates.DESCRIPTION, content_types=['text'])
async def generate_bot(message):
    """إنشاء كود البوت باستخدام Gemini API"""
    user_description = message.text
    
    # استخراج التوكن من الوصف
    token_pattern = r'\d{8,10}:[A-Za-z0-9_-]{35}'
    match = re.search(token_pattern, user_description)
    bot_token = match.group(0) if match else None
    
    # إظهار رسالة الانتظار
    wait_msg = await bot.send_message(message.chat.id, "جاري تحليل طلبك وإنشاء البوت...")
    
    # استدعاء Gemini API
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    
    prompt = f"""
    قم بإنشاء بوت تلجرام كامل باستخدام Python ومكتبة pyTelegramBotAPI (telebot).
    المتطلبات: {user_description}
    
    المتطلبات الفنية:
    - استخدم Python 3.8+
    - استخدم مكتبة pyTelegramBotAPI (telebot)
    - أضف تعليقات باللغة العربية في الكود
    - تأكد من أن الكود يعمل بدون أخطاء
    - أضف توكن البوت في متغير BOT_TOKEN (استخدم القيمة: {bot_token or "YOUR_BOT_TOKEN_HERE"})
    - تأكد من معالجة جميع الأخطاء
    - أضف أوامر أساسية مثل start و help
    - أضف في بداية الملف تعليقات تحتوي على اسم البوت ووصفه
    - تأكد من أن البوت يمكن تشغيله مباشرة
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
        response = requests.post(GEMINI_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        # استخراج النص من الاستجابة
        generated_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # استخراج كود البايثون من النص
        code_start = generated_text.find('```python')
        if code_start == -1:
            code_start = generated_text.find('```')
        
        if code_start != -1:
            code_end = generated_text.find('```', code_start + 3)
            code = generated_text[code_start + 3:code_end].strip()
            if code.startswith('python'):
                code = code[6:].strip()
        else:
            code = generated_text
        
        # حفظ الكود في بيانات المستخدم
        async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['current_code'] = code
            data['bot_token'] = bot_token
        
        # إرسال الكود كملف
        user_id = message.from_user.id
        filename = f"bot_{user_id}.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        
        await bot.delete_message(message.chat.id, wait_msg.message_id)
        
        # إنشاء أزرار
        keyboard = types.InlineKeyboardMarkup()
        
        if bot_token:
            keyboard.add(types.InlineKeyboardButton("تشغيل البوت", callback_data='run_bot'))
        else:
            keyboard.add(types.InlineKeyboardButton("إضافة توكن وتشغيل", callback_data='add_token'))
        
        keyboard.add(types.InlineKeyboardButton("تعديل الكود", callback_data='edit_code'))
        keyboard.add(types.InlineKeyboardButton("عرض الكود", callback_data='show_code'))
        
        caption = "تم إنشاء البوت بنجاح!"
        
        if not bot_token:
            caption += "\nلم يتم العثور على توكن في الوصف. سيطلب منك التوكن عند التشغيل."
        
        with open(filename, 'rb') as f:
            await bot.send_document(
                message.chat.id,
                f,
                caption=caption,
                reply_markup=keyboard
            )
        
        await bot.delete_state(message.from_user.id, message.chat.id)
        
    except Exception as e:
        logger.error(f"Error generating bot: {e}")
        await bot.delete_message(message.chat.id, wait_msg.message_id)
        await bot.send_message(message.chat.id, "عذراً، حدث خطأ أثناء إنشاء البوت. يرجى المحاولة مرة أخرى.")
        await bot.delete_state(message.from_user.id, message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == 'edit_code')
async def handle_edit_code(call):
    """بدء عملية تعديل الكود"""
    await bot.answer_callback_query(call.id)
    await bot.set_state(call.from_user.id, BotStates.EDITING, call.message.chat.id)
    
    await bot.edit_message_text(
        "يرجى إرسال التعديلات المطلوبة على الكود:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(state=BotStates.EDITING, content_types=['text'])
async def handle_edit(message):
    """معالجة التعديلات على الكود"""
    edit_request = message.text
    
    # إظهار رسالة الانتظار
    wait_msg = await bot.send_message(message.chat.id, "جاري معالجة التعديلات...")
    
    # استدعاء Gemini API لتعديل الكود
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        original_code = data.get('current_code', '')
    
    prompt = f"""
    لدي كود بوت تلجرام بالبايثون باستخدام telebot:
    {original_code}
    
    المطلوب إجراء هذه التعديلات:
    {edit_request}
    
    يرجى إعادة الكود كاملاً مع التعديلات المطلوبة.
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
        response = requests.post(GEMINI_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        # استخراج النص من الاستجابة
        generated_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # استخراج كود البايثون من النص
        code_start = generated_text.find('```python')
        if code_start == -1:
            code_start = generated_text.find('```')
        
        if code_start != -1:
            code_end = generated_text.find('```', code_start + 3)
            code = generated_text[code_start + 3:code_end].strip()
            if code.startswith('python'):
                code = code[6:].strip()
        else:
            code = generated_text
        
        # حفظ الكود المعدل في بيانات المستخدم
        async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['current_code'] = code
        
        # إرسال الكود المعدل كملف
        user_id = message.from_user.id
        filename = f"bot_{user_id}_modified.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        
        await bot.delete_message(message.chat.id, wait_msg.message_id)
        
        # إنشاء أزرار
        keyboard = types.InlineKeyboardMarkup()
        
        async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            if data.get('bot_token'):
                keyboard.add(types.InlineKeyboardButton("تشغيل البوت", callback_data='run_bot'))
            else:
                keyboard.add(types.InlineKeyboardButton("إضافة توكن وتشغيل", callback_data='add_token'))
        
        keyboard.add(types.InlineKeyboardButton("تعديل الكود", callback_data='edit_code'))
        keyboard.add(types.InlineKeyboardButton("عرض الكود", callback_data='show_code'))
        
        with open(filename, 'rb') as f:
            await bot.send_document(
                message.chat.id,
                f,
                caption="تم تعديل البوت بنجاح!",
                reply_markup=keyboard
            )
        
        await bot.delete_state(message.from_user.id, message.chat.id)
        
    except Exception as e:
        logger.error(f"Error editing bot: {e}")
        await bot.delete_message(message.chat.id, wait_msg.message_id)
        await bot.send_message(message.chat.id, "عذراً، حدث خطأ أثناء تعديل البوت. يرجى المحاولة مرة أخرى.")
        await bot.delete_state(message.from_user.id, message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == 'add_token')
async def handle_add_token(call):
    """طلب إدخال التوكن من المستخدم"""
    await bot.answer_callback_query(call.id)
    
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['waiting_for_token'] = True
    
    await bot.edit_message_text(
        "يرجى إرسال توكن البوت:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda message: message.text and len(message.text) > 30)
async def handle_token_input(message):
    """معالجة إدخال التوكن من المستخدم"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    async with bot.retrieve_data(user_id, chat_id) as data:
        if not data.get('waiting_for_token'):
            return
        
        token = message.text.strip()
        data['bot_token'] = token
        data['waiting_for_token'] = False
        
        # تحديث الكود بإضافة التوكن
        code = data.get('current_code', '')
        if "YOUR_BOT_TOKEN_HERE" in code:
            code = code.replace("YOUR_BOT_TOKEN_HERE", token)
        elif "BOT_TOKEN" in code:
            # البحث عن سطر يحتوي على BOT_TOKEN واستبداله
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if "BOT_TOKEN" in line and "=" in line:
                    lines[i] = f'BOT_TOKEN = "{token}"'
            code = '\n'.join(lines)
        
        data['current_code'] = code
    
    # حفظ الكود المحدث
    filename = f"bot_{user_id}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(code)
    
    await bot.send_message(chat_id, "تم حفظ التوكن. جاري تشغيل البوت...")
    
    # تشغيل البوت
    await run_generated_bot_from_message(message)

async def run_generated_bot_from_message(message):
    """تشغيل البوت من رسالة عادية"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    async with bot.retrieve_data(user_id, chat_id) as data:
        code = data.get('current_code', '')
        token = data.get('bot_token')
    
    if not token:
        await bot.send_message(chat_id, "لم يتم تحديد توكن البوت. يرجى إرسال التوكن أولاً.")
        return
    
    # حفظ الكود
    filename = f"bot_{user_id}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # تشغيل البوت
    await run_bot_process_message(message, filename, user_id)

async def run_bot_process_message(message, filename, user_id):
    """تشغيل عملية البوت من رسالة"""
    # تشغيل البوت
    run_msg = await bot.send_message(message.chat.id, "جاري تشغيل البوت...")
    
    # تشغيل البوت في عملية منفصلة
    process = subprocess.Popen(
        ["python", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # تخزين المعلومات حول العملية
    end_time = datetime.now() + timedelta(minutes=10)
    active_processes[user_id] = {
        'process': process,
        'end_time': end_time,
        'filename': filename
    }
    
    # إنشاء مؤقت لإنهاء العملية بعد 10 دقائق
    def stop_bot(user_id):
        time.sleep(600)  # 10 دقائق
        if user_id in active_processes:
            try:
                active_processes[user_id]['process'].terminate()
                active_processes[user_id]['process'].wait(timeout=5)
            except:
                try:
                    active_processes[user_id]['process'].kill()
                except:
                    pass
            finally:
                if user_id in active_processes:
                    del active_processes[user_id]
    
    threading.Thread(target=stop_bot, args=(user_id,), daemon=True).start()
    
    # إنشاء أزرار للتحكم
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("إيقاف البوت الآن", callback_data='stop_bot'))
    keyboard.add(types.InlineKeyboardButton("عرض السجلات", callback_data='show_logs'))
    
    success_msg = f"تم تشغيل البوت بنجاح وسيعمل حتى: {end_time.strftime('%H:%M:%S')}"
    
    await bot.edit_message_text(
        success_msg,
        chat_id=message.chat.id,
        message_id=run_msg.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'run_bot')
async def handle_run_bot(call):
    """تشغيل البوت من زر"""
    await bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    async with bot.retrieve_data(user_id, chat_id) as data:
        code = data.get('current_code', '')
        token = data.get('bot_token')
    
    if not token:
        await bot.edit_message_text(
            "لم يتم العثور على توكن البوت. يرجى استخدام زر إضافة توكن وتشغيل أولاً.",
            chat_id,
            call.message.message_id
        )
        return
    
    # حفظ الكود
    filename = f"bot_{user_id}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # تشغيل البوت
    await run_bot_process_call(call, filename, user_id)

async def run_bot_process_call(call, filename, user_id):
    """تشغيل عملية البوت من استدعاء زر"""
    # تشغيل البوت
    await bot.edit_message_text(
        "جاري تشغيل البوت...",
        call.message.chat.id,
        call.message.message_id
    )
    
    # تشغيل البوت في عملية منفصلة
    process = subprocess.Popen(
        ["python", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # تخزين المعلومات حول العملية
    end_time = datetime.now() + timedelta(minutes=10)
    active_processes[user_id] = {
        'process': process,
        'end_time': end_time,
        'filename': filename
    }
    
    # إنشاء مؤقت لإنهاء العملية بعد 10 دقائق
    def stop_bot(user_id):
        time.sleep(600)  # 10 دقائق
        if user_id in active_processes:
            try:
                active_processes[user_id]['process'].terminate()
                active_processes[user_id]['process'].wait(timeout=5)
            except:
                try:
                    active_processes[user_id]['process'].kill()
                except:
                    pass
            finally:
                if user_id in active_processes:
                    del active_processes[user_id]
    
    threading.Thread(target=stop_bot, args=(user_id,), daemon=True).start()
    
    # إنشاء أزرار للتحكم
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("إيقاف البوت الآن", callback_data='stop_bot'))
    keyboard.add(types.InlineKeyboardButton("عرض السجلات", callback_data='show_logs'))
    
    success_msg = f"تم تشغيل البوت بنجاح وسيعمل حتى: {end_time.strftime('%H:%M:%S')}"
    
    await bot.edit_message_text(
        success_msg,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'show_code')
async def handle_show_code(call):
    """عرض الكود الحالي"""
    await bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    async with bot.retrieve_data(user_id, chat_id) as data:
        code = data.get('current_code', '')
    
    if len(code) > 4000:
        code = code[:4000] + "... (الكود طويل جداً)"
    
    await bot.edit_message_text(
        f"الكود الحالي:\n\n```python\n{code}\n```",
        chat_id,
        call.message.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['cancel'])
async def cancel(message):
    """إلغاء المحادثة"""
    await bot.send_message(message.chat.id, 'تم إلغاء العملية.')
    await bot.delete_state(message.from_user.id, message.chat.id)

@bot.message_handler(func=lambda message: True)
async def echo_all(message):
    """معالجة الرسائل الأخرى"""
    await bot.send_message(message.chat.id, "لم أفهم طلبك. يرجى استخدام الأوامر المتاحة.")

async def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # إعداد قاعدة البيانات
    setup_database()
    
    # تشغيل البوت
    await bot.infinity_polling()

if __name__ == '__main__':
    asyncio.run(main())
