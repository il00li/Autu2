import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
import logging
import urllib.parse
import json
from flask import Flask, request, abort
from datetime import datetime

# تهيئة نظام التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = '8324471840:AAFqTHWy4-FZFIHGusm5RWk1Y240cV32SCw'
UNSPLASH_API_KEY = 'Nrc3mmoxm3BaQes6ZAhIgqtNq2GvZwp3-21pTwByORk'
PIXABAY_API_KEY = '51444506-bffefcaf12816bd85a20222d1'  # للفيديوهات فقط
ADMIN_ID = 6689435577  # معرف المدير
WEBHOOK_URL = 'https://autu2.onrender.com/webhook'  # تأكد من تطابق هذا مع عنوان URL الخاص بك

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# قنوات الاشتراك الإجباري
REQUIRED_CHANNELS = ['@iIl337']

# قناة التحميل
UPLOAD_CHANNEL = '@GRABOT7'

# ذاكرة مؤقتة لتخزين نتائج البحث لكل مستخدم
user_data = {}
new_users = set()  # لتتبع المستخدمين الجدد
banned_users = set()  # المستخدمون المحظورون
premium_users = set()  # المستخدمون المميزون
bot_stats = {  # إحصائيات البوت
    'total_users': 0,
    'total_searches': 0,
    'total_downloads': 0,
    'start_time': datetime.now()
}

def is_valid_url(url):
    """التحقق من صحة عنوان URL"""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def set_webhook():
    """تعيين ويب هوك للبوت"""
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        logger.info("تم تعيين ويب هوك بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تعيين ويب هوك: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    """معالجة التحديثات الواردة من تلجرام"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # التحقق من الحظر
    if user_id in banned_users:
        bot.send_message(chat_id, "⛔️ حسابك محظور من استخدام البوت.")
        return
    
    # زيادة عدد المستخدمين
    if user_id not in new_users:
        new_users.add(user_id)
        bot_stats['total_users'] += 1
        notify_admin(user_id, message.from_user.username)
    
    # التحقق من الاشتراك في القنوات
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_subscription"))
        msg = bot.send_message(chat_id, "يجب الاشتراك في القنوات التالية اولا:\n" + "\n".join(not_subscribed), reply_markup=markup)
        # حفظ معرف الرسالة الرئيسية للمستخدم
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['main_message_id'] = msg.message_id
    else:
        show_main_menu(chat_id, user_id)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    """لوحة تحكم المدير"""
    if message.from_user.id != ADMIN_ID:
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users"),
        InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")
    )
    markup.add(
        InlineKeyboardButton("👑 إدارة العضويات", callback_data="admin_subscriptions"),
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")
    )
    
    bot.send_message(ADMIN_ID, "👨‍💼 لوحة تحكم المدير:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users_panel(call):
    """لوحة إدارة المستخدمين"""
    if call.from_user.id != ADMIN_ID:
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⛔️ حظر مستخدم", callback_data="admin_ban_user"),
        InlineKeyboardButton("✅ فك حظر مستخدم", callback_data="admin_unban_user")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_back"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👥 إدارة المستخدمين:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_ban_user")
def admin_ban_user(call):
    """حظر مستخدم"""
    if call.from_user.id != ADMIN_ID:
        return
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="أرسل معرف المستخدم الذي تريد حظره:"
    )
    bot.register_next_step_handler(call.message, process_ban_user)

def process_ban_user(message):
    """معالجة حظر المستخدم"""
    try:
        user_id = int(message.text)
        banned_users.add(user_id)
        bot.send_message(ADMIN_ID, f"✅ تم حظر المستخدم {user_id} بنجاح")
        try:
            bot.send_message(user_id, "⛔️ حسابك محظور من استخدام البوت.")
        except:
            pass
        admin_panel(message)
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ معرف المستخدم غير صالح")
        admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_unban_user")
