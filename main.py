import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests

API_KEY = 'FPSXd1183dea1da3476a90735318b3930ba3'
API_URL = 'https://api.freepik.com/v1/resources'
bot = telebot.TeleBot('7968375518:AAGGfLq9elxG9GGzNiu_q_VJvPbz07Zx1Qc')  # استبدل بـ توكن بوتك

# تخزين مؤقت لنتائج البحث
user_data = {}

# أنواع المحتوى المدعومة
CONTENT_TYPES = {
    'photo': 'صور',
    'vector': 'رسومات',
    'psd': 'ملفات PSD',
    'video': 'فيديو'
}

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    welcome_text = f"""
    أهلاً بك مصممي المبدع {EMOJI['welcome']}
    هذا البوت يساعدك في العثور على أفضل الملحقات التصميمية {EMOJI['design']}
    
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
    
    if call.data == 'about_bot':
        about_text = f"""
        {EMOJI['info']} وصف البوت:
        
        هذا البوت هو مساعدك الشخصي للعثور على ملحقات التصميم 
        بجودة عالية ومجانية {EMOJI['design']}
        
        يمكنك البحث عن:
        - صور
        - فيديوهات
        - رسومات متجهية
        - ملفات PSD
        
        مطور البوت: @PIXAG7_BOT
        """
        bot.send_message(user_id, about_text)
    
    elif call.data == 'start_search':
        show_content_types(user_id)
    
    elif call.data.startswith('type_'):
        content_type = call.data.split('_')[1]
        user_data[user_id] = {'type': content_type}
        msg = bot.send_message(user_id, f'أرسل كلمة البحث {EMOJI["search"]}:')
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
            
            # إرسال الملف حسب نوعه
            file_url = result['url']
            file_type = result['type']
            
            if file_type == 'photo':
                bot.send_photo(user_id, file_url)
            elif file_type == 'vector':
                bot.send_document(user_id, file_url)
            elif file_type == 'video':
                bot.send_video(user_id, file_url)
            elif file_type == 'psd':
                bot.send_document(user_id, file_url)

def show_content_types(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for key, value in CONTENT_TYPES.items():
        buttons.append(InlineKeyboardButton(f'{value} {EMOJI["search"]}', callback_data=f'type_{key}'))
    markup.add(*buttons)
    bot.send_message(user_id, 'اختر نوع المحتوى الذي تريد البحث عنه:', reply_markup=markup)

def process_search_query(message):
    user_id = message.from_user.id
    query = message.text
    
    if user_id in user_data:
        content_type = user_data[user_id]['type']
        results = search_freepik(query, content_type)
        
        if results:
            user_data[user_id]['results'] = results
            user_data[user_id]['current_index'] = 0
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
    caption += f"العنوان: {result['title']}\n"
    
    # أزرار التنقل والتحميل
    markup = InlineKeyboardMarkup(row_width=3)
    btn_prev = InlineKeyboardButton(f'{EMOJI["prev"]} سابق', callback_data=f'result_{index}_prev')
    btn_next = InlineKeyboardButton(f'تالي {EMOJI["next"]}', callback_data=f'result_{index}_next')
    btn_download = InlineKeyboardButton(f'تحميل {EMOJI["download"]}', callback_data=f'download_{index}')
    
    markup.add(btn_prev, btn_download, btn_next)
    
    # إرسال الصورة المصغرة مع النتيجة
    if 'thumbnail' in result and result['thumbnail']:
        bot.send_photo(user_id, result['thumbnail'], caption=caption, reply_markup=markup)
    else:
        bot.send_message(user_id, caption, reply_markup=markup)

def search_freepik(query, content_type):
    headers = {'Authorization': f'Bearer {API_KEY}'}
    params = {
        'locale': 'en-US',
        'page': 1,
        'limit': 10,
        'term': query,
        'type': content_type
    }
    
    try:
        response = requests.get(API_URL, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return [{
                'id': item['id'],
                'title': item['title'],
                'url': item['url'],
                'type': item['type'],
                'thumbnail': item['thumbnails'][0]['url'] if item['thumbnails'] else None
            } for item in data.get('data', [])]
    except Exception as e:
        print(f"API Error: {e}")
    return []

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling()
