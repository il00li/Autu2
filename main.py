import os
import logging
import json
import requests
import subprocess
import threading
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# توكنات API
TELEGRAM_BOT_TOKEN = "8323080366:AAEjDLf52u7y1HL8YTXfr70PlCAYj6PktV4"
GEMINI_API_KEY = "AIzaSyA6GqakCMC7zZohjXfUH-pfTB3dmL2F5to"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# حالات المحادثة
DESCRIPTION, LIBRARIES, EDITING = range(3)

# تخزين العمليات النشطة
active_processes = {}

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء المحادثة وطلب وصف البوت المطلوب"""
    await update.message.reply_text(
        "مرحباً! أنا بوت لإنشاء بوتات تلجرام متطورة.\n\n"
        "يرجى وصف ما تريد من البوت الذي تريد إنشاءه بالتفصيل.\n"
        "مثال: 'أريد بوت لإدارة مجموعة مع خاصية الترحيب بالأعضاء الجدد وحذف الرسائل غير المرغوب فيها'"
    )
    return DESCRIPTION

async def ask_for_libraries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب المكتبات الإضافية من المستخدم"""
    user_description = update.message.text
    context.user_data['description'] = user_description
    
    await update.message.reply_text(
        "📚 هل تريد إضافة أي مكتبات إضافية للبوت؟\n\n"
        "يرجى ذكر أسماء المكتبات مفصولة بفواصل (مثل: requests, pandas, numpy)\n"
        "أو اكتب 'لا' إذا لم تكن تحتاج إلى مكتبات إضافية."
    )
    return LIBRARIES