def admin_unban_user(call):
    """فك حظر مستخدم"""
    if call.from_user.id != ADMIN_ID:
        return
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="أرسل معرف المستخدم الذي تريد فك حظره:"
    )
    bot.register_next_step_handler(call.message, process_unban_user)

def process_unban_user(message):
    """معالجة فك حظر المستخدم"""
    try:
        user_id = int(message.text)
        if user_id in banned_users:
            banned_users.remove(user_id)
            bot.send_message(ADMIN_ID, f"✅ تم فك حظر المستخدم {user_id} بنجاح")
            try:
                bot.send_message(user_id, "✅ تم فك حظر حسابك، يمكنك الآن استخدام البوت مرة أخرى.")
            except:
                pass
        else:
            bot.send_message(ADMIN_ID, f"❌ المستخدم {user_id} غير محظور")
        admin_panel(message)
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ معرف المستخدم غير صالح")
        admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_subscriptions")
def admin_subscriptions_panel(call):
    """لوحة إدارة العضويات"""
    if call.from_user.id != ADMIN_ID:
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👑 تفعيل العضوية", callback_data="admin_activate_sub"),
        InlineKeyboardButton("🚫 إلغاء العضوية", callback_data="admin_deactivate_sub")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_back"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👑 إدارة العضويات:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate_sub")
def admin_activate_sub(call):
    """تفعيل العضوية للمستخدم"""
    if call.from_user.id != ADMIN_ID:
        return
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="أرسل معرف المستخدم الذي تريد تفعيل العضوية له:"
    )
    bot.register_next_step_handler(call.message, process_activate_sub)

def process_activate_sub(message):
    """معالجة تفعيل العضوية"""
    try:
        user_id = int(message.text)
        premium_users.add(user_id)
        bot.send_message(ADMIN_ID, f"✅ تم تفعيل العضوية للمستخدم {user_id} بنجاح")
        try:
            bot.send_message(user_id, "🎉 تم ترقية حسابك إلى العضوية المميزة! يمكنك الآن الاستفادة من جميع ميزات البوت.")
        except:
            pass
        admin_panel(message)
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ معرف المستخدم غير صالح")
        admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_deactivate_sub")
def admin_deactivate_sub(call):
    """إلغاء العضوية للمستخدم"""
    if call.from_user.id != ADMIN_ID:
        return
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="أرسل معرف المستخدم الذي تريد إلغاء العضوية له:"
    )
    bot.register_next_step_handler(call.message, process_deactivate_sub)

def process_deactivate_sub(message):
    """معالجة إلغاء العضوية"""
    try:
        user_id = int(message.text)
        if user_id in premium_users:
            premium_users.remove(user_id)
            bot.send_message(ADMIN_ID, f"✅ تم إلغاء العضوية للمستخدم {user_id} بنجاح")
            try:
                bot.send_message(user_id, "❌ تم إلغاء العضوية المميزة لحسابك.")
            except:
                pass
        else:
            bot.send_message(ADMIN_ID, f"❌ المستخدم {user_id} ليس لديه عضوية مميزة")
        admin_panel(message)
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ معرف المستخدم غير صالح")
        admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    """عرض إحصائيات البوت للمدير"""
    if call.from_user.id != ADMIN_ID:
        return
    
    uptime = datetime.now() - bot_stats['start_time']
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    stats_text = f"""
📊 إحصائيات البوت:
    
👥 إجمالي المستخدمين: {bot_stats['total_users']}
🔍 إجمالي عمليات البحث: {bot_stats['total_searches']}
💾 إجمالي التحميلات: {bot_stats['total_downloads']}
⏰ وقت التشغيل: {days} أيام, {hours} ساعات, {minutes} دقائق
👑 المستخدمون المميزون: {len(premium_users)}
⛔️ المستخدمون المحظورون: {len(banned_users)}
    """
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=stats_text,
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_back"))
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    """العودة إلى لوحة التحكم الرئيسية"""
    admin_panel(call.message)

