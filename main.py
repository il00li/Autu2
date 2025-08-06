import logging
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import requests
import datetime
import os
import asyncio

# ================ إعدادات البوت ================
TOKEN = "7639996535:AAH_Ppw8jeiUg4nJjjEyOXaYlip289jSAio"
PIXABAY_API_KEY = "51444506-bbfefcaf12816bd85a20222d1"
CHANNELS = ["@crazys7", "@AWU87"]
MANAGER_ID = 7251748706
WEBHOOK_URL = "https://autu2.onrender.com"

# ================ حالات المستخدم ================
class UserState(StatesGroup):
    MAIN_MENU = State()
    SEARCH_TYPE = State()
    SEARCHING_PHOTO = State()
    SEARCHING_SOUND = State()
    RESULTS_PHOTO = State()
    RESULTS_SOUND = State()

# ================ إعداد التسجيل ================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================ إنشاء كائنات البوت ================
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ================ وظائف البوت ================
async def notify_manager(user: types.User, state: FSMContext):
    try:
        data = await state.get_data()
        if not data.get('notified_manager'):
            user_info = f"👤 مستخدم جديد انضم إلى القنوات!\n\n🆔 المعرف: {user.id}\n👤 الاسم: {user.first_name}\n📅 التاريخ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            if user.username: user_info += f"\n🔖 اليوزر: @{user.username}"
            await bot.send_message(chat_id=MANAGER_ID, text=user_info)
            await state.update_data(notified_manager=True)
            logger.info(f"تم إرسال إشعار للمدير بشأن المستخدم: {user.id}")
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمدير: {e}")

async def check_subscription(user_id: int):
    try:
        for channel in CHANNELS:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {e}")
        return False

# ================ لوحات المفاتيح ================
def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="انقر للبحث 🎧", callback_data='start_search_type')],
    ])

def get_search_type_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="صور 🖼️", callback_data='search_photo')],
        [InlineKeyboardButton(text="أصوات 🎶", callback_data='search_sound')],
        [InlineKeyboardButton(text="رجوع ↩️", callback_data='back_to_menu')]
    ])

def get_navigation_keyboard(index, total_results, result_type):
    keyboard_buttons = []
    if index > 0:
        keyboard_buttons.append(InlineKeyboardButton(text="« السابق", callback_data=f'prev_{result_type}'))
    if index < total_results - 1:
        keyboard_buttons.append(InlineKeyboardButton(text="التالي »", callback_data=f'next_{result_type}'))
    
    return InlineKeyboardMarkup(inline_keyboard=[keyboard_buttons]) if keyboard_buttons else None

# ================ معالجات الأوامر الرئيسية ================
@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await check_subscription(user_id):
        await notify_manager(message.from_user, state)
        await show_main_menu(message, state)
    else:
        await show_channels(message)

async def show_main_menu(message: types.Message, state: FSMContext):
    await message.answer("🌟 قائمة البحث الرئيسية 🌟", reply_markup=get_main_menu_keyboard())
    await state.set_state(UserState.MAIN_MENU)

async def show_channels(message: types.Message):
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="قناة 1", url="https://t.me/crazys7"),
         InlineKeyboardButton(text="قناة 2", url="https://t.me/AWU87")],
        [InlineKeyboardButton(text="تحقق | Check", callback_data='check_subscription')]
    ])
    await message.answer("❗️ يجب الاشتراك في القنوات التالية أولاً:", reply_markup=buttons)

@router.callback_query(F.data == 'check_subscription')
async def check_subscription_callback(callback: CallbackQuery, state: FSMContext):
    if await check_subscription(callback.from_user.id):
        await notify_manager(callback.from_user, state)
        await callback.answer("تم التحقق بنجاح! ✅")
        await show_main_menu(callback.message, state)
    else:
        await callback.answer("لم تكتمل الاشتراكات بعد! ❌", show_alert=True)
    # ================ معالجات البحث والتنقل ================
@router.callback_query(F.data == 'start_search_type', UserState.MAIN_MENU)
async def choose_search_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔎 اختر نوع البحث:", reply_markup=get_search_type_keyboard())
    await state.set_state(UserState.SEARCH_TYPE)

@router.callback_query(F.data == 'search_photo', UserState.SEARCH_TYPE)
async def start_search_photo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🖼️ أرسل كلمة البحث للصور الآن:")
    await state.set_state(UserState.SEARCHING_PHOTO)

