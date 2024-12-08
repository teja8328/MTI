OBJ_fyers = {}
SMART_API_OBJ_angelone = {}
PSEUDO_API_OBJ = {}
fyers_access_token = {}
angel_one_data = {}
fyers_clientID = {}

SYMBOL = 'NIFTY'

# Angelone details 
apikey =    'zG8s9Lns'
username =  'S764774'
pwd =       '5615'
token =     'BEVPD3QKMIWCWBSYYXZH4HOQPI'

# Fyers details
fyers_clientID = None
fyers_secretKey = None
fyers_userId = None
fyers_qrCode = None
fyers_password = None

SMART_API_OBJ =None
LIVE_FEED_JSON= {}
symbols_list = []

fyers_data = {
    'order_type' : {
        "LIMIT" : 1,
        "MARKET" : 2,
        "STOP" : 3,
        "STOPLIMIT" : 4
    },
    'Side' : {
        'BUY' : 1,
        'SELL' : -1
    },
}

index_data = {
    'NIFTY' : '25',
    'BANKNIFTY' : '15',
    'FINNIFTY' : '25',
    "SENSEX" : '10'
}

atm_strike = None
flattrade_api = {}
flattrade_sessions = {}
got_object = False

angelone_live_pnl = {}
 
flattrade_data = {
    "transaction_type" : {
        "BUY" : "B",
        "SELL" : "S"
    },
    "order_type" : {
        "LIMIT" : "LMT",
        "MARKET": "MKT"
    },
    "option_type" : {
        "CE" : "C",
        "PE" : "P"
    }
}

API_KEY = None
CLIENT_CODE = None
TOKEN = None
PASSWORD = None
AUTH_TOKEN = None
FEED_TOKEN = None

fyers_websocket_response = []
angelone_live_ltp = {}
fyers_live_ltp = {}
flattrade_live_ltp={}
all_angelone_details = {}
all_flattrade_details = {}
fyers_order=None
fyers_position=None
fyers_holdings=None
fyers_orders_book={}

all_lpt_data = {}
 
position_symbols_unsubscribe = {}
portfolio_symbols_unsubscribe = {}

active_connections = {}
pending_disconnections = {}