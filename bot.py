import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get('8349780937:AAHIZaAIBxY6Yu4mCr_5z6oDRk-Rovvdj3o')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('مرحباً! أنا بوتك 🚀')

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == '__main__':
    main()