def notify_admin(user_id, username):
    """إرسال إشعار للمدير عند انضمام مستخدم جديد"""
    try:
        username = f"@{username}" if username else "بدون معرف"
        user_status = "👑 مميز" if user_id in premium_users else "👤 عادي"
        message = "مستخدم جديد انضم للبوت:\n\n"
        message += f"ID: {user_id}\n"
        message += f"Username: {username}\n"
        message += f"الحالة: {user_status}"
        bot.send_message(ADMIN_ID, message)
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمدير: {e}")

def check_subscription(user_id):
    not_subscribed = []
    for channel in REQUIRED_CHANNELS:
        try:
            # الحصول على حالة المستخدم في القناة
            chat_member = bot.get_chat_member(chat_id=channel, user_id=user_id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except Exception as e:
            logger.error(f"خطأ في التحقق من الاشتراك: {e}")
            not_subscribed.append(channel)
    return not_subscribed

def show_main_menu(chat_id, user_id):
    # إعادة ضبط بيانات المستخدم
    if user_id not in user_data:
        user_data[user_id] = {}
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
    markup.add(InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"))
    
    welcome_msg = "🎨 PEXELBO\nابحث باللغة الإنجليزية عن الصور والفيديوهات عالية الجودة"
    
    # إذا كانت هناك رسالة سابقة، نقوم بتعديلها بدلاً من إرسال رسالة جديدة
    if 'main_message_id' in user_data[user_id]:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['main_message_id'],
                text=welcome_msg,
                reply_markup=markup
            )
            return
        except Exception as e:
            logger.error(f"خطأ في تعديل القائمة الرئيسية: {e}")
            # إذا فشل التعديل، نرسل رسالة جديدة
            msg = bot.send_message(chat_id, welcome_msg, reply_markup=markup)
            user_data[user_id]['main_message_id'] = msg.message_id
    else:
        # إرسال رسالة جديدة
        msg = bot.send_message(chat_id, welcome_msg, reply_markup=markup)
        user_data[user_id]['main_message_id'] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def verify_subscription(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_subscription"))
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="يجب الاشتراك في القنوات التالية اولا:\n" + "\n".join(not_subscribed),
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"خطأ في تعديل رسالة الاشتراك: {e}")
    else:
        show_main_menu(chat_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "search")
def show_content_types(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # التحقق من العضوية المميزة
    if user_id not in premium_users:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👑 ترقية إلى المميز", callback_data="upgrade_premium"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="⛔️ هذه الميزة متاحة فقط للأعضاء المميزين",
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"خطأ في عرض رسالة العضوية: {e}")
        return
    
    # إعادة ضبط بيانات البحث
    if user_id not in user_data:
        user_data[user_id] = {}
    
    # إخفاء الرسالة السابقة
    try:
        bot.answer_callback_query(call.id)
    except:
        pass
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📷 Photos", callback_data="type_photo"),
        InlineKeyboardButton("🎨 Illustrations", callback_data="type_illustration")
    )
    markup.add(
        InlineKeyboardButton("🖼️ 3D Illustrations", callback_data="type_3d"),
        InlineKeyboardButton("🎥 Videos", callback_data="type_video")
    )
    markup.add(InlineKeyboardButton("🌐 All", callback_data="type_all"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="اختر نوع المحتوى:",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"خطأ في عرض انواع المحتوى: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
def request_search_term(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    content_type = call.data.split("_")[1]
    
    # تخزين نوع المحتوى المختار
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['content_type'] = content_type
    
    # طلب كلمة البحث مع زر إلغاء
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("الغاء البحث", callback_data="cancel_search"))
    
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="🔍 ارسل كلمة البحث باللغة الانجليزية:",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"خطأ في طلب كلمة البحث: {e}")
    
    # حفظ معرف الرسالة للاستخدام لاحقاً
    user_data[user_id]['search_message_id'] = call.message.message_id
    # تسجيل الخطوة التالية
    bot.register_next_step_handler(call.message, process_search_term, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_search")
def cancel_search(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    show_main_menu(chat_id, user_id)

def process_search_term(message, user_id):
    chat_id = message.chat.id
    search_term = message.text
    
    # زيادة عداد عمليات البحث
    bot_stats['total_searches'] += 1
    
    # حذف رسالة إدخال المستخدم
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        logger.error(f"خطأ في حذف رسالة المستخدم: {e}")
    
    # استرجاع نوع المحتوى
    if user_id not in user_data or 'content_type' not in user_data[user_id]:
        show_main_menu(chat_id, user_id)
        return
    
    content_type = user_data[user_id]['content_type']
    
    # تحديث الرسالة السابقة لإظهار حالة التحميل
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=user_data[user_id]['search_message_id'],
            text="⏳ جاري البحث في قاعدة البيانات...",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"خطأ في عرض رسالة التحميل: {e}")
    
    # البحث حسب النوع
    if content_type == 'video':
        # استخدام Pixabay للفيديوهات
        results = search_pixabay(search_term, content_type)
    else:
        # استخدام Unsplash للصور والرسوم
        results = search_unsplash(search_term, content_type)
    
    if not results or len(results) == 0:
        # عرض خيارات عند عدم وجود نتائج
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
        markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main"))
        
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['search_message_id'],
                text=f"❌ لم يتم العثور على نتائج لكلمة: {search_term}\nيرجى المحاولة بكلمات أخرى",
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"خطأ في عرض رسالة عدم وجود نتائج: {e}")
        return
    
    # حفظ النتائج
    user_data[user_id]['search_term'] = search_term
    user_data[user_id]['search_results'] = results
    user_data[user_id]['current_index'] = 0
    
    # عرض النتيجة الأولى في نفس رسالة "جاري البحث"
    show_result(chat_id, user_id, message_id=user_data[user_id]['search_message_id'])

def search_unsplash(query, content_type):
    """البحث في Unsplash للصور والرسوم"""
    base_url = "https://api.unsplash.com/search/photos"
    headers = {
        'Authorization': f'Client-ID {UNSPLASH_API_KEY}'
    }
    
    params = {
        'query': query,
        'per_page': 30,
        'lang': 'en'
    }
    
    # تحديد نوع المحتوى
    if content_type == 'illustration':
        params['query'] += ' illustration'
    elif content_type == '3d':
        params['query'] += ' 3d illustration'
    elif content_type == 'all':
        # لا نضيف أي شيء للبحث العام
        pass
    
    try:
        logger.info(f"البحث في Unsplash عن: {query} ({content_type})")
        response = requests.get(base_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.info(f"تم العثور على {len(data.get('results', []))} نتيجة من Unsplash")
        return data.get('results', [])
    except Exception as e:
        logger.error(f"خطأ في واجهة Unsplash: {e}")
        return []

def search_pixabay(query, content_type):
    """البحث في Pixabay للفيديوهات فقط"""
    if content_type != 'video':
        return []
    
    base_url = "https://pixabay.com/api/videos/"
    params = {
        'key': PIXABAY_API_KEY,
        'q': query,
        'per_page': 30,
        'lang': 'en'
    }
    
    try:
        logger.info(f"البحث في Pixabay عن: {query} ({content_type})")
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.info(f"تم العثور على {len(data.get('hits', []))} نتيجة من Pixabay")
        return data.get('hits', [])
    except Exception as e:
        logger.error(f"خطأ في واجهة Pixabay: {e}")
        return []

def show_result(chat_id, user_id, message_id=None):
    if user_id not in user_data or 'search_results' not in user_data[user_id]:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['search_message_id'],
                text="انتهت جلسة البحث، ابدأ بحثاً جديداً"
            )
        except:
            pass
        return
    
    results = user_data[user_id]['search_results']
    current_index = user_data[user_id]['current_index']
    search_term = user_data[user_id].get('search_term', '')
    content_type = user_data[user_id].get('content_type', '')
    
    if current_index < 0 or current_index >= len(results):
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['last_message_id'],
                text="نهاية النتائج"
            )
        except:
            pass
        return
    
    item = results[current_index]
    
    # بناء الرسالة
    caption = f"🔍 البحث: {search_term}\n"
    caption += f"📄 النتيجة {current_index+1} من {len(results)}\n"
    
    # بناء أزرار التنقل
    markup = InlineKeyboardMarkup(row_width=3)
    nav_buttons = []
    
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"nav_prev"))
    
    nav_buttons.append(InlineKeyboardButton("💾 تحميل", callback_data="download"))
    
    if current_index < len(results) - 1:
        nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"nav_next"))
    
    markup.row(*nav_buttons)
    markup.row(InlineKeyboardButton("🔍 جديد", callback_data="search"))
    markup.row(InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main"))
    
    # إرسال النتيجة
    try:
        # إذا كانت النتيجة فيديو من Pixabay
        if content_type == 'video' and 'videos' in item:
            video_url = item['videos']['medium']['url']
            
            # التحقق من صحة URL
            if not is_valid_url(video_url):
                raise ValueError("رابط الفيديو غير صالح")
            
            # محاولة تعديل الرسالة الحالية
            if message_id:
                try:
                    # تعديل الوسائط والتسمية التوضيحية معاً
                    bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=telebot.types.InputMediaVideo(
                            media=video_url,
                            caption=caption
                        ),
                        reply_markup=markup
                    )
                    # حفظ معرف الرسالة
                    user_data[user_id]['last_message_id'] = message_id
                    return
                except Exception as e:
                    logger.error(f"فشل في تعديل رسالة الفيديو: {e}")
            
            # إرسال رسالة جديدة إذا لم تنجح عملية التعديل
            msg = bot.send_video(chat_id, video_url, caption=caption, reply_markup=markup)
            user_data[user_id]['last_message_id'] = msg.message_id
        else:
            # الحصول على رابط الصورة من Unsplash
            image_url = item.get('urls', {}).get('regular', item.get('urls', {}).get('small', ''))
            
            # التحقق من صحة URL
            if not is_valid_url(image_url):
                raise ValueError("رابط الصورة غير صالح")
            
            # محاولة تعديل الرسالة الحالية
            if message_id:
                try:
                    # تعديل الوسائط والتسمية التوضيحية معاً
                    bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=telebot.types.InputMediaPhoto(
                            media=image_url,
                            caption=caption
                        ),
                        reply_markup=markup
                    )
                    # حفظ معرف الرسالة
                    user_data[user_id]['last_message_id'] = message_id
                    return
                except Exception as e:
                    logger.error(f"فشل في تعديل رسالة الصورة: {e}")
            
            # إرسال رسالة جديدة إذا لم تنجح عملية التعديل
            msg = bot.send_photo(chat_id, image_url, caption=caption, reply_markup=markup)
            user_data[user_id]['last_message_id'] = msg.message_id
    except Exception as e:
        logger.error(f"خطأ في عرض النتيجة: {e}")
        # المحاولة مع نتيجة أخرى
        user_data[user_id]['current_index'] += 1
        if user_data[user_id]['current_index'] < len(results):
            show_result(chat_id, user_id, message_id)
        else:
            show_no_results(chat_id, user_id)

