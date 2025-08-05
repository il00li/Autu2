import telebot
from telebot import types
import requests
import json

# 🤖 إعدادات البوت الأساسية 🤖
BOT_TOKEN = "7639996535:AAH_Ppw8jeiUg4nJjjEyOXaYlip289jSAio"
PIXABAY_API_KEY = "51444506-bffefcaf12816bd85a20222d1" # ⚠️ لا تنسَ استبدال هذا بمفتاح API الخاص بك من Pixabay ⚠️

# 👥 قنوات الاشتراك الإجباري 👥
MANDATORY_CHANNELS = {
    "@crazys7": "https://t.me/crazys7",
    "@AWU87": "https://t.me/AWU87"
}

# 🚀 تهيئة البوت 🚀
bot = telebot.TeleBot(BOT_TOKEN)

# 💾 بيانات جلسات المستخدمين (للحفاظ على حالة البحث لكل مستخدم) 💾
user_sessions = {}

# 🎨 لوحة المفاتيح Inline لاختيار نوع الأيقونات 🎨
search_type_keyboard = types.InlineKeyboardMarkup()
search_type_keyboard.row(
    types.InlineKeyboardButton("✨ رسوم توضيحية ✨", callback_data="type_illustration"),
    types.InlineKeyboardButton("📐 رسوم متجهة 📐", callback_data="type_vector")
)

def check_subscription(user_id):
    """
    تتحقق مما إذا كان المستخدم مشتركًا في جميع القنوات الإجبارية.
    """
    for channel_username in MANDATORY_CHANNELS:
        try:
            member = bot.get_chat_member(channel_username, user_id)
            # حالات العضوية المقبولة: 'member', 'administrator', 'creator'
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            # طباعة الخطأ للمطور للمساعدة في التصحيح
            print(f"❌ خطأ أثناء التحقق من القناة {channel_username}: {e}")
            return False
    return True

def subscription_keyboard():
    """
    تنشئ لوحة مفاتيح Inline تحتوي على روابط للقنوات الإجبارية وزر للتحقق من الاشتراك.
    """
    keyboard = types.InlineKeyboardMarkup()
    for channel_name, channel_link in MANDATORY_CHANNELS.items():
        keyboard.add(types.InlineKeyboardButton(text=f"🔗 اشترك في {channel_name}", url=channel_link))
    keyboard.add(types.InlineKeyboardButton(text="✅ تحقق من الاشتراك ✅", callback_data="check_sub"))
    return keyboard

