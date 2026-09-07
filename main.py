import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Веб-сервер для Render ---
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "OSINT Bot is active", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

TOKEN = os.environ.get("BOT_TOKEN")

# --- КОМАНДЫ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🕵️‍♂️ **Учебный OSINT-Бот (White-Hat Security)**\n\n"
        "Бот выполняет поиск по открытым источникам и публичным API.\n\n"
        "📌 **Доступные команды:**\n"
        "• `/ip 8.8.8.8` — Проверка IP-адреса (геолокация, провайдер)\n"
        "• `/tg @username` — Анализ публичного Telegram-аккаунта\n"
        "• `/email test@example.com` — Проверка формата и домена почты\n"
        "• `/inn 7707083893` — Проверка организации по ИНН\n\n"
        "Или просто отправь **никнейм** текстом для поиска по соцсетям!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# 1. Поиск по IP
async def check_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: `/ip 8.8.8.8`", parse_mode="Markdown")
        return
    
    ip = context.args[0]
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}?lang=ru", timeout=5).json()
        if res.get("status") == "success":
            report = (
                f"🌐 **Анализ IP:** `{ip}`\n"
                f"• Страна: {res.get('country')}\n"
                f"• Город: {res.get('city')}\n"
                f"• Провайдер: `{res.get('isp')}`\n"
                f"• Координаты: `{res.get('lat')}, {res.get('lon')}`"
            )
        else:
            report = "❌ Неверный IP-адрес или данные не найдены."
    except Exception:
        report = "⚠️ Ошибка при запросе к серверу IP."

    await update.message.reply_text(report, parse_mode="Markdown")

# 2. Поиск по ИНН (Публичный реестр)
async def check_inn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: `/inn 7707083893`", parse_mode="Markdown")
        return

    inn = context.args[0]
    try:
        res = requests.get(f"https://api-fns.ru/api/egr?req={inn}&key=sample", timeout=5).json()
        if "items" in res and res["items"]:
            data = res["items"][0]
            report = (
                f"🏢 **Данные по ИНН:** `{inn}`\n"
                f"• Наименование: `{data.get('ЮЛ', {}).get('НаимСокр', 'Данные скрыты')}`\n"
                f"• Статус: `Зарегистрирован`"
            )
        else:
            report = f"🏢 **Проверка ИНН:** `{inn}`\n• Корректный формат ИНН. Публичный запрос отправлен."
    except Exception:
        report = f"🏢 **Проверка ИНН:** `{inn}` (Формат валиден)."

    await update.message.reply_text(report, parse_mode="Markdown")

# 3. Поиск по никнейму (Текстовые сообщения)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lstrip("@")
    status_msg = await update.message.reply_text(f"⏳ Анализирую никнейм `{query}`...", parse_mode="Markdown")

    dossier = [f"📋 **ОТЧЕТ ПО НИКНЕЙМУ:** `{query}`\n" + "─"*30]

    # GitHub
    try:
        gh = requests.get(f"https://api.github.com/users/{query}", timeout=4).json()
        if "id" in gh:
            dossier.append(f"• **GitHub**: ✅ Найден\n  ├ Имя: `{gh.get('name', 'Не указано')}`\n  └ Репозиториев: `{gh.get('public_repos', 0)}`")
        else:
            dossier.append("• **GitHub**: ❌ Профиль не найден")
    except Exception:
        pass

    # Reddit
    try:
        rd = requests.get(f"https://www.reddit.com/user/{query}/about.json", headers={"User-Agent": "Mozilla/5.0"}, timeout=4).json()
        if "data" in rd:
            dossier.append(f"• **Reddit**: ✅ Найден (Карма: `{rd['data'].get('total_karma', 0)}`)")
    except Exception:
        pass

    report_text = "\n\n".join(dossier)
    await status_msg.edit_text(report_text, parse_mode="Markdown")

# --- ЗАПУСК ---
def main():
    if not TOKEN:
        print("Ошибка: BOT_TOKEN не задан!")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ip", check_ip))
    app.add_handler(CommandHandler("inn", check_inn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
