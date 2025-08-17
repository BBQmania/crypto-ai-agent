import os
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# Pobieramy token z Environment Variables (Render -> Environment)
TOKEN = os.getenv("TELEGRAM_TOKEN")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot działa! Witaj w Jarvis Shadow!")

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Dostępne komendy:\n/start - uruchom bota\n/help - pomoc")

def main():
    if not TOKEN:
        raise ValueError("❌ Brak TELEGRAM_TOKEN w Environment Variables!")

    # Tworzymy aplikację
    app = Application.builder().token(TOKEN).build()

    # Handlery (komendy)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Uruchomienie
    print("🚀 Jarvis Shadow Bot wystartował i czeka na komendy...")
    app.run_polling()

if __name__ == "__main__":
    main()
