import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json

TOKEN = '8373741818:AAHTndgrs7FXSQr9arQ-_-3JXIRenv9k2x8'
PIXABAY_API_KEY = '39878241-6c3d5e7d3b1d7a2d2c6f4c1a3'  # استبدلها بمفتاحك الفعلي

bot = telebot.TeleBot(TOKEN)

# قنوات الاشتراك الإجباري
REQUIRED_CHANNELS = ['@crazys7', '@AWU87']

# ذاكرة مؤقتة لتخزين نتائج البحث لكل مستخدم
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    # التحقق من الاشتراك في القنوات
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_subscription"))
        bot.send_message(message.chat.id, "⛔ يجب الاشتراك في القنوات التالية أولاً:\n" + "\n".join(not_subscribed), reply_markup=markup)
    else:
        show_main_menu(message.chat.id, user_id)

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
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("انقر للبحث ⌕", callback_data="search"),
        InlineKeyboardButton("(⊙-DEV-☉)", callback_data="about_dev")
    )
    welcome_msg = "(◕‿◕)\n   \|/          PEXELBO\n   / \\\nابحث بالانجليزي '"
    bot.send_message(chat_id, welcome_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def verify_subscription(call):
    user_id = call.from_user.id
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_subscription"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             text="⛔ يجب الاشتراك في القنوات التالية أولاً:\n" + "\n".join(not_subscribed),
                             reply_markup=markup)
    else:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        show_main_menu(call.message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "search")
def show_content_types(call):
    user_id = call.from_user.id
    # إعادة ضبط بيانات البحث
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id].pop('search_results', None)
    user_data[user_id].pop('current_index', None)
    
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("Photos", callback_data="type_photo"),
        InlineKeyboardButton("Vectors", callback_data="type_vector"),
        InlineKeyboardButton("Illustrations", callback_data="type_illustration"),
        InlineKeyboardButton("Videos", callback_data="type_video"),
        InlineKeyboardButton("All", callback_data="type_all")
    ]
    markup.add(*buttons)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="اختر نوع المحتوى:",
                          reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
def request_search_term(call):
    content_type = call.data.split("_")[1]
    user_id = call.from_user.id
    
    # تخزين نوع المحتوى المختار
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['content_type'] = content_type
    
    # حذف الرسالة السابقة
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    # طلب كلمة البحث مع زر إلغاء
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("إلغاء البحث", callback_data="cancel_search"))
    
    msg = bot.send_message(call.message.chat.id, "🔍 أرسل كلمة البحث باللغة الإنجليزية:", reply_markup=markup)
    
    # حفظ معرف الرسالة للاستخدام لاحقاً
    user_data[user_id]['search_message_id'] = msg.message_id
    bot.register_next_step_handler(msg, process_search_term, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_search")
def cancel_search(call):
    user_id = call.from_user.id
    # حذف رسالة طلب البحث
    if user_id in user_data and 'search_message_id' in user_data[user_id]:
        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=user_data[user_id]['search_message_id'])
        except:
            pass
    
    # العودة للقائمة الرئيسية
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    show_main_menu(call.message.chat.id, user_id)

def process_search_term(message, user_id):
    chat_id = message.chat.id
    search_term = message.text
    
    # حذف رسالة طلب البحث
    if user_id in user_data and 'search_message_id' in user_data[user_id]:
        try:
            bot.delete_message(chat_id, user_data[user_id]['search_message_id'])
        except:
            pass
    
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
    
    # إرسال رسالة تحميل
    loading_msg = bot.send_message(chat_id, "🔍 جاري البحث في قاعدة البيانات...")
    
    # البحث في Pixabay
    results = search_pixabay(search_term, content_type)
    
    # حذف رسالة التحميل
    try:
        bot.delete_message(chat_id, loading_msg.message_id)
    except:
        pass
    
    if not results or 'hits' not in results or len(results['hits']) == 0:
        # عرض خيارات عند عدم وجود نتائج
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🔍 بحث جديد", callback_data="search"),
            InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")
        )
        bot.send_message(chat_id, "⚠️ لم يتم العثور على نتائج لكلمة: {}\nيرجى المحاولة بكلمات أخرى".format(search_term), 
                         reply_markup=markup)
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
        'lang': 'en'  # إضافة اللغة الإنجليزية لتحسين النتائج
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
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("Pixabay API timeout")
        return None
    except Exception as e:
        print(f"Pixabay API error: {e}")
        return None

def show_result(chat_id, user_id):
    if user_id not in user_data or 'search_results' not in user_data[user_id]:
        bot.send_message(chat_id, "❌ انتهت جلسة البحث، ابدأ بحثاً جديداً /start")
        return
    
    results = user_data[user_id]['search_results']
    current_index = user_data[user_id]['current_index']
    search_term = user_data[user_id].get('search_term', '')
    
    if current_index < 0 or current_index >= len(results):
        bot.send_message(chat_id, "⏹️ نهاية النتائج")
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
    markup.row(*row_buttons)
    markup.add(InlineKeyboardButton("⬇️ تحميل", callback_data="download"))
    markup.add(InlineKeyboardButton("🔍 بحث جديد", callback_data="search"))
    
    # إرسال المحتوى المناسب
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
            bot.send_message(chat_id, "❌ حدث خطأ في عرض النتائج، يرجى المحاولة بكلمات أخرى", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("nav_"))
def navigate_results(call):
    user_id = call.from_user.id
    action = call.data.split("_")[1]
    
    if user_id not in user_data or 'search_results' not in user_data[user_id]:
        bot.answer_callback_query(call.id, "❌ الجلسة منتهية، ابدأ بحثاً جديداً")
        return
    
    # تحديث الفهرس
    if action == 'prev':
        user_data[user_id]['current_index'] -= 1
    elif action == 'next':
        user_data[user_id]['current_index'] += 1
    
    # حذف الرسالة القديمة
    try:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except:
        pass
    
    # عرض النتيجة الجديدة
    show_result(call.message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "download")
def download_content(call):
    user_id = call.from_user.id
    # إزالة أزرار التنقل
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None
    )
    bot.answer_callback_query(call.id, "✅ تم التحميل! أرسل /start للبحث مجدداً")
    
    # إظهار خيارات جديدة
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔍 بحث جديد", callback_data="search"),
        InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")
    )
    bot.send_message(call.message.chat.id, "تم تحميل المحتوى بنجاح!\nماذا تريد أن تفعل الآن؟", reply_markup=markup)

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
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    show_main_menu(call.message.chat.id, user_id)

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True) 
