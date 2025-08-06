import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json

TOKEN = '8373741818:AAHTDbjVJUu6tY29pUvuUb38rSLQuSgBTQA '
PIXABAY_API_KEY = '39878241-6c3d5e7d3b1d7a2d2c6f4c1a3'  # استبدلها بمفتاحك الفعلي
ADMIN_ID = 7251748706  # معرف المدير

bot = telebot.TeleBot(TOKEN)

# قنوات الاشتراك الإجباري
REQUIRED_CHANNELS = ['@crazys7', '@AWU87']

# ذاكرة مؤقتة لتخزين نتائج البحث لكل مستخدم
user_data = {}
new_users = set()  # لتتبع المستخدمين الجدد

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # التحقق من المستخدم الجديد
    if user_id not in new_users:
        new_users.add(user_id)
        notify_admin(user_id, message.from_user.username)
    
    # التحقق من الاشتراك في القنوات
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_subscription"))
        bot.send_message(chat_id, "⛔ يجب الاشتراك في القنوات التالية أولاً:\n" + "\n".join(not_subscribed), reply_markup=markup)
    else:
        show_main_menu(chat_id, user_id)

def notify_admin(user_id, username):
    """إرسال إشعار للمدير عند انضمام مستخدم جديد"""
    try:
        username = f"@{username}" if username else "بدون معرف"
        message = f"👤 مستخدم جديد انضم للبوت:\n\n"
        message += f"🆔 ID: {user_id}\n"
        message += f"👤 Username: {username}"
        bot.send_message(ADMIN_ID, message)
    except Exception as e:
        print(f"Error notifying admin: {e}")

def check_subscription(user_id):
    not_subscribed = []
    for channel in REQUIRED_CHANNELS:
        try:
            chat_member = bot.get_chat_member(chat_id=channel, user_id=user_id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except Exception as e:
            print(f"Error checking subscription: {e}")
            not_subscribed.append(channel)
    return not_subscribed

def show_main_menu(chat_id, user_id):
    # إعادة ضبط بيانات المستخدم
    user_data[user_id] = {}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("انقر للبحث ⌕", callback_data="search"))
    markup.add(InlineKeyboardButton("(⊙-DEV-☉)", callback_data="about_dev"))
    
    welcome_msg = "(◕‿◕)\n   \|/          PEXELBO\n   / \\\nابحث بالانجليزي '"
    
    # إذا كانت هناك رسالة سابقة، نقوم بتعديلها بدلاً من إرسال رسالة جديدة
    if user_id in user_data and 'main_message_id' in user_data[user_id]:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['main_message_id'],
                text=welcome_msg,
                reply_markup=markup
            )
            return
        except:
            pass
    
    # إرسال رسالة جديدة إذا لم تكن هناك رسالة سابقة
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
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="⛔ يجب الاشتراك في القنوات التالية أولاً:\n" + "\n".join(not_subscribed),
            reply_markup=markup
        )
    else:
        show_main_menu(chat_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "search")
def show_content_types(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # إعادة ضبط بيانات البحث
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id].pop('search_results', None)
    user_data[user_id].pop('current_index', None)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Photos", callback_data="type_photo"))
    markup.add(InlineKeyboardButton("Vectors", callback_data="type_vector"))
    markup.add(InlineKeyboardButton("Illustrations", callback_data="type_illustration"))
    markup.add(InlineKeyboardButton("Videos", callback_data="type_video"))
    markup.add(InlineKeyboardButton("All", callback_data="type_all"))
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text="اختر نوع المحتوى:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
def request_search_term(call):
    content_type = call.data.split("_")[1]
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # تخزين نوع المحتوى المختار
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['content_type'] = content_type
    
    # طلب كلمة البحث مع زر إلغاء
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("إلغاء البحث", callback_data="cancel_search"))
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text="🔍 أرسل كلمة البحث باللغة الإنجليزية:",
        reply_markup=markup
    )
    
    # حفظ معرف الرسالة للاستخدام لاحقاً
    user_data[user_id]['search_message_id'] = call.message.message_id
    bot.register_next_step_handler(call.message, process_search_term, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_search")
def cancel_search(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    show_main_menu(chat_id, user_id)

def process_search_term(message, user_id):
    chat_id = message.chat.id
    search_term = message.text
    
    # حذف رسالة إدخال المستخدم
    try:
        bot.delete_message(chat_id, message.message_id)
    except:
        pass
    
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
            text="🔍 جاري البحث في قاعدة البيانات..."
        )
    except:
        pass
    
    # البحث في Pixabay
    results = search_pixabay(search_term, content_type)
    
    if not results or 'hits' not in results or len(results['hits']) == 0:
        # عرض خيارات عند عدم وجود نتائج
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
        markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main"))
        
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['search_message_id'],
                text=f"⚠️ لم يتم العثور على نتائج لكلمة: {search_term}\nيرجى المحاولة بكلمات أخرى",
                reply_markup=markup
            )
        except:
            pass
        return
    
    # حفظ النتائج
    user_data[user_id]['search_term'] = search_term
    user_data[user_id]['search_results'] = results['hits']
    user_data[user_id]['current_index'] = 0
    
    # عرض النتيجة الأولى
    show_result(chat_id, user_id)

def search_pixabay(query, content_type):
    base_url = "https://pixabay.com/api/"
    params = {
        'key': PIXABAY_API_KEY,
        'q': query,
        'per_page': 50,
        'lang': 'en'
    }
    
    # تحديد نوع المحتوى
    if content_type == 'photo':
        params['image_type'] = 'photo'
    elif content_type == 'vector':
        params['image_type'] = 'vector'
    elif content_type == 'illustration':
        params['image_type'] = 'photo'
        params['category'] = 'design'
    elif content_type == 'video':
        params['video_type'] = 'all'
        base_url = "https://pixabay.com/api/videos/"
    else:  # all
        params['image_type'] = 'all'
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Pixabay API error: {e}")
        return None

