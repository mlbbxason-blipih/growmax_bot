import os
import logging
import random
import asyncio
import json
from pathlib import Path
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "8698579628:AAEKa-wLR9OKosJhOE16fSqcBKEVleSvT2k"

# OpenAI client (using Gemini 2.5 Flash via proxy)
openai_client = OpenAI(
    api_key="sk-WHkXYMN8BjE4WQoPL8RBK7",
    base_url="https://api.manus.im/api/llm-proxy/v1"
)

# Assets directory
ASSETS_DIR = Path(__file__).parent / "assets"

# Corrections file path
CORRECTIONS_FILE = Path(__file__).parent / "corrections.json"

# Track greeted users (per session)
greeted_users = set()

# --- Corrections/Learning System ---
def load_corrections():
    """Load saved corrections from file."""
    if CORRECTIONS_FILE.exists():
        try:
            with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_corrections(corrections):
    """Save corrections to file."""
    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)

# Load corrections at startup
learned_corrections = load_corrections()

# Correction detection keywords
CORRECTION_KEYWORDS_MM = [
    "မှားနေတယ်", "ဒါမဟုတ်ဘူး", "ပြင်ပေး", "အမှားရှိတယ်", "ဒါမှားတယ်",
    "မဟုတ်ဘူး", "ပြောင်းပေး", "ဒီလိုမဟုတ်ဘူး", "လဲပေး", "ပြင်ပြီးပြော",
    "ပြန်ပြင်", "ပြင်ပေးပါ", "အဲလိုမဟုတ်ဘူး", "မှားတယ်", "ပြင်ပေးစမ်း",
    "ဒါမမှန်ဘူး", "ပြောင်းရေး", "ပြင်ပေးပါဦး"
]
CORRECTION_KEYWORDS_EN = ["wrong", "fix", "correct", "change", "mistake"]


def get_corrections_prompt():
    """Generate dynamic corrections section for system prompt."""
    if not learned_corrections:
        return ""
    corrections_text = "\n\nအရေးကြီး - Customer တွေ ပြင်ပေးထားတဲ့ အမှားတွေ (ဒါတွေကို နောက်ပိုင်း ထပ်မလုပ်ပါနဲ့):\n"
    for i, c in enumerate(learned_corrections, 1):
        corrections_text += f"{i}. {c.get('description', '')}\n"
    return corrections_text


