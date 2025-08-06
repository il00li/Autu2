import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import logging
from urllib.parse import quote

# تهيئة التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# بيانات API من Flaticon
FLATICON_API_KEY = '92d3add3fbed4ab7a1dcb2cc1cb55a3f'  # استبدل بمفتاحك الفعلي
FLATICON_API_URL = "https://api.flaticon.com/v3"

# تهيئة البوت
bot = telebot.TeleBot('7968375518:AAHhFQcaIvAS48SRnVUxQ7fd_bltB9MTIBc')  # استبدل بتوكن البوت الصحيح

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
    'error': '!',
    'icon': '*'
}

# قنوات الاشتراك الإجباري
REQUIRED_CHANNELS = ['@crazys7', '@AWU87']

# جلسة API مع الهيدرات المطلوبة
session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "Authorization": f"Bearer {FLATICON_API_KEY}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

def check_subscription(user_id):
    """التحقق من اشتراك المستخدم في القنوات المطلوبة"""
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            logging.error(f"خطأ في التحقق من القناة {channel}: {e}")
            return False
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.from_user.id
        
        if not check_subscription(user_id):
            channels_text = "\n".join([f"- {channel}" for channel in REQUIRED_CHANNELS])
            bot.send_message(
                user_id,
                f"عذراً، يجب الاشتراك في القنوات التالية أولاً:\n{channels_text}\nبعد الاشتراك أرسل /start مرة أخرى"
            )
            return

        welcome_text = f"""
        أهلاً بك في بوت الأيقونات الاحترافية {EMOJI['welcome']}
        هذا البوت يتيح لك البحث عن أيقونات Flaticon وتحميلها {EMOJI['icon']}
        
        القنوات الرسمية:
        - @crazys7
        - @AWU87
        
        اختر أحد الخيارات للبدء:
        """
        
        markup = InlineKeyboardMarkup(row_width=2)
        btn_search = InlineKeyboardButton(f'بدء البحث {EMOJI["search"]}', callback_data='start_search')
        btn_about = InlineKeyboardButton(f'عن البوت {EMOJI["info"]}', callback_data='about_bot')
        markup.add(btn_search, btn_about)
        
        bot.send_message(user_id, welcome_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"خطأ في send_welcome: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        user_id = call.from_user.id
        
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
            
            بوت الأيقونات الاحترافية {EMOJI['icon']}
            يعمل باستخدام واجهة Flaticon API
            
            الميزات:
            - بحث متقدم في ملايين الأيقونات
            - تحميل مباشر بصيغة SVG
            - واجهة مستخدم سهلة
            
            المطور: @PIXAG7_BOT
            """
            bot.send_message(user_id, about_text)
        
        elif call.data == 'start_search':
            msg = bot.send_message(user_id, f'أدخل كلمة البحث للأيقونات {EMOJI["search"]}:')
            bot.register_next_step_handler(msg, process_search_query)
        
        elif call.data.startswith('result_'):
            data_parts = call.data.split('_')
            result_index = int(data_parts[1])
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
        
        elif call.data.startswith('download_'):
            if user_id in user_data and 'results' in user_data[user_id]:
                current_index = user_data[user_id]['current_index']
                result = user_data[user_id]['results'][current_index]
                
                download_icon(user_id, result['id'])
    except Exception as e:
        logging.error(f"خطأ في handle_callback: {e}")

def process_search_query(message):
    try:
        user_id = message.from_user.id
        query = message.text.strip()
        
        if not query:
            bot.send_message(user_id, f"الرجاء إدخال كلمة بحث صحيحة {EMOJI['error']}")
            return
        
        bot.send_message(user_id, f"جاري البحث عن أيقونات لـ '{query}'...")
        
        results = search_flaticon(query)
        
        if results:
            user_data[user_id] = {
                'results': results,
                'current_index': 0
            }
            show_result(user_id, 0)
        else:
            bot.send_message(user_id, f"لم يتم العثور على نتائج {EMOJI['error']}")
    except Exception as e:
        logging.error(f"خطأ في process_search_query: {e}")

def show_result(user_id, index):
    try:
        if user_id not in user_data or 'results' not in user_data[user_id]:
            return
        
        results = user_data[user_id]['results']
        result = results[index]
        
        caption = f"النتيجة {index+1} من {len(results)}\n"
        caption += f"اسم الأيقونة: {result['name']}\n"
        caption += f"المكتبة: {result['library']}"
        
        markup = InlineKeyboardMarkup(row_width=3)
        btn_prev = InlineKeyboardButton(f'{EMOJI["prev"]} سابق', callback_data=f'result_{index}_prev')
        btn_next = InlineKeyboardButton(f'تالي {EMOJI["next"]}', callback_data=f'result_{index}_next')
        btn_download = InlineKeyboardButton(f'تحميل SVG {EMOJI["download"]}', callback_data=f'download_{index}')
        
        markup.add(btn_prev, btn_download, btn_next)
        
        if result.get('preview_url'):
            bot.send_photo(user_id, result['preview_url'], caption=caption, reply_markup=markup)
        else:
            bot.send_message(user_id, caption, reply_markup=markup)
    except Exception as e:
        logging.error(f"خطأ في show_result: {e}")

def search_flaticon(query):
    """البحث عن الأيقونات في Flaticon API"""
    try:
        url = f"{FLATICON_API_URL}/search"
        params = {
            'q': query,
            'limit': 10,
            'type': 'all'
        }
        
        response = session.get(url, params=params, timeout=10)
        logging.info(f"API Request: {response.url}")
        logging.info(f"API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return [{
                'id': item['id'],
                'name': item.get('name', 'بدون اسم'),
                'library': item.get('library', {}).get('name', 'غير معروف'),
                'preview_url': item.get('images', {}).get('128', '')
            } for item in data.get('data', [])]
        else:
            logging.error(f"خطأ API: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logging.error(f"خطأ في search_flaticon: {e}")
        return []

def download_icon(user_id, icon_id):
    """تحميل الأيقونة وإرسالها للمستخدم"""
    try:
        url = f"{FLATICON_API_URL}/item/{icon_id}/download"
        params = {'format': 'svg'}
        
        response = session.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            download_url = data.get('data', {}).get('svg', {}).get('url', '')
            
            if download_url:
                bot.send_document(user_id, download_url, caption="تم التحميل بنجاح")
            else:
                bot.send_message(user_id, f"خطأ في الحصول على رابط التحميل {EMOJI['error']}")
        else:
            bot.send_message(user_id, f"خطأ في تحميل الأيقونة {EMOJI['error']}")
            logging.error(f"خطأ تحميل: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"خطأ في download_icon: {e}")
        bot.send_message(user_id, f"حدث خطأ أثناء التحميل {EMOJI['error']}")

if __name__ == '__main__':
    try:
        logging.info("جارٍ تشغيل البوت...")
        bot.polling(none_stop=True, interval=3, timeout=60)
    except Exception as e:
        logging.critical(f"انهيار البوت: {e}")
