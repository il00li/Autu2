import os
import logging
import json
import requests
import subprocess
import threading
import time
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# توكنات API
TELEGRAM_BOT_TOKEN = "8403108424:AAHnOZp4bsQjlCB4tf2LUl0JbprYvrVESmw"
GEMINI_API_KEY = "AIzaSyA6GqakCMC7zZohjXfUH-pfTB3dmL2F5to"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# حالات المحادثة
DESCRIPTION, EDITING = range(2)

# تخزين العمليات النشطة
active_processes = {}
bot_processes = {}

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء المحادثة وطلب وصف البوت المطلوب"""
    await update.message.reply_text(
        "🚀 **مرحباً! أنا بوت لإنشاء بوتات تلجرام متطورة**\n\n"
        "📝 **يرجى وصف البوت الذي تريد إنشاءه بالتفصيل، وتأكد من تضمين:**\n"
        "• الوظائف المطلوبة\n"
        "• التوكن إذا كان لديك (أو اكتب 'أحتاج توكن' وسأساعدك)\n"
        "• أي متطلبات خاصة\n\n"
        "**مثال:** 'أريد بوت لإدارة مجموعة مع خاصية الترحيب بالأعضاء الجدد، وحذف الرسائل غير المرغوب فيها، وتوكن البوت هو: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'"
    )
    return DESCRIPTION

def extract_token(description):
    """استخراج توكن البوت من الوصف"""
    token_pattern = r'\d{8,10}:[A-Za-z0-9_-]{35}'
    match = re.search(token_pattern, description)
    if match:
        return match.group(0)
    return None

def detect_required_libraries(code):
    """اكتشاف المكتبات المطلوبة تلقائياً من الكود"""
    libraries = set()
    
    # مكتبات شائعة في بوتات التلجرام
    common_patterns = {
        'requests': r'import requests|from requests',
        'pandas': r'import pandas|from pandas',
        'numpy': r'import numpy|from numpy',
        'beautifulsoup4': r'from bs4|import bs4',
        'selenium': r'import selenium|from selenium',
        'pillow': r'import PIL|from PIL|from PIL\.|import Image',
        'python-dotenv': r'import dotenv|from dotenv',
        'aiohttp': r'import aiohttp|from aiohttp',
        'redis': r'import redis|from redis',
        'pymongo': r'import pymongo|from pymongo',
        'sqlalchemy': r'import sqlalchemy|from sqlalchemy',
        'psutil': r'import psutil|from psutil',
        'matplotlib': r'import matplotlib|from matplotlib',
        'openai': r'import openai|from openai',
    }
    
    for lib, pattern in common_patterns.items():
        if re.search(pattern, code, re.IGNORECASE):
            libraries.add(lib)
    
    return list(libraries)

async def generate_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء كود البوت باستخدام Gemini API"""
    user_description = update.message.text
    
    # استخراج التوكن من الوصف
    bot_token = extract_token(user_description)
    
    # إظهار رسالة الانتظار
    wait_msg = await update.message.reply_text("🔮 جاري تحليل طلبك وإنشاء البوت...")
    
    # استدعاء Gemini API
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    
    prompt = f"""
    قم بإنشاء بوت تلجرام كامل باستخدام Python ومكتبة python-telegram-bot version 20.x.
    المتطلبات: {user_description}
    
    المتطلبات الفنية:
    - استخدم Python 3.8+
    - استخدم مكتبة python-telegram-bot version 20.x
    - أضف تعليقات باللغة العربية في الكود
    - تأكد من أن الكود يعمل بدون أخطاء
    - أضف توكن البوت في متغير BOT_TOKEN (استخدم القيمة: {bot_token or "YOUR_BOT_TOKEN_HERE"})
    - تأكد من معالجة جميع الأخطاء
    - أضف أوامر أساسية مثل /start و /help
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
        
        # اكتشاف المكتبات المطلوبة تلقائياً
        required_libraries = detect_required_libraries(code)
        
        # إضافة معلومات حول المكتبات المطلوبة في رأس الملف
        if required_libraries:
            libraries_comment = f"# المكتبات المطلوبة: {', '.join(required_libraries)}\n# قم بتثبيتها باستخدام: pip install {' '.join(required_libraries)}\n\n"
            code = libraries_comment + code
        
        # حفظ الكود في context للمستخدم
        context.user_data['current_code'] = code
        context.user_data['bot_token'] = bot_token
        context.user_data['libraries'] = required_libraries
        
        # إرسال الكود كملف
        user_id = update.message.from_user.id
        filename = f"bot_{user_id}.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        
        await wait_msg.delete()
        
        # إنشاء أزرار
        keyboard = []
        
        if bot_token:
            keyboard.append([InlineKeyboardButton("▶️ تشغيل البوت (10 دقائق)", callback_data='run_bot')])
        else:
            keyboard.append([InlineKeyboardButton("🔑 إضافة توكن وتشغيل", callback_data='add_token')])
        
        keyboard.append([InlineKeyboardButton("✏️ تعديل الكود", callback_data='edit_code')])
        keyboard.append([InlineKeyboardButton("📄 عرض الكود", callback_data='show_code')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = "✅ تم إنشاء البوت بنجاح!"
        
        if required_libraries:
            caption += f"\n📚 المكتبات المطلوبة: {', '.join(required_libraries)}"
        
        if not bot_token:
            caption += "\n⚠️ لم يتم العثور على توكن في الوصف. سيطلب منك التوكن عند التشغيل."
        
        await update.message.reply_document(
            document=open(filename, 'rb'),
            caption=caption,
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating bot: {e}")
        await wait_msg.delete()
        await update.message.reply_text("عذراً، حدث خطأ أثناء إنشاء البوت. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'run_bot':
        # تشغيل البوت
        await run_generated_bot(query, context)
        
    elif query.data == 'add_token':
        # طلب التوكن من المستخدم
        await query.edit_message_caption("🔑 يرجى إرسال توكن البوت:")
        context.user_data['waiting_for_token'] = True
        
    elif query.data == 'edit_code':
        # طلب التعديلات من المستخدم
        await query.edit_message_caption("📝 يرجى إرسال التعديلات المطلوبة على الكود:")
        context.user_data['editing_message_id'] = query.message.message_id
        return EDITING
        
    elif query.data == 'show_code':
        # عرض الكود كنص
        code = context.user_data.get('current_code', '')
        if len(code) > 4000:
            code = code[:4000] + "\n\n... (الكود طويل جداً، يرجى تحميل الملف لعرضه كاملاً)"
        
        await query.edit_message_caption(f"📝 كود البوت:\n\n```python\n{code}\n```", parse_mode='Markdown')

async def handle_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال التوكن من المستخدم"""
    if not context.user_data.get('waiting_for_token'):
        return
    
    token = update.message.text.strip()
    context.user_data['bot_token'] = token
    
    # تحديث الكود بإضافة التوكن
    code = context.user_data.get('current_code', '')
    if "YOUR_BOT_TOKEN_HERE" in code:
        code = code.replace("YOUR_BOT_TOKEN_HERE", token)
    elif "BOT_TOKEN" in code:
        # البحث عن سطر يحتوي على BOT_TOKEN واستبداله
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if "BOT_TOKEN" in line and "=" in line:
                lines[i] = f'BOT_TOKEN = "{token}"'
        code = '\n'.join(lines)
    
    context.user_data['current_code'] = code
    
    # حفظ الكود المحدث
    user_id = update.message.from_user.id
    filename = f"bot_{user_id}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(code)
    
    await update.message.reply_text("✅ تم حفظ التوكن. جاري تشغيل البوت...")
    
    # تشغيل البوت
    await run_generated_bot_from_message(update, context)

