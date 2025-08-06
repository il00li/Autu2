import logging
import requests
import datetime
import json
import os

# ================ إعدادات البوت ================
TOKEN = "7639996535:AAH_Ppw8jeiUg4nJjjEyOXaYlip289jSAio"
PIXABAY_API_KEY = "51444506-bbfefcaf12816bd85a20222d1"
CHANNELS = ["@crazys7", "@AWU87"]
MANAGER_ID = 7251748706
WEBHOOK_URL = "https://autu2.onrender.com"

# ================ إعداد التسجيل ================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================ وظائف API ================
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة: {e}")
        return None

def send_photo(chat_id, photo, caption, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo,
        "caption": caption,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"خطأ في إرسال صورة: {e}")
        return None

def edit_message_reply_markup(chat_id, message_id, reply_markup):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageReplyMarkup"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": json.dumps(reply_markup)
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"خطأ في تعديل لوحة المفاتيح: {e}")

def edit_message_media(chat_id, message_id, media, reply_markup):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageMedia"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "media": json.dumps(media),
        "reply_markup": json.dumps(reply_markup)
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"خطأ في تعديل الوسائط: {e}")

def send_audio(chat_id, audio, caption, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "audio": audio,
        "caption": caption,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"خطأ في إرسال ملف صوتي: {e}")
        return None

def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logger.error(f"خطأ في حذف رسالة: {e}")

# ================ لوحات المفاتيح ================
def get_main_menu_keyboard():
    return {"inline_keyboard": [[{"text": "انقر للبحث 🎧", "callback_data": "start_search_type"}]]}

def get_search_type_keyboard():
    return {"inline_keyboard": [
        [{"text": "صور 🖼️", "callback_data": "search_photo"}],
        [{"text": "أصوات 🎶", "callback_data": "search_sound"}],
        [{"text": "رجوع ↩️", "callback_data": "back_to_menu"}]
    ]}

def get_navigation_keyboard(index, total_results, result_type):
    keyboard_buttons = []
    if index > 0:
        keyboard_buttons.append({"text": "« السابق", "callback_data": f'prev_{result_type}'})
    if index < total_results - 1:
        keyboard_buttons.append({"text": "التالي »", "callback_data": f'next_{result_type}'})
    
    return {"inline_keyboard": [keyboard_buttons]} if keyboard_buttons else None
    # ================ إدارة الحالة (تخزين مؤقت) ================
user_states = {}

def get_user_state(user_id):
    return user_states.get(user_id, {"state": "MAIN_MENU", "data": {}})

def set_user_state(user_id, state, data=None):
    user_states[user_id] = {"state": state, "data": data or {}}

# ================ معالجات الرسائل والـ callbacks ================
def handle_update(update):
    if 'message' in update:
        handle_message(update['message'])
    elif 'callback_query' in update:
        handle_callback_query(update['callback_query'])

def handle_message(message):
    user_id = message['from']['id']
    chat_id = message['chat']['id']
    text = message.get('text', '')
    
    current_state = get_user_state(user_id)
    
    if text == '/start':
        if check_subscription(user_id):
            notify_manager(message['from'])
            send_message(chat_id, "🌟 قائمة البحث الرئيسية 🌟", reply_markup=get_main_menu_keyboard())
            set_user_state(user_id, "MAIN_MENU")
        else:
            show_channels(chat_id)
            
    elif current_state['state'] == "SEARCHING_PHOTO":
        perform_photo_search(user_id, chat_id, text)
        
    elif current_state['state'] == "SEARCHING_SOUND":
        perform_sound_search(user_id, chat_id, text)

