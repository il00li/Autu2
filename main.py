import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = '8373741818:AAGep7gyqdkR8xv-08XyLDNmUxRzbMUQhnY'
bot = telebot.TeleBot(BOT_TOKEN)

# بدء التشغيل
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(message.chat.id, "👋 أهلاً! أرسل لي كلمة لأبحث لك عن أيقونات 🧩")

# الرد على أي كلمة بحث
@bot.message_handler(func=lambda msg: True)
def icon_search(message):
    query = message.text.strip()
    if not query:
        bot.reply_to(message, "❗ الرجاء كتابة كلمة للبحث")
        return

    # توليد رابط بحث Google Images باستخدام الكلمة
    google_search_url = f"https://www.google.com/search?tbm=isch&q={query}+icon"

    # إنشاء زر Inline لفتح الرابط
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text="🔎 عرض الأيقونات في Google", url=google_search_url)
    markup.add(button)

    # إرسال الرسالة مع الزر
    bot.send_message(
        message.chat.id,
        f"🔍 تم إنشاء بحث لـ: *{query} icon*\nاضغط على الزر لرؤية النتائج:",
        parse_mode="Markdown",
        reply_markup=markup
    )

# تشغيل البوت
bot.infinity_polling()