def show_no_results(chat_id, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
    markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main"))
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=user_data[user_id]['search_message_id'],
            text="❌ لم يتم العثور على أي نتائج، يرجى المحاولة بكلمات أخرى",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"خطأ في عرض رسالة عدم وجود نتائج: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("nav_"))
def navigate_results(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    action = call.data.split("_")[1]
    
    if user_id not in user_data or 'search_results' not in user_data[user_id]:
        bot.answer_callback_query(call.id, "انتهت جلسة البحث، ابدأ بحثاً جديداً")
        return
    
    # تحديث الفهرس
    if action == 'prev':
        user_data[user_id]['current_index'] -= 1
    elif action == 'next':
        user_data[user_id]['current_index'] += 1
    
    # حفظ معرف الرسالة الحالية (التي نضغط عليها)
    user_data[user_id]['last_message_id'] = call.message.message_id
    
    # عرض النتيجة الجديدة في نفس الرسالة
    show_result(chat_id, user_id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "download")
def download_content(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if user_id not in user_data or 'search_results' not in user_data[user_id]:
        bot.answer_callback_query(call.id, "انتهت جلسة البحث")
        return
    
    current_index = user_data[user_id]['current_index']
    item = user_data[user_id]['search_results'][current_index]
    content_type = user_data[user_id]['content_type']
    
    # زيادة عداد التحميلات
    bot_stats['total_downloads'] += 1
    
    # إرسال المحتوى إلى قناة التحميل
    try:
        # بناء الهاشتاق بناءً على نوع المحتوى
        hashtag = f"#{content_type.capitalize()}"
        username = f"@{call.from_user.username}" if call.from_user.username else "مستخدم"
        caption = f"تم التحميل بواسطة {username}\n{hashtag}"
        
        if content_type == 'video' and 'videos' in item:
            video_url = item['videos']['medium']['url']
            bot.send_video(UPLOAD_CHANNEL, video_url, caption=caption)
        else:
            image_url = item.get('urls', {}).get('regular', item.get('urls', {}).get('small', ''))
            bot.send_photo(UPLOAD_CHANNEL, image_url, caption=caption)
    except Exception as e:
        logger.error(f"خطأ في إرسال المحتوى إلى القناة: {e}")
    
    # إزالة أزرار التنقل
    try:
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"خطأ في ازالة الازرار: {e}")
    
    # إظهار رسالة تأكيد
    bot.answer_callback_query(call.id, "تم التحميل بنجاح! ✅", show_alert=False)
    
    # إظهار خيارات جديدة في رسالة منفصلة
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
    markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main"))
    
    bot.send_message(chat_id, "✅ تم تحميل المحتوى بنجاح!\nماذا تريد أن تفعل الآن؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "settings")
def show_settings(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("👤 عن المطور", callback_data="about_dev"))
    markup.add(InlineKeyboardButton("👑 ترقية إلى المميز", callback_data="upgrade_premium"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="⚙️ إعدادات البوت:",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"خطأ في عرض الإعدادات: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "upgrade_premium")
def upgrade_premium(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="settings"))
    
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="👑 لترقية حسابك إلى العضوية المميزة، يرجى التواصل مع المدير @Ili8_8ill",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"خطأ في عرض ترقية العضوية: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "about_dev")
def show_dev_info(call):
    dev_info = """
👤 عن المطور @Ili8_8ill
مطور مبتدئ في عالم بوتات تيليجرام، بدأ رحلته بشغف كبير لتعلم البرمجة وصناعة أدوات ذكية تساعد المستخدمين وتضيف قيمة للمجتمعات الرقمية. يسعى لتطوير مهاراته يومًا بعد يوم من خلال التجربة، التعلم، والمشاركة في مشاريع بسيطة لكنها فعالة.

📢 القنوات المرتبطة:
@iIl337 - @GRABOT7

📞 للتواصل:
تابع الحساب @Ili8_8ill
    """
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="settings"))
    
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=dev_info,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"خطأ في عرض معلومات المطور: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def return_to_main(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    show_main_menu(chat_id, user_id)

if __name__ == '__main__':
    logger.info("بدء تشغيل البوت...")
    set_webhook()
    app.run(host='0.0.0.0', port=10000) 
