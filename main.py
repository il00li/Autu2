import telebot
from telebot import types
import requests
import json

# Replace with your actual bot token
BOT_TOKEN = "7639996535:AAH_Ppw8jeiUg4nJjjEyOXaYlip289jSAio"
# Replace with your actual Pixabay API Key
PIXABAY_API_KEY = "51444506-bffefcaf12816bd85a20222d1"

# Mandatory channels for subscription
MANDATORY_CHANNELS = {
    "@crazys7": "https://t.me/crazys7",
    "@AWU87": "https://t.me/AWU87"
}

bot = telebot.TeleBot(BOT_TOKEN)

# Dictionary to store user session data
# Stores the search query, current image index, image type, and search results
user_sessions = {}

# Dictionary to store the user's preferred search type
user_search_type = {}

# Inline keyboard for search types
search_type_keyboard = types.InlineKeyboardMarkup()
search_type_keyboard.row(
    types.InlineKeyboardButton("الكل (All)", callback_data="type_all"),
    types.InlineKeyboardButton("صور (Photo)", callback_data="type_photo")
)
search_type_keyboard.row(
    types.InlineKeyboardButton("رسوم (Illustration)", callback_data="type_illustration"),
    types.InlineKeyboardButton("رسوم متجهة (Vector)", callback_data="type_vector")
)