def handle_callback_query(callback_query):
    user_id = callback_query['from']['id']
    chat_id = callback_query['message']['chat']['id']
    message_id = callback_query['message']['message_id']
    data = callback_query['data']
    
    current_state = get_user_state(user_id)
    
    if data == 'check_subscription':
        if check_subscription(user_id):
            notify_manager(callback_query['from'])
            send_message(chat_id, "تم التحقق بنجاح! ✅")
            send_message(chat_id, "🌟 قائمة البحث الرئيسية 🌟", reply_markup=get_main_menu_keyboard())
            set_user_state(user_id, "MAIN_MENU")
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_query['id'], "text": "لم تكتمل الاشتراكات بعد! ❌", "show_alert": True})
            
    elif data == 'start_search_type' and current_state['state'] == "MAIN_MENU":
        edit_message_reply_markup(chat_id, message_id, get_search_type_keyboard())
        set_user_state(user_id, "SEARCH_TYPE")
        
    elif data == 'search_photo' and current_state['state'] == "SEARCH_TYPE":
        send_message(chat_id, "🖼️ أرسل كلمة البحث للصور الآن:")
        set_user_state(user_id, "SEARCHING_PHOTO")
    
    elif data == 'search_sound' and current_state['state'] == "SEARCH_TYPE":
        send_message(chat_id, "🎶 أرسل كلمة البحث للمؤثرات الصوتية الآن:")
        set_user_state(user_id, "SEARCHING_SOUND")
    
    elif data.startswith('next_photo') and current_state['state'] == "RESULTS_PHOTO":
        navigate_photo_results(user_id, chat_id, message_id, 'next')
    
    elif data.startswith('prev_photo') and current_state['state'] == "RESULTS_PHOTO":
        navigate_photo_results(user_id, chat_id, message_id, 'prev')

    elif data.startswith('next_sound') and current_state['state'] == "RESULTS_SOUND":
        navigate_sound_results(user_id, chat_id, message_id, 'next')

    elif data.startswith('prev_sound') and current_state['state'] == "RESULTS_SOUND":
        navigate_sound_results(user_id, chat_id, message_id, 'prev')

    elif data == 'back_to_menu':
        delete_message(chat_id, message_id)
        send_message(chat_id, "🌟 قائمة البحث الرئيسية 🌟", reply_markup=get_main_menu_keyboard())
        set_user_state(user_id, "MAIN_MENU")

# ================ وظائف مساعدة ================
def check_subscription(user_id):
    try:
        for channel in CHANNELS:
            url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={channel}&user_id={user_id}"
            response = requests.get(url)
            status = response.json()['result']['status']
            if status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {e}")
        return False

def notify_manager(user_data):
    user_id = user_data['id']
    current_state = get_user_state(user_id)
    if not current_state['data'].get('notified_manager'):
        user_info = f"👤 مستخدم جديد انضم إلى القنوات!\n\n🆔 المعرف: {user_data['id']}\n👤 الاسم: {user_data['first_name']}\n📅 التاريخ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if user_data.get('username'): user_info += f"\n🔖 اليوزر: @{user_data['username']}"
        send_message(MANAGER_ID, user_info)
        current_state['data']['notified_manager'] = True
        set_user_state(user_id, current_state['state'], current_state['data'])

def show_channels(chat_id):
    buttons = {"inline_keyboard": [
        [{"text": "قناة 1", "url": "https://t.me/crazys7"}, {"text": "قناة 2", "url": "https://t.me/AWU87"}],
        [{"text": "تحقق | Check", "callback_data": "check_subscription"}]
    ]}
    send_message(chat_id, "❗️ يجب الاشتراك في القنوات التالية أولاً:", reply_markup=buttons)

# ================ دوال البحث ================
def perform_photo_search(user_id, chat_id, search_query):
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={search_query}&image_type=photo&per_page=40"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('hits', [])
        
        if results:
            data = {"results": results, "current_index": 0, "current_query": search_query}
            set_user_state(user_id, "RESULTS_PHOTO", data)
            show_photo_result(chat_id, data)
        else:
            send_message(chat_id, "⚠️ لم يتم العثور على نتائج. حاول بكلمات أخرى.")
            send_message(chat_id, "🌟 قائمة البحث الرئيسية 🌟", reply_markup=get_main_menu_keyboard())
            set_user_state(user_id, "MAIN_MENU")
    except Exception as e:
        logger.error(f"خطأ في البحث عن الصور: {e}")
        send_message(chat_id, "❌ حدث خطأ في البحث. يرجى المحاولة لاحقًا.")
        send_message(chat_id, "🌟 قائمة البحث الرئيسية 🌟", reply_markup=get_main_menu_keyboard())
        set_user_state(user_id, "MAIN_MENU")

