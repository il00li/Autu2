import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import re

# بيانات API من الصورة
FLATICON_API_KEY = '92d3add3fbed4ab7a1dcb2cc1cb55a3f'
SECONDARY_API_KEY = 'cccf9331ea24469f8356d5bbaa2b929a'

# تهيئة البوت
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
    'error': '!',
    'icon': '*'
}

# قنوات الاشتراك الإجباري
REQUIRED_CHANNELS = ['@crazys7', '@AWU87']

# جلسة API
session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "Authorization": f"Bearer {FLATICON_API_KEY}"
})

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
    أهلاً بك في نظام الأيقونات المتكامل {EMOJI['welcome']}
    هذا البوت يساعدك في العثور على أفضل الأيقونات التصميمية {EMOJI['icon']}
    
    مميزات النظام:
    - بحث متقدم في قاعدة أيقونات Flaticon
    - تحميل مباشر بصيغة SVG
    - واجهة مستخدم بديهية
    
    قنوات الدعم:
    - @crazys7
    - @AWU87
    
    اختر أحد الخيارات للبدء:
    """
    
    markup = InlineKeyboardMarkup(row_width=2)
    btn_search = InlineKeyboardButton(f'بدء البحث {EMOJI["search"]}', callback_data='start_search')
    btn_about = InlineKeyboardButton(f'عن النظام {EMOJI["info"]}', callback_data='about_system')
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
    
    if call.data == 'about_system':
        about_text = f"""
        {EMOJI['info']} وصف النظام:
        
        نظام متكامل للبحث عن الأيقونات وتحميلها {EMOJI['icon']}
        يعمل باستخدام واجهة برمجة تطبيقات Flaticon الرسمية
        
        الميزات:
        - بحث سريع ودقيق
        - معاينة الأيقونات قبل التحميل
        - تحميل مباشر بصيغة SVG
        - واجهة مستخدم متطورة
        
        إعدادات النظام:
        - المفتاح الأساسي: {FLATICON_API_KEY[:8]}...{FLATICON_API_KEY[-8:]}
        - المفتاح الثانوي: {SECONDARY_API_KEY[:8]}...{SECONDARY_API_KEY[-8:]}
        
        للتواصل مع الدعم الفني: @PIXAG7_BOT
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
            
            # تحميل الأيقونة كملف SVG
            icon_id = result['id']
            icon_url = get_icon_download_url(icon_id)
            
            if icon_url:
                try:
                    # إرسال الأيقونة كملف
                    bot.send_document(user_id, icon_url, caption=f"الأيقونة: {result['name']}")
                except Exception as e:
                    print(f"Download error: {e}")
                    bot.send_message(user_id, f"حدث خطأ في التحميل {EMOJI['error']}")
            else:
                bot.send_message(user_id, f"لم أتمكن من تحميل الأيقونة {EMOJI['error']}")

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
    bot.send_message(user_id, f"جاري البحث عن أيقونات لـ '{query}'...")
    results = search_flaticon(query)
    
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
    result = results[index]
    
    # إنشاء واجهة النتائج
    caption = f"النتيجة {index+1} من {len(results)}\n"
    caption += f"اسم الأيقونة: {result['name']}\n"
    caption += f"المكتبة: {result['library']}"
    
    # أزرار التنقل والتحميل
    markup = InlineKeyboardMarkup(row_width=3)
    btn_prev = InlineKeyboardButton(f'{EMOJI["prev"]} سابق', callback_data=f'result_{index}_prev')
    btn_next = InlineKeyboardButton(f'تالي {EMOJI["next"]}', callback_data=f'result_{index}_next')
    btn_download = InlineKeyboardButton(f'تحميل SVG {EMOJI["download"]}', callback_data=f'download_{index}')
    
    markup.add(btn_prev, btn_download, btn_next)
    
    # إرسال صورة الأيقونة
    try:
        # استخدام الصورة المصغرة
        preview_url = result['images']['128'] if 'images' in result else None
        if preview_url:
            bot.send_photo(user_id, preview_url, caption=caption, reply_markup=markup)
        else:
            bot.send_message(user_id, caption, reply_markup=markup)
    except Exception as e:
        print(f"Thumbnail error: {e}")
        bot.send_message(user_id, caption, reply_markup=markup)

def search_flaticon(query):
    """البحث عن الأيقونات باستخدام Flaticon API"""
    try:
        url = f"https://api.flaticon.com/v3/search"
        params = {
            'q': query,
            'limit': 10,
            'type': 'all'
        }
        response = session.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return [{
                'id': item['id'],
                'name': item.get('name', 'No Name'),
                'library': item.get('library', {}).get('name', 'Unknown'),
                'images': item.get('images', {})
            } for item in data.get('data', [])]
        else:
            print(f"Flaticon API Error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"API Exception: {e}")
        return []

def get_icon_download_url(icon_id):
    """الحصول على رابط تحميل الأيقونة بصيغة SVG"""
    try:
        url = f"https://api.flaticon.com/v3/item/{icon_id}/download"
        params = {'format': 'svg'}
        response = session.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('svg', {}).get('url', '')
        else:
            print(f"Download API Error: {response.status_code} - {response.text}")
            return ''
    except Exception as e:
        print(f"Download Exception: {e}")
        return ''

if __name__ == '__main__':
    print("System running...")
    bot.polling(none_stop=True) 
