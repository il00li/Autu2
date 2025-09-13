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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# توكنات API
TELEGRAM_BOT_TOKEN = "8403108424:AAHnOZp4bsQjlCB4tf2LUl0JbprYvrVESmw"
GEMINI_API_KEY = "AIzaSyA6GqakCMC7zZohjXfUH-pfTB3dmL2F5to"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# إعدادات القناة الخاصة
CHANNEL_ID = -1003091756917  # ايدي القناة الخاصة
ADMIN_ID = 6689435577  # ايدي المدير

# حالات المحادثة
DESCRIPTION, EDITING, WAITING_CODE, WAITING_FILE, WAITING_NEW_CODE, WAITING_RUN_MODE = range(6)

# تخزين العمليات النشطة
active_processes = {}
user_files = {}

# الرموز التعبيرية العشوائية
EMOJIS = ["🍃", "🍀", "🌱", "🌿", "💐", "🌴", "🌾", "🌳", "🐢", "🐉", "🐸", "🐊", "🌵", "🐛", "🌹"]

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء المحادثة مع أزرار إنشاء البوت والخيارات"""
    emoji1 = get_random_emoji()
    emoji2 = get_random_emoji()
    
    keyboard = [
        [InlineKeyboardButton(f"{emoji1} إنشاء بوت بالذكاء الاصطناعي", callback_data='create_bot')],
        [InlineKeyboardButton(f"{emoji2} خيارات مفيدة", callback_data='useful_options')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "مرحباً أنا بوت لإنشاء بوتات تلجرام متطورة\n\n"
        "يمكنك إنشاء بوتات باستخدام الذكاء الاصطناعي أو استخدام الخيارات المتقدمة",
        reply_markup=reply_markup
    )

async def handle_create_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية إنشاء البوت بالذكاء الاصطناعي"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "يرجى وصف البوت الذي تريد إنشاءه بالتفصيل، وتأكد من تضمين\n"
        "• الوظائف المطلوبة\n"
        "• التوكن إذا كان لديك (أو اكتب أحتاج توكن وسأساعدك)\n"
        "• أي متطلبات خاصة\n\n"
        "مثال: أريد بوت لإدارة مجموعة مع خاصية الترحيب بالأعضاء الجدد، وحذف الرسائل غير المرغوب فيها، وتوكن البوت هو: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    )
    return DESCRIPTION

async def handle_useful_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خيارات مفيدة"""
    query = update.callback_query
    await query.answer()
    
    emoji1 = get_random_emoji()
    emoji2 = get_random_emoji()
    emoji3 = get_random_emoji()
    emoji4 = get_random_emoji()
    emoji5 = get_random_emoji()
    
    keyboard = [
        [InlineKeyboardButton(f"{emoji1} رفع ملف جاهز", callback_data='upload_file')],
        [InlineKeyboardButton(f"{emoji2} إنشاء ملف", callback_data='create_file')],
        [InlineKeyboardButton(f"{emoji3} حذف ملف", callback_data='delete_file')],
        [InlineKeyboardButton(f"{emoji4} استبدال ملف", callback_data='replace_file')],
        [InlineKeyboardButton(f"{emoji5} الرجوع للقائمة الرئيسية", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "خيارات مفيدة\n\n"
        "اختر أحد الخيارات التالية:",
        reply_markup=reply_markup
    )

async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة إلى القائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    
    emoji1 = get_random_emoji()
    emoji2 = get_random_emoji()
    
    keyboard = [
        [InlineKeyboardButton(f"{emoji1} إنشاء بوت بالذكاء الاصطناعي", callback_data='create_bot')],
        [InlineKeyboardButton(f"{emoji2} خيارات مفيدة", callback_data='useful_options')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "مرحباً أنا بوت لإنشاء بوتات تلجرام متطورة\n\n"
        "يمكنك إنشاء بوتات باستخدام الذكاء الاصطناعي أو استخدام الخيارات المتقدمة",
        reply_markup=reply_markup
    )

async def handle_upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفع ملف جاهز"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("يرجى إرسال ملف Python الذي تريد رفعه:")
    return WAITING_FILE

async def handle_create_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية إنشاء ملف"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "يرجى إرسال كود Python الذي تريد حفظه في ملف.\n"
        "يمكنك إرسال الكود على عدة رسائل، وعند الانتهاء ارسل done"
    )
    context.user_data['code_parts'] = []
    return WAITING_CODE

async def handle_done_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنهاء عملية إنشاء الملف"""
    user_id = update.message.from_user.id
    code_parts = context.user_data.get('code_parts', [])
    
    if not code_parts:
        await update.message.reply_text("لم يتم إرسال أي كود. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END
    
    # جمع جميع أجزاء الكود
    full_code = "\n".join(code_parts)
    
    # حفظ الكود في ملف مؤقت
    temp_filename = f"temp_{user_id}_{int(time.time())}.py"
    with open(temp_filename, 'w', encoding='utf-8') as f:
        f.write(full_code)
    
    # رفع الملف إلى القناة الخاصة
    try:
        with open(temp_filename, 'rb') as f:
            message = await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=f,
                caption=f"ملف المستخدم: {user_id}"
            )
        
        file_id = message.document.file_id
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
        
        keyboard = [
            [InlineKeyboardButton(f"{emoji1} تشغيل الملف", callback_data=f'run_file:{final_filename}')],
            [InlineKeyboardButton(f"{emoji2} حذف الملف", callback_data=f'delete_file:{final_filename}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # إرسال الملف للمستخدم
        await context.bot.send_document(
            chat_id=user_id,
            document=file_id,
            caption="تم حفظ الملف بنجاح",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error uploading file to channel: {e}")
        await update.message.reply_text("حدث خطأ أثناء حفظ الملف")
    
    finally:
        # حذف الملف المؤقت
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    
    return ConversationHandler.END

async def handle_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال الكود"""
    code_part = update.message.text
    if 'code_parts' not in context.user_data:
        context.user_data['code_parts'] = []
    
    context.user_data['code_parts'].append(code_part)
    await update.message.reply_text("تم حفظ جزء الكود. استمر في إرسال الأجزاء أو ارسل done عند الانتهاء")
    return WAITING_CODE

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفع الملف"""
    user_id = update.message.from_user.id
    document = update.message.document
    
    if not document.file_name.endswith('.py'):
        await update.message.reply_text("يرجى رفع ملف Python فقط (امتداد .py)")
        return ConversationHandler.END
    
    try:
        # تحميل الملف
        file = await document.get_file()
        temp_filename = f"temp_{user_id}_{document.file_name}"
        await file.download_to_drive(temp_filename)
        
        # رفع الملف إلى القناة الخاصة
        with open(temp_filename, 'rb') as f:
            message = await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=f,
                caption=f"ملف المستخدم: {user_id}"
            )
        
        file_id = message.document.file_id
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
        
        keyboard = [
            [InlineKeyboardButton(f"{emoji1} تشغيل الملف", callback_data=f'run_file:{final_filename}')],
            [InlineKeyboardButton(f"{emoji2} حذف الملف", callback_data=f'delete_file:{final_filename}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"تم رفع الملف بنجاح: {document.file_name}",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error handling file upload: {e}")
        await update.message.reply_text("حدث خطأ أثناء رفع الملف")
    
    finally:
        # حذف الملف المؤقت
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    
    return ConversationHandler.END

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

async def handle_delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الملفات للحذف"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    files = await load_user_files(user_id)
    
    if not files:
        await query.edit_message_text("لا توجد ملفات لحذفها")
        return
    
    keyboard = []
    for filename in files:
        short_name = os.path.basename(filename)
        emoji = get_random_emoji()
        keyboard.append([InlineKeyboardButton(f"{emoji} {short_name}", callback_data=f'confirm_delete:{filename}')])
    
    emoji_back = get_random_emoji()
    keyboard.append([InlineKeyboardButton(f"{emoji_back} الرجوع", callback_data='useful_options')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "اختر الملف الذي تريد حذفه",
        reply_markup=reply_markup
    )

async def handle_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد حذف الملف"""
    query = update.callback_query
    await query.answer()
    
    filename = query.data.split(':', 1)[1]
    user_id = query.from_user.id
    
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
        
        await query.edit_message_text("تم حذف الملف بنجاح")
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        await query.edit_message_text("حدث خطأ أثناء حذف الملف")

async def handle_replace_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الملفات للاستبدال"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    files = await load_user_files(user_id)
    
    if not files:
        await query.edit_message_text("لا توجد ملفات لاستبدالها")
        return
    
    keyboard = []
    for filename in files:
        short_name = os.path.basename(filename)
        emoji = get_random_emoji()
        keyboard.append([InlineKeyboardButton(f"{emoji} {short_name}", callback_data=f'select_replace:{filename}')])
    
    emoji_back = get_random_emoji()
    keyboard.append([InlineKeyboardButton(f"{emoji_back} الرجوع", callback_data='useful_options')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "اختر الملف الذي تريد استبداله",
        reply_markup=reply_markup
    )

async def handle_select_replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار الملف للاستبدال"""
    query = update.callback_query
    await query.answer()
    
    filename = query.data.split(':', 1)[1]
    context.user_data['replace_filename'] = filename
    
    await query.edit_message_text(
        f"يرجى إرسال الكود الجديد لملف {os.path.basename(filename)}.\n"
        "يمكنك إرسال الكود على عدة رسائل، وعند الانتهاء ارسل done"
    )
    context.user_data['code_parts'] = []
    return WAITING_NEW_CODE

async def handle_done_new_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنهاء عملية استبدال الملف"""
    user_id = update.message.from_user.id
    code_parts = context.user_data.get('code_parts', [])
    filename = context.user_data.get('replace_filename')
    
    if not code_parts or not filename:
        await update.message.reply_text("لم يتم إرسال أي كود أو لم يتم تحديد ملف. يرجى المحاولة مرة أخرى")
        return ConversationHandler.END
    
    # جمع جميع أجزاء الكود
    full_code = "\n".join(code_parts)
    
    # حفظ الكود في ملف مؤقت
    temp_filename = f"temp_{user_id}_{int(time.time())}.py"
    with open(temp_filename, 'w', encoding='utf-8') as f:
        f.write(full_code)
    
    try:
        # رفع الملف الجديد إلى القناة الخاصة
        with open(temp_filename, 'rb') as f:
            message = await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=f,
                caption=f"ملف مستبدل للمستخدم: {user_id}"
            )
        
        file_id = message.document.file_id
        
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
        
        keyboard = [
            [InlineKeyboardButton(f"{emoji1} تشغيل الملف", callback_data=f'run_file:{filename}')],
            [InlineKeyboardButton(f"{emoji2} حذف الملف", callback_data=f'delete_file:{filename}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # إرسال الملف للمستخدم
        await context.bot.send_document(
            chat_id=user_id,
            document=file_id,
            caption="تم استبدال الملف بنجاح",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error replacing file: {e}")
        await update.message.reply_text("حدث خطأ أثناء استبدال الملف")
    
    finally:
        # حذف الملف المؤقت
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    
    return ConversationHandler.END

async def handle_run_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب وضع التشغيل للملف"""
    query = update.callback_query
    await query.answer()
    
    filename = query.data.split(':', 1)[1]
    context.user_data['selected_file'] = filename
    
    emoji1 = get_random_emoji()
    emoji2 = get_random_emoji()
    
    keyboard = [
        [InlineKeyboardButton(f"{emoji1} التشغيل الدائم", callback_data='run_permanent')],
        [InlineKeyboardButton(f"{emoji2} التشغيل للتطوير (10 دقائق)", callback_data='run_development')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "اختر وضع التشغيل:",
        reply_markup=reply_markup
    )
    
    return WAITING_RUN_MODE

async def handle_run_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار وضع التشغيل"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    filename = context.user_data.get('selected_file')
    mode = query.data
    
    if not filename:
        await query.edit_message_text("لم يتم تحديد ملف للتشغيل")
        return ConversationHandler.END
    
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
        await query.edit_message_text("الملف غير موجود")
        return ConversationHandler.END
    
    file_id = result[0]
    
    # تحميل الملف من القناة
    try:
        file = await context.bot.get_file(file_id)
        local_filename = f"run_{user_id}_{os.path.basename(filename)}"
        await file.download_to_drive(local_filename)
        
        # تشغيل الملف حسب الوضع المختار
        if mode == 'run_permanent':
            await run_file_permanent(query, context, local_filename, user_id)
        else:  # run_development
            await run_file_development(query, context, local_filename, user_id)
            
    except Exception as e:
        logger.error(f"Error running file: {e}")
        await query.edit_message_text("حدث خطأ أثناء تشغيل الملف")
    
    return ConversationHandler.END

async def run_file_permanent(query, context, filename, user_id):
    """تشغيل الملف بشكل دائم"""
    await query.edit_message_text("جاري التشغيل الدائم للملف...")
    
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
        
        keyboard = [
            [InlineKeyboardButton(f"{emoji1} إيقاف التشغيل", callback_data=f'stop_process:{filename}')],
            [InlineKeyboardButton(f"{emoji2} عرض السجلات", callback_data=f'show_logs:{filename}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "تم تشغيل الملف بشكل دائم",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in permanent run: {e}")
        await query.edit_message_text("حدث خطأ أثناء التشغيل الدائم للملف")

async def run_file_development(query, context, filename, user_id):
    """تشغيل الملف لوضع التطوير (10 دقائق)"""
    await query.edit_message_text("جاري تشغيل الملف لوضع التطوير (10 دقائق)...")
    
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
        
        keyboard = [
            [InlineKeyboardButton(f"{emoji1} إيقاف التشغيل", callback_data=f'stop_process:{filename}')],
            [InlineKeyboardButton(f"{emoji2} عرض السجلات", callback_data=f'show_logs:{filename}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"تم تشغيل الملف لوضع التطوير وسيعمل حتى: {end_time.strftime('%H:%M:%S')}",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in development run: {e}")
        await query.edit_message_text("حدث خطأ أثناء تشغيل الملف لوضع التطوير")

async def handle_stop_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف عملية التشغيل"""
    query = update.callback_query
    await query.answer()
    
    filename = query.data.split(':', 1)[1]
    user_id = query.from_user.id
    
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
        
        await query.edit_message_text("تم إيقاف التشغيل بنجاح")
    else:
        await query.edit_message_text("لا توجد عملية نشطة لهذا الملف")

async def handle_show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض سجلات التشغيل"""
    query = update.callback_query
    await query.answer()
    
    filename = query.data.split(':', 1)[1]
    user_id = query.from_user.id
    
    if user_id in active_processes and active_processes[user_id]['filename'] == filename:
        process = active_processes[user_id]['process']
        try:
            # محاولة قراءة السجلات بدون انتظار
            stdout, stderr = process.communicate(timeout=1)
            logs = f"سجلات الملف:\n\nstdout:\n{stdout}\n\nstderr:\n{stderr}"
            
            if len(logs) > 4000:
                logs = logs[:4000] + "... (السجلات طويلة جداً)"
                
            await query.edit_message_text(logs)
        except subprocess.TimeoutExpired:
            # العملية لا تزال تعمل، لا توجد سجلات جديدة
            await query.edit_message_text("الملف لا يزال يعمل ولم تظهر سجلات جديدة بعد")
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            await query.edit_message_text("حدث خطأ أثناء قراءة السجلات")
    else:
        await query.edit_message_text("لا توجد عملية نشطة لهذا الملف")

# باقي الدوال (generate_bot, handle_edit, handle_token_input, etc.) تبقى كما هي
# مع تعديلات طفيفة لإضافة الرموز التعبيرية العشوائية وإزالة الرموز من النصوص

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # إعداد قاعدة البيانات
    setup_database()
    
    # إنشاء التطبيق مع webhook
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # إعداد webhook
    async def set_webhook():
        await application.bot.set_webhook(
            url="https://autu2.onrender.com",
            allowed_updates=["message", "callback_query"]
        )
        print("Webhook set successfully")
    
    # إنشاء معالج المحادثة الرئيسي
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(handle_create_bot, pattern='^create_bot$'),
            CallbackQueryHandler(handle_useful_options, pattern='^useful_options$'),
            CallbackQueryHandler(handle_back_to_main, pattern='^back_to_main$'),
            CallbackQueryHandler(handle_upload_file, pattern='^upload_file$'),
            CallbackQueryHandler(handle_create_file, pattern='^create_file$'),
            CallbackQueryHandler(handle_delete_file, pattern='^delete_file$'),
            CallbackQueryHandler(handle_replace_file, pattern='^replace_file$'),
            CallbackQueryHandler(handle_run_file, pattern='^run_file:'),
            CallbackQueryHandler(handle_run_mode, pattern='^(run_permanent|run_development)$'),
            CallbackQueryHandler(handle_stop_process, pattern='^stop_process:'),
            CallbackQueryHandler(handle_show_logs, pattern='^show_logs:'),
            CallbackQueryHandler(handle_confirm_delete, pattern='^confirm_delete:'),
            CallbackQueryHandler(handle_select_replace, pattern='^select_replace:')
        ],
        states={
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_bot)],
            EDITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit)],
            WAITING_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_input),
                CommandHandler('done', handle_done_code)
            ],
            WAITING_FILE: [MessageHandler(filters.Document.ALL, handle_file_upload)],
            WAITING_NEW_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_input),
                CommandHandler('done', handle_done_new_code)
            ],
            WAITING_RUN_MODE: [CallbackQueryHandler(handle_run_mode, pattern='^(run_permanent|run_development)$')]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # إضافة المعالجات
    application.add_handler(conv_handler)
    
    # تشغيل التطبيق مع webhook
    port = int(os.environ.get('PORT', 10000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_BOT_TOKEN,
        webhook_url=f"https://autu2.onrender.com/{TELEGRAM_BOT_TOKEN}"
    )

if __name__ == '__main__':
    main() 