async def run_generated_bot_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشغيل البوت من رسالة عادية"""
    user_id = update.message.from_user.id
    code = context.user_data.get('current_code', '')
    token = context.user_data.get('bot_token')
    
    if not token:
        await update.message.reply_text("❌ لم يتم تحديد توكن البوت. يرجى إرسال التوكن أولاً.")
        return
    
    # حفظ الكود
    filename = f"bot_{user_id}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # تشغيل البوت
    await run_bot_process(update, context, filename, user_id)

async def run_generated_bot(query, context):
    """تشغيل البوت من استعلام زر"""
    user_id = query.from_user.id
    code = context.user_data.get('current_code', '')
    token = context.user_data.get('bot_token')
    
    if not token:
        await query.edit_message_caption("❌ لم يتم العثور على توكن البوت. يرجى استخدام زر 'إضافة توكن وتشغيل' أولاً.")
        return
    
    # حفظ الكود
    filename = f"bot_{user_id}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # تشغيل البوت
    await run_bot_process(query, context, filename, user_id, is_query=True)

async def run_bot_process(update, context, filename, user_id, is_query=False):
    """تشغيل عملية البوت"""
    # تثبيت المكتبات المطلوبة إذا كانت موجودة
    libraries = context.user_data.get('libraries', [])
    if libraries:
        install_msg = "🔧 جاري تثبيت المكتبات المطلوبة..."
        if is_query:
            await update.edit_message_caption(install_msg)
        else:
            await update.message.reply_text(install_msg)
        
        try:
            # تثبيت المكتبات
            subprocess.run(["pip", "install"] + libraries, check=True, timeout=120)
        except subprocess.TimeoutExpired:
            logger.error("Timeout while installing libraries")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error installing libraries: {e}")
    
    # تشغيل البوت
    run_msg = "🚀 جاري تشغيل البوت لمدة 10 دقائق..."
    if is_query:
        await update.edit_message_caption(run_msg)
    else:
        await update.message.reply_text(run_msg)
    
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
    
    # تخزين معلومات البوت للتحكم به
    bot_processes[user_id] = {
        'process': process,
        'start_time': datetime.now(),
        'end_time': end_time,
        'filename': filename,
        'user_id': user_id
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
                if user_id in bot_processes:
                    del bot_processes[user_id]
    
    threading.Thread(target=stop_bot, args=(user_id,), daemon=True).start()
    
    # إنشاء أزرار للتحكم
    keyboard = [
        [InlineKeyboardButton("⏹️ إيقاف البوت الآن", callback_data='stop_bot')],
        [InlineKeyboardButton("📊 عرض السجلات", callback_data='show_logs')],
        [InlineKeyboardButton("🔄 إعادة تشغيل البوت", callback_data='restart_bot')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    success_msg = f"✅ تم تشغيل البوت بنجاح وسيعمل حتى: {end_time.strftime('%H:%M:%S')}"
    
    if is_query:
        await update.edit_message_caption(success_msg, reply_markup=reply_markup)
    else:
        await update.message.reply_text(success_msg, reply_markup=reply_markup)

async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة التعديلات على الكود"""
    edit_request = update.message.text
    
    # إظهار رسالة الانتظار
    wait_msg = await update.message.reply_text("🔮 جاري معالجة التعديلات...")
    
    # استدعاء Gemini API لتعديل الكود
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    
    original_code = context.user_data['current_code']
    
    prompt = f"""
    لدي كود بوت تلجرام بالبايثون:
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
        
        # اكتشاف المكتبات المطلوبة تلقائياً
        required_libraries = detect_required_libraries(code)
        
        # إضافة معلومات حول المكتبات المطلوبة في رأس الملف
        if required_libraries:
            libraries_comment = f"# المكتبات المطلوبة: {', '.join(required_libraries)}\n# قم بتثبيتها باستخدام: pip install {' '.join(required_libraries)}\n\n"
            code = libraries_comment + code
        
        # حفظ الكود المعدل في context
        context.user_data['current_code'] = code
        context.user_data['libraries'] = required_libraries
        
        # إرسال الكود المعدل كملف
        user_id = update.message.from_user.id
        filename = f"bot_{user_id}_modified.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        
        await wait_msg.delete()
        
        # إنشاء أزرار
        keyboard = []
        
        if context.user_data.get('bot_token'):
            keyboard.append([InlineKeyboardButton("▶️ تشغيل البوت (10 دقائق)", callback_data='run_bot')])
        else:
            keyboard.append([InlineKeyboardButton("🔑 إضافة توكن وتشغيل", callback_data='add_token')])
        
        keyboard.append([InlineKeyboardButton("✏️ تعديل الكود", callback_data='edit_code')])
        keyboard.append([InlineKeyboardButton("📄 عرض الكود", callback_data='show_code')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = "✅ تم تعديل البوت بنجاح!"
        
        if required_libraries:
            caption += f"\n📚 المكتبات المطلوبة: {', '.join(required_libraries)}"
        
        await update.message.reply_document(
            document=open(filename, 'rb'),
            caption=caption,
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error editing bot: {e})
        await wait_msg.delete()
        await update.message.reply_text("عذراً، حدث خطأ أثناء تعديل البوت. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def handle_stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف البوت يدوياً"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
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
            if user_id in bot_processes:
                del bot_processes[user_id]
        
        await query.edit_message_text("✅ تم إيقاف البوت بنجاح.")
    else:
        await query.edit_message_text("⚠️ لا يوجد بوت نشط لإيقافه.")

async def handle_restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعادة تشغيل البوت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in active_processes:
        # إيقاف البوت الحالي
        try:
            active_processes[user_id]['process'].terminate()
            active_processes[user_id]['process'].wait(timeout=5)
        except:
            try:
                active_processes[user_id]['process'].kill()
            except:
                pass
        
        # تشغيل البوت مرة أخرى
        code = context.user_data.get('current_code', '')
        filename = f"bot_{user_id}_restarted.py"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        
        await query.edit_message_text("🔄 جاري إعادة تشغيل البوت...")
        
        # تشغيل البوت من جديد
        process = subprocess.Popen(
            ["python", filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # تخزين المعلومات حول العملية الجديدة
        end_time = datetime.now() + timedelta(minutes=10)
        active_processes[user_id] = {
            'process': process,
            'end_time': end_time,
            'filename': filename
        }
        
        bot_processes[user_id] = {
            'process': process,
            'start_time': datetime.now(),
            'end_time': end_time,
            'filename': filename,
            'user_id': user_id
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
                    if user_id in bot_processes:
                        del bot_processes[user_id]
        
        threading.Thread(target=stop_bot, args=(user_id,), daemon=True).start()
        
        # إنشاء أزرار للتحكم
        keyboard = [
            [InlineKeyboardButton("⏹️ إيقاف البوت الآن", callback_data='stop_bot')],
            [InlineKeyboardButton("📊 عرض السجلات", callback_data='show_logs')],
            [InlineKeyboardButton("🔄 إعادة تشغيل البوت", callback_data='restart_bot')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        success_msg = f"✅ تم إعادة تشغيل البوت بنجاح وسيعمل حتى: {end_time.strftime('%H:%M:%S')}"
        await query.edit_message_text(success_msg, reply_markup=reply_markup)
    else:
        await query.edit_message_text("⚠️ لا يوجد بوت نشط لإعادة تشغيله.")

async def handle_show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض سجلات البوت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in active_processes:
        process = active_processes[user_id]['process']
        try:
            # محاولة قراءة السجلات بدون انتظار
            stdout, stderr = process.communicate(timeout=1)
            logs = f"📊 سجلات البوت:\n\n**stdout:**\n{stdout}\n\n**stderr:**\n{stderr}"
            
            if len(logs) > 4000:
                logs = logs[:4000] + "... (السجلات طويلة جداً)"
                
            await query.edit_message_text(logs, parse_mode='Markdown')
        except subprocess.TimeoutExpired:
            # العملية لا تزال تعمل، لا توجد سجلات جديدة
            await query.edit_message_text("📊 البوت لا يزال يعمل ولم تظهر سجلات جديدة بعد.")
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            await query.edit_message_text("⚠️ حدث خطأ أثناء قراءة السجلات.")
    else:
        await query.edit_message_text("⚠️ لا يوجد بوت نشط لعرض سجلاته.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء المحادثة"""
    await update.message.reply_text('تم إلغاء العملية.')
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    # إعلام المستخدم بالخطأ
    if update and update.message:
        await update.message.reply_text('عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.')

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # إنشاء معالج المحادثة
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_bot)],
            EDITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # إضافة المعالجات
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(run_bot|add_token|edit_code|show_code)$'))
    application.add_handler(CallbackQueryHandler(handle_stop_bot, pattern='^stop_bot$'))
    application.add_handler(CallbackQueryHandler(handle_show_logs, pattern='^show_logs$'))
    application.add_handler(CallbackQueryHandler(handle_restart_bot, pattern='^restart_bot$'))
    
    # معالج لإدخال التوكن
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token_input))
    
    # بدء البوت
    print("✅ البوت يعمل...")
    application.run_polling()

if __name__ == '__main__':
    main() 