def perform_sound_search(user_id, chat_id, search_query):
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={search_query}&video_type=all&per_page=40"

    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('hits', [])
        
        if results:
            data = {"results": results, "current_index": 0, "current_query": search_query}
            set_user_state(user_id, "RESULTS_SOUND", data)
            show_sound_result(chat_id, data)
        else:
            send_message(chat_id, "⚠️ لم يتم العثور على نتائج. حاول بكلمات أخرى.")
            send_message(chat_id, "🌟 قائمة البحث الرئيسية 🌟", reply_markup=get_main_menu_keyboard())
            set_user_state(user_id, "MAIN_MENU")
    except Exception as e:
        logger.error(f"خطأ في البحث عن الأصوات: {e}")
        send_message(chat_id, "❌ حدث خطأ في البحث. يرجى المحاولة لاحقًا.")
        send_message(chat_id, "🌟 قائمة البحث الرئيسية 🌟", reply_markup=get_main_menu_keyboard())
        set_user_state(user_id, "MAIN_MENU")

def show_photo_result(chat_id, data, message_id=None):
    index = data['current_index']
    results = data['results']
    result = results[index]

    keyboard = get_navigation_keyboard(index, len(results), 'photo')
    caption = f"📸 المصور: {result['user']}\n\nصورة {index + 1} من {len(results)}"
    
    if message_id:
        media = {"type": "photo", "media": result['largeImageURL'], "caption": caption}
        edit_message_media(chat_id, message_id, media, keyboard)
    else:
        send_photo(chat_id, result['largeImageURL'], caption, keyboard)

def show_sound_result(chat_id, data, message_id=None):
    index = data['current_index']
    results = data['results']
    result = results[index]
    
    keyboard = get_navigation_keyboard(index, len(results), 'sound')
    sound_url = result['videos']['tiny']['url'] 
    caption = f"🎶 مؤثر صوتي من: {result['user']}\n\nصوت {index + 1} من {len(results)}"

    if message_id:
        delete_message(chat_id, message_id)
    send_audio(chat_id, sound_url, caption, keyboard)

def navigate_photo_results(user_id, chat_id, message_id, direction):
    current_state = get_user_state(user_id)
    data = current_state['data']
    current_index = data['current_index']
    
    new_index = current_index + 1 if direction == 'next' else current_index - 1
    
    data['current_index'] = new_index
    set_user_state(user_id, "RESULTS_PHOTO", data)
    show_photo_result(chat_id, data, message_id)

def navigate_sound_results(user_id, chat_id, message_id, direction):
    current_state = get_user_state(user_id)
    data = current_state['data']
    current_index = data['current_index']
    
    new_index = current_index + 1 if direction == 'next' else current_index - 1
    
    data['current_index'] = new_index
    set_user_state(user_id, "RESULTS_SOUND", data)
    show_sound_result(chat_id, data, message_id)

# ================ التشغيل الرئيسي ================
if __name__ == '__main__':
    from aiohttp import web

    async def webhook_handler(request):
        if request.method == 'POST':
            update = await request.json()
            handle_update(update)
            return web.Response(text="ok")
        else:
            return web.Response(text="Hello, bot is running!")

    async def on_startup(app):
        # Setting webhook on startup
        url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
        payload = {"url": WEBHOOK_URL}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            logger.info("Webhook set successfully.")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")

    async def on_shutdown(app):
        # Removing webhook on shutdown
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        try:
            requests.post(url)
            logger.info("Webhook removed successfully.")
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")

    app = web.Application()
    app.router.add_post('/', webhook_handler)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    port = int(os.environ.get('PORT', 8443))
    web.run_app(app, host='0.0.0.0', port=port)
    
