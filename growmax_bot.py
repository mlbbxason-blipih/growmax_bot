
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# System prompt for OpenAI
SYSTEM_PROMPT = (
    "You are a knowledgeable, warm, polite, and friendly sales assistant for height growth supplements. "
    "Your goal is to answer customer questions about height growth products intelligently, factually, and with care. "
    "Always maintain a warm and polite tone, using phrases like 'မဂ္ဂလာပါ' (Mingalabar) or 'ဟုတ်ကဲ့' (Yes, politely) when appropriate. "
    "Provide helpful and accurate information about height growth, the product, and its benefits. "
    "If a question is outside the scope of height growth supplements, politely redirect the conversation back to the product or general well-being."
)

# Handler for /start, /hi, /hello commands and general greetings
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"မဂ္ဂလာပါ {user.mention_html()}! ဘာများကူညီပေးရမလဲ❤️",
    )

# Handler for general messages, using OpenAI for intelligent responses
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    logger.info(f"User message: {user_message}")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini", # Using gpt-4.1-mini as requested, or similar
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300,
            temperature=0.7,
        )
        bot_reply = response.choices[0].message.content
        await update.message.reply_text(bot_reply)
    except Exception as e:
        logger.error(f"Error communicating with OpenAI: {e}")
        await update.message.reply_text(
            "ဟုတ်ကဲ့၊ နားမလည်သေးပါဘူး။ အရပ်ရှည်ဆေးနဲ့ပတ်သက်ပြီး ဘာသိချင်ပါသလဲရှင့်။" # Polite error message in Burmese
        )

def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # On different commands - answer in Telegram
    application.add_handler(CommandHandler(["start", "hi", "hello"], start))

    # On non command i.e message - handle with OpenAI
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
