
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
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
    "You are a warm, polite, knowledgeable, and friendly sales assistant for height growth supplements (အရပ်ရှည်ဆေး). "
    "Always respond in proper Burmese (Myanmar language). "
    "Your goal is to answer customer questions about height growth with factual, helpful information and care. "
    "Be friendly and use the ❤️ emoji occasionally. "
    "If a question is outside the scope of height growth supplements, politely redirect the conversation back to the product or general well-being."
)

# Hardcoded greeting response
GREETING_RESPONSE = "မဂ္ဂလာပါ ဘာများကူညီပေးရမလဲ❤️"

# Handler for /start, /hi, /hello commands and general greetings
async def start_and_greet(update: Update, context) -> None:
    await update.message.reply_text(GREETING_RESPONSE)

# Handler for general messages, using OpenAI for intelligent responses
async def handle_message(update: Update, context) -> None:
    user_message = update.message.text
    logger.info(f"User message: {user_message}")

    # Check if the message is a greeting that should be handled by the hardcoded response
    # This check is redundant if the filters are set up correctly, but adds a layer of safety
    lower_message = user_message.lower()
    if lower_message in ["hi", "hello", "hey", "မင်္ဂလာပါ", "ဟိုင်း"] or user_message.startswith('/'):
        # This message should have been caught by start_and_greet or other command handlers
        # If it reaches here, it means it wasn't a command and wasn't a simple greeting that should be hardcoded.
        # For now, we'll let it pass to OpenAI, but this logic might need refinement if more complex greeting patterns are desired.
        pass

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
    # Create the Application and pass it your bot\'s token.
    application = Application.builder().token(BOT_TOKEN).build()

    # On different commands and specific greetings - answer with hardcoded response
    application.add_handler(CommandHandler(["start", "hi", "hello"], start_and_greet))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(?i)(hi|hello|hey|မင်္ဂလာပါ|ဟိုင်း)$"), start_and_greet))

    # On non command i.e message - handle with OpenAI
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