def check_subscription(user_id):
    """
    Checks if the user is a member of all mandatory channels.
    """
    for channel_username in MANDATORY_CHANNELS:
        try:
            member = bot.get_chat_member(channel_username, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            # Handle cases where the bot is not an admin in the channel
            print(f"Error checking channel {channel_username}: {e}")
            return False
    return True

def subscription_keyboard():
    """
    Creates an inline keyboard with links to mandatory channels.
    """
    keyboard = types.InlineKeyboardMarkup()
    for channel_name, channel_link in MANDATORY_CHANNELS.items():
        keyboard.add(types.InlineKeyboardButton(text=f"اشترك في {channel_name}", url=channel_link))
    keyboard.add(types.InlineKeyboardButton(text="تحقق من الاشتراك ✅", callback_data="check_sub"))
    return keyboard

def pixabay_search(query, image_type, page):
    """
    Performs a Pixabay search for images.
    
    Args:
        query (str): The search query.
        image_type (str): The type of image (all, photo, illustration, vector).
        page (int): The page number of the search results.

    Returns:
        dict: A JSON object containing the search results, or None if an error occurs.
    """
    url = "https://pixabay.com/api/"
    params = {
        'key': PIXABAY_API_KEY,
        'q': query,
        'image_type': image_type,
        'page': page,
        'per_page': 20  # You can adjust this number
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during Pixabay search: {e}")
        return None

def create_navigation_keyboard(current_index, total_results):
    """
    Creates an inline keyboard for navigating search results.
    """
    keyboard = types.InlineKeyboardMarkup()
    buttons = []
    
    # 'Previous' button
    if current_index > 0:
        buttons.append(types.InlineKeyboardButton(text="◀️ السابق", callback_data="nav_prev"))

    # 'Next' button
    if current_index < total_results - 1:
        buttons.append(types.InlineKeyboardButton(text="التالي ▶️", callback_data="nav_next"))

    keyboard.row(*buttons)
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Handles the /start command.
    """
    if not check_subscription(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "أهلاً بك! يرجى الاشتراك في القنوات التالية لاستخدام البوت:",
            reply_markup=subscription_keyboard()
        )
        return

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("بدء البحث 🎧", "نوع البحث 💐")
    bot.send_message(
        message.chat.id,
        "أهلاً بك في بوت Pixabay! يمكنك الآن استخدام الأزرار أدناه.",
        reply_markup=keyboard
    )

@bot.message_handler(func=lambda message: message.text == "نوع البحث 💐")
def handle_search_type_command(message):
    """
    Handles the 'نوع البحث 💐' button, allowing the user to select the image type.
    """
    if not check_subscription(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "عذرًا، يجب عليك الاشتراك أولاً لاستخدام البوت.",
            reply_markup=subscription_keyboard()
        )
        return

    user_id = message.from_user.id
    current_type = user_search_type.get(user_id, 'all')
    bot.send_message(
        message.chat.id,
        f"النوع الحالي: {current_type.capitalize()}\nاختر نوع البحث المفضل لديك:",
        reply_markup=search_type_keyboard
    )

@bot.message_handler(func=lambda message: message.text == "بدء البحث 🎧")
def handle_start_search_command(message):
    """
    Handles the 'بدء البحث 🎧' button, prompting the user for a search query.
    """
    if not check_subscription(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "عذرًا، يجب عليك الاشتراك أولاً لاستخدام البوت.",
            reply_markup=subscription_keyboard()
        )
        return

    user_id = message.from_user.id
    current_type = user_search_type.get(user_id, 'all')
    msg = bot.send_message(
        message.chat.id,
        f"أرسل لي كلمة مفتاحية للبحث عنها. (نوع البحث: {current_type.capitalize()})"
    )
    bot.register_next_step_handler(msg, process_search_query)

def process_search_query(message):
    """
    Processes the user's search query and starts the search process.
    """
    chat_id = message.chat.id
    query = message.text
    user_id = message.from_user.id
    image_type = user_search_type.get(user_id, 'all')

    search_results = pixabay_search(query, image_type, page=1)

    if not search_results or search_results['totalHits'] == 0:
        bot.reply_to(message, "عذرًا، لم يتم العثور على أي صور لهذه الكلمة.")
        return

    # Store session data
    user_sessions[chat_id] = {
        'query': query,
        'image_type': image_type,
        'results': search_results['hits'],
        'current_index': 0,
        'total_results': len(search_results['hits']),
        'page': 1
    }

    # Send the first image
    first_image = user_sessions[chat_id]['results'][0]
    keyboard = create_navigation_keyboard(0, user_sessions[chat_id]['total_results'])

    bot.send_photo(
        chat_id,
        first_image['largeImageURL'],
        caption=f"النتيجة 1 من {search_results['totalHits']}",
        reply_markup=keyboard
    )
    
@bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def handle_type_selection(call):
    """
    Handles inline keyboard button presses for selecting search type.
    """
    user_id = call.from_user.id
    selected_type = call.data.split('_')[1]
    
    user_search_type[user_id] = selected_type
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"تم تحديد نوع البحث: {selected_type.capitalize()}",
        reply_markup=None
    )
    bot.answer_callback_query(call.id, text=f"تم تحديد نوع البحث إلى {selected_type.capitalize()}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('nav_'))
def handle_navigation(call):
    """
    Handles inline keyboard button presses for navigating search results.
    """
    chat_id = call.message.chat.id
    
    if chat_id not in user_sessions:
        bot.send_message(chat_id, "عذرًا، انتهت صلاحية الجلسة. ابدأ بحثًا جديدًا.")
        bot.answer_callback_query(call.id, "انتهت الجلسة.")
        return
        
    session = user_sessions[chat_id]
    current_index = session['current_index']
    
    if call.data == "nav_next":
        current_index += 1
    elif call.data == "nav_prev":
        current_index -= 1
        
    if 0 <= current_index < session['total_results']:
        session['current_index'] = current_index
        new_image = session['results'][current_index]
        keyboard = create_navigation_keyboard(current_index, session['total_results'])
        
        try:
            bot.edit_message_media(
                chat_id,
                call.message.message_id,
                media=types.InputMediaPhoto(new_image['largeImageURL']),
                reply_markup=keyboard
            )
            bot.edit_message_caption(
                chat_id=chat_id,
                message_id=call.message.message_id,
                caption=f"النتيجة {current_index + 1} من {session['total_results']}",
                reply_markup=keyboard
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                bot.answer_callback_query(call.id, "هذه هي الصورة الحالية.")
            else:
                print(f"Error editing message: {e}")
                bot.answer_callback_query(call.id, "حدث خطأ.")
    else:
        bot.answer_callback_query(call.id, "لا توجد نتائج أخرى في هذه الصفحة.")

@bot.callback_query_handler(func=lambda call: call.data == 'check_sub')
def check_sub_handler(call):
    """
    Handles the 'check subscription' button.
    """
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "لم يتم الاشتراك في جميع القنوات بعد!")


# Start the bot
print("Bot is running...")
bot.polling()