def pixabay_search(query, image_type, page=1):
    """
    تُجري بحثًا عن الصور في Pixabay API.
    """
    url = "https://pixabay.com/api/"
    params = {
        'key': PIXABAY_API_KEY,
        'q': query,
        'image_type': image_type,
        'page': page,
        'per_page': 20 # عدد النتائج في كل صفحة
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # ترفع استثناء لأكواد الحالة السيئة (مثل 4xx أو 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ خطأ أثناء البحث في Pixabay: {e}")
        return None

def create_navigation_keyboard(current_index, total_results):
    """
    تنشئ لوحة مفاتيح Inline للتنقل بين نتائج البحث (السابق/التالي).
    """
    keyboard = types.InlineKeyboardMarkup()
    buttons = []
    
    # زر 'السابق' يظهر إذا لم تكن النتيجة الأولى
    if current_index > 0:
        buttons.append(types.InlineKeyboardButton(text="◀️ السابق", callback_data="nav_prev"))

    # زر 'التالي' يظهر إذا لم تكن النتيجة الأخيرة في الصفحة الحالية
    if current_index < total_results - 1:
        buttons.append(types.InlineKeyboardButton(text="التالي ▶️", callback_data="nav_next"))

    # إضافة الأزرار إلى صف واحد
    keyboard.row(*buttons)
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome_and_ask_query(message):
    """
    تتعامل مع الأمر /start وتطالب المستخدم بكلمة بحث.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    # التحقق من الاشتراك أولاً
    if not check_subscription(user_id):
        bot.send_message(
            chat_id,
            "👋 أهلاً بك! لاستخدام بوت الأيقونات، يرجى الاشتراك في قنواتنا أولاً:",
            reply_markup=subscription_keyboard()
        )
        return
    
    # تهيئة نوع البحث الافتراضي إذا كانت الجلسة جديدة
    if user_id not in user_sessions:
        user_sessions[user_id] = {'image_type': 'illustration'} # الافتراضي: رسوم توضيحية
    
    # إرسال رسالة الترحيب وطلب كلمة البحث مع خيارات نوع البحث
    msg = bot.send_message(
        chat_id,
        "✨ أهلاً بك في بوت أيقونات Pixabay! ✨\n\n"
        "أرسل لي كلمة مفتاحية للبحث عن الأيقونات.\n"
        "يمكنك أيضًا اختيار نوع الأيقونات من الأزرار أدناه:",
        reply_markup=search_type_keyboard
    )
    # تسجيل معالج الخطوة التالية لمعالجة كلمة البحث التي سيرسلها المستخدم
    bot.register_next_step_handler(msg, process_search_query)

def process_search_query(message):
    """
    تُعالج كلمة البحث التي أرسلها المستخدم وتبدأ عملية البحث.
    """
    chat_id = message.chat.id
    query = message.text
    user_id = message.from_user.id
    
    # التحقق من الاشتراك مرة أخرى في حال غادر المستخدم القناة بعد /start
    if not check_subscription(user_id):
        bot.send_message(
            chat_id,
            "🚫 عذرًا، يجب عليك الاشتراك أولاً لاستخدام البوت. 🚫",
            reply_markup=subscription_keyboard()
        )
        return

    # الحصول على نوع البحث من جلسة المستخدم، أو استخدام 'illustration' كافتراضي
    image_type = user_sessions.get(user_id, {}).get('image_type', 'illustration')

    # إجراء البحث في Pixabay
    search_results = pixabay_search(query, image_type, page=1)

    # التحقق مما إذا كانت هناك نتائج
    if not search_results or not search_results.get('hits'): # استخدام .get('hits') لتجنب KeyError
        bot.reply_to(message, "😔 عذرًا، لم يتم العثور على أي أيقونات لهذه الكلمة. حاول بكلمة أخرى! 😔\n"
                               "للبدء من جديد، أرسل /start")
        return

    # تخزين بيانات الجلسة للمستخدم
    user_sessions[chat_id] = {
        'query': query,
        'image_type': image_type,
        'results': search_results['hits'], # تخزين النتائج الفعلية المستلمة
        'current_index': 0,
        'total_results': len(search_results['hits']),
        'page': 1
    }

    # إرسال أول أيقونة من النتائج
    first_image = user_sessions[chat_id]['results'][0]
    keyboard = create_navigation_keyboard(0, user_sessions[chat_id]['total_results'])

    bot.send_photo(
        chat_id,
        first_image['largeImageURL'],
        caption=f"🖼️ أيقونة ({image_type.capitalize()}) - النتيجة 1 من {user_sessions[chat_id]['total_results']} 🖼️",
        reply_markup=keyboard
    )
    
@bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def handle_type_selection(call):
    """
    تتعامل مع ضغط أزرار Inline لاختيار نوع البحث (رسوم توضيحية/متجهة).
    """
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    selected_type = call.data.split('_')[1] # استخراج نوع البحث من callback_data
    
    # تحديث نوع البحث في جلسة المستخدم
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {'image_type': selected_type}
    else:
        user_sessions[chat_id]['image_type'] = selected_type
    
    # تعديل الرسالة الأصلية لإظهار النوع المختار
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"✅ تم تحديد نوع الأيقونات: {selected_type.capitalize()} ✅\n"
             f"الآن، أرسل كلمة مفتاحية جديدة للبحث عن أيقونات بهذا النوع.",
        reply_markup=None # إزالة لوحة المفاتيح بعد الاختيار
    )
    bot.answer_callback_query(call.id, text=f"تم تحديد نوع البحث إلى {selected_type.capitalize()}")
    
    # تسجيل معالج الخطوة التالية مرة أخرى لاستقبال كلمة البحث الجديدة بعد اختيار النوع
    bot.register_next_step_handler(call.message, process_search_query)

@bot.callback_query_handler(func=lambda call: call.data.startswith('nav_'))
def handle_navigation(call):
    """
    تتعامل مع ضغط أزرار Inline للتنقل بين نتائج البحث (السابق/التالي).
    """
    chat_id = call.message.chat.id
    
    # التحقق من وجود جلسة للمستخدم
    if chat_id not in user_sessions:
        bot.send_message(chat_id, "⚠️ عذرًا، انتهت صلاحية الجلسة. يرجى البدء ببحث جديد عبر /start ⚠️")
        bot.answer_callback_query(call.id, "انتهت الجلسة.")
        return
        
    session = user_sessions[chat_id]
    current_index = session['current_index']
    
    # تحديث المؤشر بناءً على الزر المضغوط
    if call.data == "nav_next":
        current_index += 1
    elif call.data == "nav_prev":
        current_index -= 1
        
    # التحقق من أن المؤشر ضمن حدود النتائج المتاحة في الجلسة الحالية
    if 0 <= current_index < session['total_results']:
        session['current_index'] = current_index # تحديث المؤشر في الجلسة
        new_image = session['results'][current_index] # الحصول على الأيقونة الجديدة
        keyboard = create_navigation_keyboard(current_index, session['total_results']) # إنشاء لوحة مفاتيح جديدة

        try:
            # إنشاء كائن InputMediaPhoto مع الصورة الجديدة والوصف المحدث
            new_media = types.InputMediaPhoto(
                media=new_image['largeImageURL'],
                caption=f"🖼️ أيقونة ({session['image_type'].capitalize()}) - النتيجة {current_index + 1} من {session['total_results']} 🖼️"
            )
            
            # تعديل الرسالة الحالية (الصورة والوصف ولوحة المفاتيح)
            bot.edit_message_media(
                media=new_media,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
            bot.answer_callback_query(call.id, text="تم التنقل بنجاح! ✨")
        except telebot.apihelper.ApiTelegramException as e:
            # التعامل مع خطأ "الرسالة لم تتغير" لتجنب الأخطاء غير الضرورية
            if "message is not modified" in str(e):
                bot.answer_callback_query(call.id, "هذه هي الأيقونة الحالية بالفعل! 😅")
            else:
                print(f"❌ خطأ أثناء تعديل الرسالة: {e}")
                bot.answer_callback_query(call.id, "حدث خطأ أثناء التنقل. 😔")
    else:
        bot.answer_callback_query(call.id, "لا توجد أيقونات أخرى في هذه الصفحة! 🚫")

@bot.callback_query_handler(func=lambda call: call.data == 'check_sub')
def check_sub_handler(call):
    """
    تتعامل مع زر 'تحقق من الاشتراك'.
    """
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id) # حذف رسالة التحقق
        send_welcome_and_ask_query(call.message) # إعادة توجيه المستخدم لرسالة الترحيب
    else:
        bot.answer_callback_query(call.id, "❌ لم يتم الاشتراك في جميع القنوات بعد! 😔")

# 🚀 بدء تشغيل البوت 🚀
print("🎉 البوت يعمل الآن... ابدأ المحادثة في تيليجرام! 🎉")
bot.polling()
 
