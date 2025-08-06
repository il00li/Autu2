import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import logging
from urllib.parse import quote
import time

# تكوين السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot.log'
)

# إعدادات API
FLATICON_API_KEY = '92d3add3fbed4ab7a1dcb2cc1cb55a3f'  # استبدله بمفتاحك الصحيح
FLATICON_API_URL = "https://api.flaticon.com/v3"

# إعداد البوت
try:
    bot = telebot.TeleBot('7968375518:AAHhFQcaIvAS48SRnVUxQ7fd_bltB9MTIBc')  # استبدل بتوكن البوت
except Exception as e:
    logging.critical(f"فشل تهيئة البوت: {e}")
    exit()

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

# جلسة API محسنة
session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {FLATICON_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "FlaticonBot/2.0"
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
        
        ✨ الميزات:
        - بحث متقدم في ملايين الأيقونات
        - معاينة قبل التحميل
        - تحميل مباشر بصيغة SVG
        
        📢 القنوات الرسمية:
        - @crazys7
        - @AWU87
        
        اختر أحد الخيارات:
        """
        
        markup = InlineKeyboardMarkup(row_width=2)
        btn_search = InlineKeyboardButton(f'بحث عن أيقونة {EMOJI["search"]}', callback_data='start_search')
        btn_help = InlineKeyboardButton(f'مساعدة {EMOJI["info"]}', callback_data='show_help')
        markup.add(btn_search, btn_help)
        
        bot.send_message(user_id, welcome_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"خطأ في send_welcome: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        user_id = call.from_user.id
        
        if call.data == 'start_search':
            msg = bot.send_message(user_id, f"أدخل كلمة البحث للأيقونات {EMOJI['search']}:")
            bot.register_next_step_handler(msg, process_search)
            
        elif call.data == 'show_help':
            help_text = f"""
            {EMOJI['info']} دليل استخدام البوت:
            
            1. أرسل /start للبدء
            2. اختر 'بحث عن أيقونة'
            3. أدخل كلمة البحث (مثال: heart, phone)
            4. تصفح النتائج واستخدم الأزرار للتنقل
            5. اضغط 'تحميل' للحصول على الأيقونة
            
            📌 ملاحظات:
            - يمكنك البحث باللغة الإنجليزية فقط
            - الحد الأقصى للنتائج: 10 أيقونات
            - الدعم الفني: @PIXAG7_BOT
            """
            bot.send_message(user_id, help_text)
            
        elif call.data.startswith('page_'):
            page = int(call.data.split('_')[1])
            show_results(user_id, page)
            
        elif call.data.startswith('download_'):
            icon_id = call.data.split('_')[1]
            download_icon(user_id, icon_id)
            
    except Exception as e:
        logging.error(f"خطأ في handle_callback: {e}")

def process_search(message):
    try:
        user_id = message.from_user.id
        query = message.text.strip()
        
        if len(query) < 2:
            bot.send_message(user_id, f"الكلمة قصيرة جداً {EMOJI['error']}")
            return
            
        bot.send_message(user_id, f"🔍 جاري البحث عن '{query}'...")
        
        # البحث مع إضافة تأخير لتجنب rate limits
        time.sleep(1)
        results = search_icons(query)
        
        if not results or len(results) == 0:
            bot.send_message(user_id, f"⚠️ لم أجد نتائج، حاول بكلمة أخرى")
            return
            
        user_data[user_id] = {
            'query': query,
            'results': results,
            'page': 0
        }
        
        show_results(user_id, 0)
        
    except Exception as e:
        logging.error(f"خطأ في process_search: {e}")
        bot.send_message(user_id, "حدث خطأ أثناء البحث، حاول لاحقاً")

def search_icons(query):
    """البحث عن الأيقونات في Flaticon API"""
    try:
        url = f"{FLATICON_API_URL}/search"
        params = {
            'q': query,
            'limit': 10,
            'type': 'all'
        }
        
        response = session.get(url, params=params, timeout=15)
        logging.info(f"API Request: {response.url}")
        
        if response.status_code == 200:
            data = response.json()
            return [{
                'id': item['id'],
                'name': item.get('name', 'بدون اسم'),
                'library': item.get('library', {}).get('name', 'غير معروف'),
                'preview': item.get('images', {}).get('128', ''),
                'download_url': f"https://api.flaticon.com/v3/item/{item['id']}/download?format=svg"
            } for item in data.get('data', [])]
        else:
            logging.error(f"خطأ API: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logging.error(f"خطأ في search_icons: {e}")
        return []

def show_results(user_id, page):
    try:
        if user_id not in user_data:
            return
            
        data = user_data[user_id]
        results = data['results']
        total_pages = (len(results) + 2) // 3  # 3 نتائج لكل صفحة
        
        if page < 0 or page >= total_pages:
            return
            
        user_data[user_id]['page'] = page
        start_idx = page * 3
        end_idx = min(start_idx + 3, len(results))
        
        for i in range(start_idx, end_idx):
            icon = results[i]
            caption = f"{icon['name']}\nالمكتبة: {icon['library']}"
            
            markup = InlineKeyboardMarkup()
            btn_download = InlineKeyboardButton(
                f"تحميل SVG {EMOJI['download']}", 
                callback_data=f'download_{icon["id"]}'
            )
            markup.add(btn_download)
            
            if icon['preview']:
                bot.send_photo(user_id, icon['preview'], caption=caption, reply_markup=markup)
            else:
                bot.send_message(user_id, caption, reply_markup=markup)
        
        # أزرار التنقل بين الصفحات
        if total_pages > 1:
            markup = InlineKeyboardMarkup(row_width=3)
            buttons = []
            
            if page > 0:
                buttons.append(InlineKeyboardButton(f"{EMOJI['prev']} السابق", callback_data=f'page_{page-1}'))
            
            buttons.append(InlineKeyboardButton(f"الصفحة {page+1}/{total_pages}", callback_data='_'))
            
            if page < total_pages - 1:
                buttons.append(InlineKeyboardButton(f"التالي {EMOJI['next']}", callback_data=f'page_{page+1}'))
            
            markup.add(*buttons)
            bot.send_message(user_id, "تصفح النتائج:", reply_markup=markup)
            
    except Exception as e:
        logging.error(f"خطأ في show_results: {e}")

def download_icon(user_id, icon_id):
    try:
        bot.send_message(user_id, "⏳ جاري تحضير الأيقونة...")
        
        # البحث عن الأيقونة في النتائج المحفوظة
        icon_data = None
        if user_id in user_data:
            for icon in user_data[user_id]['results']:
                if icon['id'] == icon_id:
                    icon_data = icon
                    break
        
        if icon_data:
            bot.send_document(
                user_id,
                icon_data['download_url'],
                caption=f"تم التحميل: {icon_data['name']}"
            )
        else:
            bot.send_message(user_id, "⚠️ لم أتمكن من العثور على الأيقونة المطلوبة")
            
    except Exception as e:
        logging.error(f"خطأ في download_icon: {e}")
        bot.send_message(user_id, "❌ حدث خطأ أثناء التحميل، حاول مرة أخرى")

if __name__ == '__main__':
    try:
        logging.info("🚀 بدء تشغيل البوت...")
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except KeyboardInterrupt:
        logging.info("⏹ إيقاف البوت...")
    except Exception as e:
        logging.critical(f"🔥 خطأ غير متوقع: {e}")
    finally:
        session.close()
        logging.info("✅ تم إغلاق الجلسات") 
