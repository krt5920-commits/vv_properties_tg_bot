
import logging
import os
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import OpenAI

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")

# OpenAI client setup
openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

# System prompt for GPT
SYSTEM_PROMPT = (
    "You are a helpful assistant for a real estate consultant in the UAE. "
    "Your main goal is to assist clients with inquiries about properties in the UAE, "
    "specifically focusing on the consultant's personal portfolio and the Arabian Hills Estate project. "
    "You should gently guide the conversation towards scheduling a meeting. "
    "Do not invent specific prices or properties; always refer to the provided Google Sheet for personal properties "
    "and the Google Drive folder for Arabian Hills materials. "
    "When a client provides contact details or a preferred meeting time, acknowledge it and prepare to forward it to the owner. "
    "Maintain a professional and friendly tone, like a real estate consultant in Dubai. "
    "Use emojis where appropriate to enhance friendliness."
)

# Texts for the bot (English and Russian)
BOT_TEXTS = {
    "en": {
        "start_greeting": "Hello! I can help you with real estate in the UAE. What would you like to know about?",
        "personal_properties_button": "🏡 My personal properties",
        "arabian_hills_button": "🌴 Arabian Hills Estate",
        "personal_properties_info": (
            "Here are all my personal property listings with full details (prices, sizes, locations):\n"
            "https://docs.google.com/spreadsheets/d/1cVUkj9sT_fsCUutg1iTl2hZ62ijLPJsrLqRiv9mQJzQ/edit?usp=drivesdk\n\n"
            "All information is in the file. If you're interested in any unit, let me know which one and we can schedule a meeting to discuss in detail. What time works best for you?"
        ),
        "arabian_hills_info": (
            "🌴 ARABIAN HILLS ESTATE\n"
            "✨ 244 Million Sq.Ft. Lagoon Community\n"
            "🏇 Next Iconic Largest Polo & Equestrian Club in the UAE\n"
            "🔥 Up to 7.5% Commission\n\n"
            "🏡 Villa Plots (B + G + 1)\n"
            "Full Payment: from AED 55+ / sq.ft\n"
            "2-Year Payment Plan: AED 110 / sq.ft\n"
            "5-Year Payment Plan: AED 150 / sq.ft\n\n"
            "🏢 Mixed-Use Commercial & Mall Plots / School, Healthcare plots (B + G + 2)\n"
            "Full Payment: AED 250 / sq.ft\n"
            "5-Year Payment Plan: AED 270 / sq.ft\n\n"
            "📂 Brochures and full project materials:\n"
            "https://drive.google.com/drive/folders/1CQ83m3fT6Q2gg354FGDV6YaNEpwNHDh\n\n"
            "💡 Important: I can offer Arabian Hills plots CHEAPER than the developer's direct price — through secondary market listings. Plots starting from 12,000 sq.ft. If you'd like to discuss specific units (smaller/larger, cheaper/more expensive), let's schedule a meeting. What time works for you?"
        ),
        "meeting_confirmation": "Great, I'll confirm with the owner and get back to you."
    },
    "ru": {
        "start_greeting": "Привет! Я могу помочь вам с недвижимостью в ОАЭ. Что бы вы хотели узнать?",
        "personal_properties_button": "🏡 Мои личные объекты",
        "arabian_hills_button": "🌴 Arabian Hills Estate",
        "personal_properties_info": (
            "Вот все мои личные объекты недвижимости с полной информацией (цены, размеры, расположение):\n"
            "https://docs.google.com/spreadsheets/d/1cVUkj9sT_fsCUutg1iTl2hZ62ijLPJsrLqRiv9mQJzQ/edit?usp=drivesdk\n\n"
            "Вся информация находится в файле. Если вас заинтересовал какой-либо объект, дайте мне знать, и мы сможем назначить встречу для детального обсуждения. Какое время вам подходит?"
        ),
        "arabian_hills_info": (
            "🌴 ARABIAN HILLS ESTATE\n"
            "✨ Сообщество с лагуной площадью 244 миллиона кв. футов\n"
            "🏇 Следующий знаковый крупнейший клуб поло и конного спорта в ОАЭ\n"
            "🔥 Комиссия до 7.5%\n\n"
            "🏡 Участки под виллы (B + G + 1)\n"
            "Полная оплата: от 55+ дирхамов / кв. фут\n"
            "План оплаты на 2 года: 110 дирхамов / кв. фут\n"
            "План оплаты на 5 лет: 150 дирхамов / кв. фут\n\n"
            "🏢 Участки под коммерцию и торговые центры / школы, здравоохранение (B + G + 2)\n"
            "Полная оплата: 250 дирхамов / кв. фут\n"
            "План оплаты на 5 лет: 270 дирхамов / кв. фут\n\n"
            "📂 Брошюры и полные материалы проекта:\n"
            "https://drive.google.com/drive/folders/1CQ83m3fT6Q2gg354FGDV6YaNEpwNHDh\n\n"
            "💡 Важно: Я могу предложить участки в Arabian Hills ДЕШЕВЛЕ, чем прямая цена застройщика — через предложения на вторичном рынке. Участки от 12 000 кв. футов. Если вы хотите обсудить конкретные объекты (меньше/больше, дешевле/дороже), давайте назначим встречу. Какое время вам подходит?"
        ),
        "meeting_confirmation": "Отлично, я свяжусь с владельцем и сообщу вам."
    }
}

