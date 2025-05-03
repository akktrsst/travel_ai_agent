import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters,
    ConversationHandler
)
from TravelAgents import TravelAgents
from TravelTasks import TravelTasks
import requests
from crewai import Crew, Process
import builtins
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN=os.environ.get('YOUR_TELEGRAM_BOT_TOKEN')

_builtin_open = builtins.open
def open_utf8(*args, **kwargs):
    if len(args) > 1 and args[1] == 'w' and 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
    return _builtin_open(*args, **kwargs)
builtins.open = open_utf8 # Replace with your token

STATIC_RATES = {
    'USD': 1.0,
    'EUR': 0.92,
    'GBP': 0.79,
    'INR': 83.2,
    'JPY': 157.0,
    'CNY': 7.25,
    'AUD': 1.52,
    'CAD': 1.36,
}
CURRENCIES = list(STATIC_RATES.keys())

def get_exchange_rate(currency):
    if currency == 'USD':
        return 1.0
    url = f"https://api.frankfurter.app/latest?from=USD&to={currency}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        return data['rates'][currency]
    except Exception as e:
        print("Exchange rate error:", e)
        return STATIC_RATES.get(currency, 1.0)

# Conversation states
FROM, TO, INTERESTS, DATES, BUDGET, CURRENCY, PEOPLE = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # Clear previous data to restart
    await update.message.reply_text("Welcome to the Travel Planner Bot!\nWhere are you traveling from?")
    return FROM

async def from_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['from_city'] = update.message.text
    await update.message.reply_text("Great! What's your destination city?")
    return TO

async def to_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['destination_city'] = update.message.text
    await update.message.reply_text("What are your interests? (e.g. food, culture, shopping)")
    return INTERESTS

async def interests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['interests'] = update.message.text
    await update.message.reply_text("Enter your travel dates as YYYY-MM-DD,YYYY-MM-DD (start,end):")
    return DATES

async def dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        date_from, date_to = update.message.text.split(',')
        context.user_data['date_from'] = date_from.strip()
        context.user_data['date_to'] = date_to.strip()
        await update.message.reply_text("What is your total budget?")
        return BUDGET
    except Exception:
        await update.message.reply_text("Please enter dates in the format YYYY-MM-DD,YYYY-MM-DD")
        return DATES

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['budget'] = float(update.message.text)
        reply_markup = ReplyKeyboardMarkup([CURRENCIES], one_time_keyboard=True)
        await update.message.reply_text("Which currency?", reply_markup=reply_markup)
        return CURRENCY
    except Exception:
        await update.message.reply_text("Please enter a valid number for budget.")
        return BUDGET

async def currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currency = update.message.text.upper()
    if currency not in CURRENCIES:
        await update.message.reply_text("Please select a currency from the keyboard.")
        return CURRENCY
    context.user_data['currency'] = currency
    await update.message.reply_text("How many people are traveling?")
    return PEOPLE

async def people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['num_people'] = int(update.message.text)
    except Exception:
        await update.message.reply_text("Please enter a valid number.")
        return PEOPLE

    # All info collected, generate itinerary
    data = context.user_data
    exchange_rate = get_exchange_rate(data['currency'])
    if exchange_rate is None:
        await update.message.reply_text("Could not fetch exchange rate. Please try again later.")
        return ConversationHandler.END

    agents = TravelAgents()
    tasks = TravelTasks()
    location_expert = agents.location_expert()
    guide_expert = agents.guide_expert()
    planner_expert = agents.planner_expert()
    budget_expert = agents.budget_expert()

    location_task = tasks.location_task(location_expert, data['from_city'], data['destination_city'], data['date_from'], data['date_to'])
    guide_task = tasks.guide_task(guide_expert, data['destination_city'], data['interests'], data['date_from'], data['date_to'])
    planner_task = tasks.planner_task([location_task, guide_task], planner_expert, data['destination_city'], data['interests'], data['date_from'], data['date_to'])
    budget_task = tasks.budget_task(
        budget_expert,
        data['destination_city'],
        data['budget'],
        data['num_people'],
        data['date_from'],
        data['date_to'],
        data['currency'],
        exchange_rate
    )

    crew = Crew(
        agents=[location_expert, guide_expert, planner_expert, budget_expert],
        tasks=[location_task, guide_task, planner_task, budget_task],
        process=Process.sequential,
        full_output=True,
        share_crew=False,
        verbose=True
    )

    result = crew.kickoff()

    # If result is a dict and has 'final_output', send that, else send the whole result
    if isinstance(result, dict) and 'final_output' in result:
        await update.message.reply_text(result['final_output'][:4096])
    else:
        await update.message.reply_text(str(result)[:4096])

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Travel planning cancelled.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_city)],
            TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, to_city)],
            INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, interests)],
            DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, dates)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
            CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, currency)],
            PEOPLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, people)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,  # Allow /start to restart the conversation at any time
    )
    app.add_handler(conv_handler)
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling() 