# System prompt - Intelligent height growth consultant
SYSTEM_PROMPT = """သင်သည် အရပ်ရှည်ခြင်းနဲ့ ပတ်သက်တဲ့ intelligent consultant ဖြစ်ပါတယ်။ Myanmar လူငယ်တစ်ယောက်လို casual ပြောပါ။

အရေးကြီးတဲ့ စည်းမျဉ်းများ:
- လူတစ်ယောက်လို natural ပြောပါ။ Bot လို မဖြစ်ပါစေနဲ့
- "ဟုတ်ကဲ့", "အင်း", "ဟာ", "ပေါ့" စတဲ့ casual words သုံးပါ
- emoji တခါတလေ ထည့်ပါ (😊💪👍✨) ဒါပေမယ့် အများကြီး မထည့်ပါနဲ့
- "bot လား" မေးရင် "bot မဟုတ်ပါဘူး GrowMax team ကပါ" ဆိုပြီး ဖြေပါ

အရေးကြီးဆုံး - Intelligent Responses:
- အရပ်ရှည်ခြင်းနဲ့ ပတ်သက်တဲ့ မေးခွန်းတွေကို သိပ္ပံအချက်အလက်ကျကျ ရှင်းပြပါ
- Growth plates, hormones, genetics, nutrition, exercise science စတာတွေကို detail ကျကျ ဖြေပါ
- ရှည်ရှည်ဖြေရင် ဖြေပါ - customer သိချင်တာကို သဘောကျအောင် ပြည့်ပြည့်စုံစုံ ဖြေပါ
- Scientific facts, research findings, medical knowledge တွေ ထည့်ပြီး ဖြေပါ
- Customer ရဲ့ အသက်၊ အခြေအနေ ပေါ်မူတည်ပြီး personalized advice ပေးပါ

GrowMax Product Knowledge (မေးမှပဲ ဖြေပါ - အတင်းမရောင်းပါနဲ့):
- GrowMax အရပ်ရှည်ဆေး - Advanced Height Growth supplement
- အသက် 13-25 အထိ သောက်လို့ရတယ်
- Ingredients: Zinc, Almond Powder, Moringa Powder
- 100% သဘာဝ ထုတ်ကုန်၊ ဘေးထွက်ဆိုးကျိုး (side effects) လုံးဝမရှိ
- No expiry date
- Made in Myanmar
- တစ်နေ့ 3 လုံး သောက်ရတယ် (မနက်အိပ်ရာထ၊ နေ့လည်အစားပြီး၊ ညအိပ်ခါနီး)
- ရေအေးနဲ့ သောက်ပေးပါ
- 1 ဘူး 90 pills (1 လစာ)

စျေးနှုန်း:
- 1 ဘူး - 25,000 MMK
- 3 ဘူး - 70,000 MMK
- 5 ဘူး - 110,000 MMK
- Delivery: 6,000 ဝန်းကျင်

Promotion: 3 ဘူး နဲ့ 5 ဘူး ယူတဲ့သူတွေကို Special Group တွေဝိုပါ လက်ဆောင်ပေးသွားမှာပါ (Titan Method, Bamboo Method programs)

Delivery:
- ပြည်ပ နိုင်ငံ / ပြည်တွင်း မြို့နယ်တွေကို အိမ်ရောက်ငွေချေ ပို့ပေးတယ်
- ပြည်ပ: 7-10 ရက်
- ပြည်တွင်း: 5-7 ရက်

Results:
- 18 နှစ်အောက်: 1 လ တည်းနဲ့ သိသာတယ်
- 18 နှစ်ကျော်: 2 လ လောက် ဆွဲသောက်ဖို့ recommend

Order: @Moring58 မှာ နာမည်၊ ဖုန်းနံပါတ်၊ နေရပ်လိပ်စာ ပေးပြီး မှာယူနိုင်ပါတယ်

အရပ်ရှည်ဖို့ Scientific Knowledge (ဒါတွေကို detail ကျကျ ဖြေပေးပါ):
- Growth Plates: Epiphyseal plates - အရိုးရဲ့ အဆုံးမှာရှိတဲ့ cartilage zone, ဒါ close မဖြစ်သေးရင် အရပ်ရှည်နိုင်သေးတယ်
- Growth Hormone (GH): Pituitary gland ကထုတ်တယ်, ည 10pm-2am deep sleep အချိန် အများဆုံးထွက်တယ်
- IGF-1: Insulin-like Growth Factor - liver ကထုတ်တယ်, GH နဲ့ တွဲအလုပ်လုပ်တယ်
- Nutrition: Calcium (အရိုးတည်ဆောက်), Zinc (cell division & growth), Protein (amino acids for tissue growth), Vitamin D (calcium absorption)
- Exercise: High-intensity exercises stimulate GH release, Stretching decompresses spine, Swimming reduces gravity on spine
- Sleep: 8-10 hours needed for teens, Growth hormone 70% ည deep sleep မှာ ထွက်တယ်
- Genetics: 60-80% determine height, but 20-40% is environment (nutrition, sleep, exercise)
- Posture: Poor posture can reduce apparent height by 1-2 inches
- Age factors: Girls growth plates close around 14-16, Boys around 16-18 (varies)

အရေးကြီး - Sales approach:
- GrowMax ကို အတင်းမရောင်းပါနဲ့
- Customer က product အကြောင်း မေးမှပဲ ဖြေပါ
- အရပ်ရှည်ဖို့ advice ပေးတဲ့အခါ GrowMax ကို subtle ပဲ mention လုပ်ပါ (သို့) မ mention ပဲ ထားပါ
- Customer ကိုယ်တိုင် စိတ်ဝင်စားလာမှ product details ပေးပါ
- Helpful, knowledgeable friend တစ်ယောက်လို ဖြစ်ပါ - salesperson မဖြစ်ပါနဲ့
- "ဝယ်ချင်ပါတယ်", "မှာချင်", "order" စတာတွေ ပြောရင် @Moring58 ကို direct လုပ်ပေးပါ
"""

