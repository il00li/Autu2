import telebot
import requests
import json
import time

# تعريف توكن البوت ومفتاح Pixabay API
BOT_TOKEN = "8373741818:AAHTndgrs7FXSQr9arQ-_-3JXIRenv9k2x8"
PIXABAY_API_KEY = "51444506-bffefcaf12816bd85a20222d1"

# معرفات القنوات الإلزامية ومعرف المدير
CHANNEL_1 = "@crazys7"
CHANNEL_2 = "@AWU87"
ADMIN_ID = 7251748706

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# قاموس لتخزين بيانات المستخدمين (حالة البحث، النتائج، إلخ)
user_data = {}

# --- الدوال المساعدة ---

# دالة للتحقق من اشتراك المستخدم في القنوات
def is_subscribed(user_id):
    try:
        # التحقق من القناة الأولى
        member1 = bot.get_chat_member(CHANNEL_1, user_id)
        # التحقق من القناة الثانية
        member2 = bot.get_chat_member(CHANNEL_2, user_id)
        
        # إذا كان المستخدم مشتركًا في كلتا القناتين، يُرجع True
        return member1.status in ['member', 'creator', 'administrator'] and \
               member2.status in ['member', 'creator', 'administrator']
    except telebot.apihelper.ApiException as e:
        # يمكن أن يحدث خطأ إذا كانت القنوات خاصة
        return False

# دالة لإرسال رسالة الترحيب الرئيسية
def send_welcome_message(chat_id):
    welcome_text = """(◕‿◕)
   \|/          PEXELBO
   / \       
ابحث بالانجليزي '"""
    
    markup = telebot.types.InlineKeyboardMarkup()
    search_button = telebot.types.InlineKeyboardButton("انقر للبحث ⌕", callback_data="start_search")
    dev_info_button = telebot.types.InlineKeyboardButton("(⊙-DEV-☉)", callback_data="dev_info")
    markup.add(search_button)
    markup.add(dev_info_button)
    
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

# دالة لإرسال إشعار للمدير عند انضمام مستخدم جديد
def notify_admin(user):
    username = user.username if user.username else "لا يوجد"
    message = f"مستخدم جديد انضم:\nID: {user.id}\nالاسم: {user.first_name}\nاسم المستخدم: @{username}\nالوقت: {time.ctime()}"
    bot.send_message(ADMIN_ID, message)

# --- معالجة الأوامر والرسائل ---

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    
    # إرسال إشعار للمدير عند انضمام مستخدم جديد
    notify_admin(message.from_user)
    
    if is_subscribed(user_id):
        send_welcome_message(message.chat.id)
    else:
        # إظهار رسالة الاشتراك الإجباري
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_subscription"))
        bot.send_message(message.chat.id, "الرجاء الاشتراك في القنوات التالية للمتابعة:\n@crazys7\n@AWU87", reply_markup=markup)

# معالجة الضغط على الأزرار (Inline Keyboard)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if call.data == "check_subscription":
        if is_subscribed(user_id):
            bot.edit_message_text("شكراً لك! لقد تم التحقق.", chat_id, call.message.message_id)
            send_welcome_message(chat_id)
        else:
            bot.answer_callback_query(call.id, "لم يتم الاشتراك بعد، يرجى الانضمام للقنوات.")
            
    elif call.data == "start_search":
        # فتح قائمة أنواع المحتوى
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("Photos", callback_data="type_photos"),
                   telebot.types.InlineKeyboardButton("Vectors", callback_data="type_vectors"))
        markup.row(telebot.types.InlineKeyboardButton("Illustrations", callback_data="type_illustrations"),
                   telebot.types.InlineKeyboardButton("Videos", callback_data="type_videos"))
        markup.add(telebot.types.InlineKeyboardButton("All", callback_data="type_all"))
        
        bot.edit_message_text("اختر نوع المحتوى:", chat_id, call.message.message_id, reply_markup=markup)
        
    elif call.data.startswith("type_"):
        content_type = call.data.split('_')[1]
        
        # تخزين نوع المحتوى في بيانات المستخدم
        user_data[user_id] = {'content_type': content_type, 'state': 'awaiting_query'}
        
        # طلب كلمة البحث
        bot.edit_message_text("أرسل كلمة البحث باللغة الإنجليزية:", chat_id, call.message.message_id)
        
    elif call.data == "dev_info":
        # عرض معلومات المطور
        dev_info_text = "أنا Ili8_8ill، مطور هذا البوت...\nالقنوات: @crazys7, @AWU87"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back_to_main"))
        bot.edit_message_text(dev_info_text, chat_id, call.message.message_id, reply_markup=markup)
        
    elif call.data == "back_to_main":
        send_welcome_message(chat_id)
        bot.delete_message(chat_id, call.message.message_id)

# معالجة الرسائل النصية
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('state') == 'awaiting_query')
def handle_search_query(message):
    user_id = message.from_user.id
    query = message.text
    content_type = user_data[user_id]['content_type']
    
    # حذف رسالة المستخدم
    bot.delete_message(message.chat.id, message.message_id)
    
    # إرسال رسالة "جاري البحث..."
    processing_msg = bot.send_message(message.chat.id, "جاري البحث...")
    
    try:
        # إرسال طلب إلى Pixabay API
        if content_type == 'videos':
            url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={query}&lang=en&per_page=50"
            response = requests.get(url)
            data = response.json().get('hits', [])
            
            # معالجة بيانات الفيديو
            user_data[user_id]['results'] = data
            user_data[user_id]['index'] = 0
            
            # إرسال النتيجة الأولى
            if data:
                send_video_result(message.chat.id, user_id, processing_msg.message_id)
            else:
                bot.edit_message_text("لم يتم العثور على نتائج.", message.chat.id, processing_msg.message_id)
        else:
            url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type={content_type}&lang=en&per_page=50"
            response = requests.get(url)
            data = response.json().get('hits', [])
            
            # معالجة بيانات الصور
            user_data[user_id]['results'] = data
            user_data[user_id]['index'] = 0
            
            # إرسال النتيجة الأولى
            if data:
                send_image_result(message.chat.id, user_id, processing_msg.message_id)
            else:
                bot.edit_message_text("لم يتم العثور على نتائج.", message.chat.id, processing_msg.message_id)

    except requests.exceptions.RequestException:
        bot.edit_message_text("حدث خطأ في الاتصال، يرجى المحاولة لاحقاً.", message.chat.id, processing_msg.message_id)

    # إعادة حالة المستخدم للوضع الافتراضي
    if user_id in user_data:
        user_data[user_id]['state'] = None
        
# دالة لعرض نتيجة الصورة
def send_image_result(chat_id, user_id, message_id):
    # (هنا يتم بناء الكود الخاص بعرض الصور)
    pass

# دالة لعرض نتيجة الفيديو
def send_video_result(chat_id, user_id, message_id):
    # (هنا يتم بناء الكود الخاص بعرض الفيديوهات)
    pass

# --- بدء تشغيل البوت ---

print("Bot is running...")
bot.polling()
