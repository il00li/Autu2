import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json

# Iconify API
ICONIFY_API_URL = 'https://api.iconify.design/search'

bot = telebot.TeleBot('7968375518:AAHhFQcaIvAS48SRnVUxQ7fd_bltB9MTIBc ')  # استبدل بـ توكن بوتك

# تخزين مؤقت لنتائج البحث
user_data = {}

# رموز تعبيرية نصية
EMOJI = {
    'welcome': '(^_^)',
    'design': '<*_*>',
    'search': '🔎',
    'next': '→',
    'prev': '←',
    'download': '↓',
    'info': 'ℹ️',
    'error': '!'
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
        channels_text = "\n".join([f"- {channel}" for channel in REQUIRED_CHANNELS])
        bot.send_message(
            user_id,
            f"عذراً، يجب الاشتراك في القنوات التالية أولاً:\n{channels_text}\nبعد الاشتراك أرسل /start مرة أخرى"
        )
        return

    welcome_text = f"""
    أهلاً بك مصممي المبدع {EMOJI['welcome']}
    هذا البوت يساعدك في العثور على أفضل الأيقونات المجانية {EMOJI['design']}
    
    للتأكد من حصولك على أفضل النتائج:
    - @crazys7
    - @AWU87
    
    اختر أحد الخيارات للبدء:
    """
    
    markup = InlineKeyboardMarkup(row_width=2)
    btn_search = InlineKeyboardButton(f'بدء البحث {EMOJI["search"]}', callback_data='start_search')
    btn_about = InlineKeyboardButton(f'عن البوت {EMOJI["info"]}', callback_data='about_bot')
    markup.add(btn_search, btn_about)
    
    bot.send_message(user_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    # التحقق من الاشتراك في القنوات
    if not check_subscription(user_id):
        channels_text = "\n".join([f"- {channel}" for channel in REQUIRED_CHANNELS])
        bot.answer_callback_query(
            call.id,
            f"يجب الاشتراك في القنوات أولاً:\n{channels_text}",
            show_alert=True
        )
        return
    
    if call.data == 'about_bot':
        about_text = f"""
        {EMOJI['info']} وصف البوت:
        
        هذا البوت هو مساعدك الشخصي للعثور على أيقونات تصميمية 
        بجودة عالية ومجانية {EMOJI['design']}
        
        يمكنك البحث عن أيقونات SVG لاستخدامها في مشاريعك.
        
        مطور البوت: @PIXAG7_BOT
        """
        bot.send_message(user_id, about_text)
    
    elif call.data == 'start_search':
        msg = bot.send_message(user_id, f'أرسل كلمة البحث للأيقونات {EMOJI["search"]}:')
        bot.register_next_step_handler(msg, process_search_query)

def process_search_query(message):
    user_id = message.from_user.id
    query = message.text
    
    # التحقق من الاشتراك في القنوات
    if not check_subscription(user_id):
        channels_text = "\n".join([f"- {channel}" for channel in REQUIRED_CHANNELS])
        bot.send_message(
            user_id,
            f"عذراً، يجب الاشتراك في القنوات التالية أولاً:\n{channels_text}"
        )
        return
    
    # البحث عن الأيقونات
    results = search_icons(query)
    
    if results:
        user_data[user_id] = {
            'results': results,
            'current_index': 0
        }
        show_result(user_id, 0)
    else:
        bot.send_message(user_id, f'لم أجد نتائج {EMOJI["error"]}')

def show_result(user_id, index):
    if user_id not in user_data or 'results' not in user_data[user_id]:
        return
    
    results = user_data[user_id]['results']
    if index < 0 or index >= len(results):
        return
    
    result = results[index]
    
    # إنشاء واجهة النتائج
    caption = f"النتيجة {index+1} من {len(results)}\n"
    caption += f"الاسم: {result['name']}\n"
    
    # أزرار التنقل والتحميل
    markup = InlineKeyboardMarkup(row_width=3)
    btn_prev = InlineKeyboardButton(f'{EMOJI["prev"]} سابق', callback_data=f'result_{index}_prev')
    btn_next = InlineKeyboardButton(f'تالي {EMOJI["next"]}', callback_data=f'result_{index}_next')
    btn_download = InlineKeyboardButton(f'تحميل SVG {EMOJI["download"]}', callback_data=f'download_{index}')
    
    markup.add(btn_prev, btn_download, btn_next)
    
    # إرسال صورة الأيقونة (كصورة مصغرة)
    # نستخدم رابط SVG لكننا نعرضه كصورة في التلجرام
    svg_url = f"https://api.iconify.design/{result['name']}.svg"
    try:
        # نستخدم خدمة تحويل SVG إلى PNG للعرض (مثال: svg2png.vercel.app)
        png_url = f"https://svg2png.vercel.app/api/svg2png?url={svg_url}"
        bot.send_photo(user_id, png_url, caption=caption, reply_markup=markup)
    except Exception as e:
        print(f"Error sending icon: {e}")
        bot.send_message(user_id, caption, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('result_') or call.data.startswith('download_'))
def handle_result_nav(call):
    user_id = call.from_user.id
    data_parts = call.data.split('_')
    
    if call.data.startswith('download_'):
        index = int(data_parts[1])
        if user_id in user_data and 'results' in user_data[user_id]:
            result = user_data[user_id]['results'][index]
            svg_url = f"https://api.iconify.design/{result['name']}.svg"
            bot.send_document(user_id, svg_url, caption=f"أيقونة: {result['name']}")
        return
    
    # معالجة التنقل
    index = int(data_parts[1])
    action = data_parts[2]
    
    if user_id in user_data and 'results' in user_data[user_id]:
        results = user_data[user_id]['results']
        current_index = user_data[user_id].get('current_index', 0)
        
        if action == 'next':
            current_index = min(current_index + 1, len(results) - 1)
        elif action == 'prev':
            current_index = max(current_index - 1, 0)
        
        user_data[user_id]['current_index'] = current_index
        show_result(user_id, current_index)

def search_icons(query):
    params = {
        'query': query,
        'limit': 50  # الحد الأقصى المسموح به
    }
    
    try:
        response = requests.get(ICONIFY_API_URL, params=params)
        
        # طباعة الاستجابة للتصحيح
        print(f"Iconify API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data.get('icons', [])[:10]  # نأخذ أول 10 نتائج
        else:
            print(f"Iconify API Error: {response.text}")
            return []
    except Exception as e:
        print(f"API Exception: {e}")
        return []

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling() 
