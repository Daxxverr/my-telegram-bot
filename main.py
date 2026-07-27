import asyncio
import logging
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import google.generativeai as genai

# ================= Настройки =================
BOT_TOKEN = "8852772809:AAFbidGR_G856N0ZN7mY2_BeT6X6bWe3Msc"
GEMINI_KEY = "AQ.Ab8RN6JXf9J-ZZbI54fNYfnAbivd9AN4S21gbsL2SIA6DmgrAQ"
ADMIN_ID = 7876695432
# =============================================

# Настройка Gemini AI
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояние бота
bot_state = {
    "auto_reply": True,
    "style": "Добрый и отзывчивый помощник",
    "whitelist": [ADMIN_ID],
    "connections": {}
}

STYLES = {
    "style_kind": "Добрый и дружелюбный помощник",
    "style_serious": "Строгий, деловой и серьезный ассистент",
    "style_cold": "Холодный, краткий и сдержанный собеседник",
    "style_gamer": "Веселый геймер, использует сленг и геймерский юмор"
}

# Главное меню управления
def get_admin_keyboard():
    status = "🟢 Включен" if bot_state["auto_reply"] else "🔴 Выключен"
    kb = [
        [InlineKeyboardButton(text=f"Автоответчик: {status}", callback_data="toggle_auto")],
        [InlineKeyboardButton(text="🎭 Сменить характер AI", callback_data="change_style")],
        [InlineKeyboardButton(text="🍎 Проверить Blox Fruits Stock", callback_data="check_stock")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Команда /start и /admin
@dp.message(Command("start", "admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этой панели.")
        return
    await message.answer("🛠 **Панель управления твоим ботом:**", reply_markup=get_admin_keyboard())

# Обработка нажатий кнопок
@dp.callback_query()
async def process_callbacks(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    data = callback.data

    if data == "toggle_auto":
        bot_state["auto_reply"] = not bot_state["auto_reply"]
        await callback.message.edit_reply_markup(reply_markup=get_admin_keyboard())
        await callback.answer("Статус автоответа изменен!")

    elif data == "change_style":
        kb = [
            [InlineKeyboardButton(text="😇 Добрый", callback_data="set_style_kind"),
             InlineKeyboardButton(text="💼 Серьезный", callback_data="set_style_serious")],
            [InlineKeyboardButton(text="🧊 Холодный", callback_data="set_style_cold"),
             InlineKeyboardButton(text="🎮 Геймер", callback_data="set_style_gamer")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ]
        await callback.message.edit_text("Выбери стиль общения бота:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif data.startswith("set_"):
        style_key = data.replace("set_", "")
        bot_state["style"] = STYLES.get(style_key, "Обычный")
        await callback.message.edit_text(f"✅ Стиль изменен на: **{bot_state['style']}**", reply_markup=get_admin_keyboard())

    elif data == "back_to_menu":
        await callback.message.edit_text("🛠 **Панель управления:**", reply_markup=get_admin_keyboard())

    elif data == "check_stock":
        await callback.answer("Запрашиваем сток Blox Fruits...")
        stock_text = await fetch_blox_fruits_stock()
        await callback.message.answer(stock_text)

# Получение стока Blox Fruits
async def fetch_blox_fruits_stock():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fruitybloxd.com/api/stock") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    normal_stock = [f['name'] for f in data.get('normal', [])]
                    return "🏴‍☠️ **Текущий сток Blox Fruits:**\n\n" + "\n".join([f"• {fruit}" for fruit in normal_stock])
    except Exception:
        pass
    return "🍎 **Blox Fruits Stock:**\nСток регулярно обновляется (Rocket, Spin, Flame, Ice, Light, Buddha, Portal, Dough, Kitsune и др.)."

# Сохранение подключения Telegram Business
@dp.business_connection()
async def on_business_connect(connection: types.BusinessConnection):
    if connection.is_enabled:
        bot_state["connections"][connection.user.id] = connection.id

# Автоответчик в личке через Business
@dp.business_message()
async def on_business_message(message: Message):
    if not bot_state["auto_reply"]:
        return

    if message.from_user.id == ADMIN_ID:
        return

    prompt = f"Ты — {bot_state['style']}. Ответь кратко и по делу на сообщение от моего имени: {message.text}"
    
    try:
        response = model.generate_content(prompt)
        await message.answer(
            text=response.text,
            business_connection_id=message.business_connection_id
        )
    except Exception as e:
        print(f"Ошибка Gemini: {e}")

# Мини-сервер для поддержки бесплатного тарифа Render
async def handle_ping(request):
    return web.Response(text="Bot is active!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_web_server()
    print("Бот и сервер успешно запущены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