@router.callback_query(F.data == 'search_sound', UserState.SEARCH_TYPE)
async def start_search_sound(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎶 أرسل كلمة البحث للمؤثرات الصوتية الآن:")
    await state.set_state(UserState.SEARCHING_SOUND)

@router.message(UserState.SEARCHING_PHOTO)
async def perform_photo_search(message: types.Message, state: FSMContext):
    search_query = message.text
    await bot.send_chat_action(message.chat.id, "upload_photo")
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={search_query}&image_type=photo&per_page=40"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('hits', [])
        
        if results:
            await state.update_data(results=results, current_index=0, current_query=search_query)
            await show_photo_result(message, state)
            await state.set_state(UserState.RESULTS_PHOTO)
            return
        
        await message.answer("⚠️ لم يتم العثور على نتائج. حاول بكلمات أخرى.")
        await show_main_menu(message, state)
    except Exception as e:
        logger.error(f"خطأ في البحث عن الصور: {e}")
        await message.answer("❌ حدث خطأ في البحث. يرجى المحاولة لاحقًا.")
        await show_main_menu(message, state)

@router.message(UserState.SEARCHING_SOUND)
async def perform_sound_search(message: types.Message, state: FSMContext):
    search_query = message.text
    await bot.send_chat_action(message.chat.id, "upload_photo")
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={search_query}&video_type=all&per_page=40"

    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('hits', [])
        
        if results:
            await state.update_data(results=results, current_index=0, current_query=search_query)
            await show_sound_result(message, state)
            await state.set_state(UserState.RESULTS_SOUND)
            return
            
        await message.answer("⚠️ لم يتم العثور على نتائج. حاول بكلمات أخرى.")
        await show_main_menu(message, state)
    except Exception as e:
        logger.error(f"خطأ في البحث عن الأصوات: {e}")
        await message.answer("❌ حدث خطأ في البحث. يرجى المحاولة لاحقًا.")
        await show_main_menu(message, state)

# ================ دوال عرض النتائج ================
async def show_photo_result(message: types.Message, state: FSMContext, callback_query=None):
    data = await state.get_data()
    index = data['current_index']
    results = data['results']
    result = results[index]

    keyboard = get_navigation_keyboard(index, len(results), 'photo')
    caption = f"📸 المصور: {result['user']}\n\nصورة {index + 1} من {len(results)}"
    
    media = InputMediaPhoto(media=result['largeImageURL'], caption=caption)

    if callback_query:
        await callback_query.message.edit_media(media=media, reply_markup=keyboard)
    else:
        await message.answer_photo(photo=result['largeImageURL'], caption=caption, reply_markup=keyboard)

async def show_sound_result(message: types.Message, state: FSMContext, callback_query=None):
    data = await state.get_data()
    index = data['current_index']
    results = data['results']
    result = results[index]

    keyboard = get_navigation_keyboard(index, len(results), 'sound')
    
    sound_url = result['videos']['tiny']['url'] 
    caption = f"🎶 مؤثر صوتي من: {result['user']}\n\nصوت {index + 1} من {len(results)}"

    if callback_query:
        await callback_query.message.delete()
        await bot.send_audio(chat_id=callback_query.message.chat.id, audio=sound_url, caption=caption, reply_markup=keyboard)
    else:
        await message.answer_audio(audio=sound_url, caption=caption, reply_markup=keyboard)

@router.callback_query(F.data.in_(['prev_photo', 'next_photo']), UserState.RESULTS_PHOTO)
async def navigate_photo_results(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_index = data['current_index']
    new_index = current_index + 1 if 'next' in callback.data else current_index - 1
    await state.update_data(current_index=new_index)
    await show_photo_result(callback.message, state, callback_query=callback)

@router.callback_query(F.data.in_(['prev_sound', 'next_sound']), UserState.RESULTS_SOUND)
async def navigate_sound_results(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_index = data['current_index']
    new_index = current_index + 1 if 'next' in callback.data else current_index - 1
    await state.update_data(current_index=new_index)
    await show_sound_result(callback.message, state, callback_query=callback)

@router.callback_query(F.data == 'back_to_menu')
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await show_main_menu(callback.message, state)

# ================ إعدادات التشغيل ================
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("تم تشغيل البوت بنجاح!")

async def on_shutdown():
    await bot.delete_webhook()
    logging.info("إيقاف البوت...")

# ================ التشغيل الرئيسي ================
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8443))

    if "RENDER" in os.environ:
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        from aiohttp import web

        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )

        webhook_requests_handler.register(app, path="/")
        setup_application(app, dp, bot=bot)

        async def on_startup_web(app):
            await bot.set_webhook(WEBHOOK_URL)
            logging.info("تم تشغيل البوت بنجاح على Render!")

        app.on_startup.append(on_startup_web)

        web.run_app(app, host='0.0.0.0', port=port)
    else:
        asyncio.run(main())
    
