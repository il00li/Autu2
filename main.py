import telebot
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = 'YOUR_BOT_TOKEN'
API_KEY = 'AIzaSyDBVwFQroR5LacdaEqP9Jjltho3kTa_XSk'
CX = 'YOUR_CX_HERE'

bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}

def fetch_images(query):
    url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={CX}&searchType=image&q={query}"
    response = requests.get(url)
    data = response.json()
    return [item["link"] for item in data.get("items", [])]

@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "🔍 أرسل كلمة مفتاحية للبحث عن أيقونات")

@bot.message_handler(func=lambda msg: True)
def handle_search(msg):
    query = msg.text.strip()
    images = fetch_images(query)
    if not images:
        bot.send_message(msg.chat.id, "❌ لم أجد نتائج.")
        return

    user_sessions[msg.chat.id] = {
        "images": images,
        "index": 0,
        "query": query
    }
    send_image(msg.chat.id)

def send_image(chat_id):
    session = user_sessions[chat_id]
    index = session["index"]
    image_url = session["images"][index]

    markup = InlineKeyboardMarkup()
    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data="prev"))
    if index < len(session["images"]) - 1:
        buttons.append(InlineKeyboardButton("التالي ➡️", callback_data="next"))
    markup.row(*buttons)
    markup.add(InlineKeyboardButton("🙈 إخفاء الأزرار", callback_data="hide"))

    bot.send_photo(chat_id, image_url, caption=f"📷 نتيجة {index + 1} من {len(session['images'])}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_navigation(call):
    session = user_sessions.get(call.message.chat.id)
    if not session:
        bot.answer_callback_query(call.id, "❌ لا توجد جلسة نشطة.")
        return

    if call.data == "next":
        session["index"] += 1
    elif call.data == "prev":
        session["index"] -= 1
    elif call.data == "hide":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        image_url = session["images"][session["index"]]
        bot.send_photo(call.message.chat.id, image_url)
        return

    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_image(call.message.chat.id)

bot.infinity_polling()