def get_user_language(update: Update) -> str:
    """Determines the user's language preference."""
    if update.effective_user.language_code and update.effective_user.language_code.startswith('ru'):
        return 'ru'
    return 'en'


def restricted(func):
    """Decorator to restrict access to owner-only commands."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if str(user_id) != OWNER_CHAT_ID:
            logger.warning(f"Unauthorized access attempt by user {user_id} to {func.__name__}")
            await update.message.reply_text("You are not authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with property options."""
    lang = get_user_language(update)
    keyboard = [
        [
            InlineKeyboardButton(BOT_TEXTS[lang]["personal_properties_button"], callback_data="personal_properties"),
            InlineKeyboardButton(BOT_TEXTS[lang]["arabian_hills_button"], callback_data="arabian_hills"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(BOT_TEXTS[lang]["start_greeting"], reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    lang = get_user_language(query)

    if query.data == "personal_properties":
        await query.edit_message_text(text=BOT_TEXTS[lang]["personal_properties_info"])
        context.user_data["last_interest"] = "My properties"
    elif query.data == "arabian_hills":
        await query.edit_message_text(text=BOT_TEXTS[lang]["arabian_hills_info"])
        context.user_data["last_interest"] = "Arabian Hills"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles free-form messages using OpenAI GPT and collects meeting info."""
    user_message = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username
    lang = get_user_language(update)

    # Store conversation history for GPT
    if "conversation" not in context.user_data:
        context.user_data["conversation"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    context.user_data["conversation"].append({"role": "user", "content": user_message})

    # Check for meeting time/contact info
    meeting_keywords = ["время", "time", "встреча", "meeting", "контакт", "contact"]
    is_meeting_related = any(keyword in user_message.lower() for keyword in meeting_keywords)

    if is_meeting_related:
        # Acknowledge and send notification to owner
        await update.message.reply_text(BOT_TEXTS[lang]["meeting_confirmation"])

        owner_notification = (
            f"📩 New lead from bot:\n"
            f"User: @{username} (chat_id: {user_id})\n"
            f"Interest: {context.user_data.get("last_interest", "Not specified")}\n"
            f"Message: {user_message}\n"
            f"Requested meeting time: {user_message}" # Assuming the message itself contains the time
        )
        if OWNER_CHAT_ID:
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=owner_notification)
        else:
            logger.warning("OWNER_CHAT_ID is not set. Cannot send lead notification.")
    else:
        # Use GPT for general conversation
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or gpt-4 if available and preferred
                messages=context.user_data["conversation"],
                max_tokens=200,
                temperature=0.7,
            )
            gpt_response = response.choices[0].message.content
            context.user_data["conversation"].append({"role": "assistant", "content": gpt_response})
            await update.message.reply_text(gpt_response)
        except Exception as e:
            logger.error(f"Error communicating with OpenAI: {e}")
            await update.message.reply_text("Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз позже.")


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Please set the environment variable.")
        return
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not set. Please set the environment variable.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot with long polling
    logger.info("Bot started with long polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
