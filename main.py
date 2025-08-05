import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

BOT_TOKEN = '8373741818:AAGep7gyqdkR8xv-08XyLDNmUxRzbMUQhnY'
bot = telebot.TeleBot(BOT_TOKEN)

# تخزين الصور لكل مستخدم (في جلسة مؤقتة)
user_sessions = {}

# مثال للبحث (صور ثابتة لغرض التوضيح)
def fetch_images(query):
    # يمكنك استبدال هذه الروابط بنتائج حقيقية عبر API لاحقًا
    return [
        f"https://dummyimage.com/600x400/000/fff&text={query}+1",
        f"https://dummyimage.com/600x400/222/fff&text={query}+2",
        f"https://dummyimage.com/600x400/444/fff&text={query}+3",
    ]

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 أرسل كلمة لأبحث لك عن أيقونات ثلاثية الأبعاد!")

@bot.message_handler(func=lambda m: True)
def handle_query(message):
    query = message.text.strip()
    images = fetch_images(query)
    if not images:
        bot.send_message(message.chat.id, "❌ لم أجد نتائج.")
        return

    user_sessions[message.chat.id] = {
        "images": images,
        "index": 0,
        "query": query
    }

    send_image(message.chat.id)

def send_image(chat_id):
    session = user_sessions[chat_id]
    index = session["index"]
    image_url = session["images"][index]

    markup = InlineKeyboardMarkup()
    if index > 0:
        markup.add(InlineKeyboardButton("⬅️ السابق", callback_data="prev"))
    if index < len(session["images"]) - 1:
        markup.add(InlineKeyboardButton("التالي ➡️", callback_data="next"))
    markup.add(InlineKeyboardButton("🙈 إخفاء الأزرار", callback_data="hide"))

    bot.send_photo(chat_id, image_url, caption=f"📦 نتيجة {index + 1} من {len(session['images'])}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call: CallbackQuery):
    session = user_sessions.get(call.message.chat.id)
    if not session:
        bot.answer_callback_query(call.id, "❌ لا توجد جلسة نشطة.")
        return

    if call.data == "next":
        if session["index"] < len(session["images"]) - 1:
            session["index"] += 1
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_image(call.message.chat.id)
    elif call.data == "prev":
        if session["index"] > 0:
            session["index"] -= 1
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_image(call.message.chat.id)
    elif call.data == "hide":
        image_url = session["images"][session["index"]]
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, image_url, caption="📷 تم إخفاء الأزرار.")

# تشغيل البوت
bot.infinity_polling()
