import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

# Pobieramy token z Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cześć, tu Jarvis Shadow 🚀 Jestem gotowy do akcji!")

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Dostępne komendy:\n/start - powitanie\n/help - lista komend")

# Obsługa zwykłych wiadomości
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text(f"Powiedziałeś: {user_text}")

def main():
    app = Application.builder().token(TOKEN).build()

    # Handlery
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Bot wystartował 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