async def generate_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء كود البوت باستخدام Gemini API"""
    libraries = update.message.text
    user_description = context.user_data['description']
    
    # إظهار رسالة الانتظار
    wait_msg = await update.message.reply_text("🔮 جاري تحليل طلبك وإنشاء البوت...")
    
    # استدعاء Gemini API
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    
    # بناء النص بناءً على وجود مكتبات إضافية
    if libraries.lower() == 'لا':
        libraries_text = "لا حاجة إلى مكتبات إضافية."
    else:
        libraries_text = f"المكتبات المطلوبة: {libraries}. تأكد من تثبيتها باستخدام pip قبل التشغيل."
    
    prompt = f"""
    قم بإنشاء بوت تلجرام كامل باستخدام Python ومكتبة python-telegram-bot version 20.x.
    المتطلبات: {user_description}
    {libraries_text}
    
    المتطلبات الفنية:
    - استخدم Python 3.8+
    - استخدم مكتبة python-telegram-bot version 20.x
    - أضف تعليقات باللغة العربية في الكود
    - تأكد من أن الكود يعمل بدون أخطاء
    - أضف توكن البوت في متغير BOT_TOKEN (سيقوم المستخدم بإضافته later)
    - تأكد من معالجة جميع الأخطاء
    - أضف أوامر أساسية مثل /start و /help
    - تأكد من أن البوت يمكن تشغيله مباشرة
    - أضف في بداية الملف تعليقات تحتوي على اسم البوت ووصفه والمكتبات المطلوبة
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
        
        # استخراج كود البايثون من النص (إذا كان يحتوي على علامات代码)
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
        
        # إضافة معلومات حول المكتبات المطلوبة في رأس الملف
        if libraries.lower() != 'لا':
            libraries_comment = f"# المكتبات المطلوبة: {libraries}\n# قم بتثبيتها باستخدام: pip install {libraries.replace(',', '')}\n\n"
            code = libraries_comment + code
        
        # حفظ الكود في context للمستخدم
        context.user_data['current_code'] = code
        context.user_data['libraries'] = libraries
        
        # إرسال الكود كملف
        filename = f"bot_{update.message.from_user.id}.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        
        await wait_msg.delete()
        
        # إنشاء أزرار
        keyboard = [
            [InlineKeyboardButton("تشغيل البوت (10 دقائق)", callback_data='run_bot')],
            [InlineKeyboardButton("تعديل الكود", callback_data='edit_code')],
            [InlineKeyboardButton("عرض الكود", callback_data='show_code')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_document(
            document=open(filename, 'rb'),
            caption="تم إنشاء البوت بنجاح! يمكنك:\n- تشغيله لمدة 10 دقائق\n- تعديل الكود\n- عرض الكود",
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
        # طلب توكن البوت للتشغيل
        await query.edit_message_caption("⏳ لجاري تشغيل البوت، يرجى إرسال توكن البوت:")
        context.user_data['waiting_for_token'] = True
        return LIBRARIES  # إعادة استخدام حالة LIBRARIES لاستقبال التوكن
        
    elif query.data == 'edit_code':
        # طلب التعديلات من المستخدم
        await query.edit_message_caption("يرجى إرسال التعديلات المطلوبة على الكود:")
        context.user_data['editing_message_id'] = query.message.message_id
        return EDITING
        
    elif query.data == 'show_code':
        # عرض الكود كنص
        code = context.user_data.get('current_code', '')
        if len(code) > 4000:
            code = code[:4000] + "\n\n... (الكود طويل جداً، يرجى تحميل الملف لعرضه كاملاً)"
        
        await query.edit_message_caption(f"📝 كود البوت:\n\n```python\n{code}\n```", parse_mode='Markdown')

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة توكن البوت للتشغيل"""
    if not context.user_data.get('waiting_for_token'):
        return ConversationHandler.END
        
    token = update.message.text.strip()
    user_id = update.message.from_user.id
    code = context.user_data.get('current_code', '')
    
    # استبدال التوكن في الكود
    if "BOT_TOKEN" in code or "توكن البوت" in code:
        # البحث عن سطر يحتوي على التوكن واستبداله
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if "BOT_TOKEN" in line or "توكن البوت" in line:
                if "=" in line:
                    lines[i] = f'BOT_TOKEN = "{token}"'
        
        code = '\n'.join(lines)
    
    # حفظ الكود المعدل
    filename = f"bot_{user_id}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # تشغيل البوت
    await update.message.reply_text("🔧 جاري تشغيل البوت لمدة 10 دقائق...")
    
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
            active_processes[user_id]['process'].terminate()
            del active_processes[user_id]
    
    threading.Thread(target=stop_bot, args=(user_id,), daemon=True).start()
    
    # إنشاء أزرار للتحكم
    keyboard = [
        [InlineKeyboardButton("إيقاف البوت الآن", callback_data='stop_bot')],
        [InlineKeyboardButton("عرض السجلات", callback_data='show_logs')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ تم تشغيل البوت بنجاح وسيعمل حتى: {end_time.strftime('%H:%M:%S')}",
        reply_markup=reply_markup
    )
    
    context.user_data['waiting_for_token'] = False
    return ConversationHandler.END

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
    libraries = context.user_data.get('libraries', '')
    
    prompt = f"""
    لدي كود بوت تلجرام بالبايثون:
    {original_code}
    
    المطلوب إجراء هذه التعديلات:
    {edit_request}
    
    يرجى إعادة الكود كاملاً مع التعديلات المطلوبة.
    """
    
    if libraries and libraries.lower() != 'لا':
        prompt += f"\nتأكد من أن الكود متوافق مع المكتبات: {libraries}"
    
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
        
        # إضافة معلومات المكتبات إذا كانت موجودة
        if libraries and libraries.lower() != 'لا':
            libraries_comment = f"# المكتبات المطلوبة: {libraries}\n# قم بتثبيتها باستخدام: pip install {libraries.replace(',', '')}\n\n"
            code = libraries_comment + code
        
        # حفظ الكود المعدل في context
        context.user_data['current_code'] = code
        
        # إرسال الكود المعدل كملف
        filename = f"bot_{update.message.from_user.id}_modified.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        
        await wait_msg.delete()
        
        # إنشاء أزرار
        keyboard = [
            [InlineKeyboardButton("تشغيل البوت (10 دقائق)", callback_data='run_bot')],
            [InlineKeyboardButton("تعديل الكود", callback_data='edit_code')],
            [InlineKeyboardButton("عرض الكود", callback_data='show_code')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_document(
            document=open(filename, 'rb'),
            caption="تم تعديل البوت بنجاح! يمكنك:\n- تشغيله لمدة 10 دقائق\n- إجراء المزيد من التعديلات\n- عرض الكود",
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error editing bot: {e}")
        await wait_msg.delete()
        await update.message.reply_text("عذراً، حدث خطأ أثناء تعديل البوت. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def handle_stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف البوت يدوياً"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in active_processes:
        active_processes[user_id]['process'].terminate()
        del active_processes[user_id]
        await query.edit_message_text("✅ تم إيقاف البوت بنجاح.")
    else:
        await query.edit_message_text("⚠️ لا يوجد بوت نشط لإيقافه.")

async def handle_show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض سجلات البوت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in active_processes:
        process = active_processes[user_id]['process']
        try:
            stdout, stderr = process.communicate(timeout=1)
            logs = f"السجلات:\n\nstdout:\n{stdout}\n\nstderr:\n{stderr}"
            
            if len(logs) > 4000:
                logs = logs[:4000] + "... (السجلات طويلة جداً)"
                
            await query.edit_message_text(logs)
        except:
            await query.edit_message_text("⚠️ لا يمكن قراءة السجلات في الوقت الحالي.")
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
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_libraries)],
            LIBRARIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_bot)],
            EDITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # إضافة المعالجات
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(run_bot|edit_code|show_code)$'))
    application.add_handler(CallbackQueryHandler(handle_stop_bot, pattern='^stop_bot$'))
    application.add_handler(CallbackQueryHandler(handle_show_logs, pattern='^show_logs$'))
    
    # معالج للتوكن عندما يكون في وضع الانتظار
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token))
    
    # بدء البوت
    print("البوت يعمل...")
    application.run_polling()

if __name__ == '__main__':
    main()