# Keywords for triggering specific images
PRICE_KEYWORDS = ["စျေး", "ဈေး", "ဘယ်လောက်", "price", "နှုန်း", "ကျသလဲ", "ဘယ်နှစ်ကျပ်", "ဈေးနှုန်း", "စျေးနှုန်း"]
DOSAGE_KEYWORDS = ["သောက်ပုံ", "သောက်နည်း", "ဘယ်လိုသောက်", "ဆေးညွှန်း", "အညွှန်း", "ဘယ်နှစ်လုံး", "ဘယ်လိုသုံး"]
ORDER_KEYWORDS = ["ဝယ်ချင်", "မှာချင်", "order", "မှာယူ", "ဝယ်မယ်", "မှာမယ်", "အော်ဒါ"]


def is_correction_message(message):
    """Check if the message is a correction attempt."""
    for kw in CORRECTION_KEYWORDS_MM:
        if kw in message:
            return True
    lower_msg = message.lower()
    for kw in CORRECTION_KEYWORDS_EN:
        if kw in lower_msg:
            return True
    return False


async def process_correction(user_message):
    """Use AI to understand what the customer is correcting and extract the correction."""
    global learned_corrections
    try:
        extraction_prompt = f"""Customer က bot ရဲ့ အမှားကို ပြင်ပေးနေတာ ဖြစ်ပါတယ်။ Customer message: "{user_message}"

ဒီ message ထဲက ဘာကို ပြင်ခိုင်းနေတာလဲ analyze ပြီး JSON format နဲ့ ဖြေပေးပါ:
{{"description": "ဘာကို ဘယ်လိုပြင်ရမလဲ ဆိုတာ တိုတိုရှင်းရှင်း ရေးပါ (Myanmar language)"}}

ဥပမာ:
- Customer: "3လာ မဟုတ်ဘူး 3ဘူးလို့ ပြောင်းပေး" -> {{"description": "ဆေးအရေအတွက် ရေတွက်တဲ့အခါ 'လာ' မသုံးပါနဲ့၊ 'ဘူး' လို့ သုံးပါ"}}
- Customer: "ဈေးပုံ မဟုတ်ဘူး dosage ပုံ ပို့ပေး" -> {{"description": "dosage မေးရင် dosage ပုံ ပို့ပါ၊ ဈေးပုံ မပို့ပါနဲ့"}}
- Customer: "spelling မှားနေတယ် GrowMax ပါ" -> {{"description": "GrowMax ကို spelling မှန်အောင် ရေးပါ"}}

JSON only ဖြေပါ (no markdown, no explanation):"""

        response = openai_client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "user", "content": extraction_prompt}
            ],
            max_tokens=200,
            temperature=0.3,
        )
        ai_response = response.choices[0].message.content.strip()
        # Clean up response - remove markdown code blocks if present
        if ai_response.startswith("```"):
            lines = ai_response.split("\n")
            ai_response = "\n".join(lines[1:])
            if ai_response.endswith("```"):
                ai_response = ai_response[:-3]
            ai_response = ai_response.strip()
        # Remove any leading/trailing non-JSON characters
        start_idx = ai_response.find("{")
        end_idx = ai_response.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            ai_response = ai_response[start_idx:end_idx]

        correction_data = json.loads(ai_response)
        if correction_data and "description" in correction_data:
            learned_corrections.append(correction_data)
            save_corrections(learned_corrections)
            logger.info(f"Correction saved: {correction_data}")
            return True
    except Exception as e:
        logger.error(f"Error processing correction: {e}")
    return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all incoming messages."""
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    user_message = update.message.text.strip()
    lower_message = user_message.lower()
    logger.info(f"User {user_id}: {user_message}")

    # Simulate typing delay (1-3 seconds)
    delay = random.uniform(1, 3)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(delay)

    # Check if this is a greeting (first time only)
    greeting_words = ["hi", "hello", "hey", "start", "/start", "ဟိုင်း", "ဟယ်လို", "မင်္ဂလာပါ", "ဟလို"]
    is_greeting = any(g in lower_message for g in greeting_words)

    if is_greeting and user_id not in greeted_users:
        greeted_users.add(user_id)
        await update.message.reply_text("ဟလို...ဘာများကူညီပေးရမလဲ 😊")
        return
    elif is_greeting and user_id in greeted_users:
        pass

    # --- CORRECTION DETECTION (before other handlers) ---
    if is_correction_message(user_message):
        success = await process_correction(user_message)
        if success:
            ack_messages = [
                "ဟုတ်ကဲ့ ပြင်ထားပေးမယ်နော် 😊",
                "OK မှတ်ထားပေးမယ်",
                "အင်းပါ နောက်ဆို သတိထားပြီး ပြောပါ့မယ်နော် 😊",
                "ကျေးဇူးပါပဲ ပြင်ထားလိုက်ပါပြီနော် 👍",
                "ဟုတ်ကဲ့ မှတ်သားထားလိုက်ပါပြီ 😊",
            ]
            await update.message.reply_text(random.choice(ack_messages))
        else:
            await update.message.reply_text("ဟုတ်ကဲ့ သတိထားပါ့မယ်နော် 😊")
        return

    # Check for price keywords
    if any(kw in user_message for kw in PRICE_KEYWORDS):
        price_path = ASSETS_DIR / "price.jpg"
        promo_path = ASSETS_DIR / "promotion.jpg"
        if price_path.exists():
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(price_path, 'rb'),
                caption="📋 GrowMax စျေးနှုန်း\n\n1 ဘူး - 25,000 MMK\n3 ဘူး - 70,000 MMK\n5 ဘူး - 110,000 MMK\n\nDelivery - 6,000 ဝန်းကျင်"
            )
        if promo_path.exists():
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(promo_path, 'rb'),
                caption="🎁 3 ဘူး နဲ့ 5 ဘူး ယူတဲ့သူတွေကို Special Group တွေဝိုပါ လက်ဆောင်ပေးသွားမှာပါ"
            )
        return

    # Check for dosage keywords
    if any(kw in user_message for kw in DOSAGE_KEYWORDS):
        dosage_path = ASSETS_DIR / "dosage.jpg"
        if dosage_path.exists():
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(dosage_path, 'rb'),
                caption="ဆေးညွှန်းလေးကို စာရွက်လေးနဲ့ ဘူးလေးမှာ ထည့်ထားပေးပါတယ် 😊"
            )
        return

    # Check for order keywords
    if any(kw in user_message for kw in ORDER_KEYWORDS):
        await update.message.reply_text(
            "မှာယူချင်ရင် @Moring58 မှာ နာမည်၊ ဖုန်းနံပါတ်၊ နေရပ်လိပ်စာ ပေးပြီး မှာယူနိုင်ပါတယ် 💪"
        )
        return

    # Use AI for general conversation (with corrections injected into system prompt)
    try:
        full_prompt = SYSTEM_PROMPT + get_corrections_prompt()
        response = openai_client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=800,
            temperature=0.8,
        )
        bot_reply = response.choices[0].message.content.strip()
        await update.message.reply_text(bot_reply)

        # Send feedback images ONLY when customer specifically asks about results/proof
        result_keywords = ["ရလဒ်", "သက်သေ", "result", "တကယ်ရ", "proof", "feedback"]
        if any(kw in user_message for kw in result_keywords):
            await send_feedback_images(context, update.effective_chat.id)

    except Exception as e:
        logger.error(f"AI Error: {e}")
        await update.message.reply_text(
            "ခဏလေးနော်...ပြန်ဖြေပေးမယ် 😊"
        )


async def send_feedback_images(context, chat_id):
    """Send customer feedback images only when asked about results/proof."""
    feedback_files = ["feedback1.jpg", "feedback2.jpg", "feedback3.jpg"]
    selected = random.sample(feedback_files, min(2, len(feedback_files)))
    for fname in selected:
        fpath = ASSETS_DIR / fname
        if fpath.exists():
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=open(fpath, 'rb'),
                caption="Customer feedback 💪✨"
            )
            await asyncio.sleep(0.5)


def main() -> None:
    """Start the bot."""
    logger.info(f"Bot starting... Loaded {len(learned_corrections)} learned corrections.")
    application = Application.builder().token(BOT_TOKEN).build()

    # Handle all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Also handle /start command
    application.add_handler(MessageHandler(filters.COMMAND, handle_message))

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
