# -*- coding: utf-8 -*-
"""
Created on Sun Jan  7 17:37:36 2024

@author: Venkatesh Moti
"""

import pytz
from datetime import date
TIME_ZONE = pytz.timezone('Asia/Kolkata')
LIVE_FEED = {}
ORDER_POOL = {}
ORDER_TAG ='DFT'
 
 
# AngleOne settings
SMART_API_OBJ =None
SMART_API_OBJ2 = None
FEED_OBJ = None
AUTH_TOKEN = None
FEED_TOKEN = None
OPTION_DF =None
 
LIVE_FEED_JSON = {}
ORDER_TAG ='VKT'
 
# field names
EXG_SEG = 'NFO'
INSTRUMENT_TYPE = "OPTIDX"
EXPIRY = ''
NAME ='BANKNIFTY'
SYMBOL = "BANKNIFTY"
apikey = 'zG8s9Lns'
username = 'S764774'
pwd = '5615' #Srini3004$'
pin = '5615'
token = "BEVPD3QKMIWCWBSYYXZH4HOQPI"
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Makonis@localhost:5432/bankopt'

atm_strike = None
order_place_response = []

fyers_order_place_response = []