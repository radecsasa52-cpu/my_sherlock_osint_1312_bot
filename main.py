import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

# Список социальных сетей и сервисов для проверки никнейма
CHECK_PLATFORMS = {
    "GitHub": "https://github.com/{}",
    "Telegram": "https://t.me/{}",
    "Reddit": "https://www.reddit.com/user/{}",
    "Pinterest": "https://www.pinterest.com/{}",
    "Steam": "https://steamcommunity.com/id/{}",
    "Habr": "https://habr.com/ru/users/{}"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🔍 **Sherlock OSINT Bot**\n\n"
        "Отправь мне **никнейм** (без символа @) или **Telegram ID**, "
        "чтобы начать поиск по открытым источникам."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def search_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lstrip("@")

    # Если пользователь ввел число (предположительно Telegram ID)
    if query.isdigit():
        await analyze_tg_id(update, query)
        return

    msg = await update.message.reply_text(f"🔎 Сканирую открытые источники для никнейма `{query}`...", parse_mode="Markdown")

    found_links = []
    
    # Проверка доступности профилей
    for platform, url_pattern in CHECK_PLATFORMS.items():
        url = url_pattern.format(query)
        try:
            res = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                found_links.append(f"✅ [{platform}]({url}) — Профиль найден")
        except Exception:
            pass

    # Генерация прямых поисковых OSINT-ссылок
    osint_links = (
        f"\n\n🌐 **OSINT Досье и ссылки для поиска:**\n"
        f"• [Google Search](https://www.google.com/search?q=\"{query}\")\n"
        f"• [WhatsMyName Search](https://whatsmyname.app/?q={query})\n"
        f"• [Namechk Search](https://namechk.com/namechk/?q={query})\n"
        f"• [TG User search](https://t.me/{query})\n"
    )

    if found_links:
        result_text = "🎯 **Найденные аккаунты:**\n" + "\n".join(found_links) + osint_links
    else:
        result_text = "❌ Точных совпадений по базовым сервисам не найдено.\n" + osint_links

    await msg.edit_text(result_text, parse_mode="Markdown", disable_web_page_preview=True)

async def analyze_tg_id(update: Update, user_id: str):
    msg = f"🆔 **Анализ Telegram ID:** `{user_id}`\n\n"
    msg += (
        f"• [Профиль в Telegram](tg://user?id={user_id})\n"
        f"• [Проверка в Sangmata](https://t.me/Sangmata_beta_bot)\n"
        f"• [Поиск упоминаний в Google](https://www.google.com/search?q=\"{user_id}\")"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

def main():
    if not TOKEN:
        print("Ошибка: Переменная BOT_TOKEN не задана!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_nickname))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
