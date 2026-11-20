from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from . import config
from .agent import AYUDA, Agente

agente = Agente()


async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(AYUDA)


async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text or ""
    chat_id = str(update.effective_chat.id)
    msg_id = str(update.message.message_id)
    respuesta = agente.responder(chat_id, texto, msg_id)
    await update.message.reply_text(respuesta)


def main():
    if not config.TELEGRAM_TOKEN:
        raise SystemExit(
            "Falta TELEGRAM_TOKEN. Cópialo en proyecto/.env o expórtalo en la sesión."
        )
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", inicio))
    app.add_handler(CommandHandler("ayuda", inicio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    print("Bot EFY escuchando...")
    app.run_polling()


if __name__ == "__main__":
    main()