def show_result(chat_id, user_id):
    if user_id not in user_data or 'search_results' not in user_data[user_id]:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['search_message_id'],
                text="❌ انتهت جلسة البحث، ابدأ بحثاً جديداً"
            )
        except:
            pass
        return
    
    results = user_data[user_id]['search_results']
    current_index = user_data[user_id]['current_index']
    search_term = user_data[user_id].get('search_term', '')
    
    if current_index < 0 or current_index >= len(results):
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['last_message_id'],
                text="⏹️ نهاية النتائج"
            )
        except:
            pass
        return
    
    item = results[current_index]
    
    # بناء الرسالة
    caption = f"🔍 البحث: {search_term}\n"
    caption += f"📌 النتيجة {current_index+1} من {len(results)}\n"
    if 'tags' in item:
        caption += f"🏷️ الوسوم: {item['tags']}\n"
    
    # بناء أزرار التنقل
    markup = InlineKeyboardMarkup()
    row_buttons = []
    if current_index > 0:
        row_buttons.append(InlineKeyboardButton("◀ السابق", callback_data=f"nav_prev"))
    if current_index < len(results) - 1:
        row_buttons.append(InlineKeyboardButton("التالي ▶", callback_data=f"nav_next"))
    
    if row_buttons:
        markup.row(*row_buttons)
    
    markup.add(InlineKeyboardButton("⬇️ تحميل", callback_data="download"))
    markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
    
    # محاولة التعديل على الرسالة السابقة
    if 'last_message_id' in user_data[user_id]:
        try:
            if 'videos' in item:  # فيديو
                video_url = item['videos']['medium']['url']
                bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=user_data[user_id]['last_message_id'],
                    media=telebot.types.InputMediaVideo(video_url, caption=caption),
                    reply_markup=markup
                )
            else:  # صورة
                image_url = item['largeImageURL']
                bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=user_data[user_id]['last_message_id'],
                    media=telebot.types.InputMediaPhoto(image_url, caption=caption),
                    reply_markup=markup
                )
            return
        except:
            pass
    
    # إذا لم تنجح عملية التعديل، نرسل رسالة جديدة
    try:
        if 'videos' in item:  # فيديو
            video_url = item['videos']['medium']['url']
            msg = bot.send_video(chat_id, video_url, caption=caption, reply_markup=markup)
        else:  # صورة
            image_url = item['largeImageURL']
            msg = bot.send_photo(chat_id, image_url, caption=caption, reply_markup=markup)
        
        # حفظ معرف الرسالة للتعديل لاحقاً
        user_data[user_id]['last_message_id'] = msg.message_id
        
    except Exception as e:
        print(f"Error sending media: {e}")
        # المحاولة مع نتيجة أخرى
        user_data[user_id]['current_index'] += 1
        if user_data[user_id]['current_index'] < len(results):
            show_result(chat_id, user_id)
        else:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=user_data[user_id]['search_message_id'],
                    text="❌ حدث خطأ في عرض النتائج، يرجى المحاولة بكلمات أخرى",
                    reply_markup=markup
                )
            except:
                pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("nav_"))
def navigate_results(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    action = call.data.split("_")[1]
    
    if user_id not in user_data or 'search_results' not in user_data[user_id]:
        bot.answer_callback_query(call.id, "❌ الجلسة منتهية، ابدأ بحثاً جديداً")
        return
    
    # تحديث الفهرس
    if action == 'prev':
        user_data[user_id]['current_index'] -= 1
    elif action == 'next':
        user_data[user_id]['current_index'] += 1
    
    # حفظ معرف الرسالة للتعديل
    user_data[user_id]['last_message_id'] = call.message.message_id
    
    # عرض النتيجة الجديدة
    show_result(chat_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "download")
def download_content(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # إزالة أزرار التنقل
    bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=None
    )
    
    # إظهار رسالة تأكيد
    bot.answer_callback_query(call.id, "✅ تم التحميل بنجاح!")
    
    # إظهار خيارات جديدة في رسالة منفصلة
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
    markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main"))
    
    bot.send_message(chat_id, "تم تحميل المحتوى بنجاح!\nماذا تريد أن تفعل الآن؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "about_dev")
def show_dev_info(call):
    dev_info = """
👨‍💻 عن المطوّر @Ili8_8ill  
مطوّر مبتدئ في عالم بوتات تيليجرام، بدأ رحلته بشغف كبير لتعلم البرمجة وصناعة أدوات ذكية تساعد المستخدمين وتضيف قيمة للمجتمعات الرقمية. يسعى لتطوير مهاراته يومًا بعد يوم من خلال التجربة، التعلم، والمشاركة في مشاريع بسيطة لكنها فعّالة.

🔰 ما يميّزه في هذه المرحلة:  

• حب الاستكشاف والتعلّم الذاتي  
• بناء بوتات بسيطة بمهام محددة  
• استخدام أدوات مثل BotFather و Python  
• الانفتاح على النقد والتطوير المستمر

📡 القنوات المرتبطة:  
@crazys7 • @AWU87  

🌱 رؤية المطوّر:  
الانطلاق من الأساسيات نحو الاحتراف، خطوة بخطوة، مع طموح لصناعة بوتات تلبي احتياجات حقيقية وتُحدث فرقًا.

📬 للتواصل: @Ili8_8ill
    """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=dev_info,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def return_to_main(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    show_main_menu(chat_id, user_id)

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)
