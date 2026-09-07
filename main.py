import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Веб-сервер для поддержания работы на Render ---
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "OSINT Bot is active", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

TOKEN = os.environ.get("BOT_TOKEN")

SERVICES = {
    "GitHub": "https://api.github.com/users/{}",
    "Reddit": "https://www.reddit.com/user/{}/about.json",
    "Steam": "https://steamcommunity.com/id/{}"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🕵️‍♂️ **OSINT Досье Бот**\n\n"
        "Отправь мне **никнейм** (например: `alex`) или **Telegram ID** (число),\n"
        "и я сформирую подробный отчет."
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lstrip("@")
    status_msg = await update.message.reply_text(f"⏳ Собираю досье по запросу `{query}`...", parse_mode="Markdown")

    dossier = [f"📋 **ОТЧЕТ OSINT ДОСЬЕ:** `{query}`\n" + "─"*30]

    # --- 1. ПРОВЕРКА TELEGRAM ---
    if query.isdigit():
        dossier.append("📊 **Данные Telegram ID:**")
        dossier.append(f"• ID: `{query}`")
        dossier.append(f"• Ссылка: [Открыть](tg://user?id={query})")
    else:
        try:
            tg_res = requests.get(f"https://t.me/{query}", timeout=5)
            if "tgme_page_title" in tg_res.text:
                dossier.append("📱 **Telegram Профиль:** ✅ Найден")
                if '<meta property="og:title" content="' in tg_res.text:
                    title = tg_res.text.split('<meta property="og:title" content="')[1].split('"')[0]
                    dossier.append(f"• Имя: `{title}`")
                if '<div class="tgme_page_description">' in tg_res.text:
                    bio = tg_res.text.split('<div class="tgme_page_description">')[1].split('</div>')[0]
                    dossier.append(f"• Описание (Bio): _{bio.strip()}_")
            else:
                dossier.append("📱 **Telegram Профиль:** ❌ Не найден или скрыт")
        except Exception:
            dossier.append("📱 **Telegram Профиль:** Ошибка проверки")

    dossier.append("\n🌐 **Данные из связанных сервисов:**")

    # --- 2. ДЕТАЛИЗАЦИЯ ИЗ СЕРВИСОВ ---
    found_count = 0
    
    # GitHub
    try:
        gh_res = requests.get(SERVICES["GitHub"].format(query), timeout=4).json()
        if "id" in gh_res:
            found_count += 1
            dossier.append(f"• **GitHub**: ✅ Найден")
            dossier.append(f"  ├ Имя: `{gh_res.get('name', 'Не указано')}`")
            dossier.append(f"  ├ Публичные репозитории: `{gh_res.get('public_repos', 0)}` шт.")
            dossier.append(f"  └ Город/Локация: `{gh_res.get('location', 'Не указано')}`")
    except Exception:
        pass

    # Reddit
    try:
        rd_res = requests.get(SERVICES["Reddit"].format(query), headers={"User-Agent": "Mozilla/5.0"}, timeout=4).json()
        if "data" in rd_res:
            found_count += 1
            karma = rd_res["data"].get("total_karma", 0)
            dossier.append(f"• **Reddit**: ✅ Найден (Карма: `{karma}`)")
    except Exception:
        pass

    # Steam
    try:
        st_res = requests.get(SERVICES["Steam"].format(query), timeout=4)
        if st_res.status_code == 200 and "actual_persona_name" in st_res.text:
            found_count += 1
            dossier.append(f"• **Steam**: ✅ Профиль существует")
    except Exception:
        pass

    if found_count == 0:
        dossier.append("• Публичные данные в открытых API не найдены.")

    final_text = "\n".join(dossier)
    await status_msg.edit_text(final_text, parse_mode="Markdown", disable_web_page_preview=True)

def main():
    if not TOKEN:
        print("Ошибка: BOT_TOKEN не найден!")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
