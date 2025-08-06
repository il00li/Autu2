import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from urllib.parse import quote
import io

# Iconify API - مجاني وغير محدود
ICONIFY_API = "https://api.iconify.design"

bot = telebot.TeleBot('7968375518:AAHhFQcaIvAS48SRnVUxQ7fd_bltB9MTIBc')  # استبدل بـ توكن بوتك

# تخزين مؤقت لنتائج البحث
user_data = {}

# رموز تعبيرية نصية عصرية
EMOJI = {
    'welcome': '✨',
    'design': '✏️',
    'search': '🔍',
    'next': '▷',
    'prev': '◁',
    'download': '⤓',
    'info': 'ⓘ',
    'error': '⚠️',
    'icon': '🖼️',
    'success': '✅'
}

# قنوات الاشتراك الإجباري
REQUIRED_CHANNELS = ['@crazys7', '@AWU87']

def check_subscription(user_id):
    """التحقق من اشتراك المستخدم في القنوات المطلوبة"""
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Subscription check error: {e}")
            return False
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # التحقق من الاشتراك في القنوات
    if not check_subscription(user_id):
        channels_text = "\n".join([f"• {channel}" for channel in REQUIRED_CHANNELS])
        bot.send_message(
            user_id,
            f"🚀 مرحبًا بك في عالم التصميم!\n\n"
            f"للوصول إلى جميع الميزات، يرجى الانضمام إلى قنواتنا أولاً:\n"
            f"{channels_text}\n\n"
            f"بعد الاشتراك، أرسل /start مرة أخرى"
        )
        return

    welcome_text = f"""
    🌟 *مرحبًا بك مصممنا المبدع!* 🌟

    {EMOJI['icon']} هذا البوت سيساعدك في اكتشاف آلاف الأيقونات المجانية لتصاميمك

    ✨ *مميزات البوت*:
    - البحث في مكتبة ضخمة من الأيقونات
    - معاينة فورية قبل التحميل
    - جودة عالية بتنسيق SVG

    🛠️ *اختر أحد الخيارات*:
    """

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(f'{EMOJI["search"]} بدء البحث', callback_data='start_search'))
    markup.row(InlineKeyboardButton(f'{EMOJI["info"]} عن البوت', callback_data='about_bot'))
    
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if not check_subscription(user_id):
        channels_text = "\n".join([f"• {channel}" for channel in REQUIRED_CHANNELS])
        bot.answer_callback_query(
            call.id,
            f"يجب الاشتراك في القنوات أولاً:\n{channels_text}",
            show_alert=True
        )
        return
    
    if call.data == 'about_bot':
        about_text = f"""
        {EMOJI['info']} *معلومات البوت*:

        🛠️ *المميزات*:
        - بحث سريع في +100,000 أيقونة
        - دعم جميع المكتبات الشهيرة
        - تحميل مباشر بتنسيق SVG

        {EMOJI['design']} *كيفية الاستخدام*:
        1. اختر 'بدء البحث'
        2. اكتب كلمة البحث (مثل: heart, car)
        3. تصفح النتائج
        4. حمل الأيقونة المفضلة

        📌 المطور: @PIXAG7_BOT
        """
        bot.send_message(user_id, about_text, parse_mode='Markdown')
    
    elif call.data == 'start_search':
        msg = bot.send_message(
            user_id,
            f"{EMOJI['search']} *أدخل كلمة البحث*:\n"
            f"(مثال: music, phone, arrow)\n\n"
            f"✏️ يمكنك البحث باللغة الإنجليزية فقط",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, process_search_query)
    
    elif call.data.startswith('nav_'):
        handle_navigation(call)
    
    elif call.data.startswith('dl_'):
        handle_download(call)

def handle_navigation(call):
    user_id = call.from_user.id
    data = call.data.split('_')
    action = data[1]
    current_index = int(data[2])
    
    if user_id not in user_data or 'results' not in user_data[user_id]:
        return
    
    results = user_data[user_id]['results']
    new_index = current_index
    
    if action == 'next':
        new_index = min(current_index + 1, len(results) - 1)
    elif action == 'prev':
        new_index = max(current_index - 1, 0)
    
    user_data[user_id]['current_index'] = new_index
    show_result(user_id, new_index)

def handle_download(call):
    user_id = call.from_user.id
    index = int(call.data.split('_')[1])
    
    if user_id not in user_data or 'results' not in user_data[user_id]:
        return
    
    result = user_data[user_id]['results'][index]
    icon_name = result['name']
    
    try:
        svg_url = f"{ICONIFY_API}/{icon_name}.svg"
        response = requests.get(svg_url)
        
        if response.status_code == 200:
            svg_file = io.BytesIO(response.content)
            svg_file.name = f"{icon_name.replace(':', '-')}.svg"
            
            bot.send_document(
                user_id,
                svg_file,
                caption=f"{EMOJI['success']} تم تحميل الأيقونة: *{icon_name}*",
                parse_mode='Markdown'
            )
        else:
            bot.answer_callback_query(call.id, "⚠️ تعذر تحميل الأيقونة", show_alert=True)
    except Exception as e:
        print(f"Download error: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء التحميل", show_alert=True)

def process_search_query(message):
    user_id = message.from_user.id
    query = message.text.strip()
    
    if not query:
        bot.send_message(user_id, "⚠️ يرجى إدخال كلمة البحث")
        return
    
    bot.send_chat_action(user_id, 'typing')
    
    results = search_icons(query)
    
    if results:
        user_data[user_id] = {'results': results, 'current_index': 0}
        show_result(user_id, 0)
    else:
        bot.send_message(
            user_id,
            f"{EMOJI['error']} *لم يتم العثور على نتائج*\n\n"
            f"جرب كلمات بحث أخرى مثل:\n"
            f"• {EMOJI['search']} home\n"
            f"• {EMOJI['search']} car\n"
            f"• {EMOJI['search']} weather",
            parse_mode='Markdown'
        )

def show_result(user_id, index):
    results = user_data[user_id]['results']
    result = results[index]
    
    # إنشاء واجهة النتائج
    caption = (
        f"{EMOJI['icon']} *النتيجة {index+1} من {len(results)}*\n\n"
        f"📛 *الاسم*: `{result['name']}`\n"
        f"📚 *المكتبة*: {result.get('provider', 'غير معروف')}\n\n"
        f"استخدم الأزرار للتنقل أو التحميل"
    )
    
    # إنشاء الأزرار بشكل عمودي
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(f"{EMOJI['prev']} السابق", callback_data=f"nav_prev_{index}"))
    markup.row(InlineKeyboardButton(f"{EMOJI['download']} تحميل SVG", callback_data=f"dl_{index}"))
    markup.row(InlineKeyboardButton(f"{EMOJI['next']} التالي", callback_data=f"nav_next_{index}"))
    
    # إرسال الصورة المصغرة
    try:
        png_url = f"https://api.iconify.design/{result['name']}.png?width=400&height=400"
        bot.send_photo(
            user_id,
            png_url,
            caption=caption,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Preview error: {e}")
        bot.send_message(
            user_id,
            caption,
            reply_markup=markup,
            parse_mode='Markdown'
        )

def search_icons(query):
    try:
        url = f"{ICONIFY_API}/search?query={quote(query)}&limit=10"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('icons', [])
        
        print(f"API Error: {response.status_code}")
        return []
    except Exception as e:
        print(f"Search error: {e}")
        return []

if __name__ == '__main__':
    print("🌟 البوت يعمل الآن...")
    bot.polling() 
