import pandas as pd
from datetime import datetime,time 
import threading
from  time import sleep
from logzero import logger
import pyotp
import json
import urllib
import datetime as dt
import requests
from SmartApi import SmartConnect
from app.api.multileg import config
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from flask import Blueprint, jsonify, request, abort, Flask
from flask import Blueprint, jsonify, abort, request
from flask_restful import Api, Resource
import json
from datetime import datetime, time
from time import sleep
import logging
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime, time
from time import sleep
import logging
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.api.brokers import config
from urllib.parse import quote_plus
from sqlalchemy.orm import sessionmaker
from app.models.user import Portfolio , BrokerCredentials, Strategies, Portfolio_legs, ExecutedPortfolio,StrategyMultipliers,Performance, ExecutedEquityOrders
from app.models.user import User
from app.models.main import db
#from SmartApi import SmartConnect, SmartWebSocketOrderUpdate
from pyotp import TOTP
from fyers_apiv3.FyersWebsocket import order_ws, data_ws
from fyers_apiv3 import fyersModel
from app.api.brokers import config
import re
import pytz
import pandas as pd
import urllib.request
import io
import json
import numpy as np
from sqlalchemy import func
import datetime
import schedule
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.main import db
from sqlalchemy import or_, and_
import http.client
from app.api.brokers.pseudoAPI import PseudoAPI
from sqlalchemy.exc import SQLAlchemyError
from .error_handlers import ERROR_HANDLER
from .routes import MULTILEG_ROUTES
import os

sws = None

instrument_list_cache = None

cache_file_path = "instrument_list_cache.json"

# Define IST timezone
IST = pytz.timezone("Asia/Kolkata")

# Load the instrument list cache if it exists and is valid
def load_instrument_list_cache():
    if os.path.exists(cache_file_path):
        with open(cache_file_path, 'r') as file:
            data = json.load(file)
            # Check if the cache has expired
            if 'timestamp' in data:
                last_updated = dt.datetime.fromisoformat(data['timestamp']).astimezone(IST)
                current_time = dt.datetime.now(IST)
                
                # Reset the cache at 12:00 AM IST
                if current_time.hour == 23 and current_time.minute == 59:
                    logging.info("Cache reset at 12:00 AM IST.")
                    print("Cache reset at 12:00 AM IST")
                    return None

                # Check if cache is still valid (within 24 hours)
                # if current_time - last_updated < dt.timedelta(hours=24):
                #     logging.info("Cache is still valid.")
                #     return data['instrument_list']
                # else:
                #     logging.info("Cache expired, reloading data.")
            else:
                logging.info("Cache file does not contain a timestamp.")
    return None

# Save the instrument list to the cache file
def save_instrument_list_cache(instrument_list):
    data = {
        'instrument_list': instrument_list,
        'timestamp': dt.datetime.now(IST).isoformat()
    }
    with open(cache_file_path, 'w') as file:
        json.dump(data, file)

# Global variable to store the cached instrument list
instrument_list_cache = load_instrument_list_cache()



TIME_ZONE = pytz.timezone('Asia/Kolkata')
# Multileg class for all Multi leg related operations 
class Multileg:

    def angelone_placeorder(username, portfolio_name, broker_user_id):
        global instrument_list_cache
        data = request.json
        qtp_lots = data['qtp_lots']

        config.order_place_response = []
        responses = []
        stored_in_db = False
        existing_user = User.query.filter_by(username=username).first()

        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User Does not exist")
            return jsonify(response_data), 500

        user_id = existing_user.id
        portfolio = Portfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name).first()

        if not portfolio:
            response_data = ERROR_HANDLER.database_errors("portfolio", "Portfolio does not exist")
            return jsonify(response_data), 500

        if broker_user_id not in portfolio.strategy_accounts_id.split(','):
            response_data = ERROR_HANDLER.database_errors("portfolio", "Broker UserID does not exist for the portfolio !")
            return jsonify(response_data), 500

        strategy_name = portfolio.strategy
        strategy_details = Strategies.query.filter_by(strategy_tag=strategy_name).first()

        if strategy_details:
            multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id, broker_user_id=broker_user_id).first()
            multiplier = multiplier_record.multiplier if multiplier_record else 1
        else:
            multiplier = 1

        broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
        if broker_credentials:
            user_broker_multiplier = broker_credentials.user_multiplier 
            print("user_broker_multiplier:",user_broker_multiplier)
        else:
            user_broker_multiplier = 1

        max_open_trades = int(broker_credentials.max_open_trades)
        # Count the current open trades for this user and broker combination
        if max_open_trades != 0:
            # Count the current open trades for this user and broker combination
            current_open_trades = ExecutedPortfolio.query.filter_by(
                user_id=user_id,
                broker_user_id=broker_user_id,
                square_off=False
            ).count()

            # Check if placing this order would exceed max_open_trades
            if current_open_trades >= max_open_trades:
                return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]



        def angle_one_login():
            config.SMART_API_OBJ_angelone[broker_user_id] = SmartConnect(api_key=config.apikey)
            data = config.SMART_API_OBJ_angelone[broker_user_id].generateSession(config.username, config.pwd, pyotp.TOTP(config.token).now())
            config.AUTH_TOKEN = data['data']['jwtToken']
            config.FEED_TOKEN = config.SMART_API_OBJ_angelone[broker_user_id].getfeedToken()
            res = config.SMART_API_OBJ_angelone[broker_user_id].getProfile(data['data']['refreshToken'])
            logger.info(f'Login {res} {config.SMART_API_OBJ_angelone[broker_user_id].rmsLimit()}')

        def token_lookup(ticker, instrument_list, exchange="NSE"):
            ticker = ticker.upper()
            logger.debug(f"Looking up token for ticker: {ticker}, exchange: {exchange}")
            for instrument in instrument_list:
                if (instrument["symbol"].upper().startswith(ticker) or instrument["name"].upper() == ticker) and instrument["exch_seg"] == exchange:
                    logger.debug(f"Found token: {instrument['token']} for ticker: {ticker}")
                    return instrument["token"]
            logger.debug(f"Token not found for ticker: {ticker} on exchange: {exchange}")
            return None

        def fetch_ltp_data(exchange, symbol, token):
            logger.debug(f"Fetching LTP data for exchange: {exchange}, symbol: {symbol}, token: {token}")
            ltp_response = config.SMART_API_OBJ.ltpData(exchange, symbol, token)
            logger.debug(f"ltpData response: {ltp_response}")
            if ltp_response["status"]:
                if ltp_response["data"] is not None:
                    return ltp_response["data"]["ltp"]
                else:
                    logger.error(f"Data field is None in LTP response: {ltp_response}")
            else:
                logger.error(f"API response status is not True: {ltp_response}")
            return None

        def option_contracts(ticker, option_type, exchange="NFO"):
            option_contracts = []
            for instrument in instrument_list:
                if instrument["name"].upper() == ticker.upper() and instrument["instrumenttype"] in ["OPTSTK", "OPTIDX", "FUTIDX", "FUTSTK"] and instrument["symbol"].upper().endswith(option_type):
                    option_contracts.append(instrument)
            return pd.DataFrame(option_contracts)

        def option_contracts_atm(ticker, underlying_price, option_type):
            df_opt_contracts = option_contracts(ticker, option_type)
            df_opt_contracts["expiry"] = pd.to_datetime(df_opt_contracts["expiry"], format="%d%b%Y", errors='coerce').dt.date
            logger.debug("Option Contracts DataFrame:")
            logger.debug(df_opt_contracts)
            if df_opt_contracts["expiry"].isnull().any():
                logger.warning("Some expiry dates could not be parsed. Check format consistency.")

            today = datetime.date.today()
            df_opt_contracts["time_to_expiry"] = (df_opt_contracts["expiry"] - today).apply(lambda x: x.days if pd.notnull(x) else None)
            df_opt_contracts["strike"] = pd.to_numeric(df_opt_contracts["strike"], errors='coerce') / 100

            atm_strike = df_opt_contracts.loc[abs(df_opt_contracts["strike"] - underlying_price).argmin(), 'strike']
            df_opt_contracts_atm = df_opt_contracts[df_opt_contracts["strike"] == atm_strike].sort_values(by=["time_to_expiry"]).reset_index(drop=True)

            return df_opt_contracts_atm

        def place_limit_order(order_params):
            response = config.SMART_API_OBJ_angelone[broker_user_id].placeOrder(order_params)
            return response

        try:
            if config.SMART_API_OBJ_angelone[broker_user_id] is None:
                angle_one_login()

            # instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            # response = urllib.request.urlopen(instrument_url)
            # instrument_list = json.loads(response.read())

            if instrument_list_cache is None:
                print("Loading instrument list...")
                instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = urllib.request.urlopen(instrument_url)
                instrument_list_cache = json.loads(response.read())  # Cache the list for later use
                save_instrument_list_cache(instrument_list_cache)

            instrument_list = instrument_list_cache

            portfolio_legs = Portfolio_legs.query.filter_by(Portfolio_id=portfolio.id).all()
            buy_trades_first = portfolio.buy_trades_first
            positional_portfolio = portfolio.positional_portfolio

            for portfolio_leg in portfolio_legs:
                if buy_trades_first and portfolio_leg.transaction_type != "BUY":
                    responses.append({"message": f"Order is not placed as buy_trades_first is true and transaction_type is {legs.transaction_type}"})
                    continue  # Skip the current leg and move to the next one

                    
                from datetime import datetime

                # Retrieve the current datetime
                current_datetime = datetime.now().strftime('%d %b %H:%M:%S')

                if positional_portfolio:
                    # Check if legs.start_time is a valid, non-empty string before parsing
                    if portfolio_leg.start_time:
                        try:
                            start_time = datetime.strptime(portfolio_leg.start_time, '%d %b %H:%M:%S').strftime('%d %b %H:%M:%S')

                            # Check if the current datetime is greater than or equal to the start time
                            if current_datetime < start_time:
                                responses.append({"message": f"Order for {portfolio_leg.portfolio_name} is skipped as start_time {portfolio_leg.start_time} has not been reached."})
                                continue  # Skip this leg and move to the next one
                        except ValueError:
                            responses.append({"message": f"Invalid date format for start_time {portfolio_leg.start_time}."})
                            continue  # Skip this leg if parsing fails
                    else:
                        responses.append({"message": f"start_time for {portfolio_leg.portfolio_name} is missing or empty"})
                        continue  # Skip this leg if start_time is empty
                else:
                    pass

                portfolio_strategy = portfolio.strategy
                strategy = Strategies.query.filter_by(strategy_tag=portfolio_strategy).first()
                print("strategy:", strategy)

                if strategy:
                    allowed_trades = strategy.allowed_trades 
                    print("allowed_trades:", allowed_trades)
                else:
                    allowed_trades = 'Both'  

                # Map side to corresponding allowed trade type
                side = portfolio_leg.transaction_type
                if side == "BUY":
                    trade_type = "Long"
                elif side == "SELL":
                    trade_type = "Short"
                else:
                    return [{"message": "Invalid transaction type"}], 500

                # Check if the trade is allowed by the strategy
                if allowed_trades == 'Both' or allowed_trades == trade_type:
                    pass  
                else:
                    return [{"message": f"Allowed Trade details do not match for strategy: {portfolio_strategy} | {allowed_trades}"}], 500

                limit_price = portfolio_leg.limit_price
                symbol = portfolio.symbol
                transaction_type = portfolio_leg.transaction_type
                option_type = portfolio_leg.option_type
                # lots = int(portfolio_leg.lots) * int(qtp_lots) * int(multiplier) * int(user_broker_multiplier)

                max_lots = portfolio.max_lots
                if max_lots != '0':
                    max_lots = int(max_lots)

                leg_lots = int(portfolio_leg.lots)

                order_lots = 0
                
                if max_lots != '0':
                    # Step 1: Determine order lots
                    max_lots = int(max_lots)
                    leg_lots = int(portfolio_leg.lots)

                    order_lots = min(leg_lots, max_lots)
                    print("order_lots:", order_lots)

                    # Step 2: Calculate initial final_lots
                    final_lots = order_lots * int(qtp_lots) * int(user_broker_multiplier) * int(multiplier)

                    # Step 3: Ensure final_lots does not exceed max_lots
                    final_lots = min(final_lots, max_lots)

                    # Step 4: Calculate quantity
                    total_quantity = final_lots * int(config.index_data.get(portfolio.symbol, 1))
                else:
                    # If max_lots is None, calculate based on legs.lots only
                    total_quantity = int(portfolio_leg.lots) * int(qtp_lots) * int(user_broker_multiplier) * int(multiplier) * int(config.index_data.get(portfolio.symbol, 1))

                # Print quantity for debugging
                    print("total_quantity:", total_quantity)

                # if portfolio.symbol == "BANKNIFTY":
                #     total_quantity = lots * 15
                # elif portfolio.symbol == "NIFTY":
                #     total_quantity = lots * 25
                # elif portfolio.symbol == "FINNIFTY":
                #     total_quantity = lots * 25

                expiry_date_str = portfolio_leg.expiry_date
                import datetime
                expiry_date = datetime.datetime.strptime(expiry_date_str, "%d%b%Y").date()
                
                strike = portfolio_leg.strike

                if strike == 'ATM':
                    strike = 0
                elif strike.startswith('ATM+'):
                    strike = int(strike[4:])
                elif strike.startswith('ATM-'):
                    strike = -int(strike[4:])
                else:
                    strike = int(strike)

                if symbol.upper() == "NIFTY":
                    token_symbol = "NIFTY 50"
                else:
                    token_symbol = symbol

                token = token_lookup(token_symbol, instrument_list)
                if token is None:
                    return jsonify({"error": "Token not found"}), 500

                underlying_price = fetch_ltp_data("NSE", token_symbol, token)
                if underlying_price is None:
                    return jsonify({"error": "Failed to fetch underlying price"}), 500

                if option_type == 'CE':
                    opt_chain = option_contracts_atm(symbol, underlying_price + strike, option_type)
                elif option_type == 'PE':
                    opt_chain = option_contracts_atm(symbol, underlying_price - strike, option_type)

                opt_chain["instrument_type"] = opt_chain["symbol"].str[-2:]

                expiry_list = opt_chain['expiry'].tolist()

                if expiry_date not in expiry_list:
                    return jsonify({"error": f"Expiry date {expiry_date_str} is not in list"}), 500

                expiry_index = expiry_list.index(expiry_date)
                price = fetch_ltp_data("NFO", opt_chain.symbol.to_list()[expiry_index], opt_chain.token.to_list()[expiry_index])
                symboltoken = opt_chain.token.to_list()[expiry_index]
                tradingsymbol = opt_chain.symbol.to_list()[expiry_index]
                order_type = portfolio.order_type

                order_params = {
                    "variety": "NORMAL",
                    "tradingsymbol": tradingsymbol,
                    "symboltoken": symboltoken,
                    "transactiontype": transaction_type,
                    "exchange": opt_chain.exch_seg.to_list()[expiry_index],
                    "ordertype": order_type,
                    "producttype": "INTRADAY" if portfolio.product_type == "MIS" else "CARRYFORWARD",
                    "duration": "DAY",
                    "price": limit_price if order_type == "LIMIT" else 0,
                    "quantity": total_quantity,
                    "ordertag": portfolio.strategy
                }

                print("Order Params :",order_params,"\n\n\n\n\n")

                order_id = place_limit_order(order_params)
                order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}

                product_type=order_params["producttype"]
                duration=order_params["duration"]
                price=float(order_params["price"])
                status = order['data'][::-1][0]['orderstatus']

                stored_in_db = False
                response_data = {'message': order['data'][::-1][0]['text'],'orderstatus':order['data'][::-1][0]['status']}
                if order['data'][::-1][0]['status'] == 'rejected':
                    config.order_place_response.append(response_data)
                    
                elif order['data'][::-1][0]['status'] == 'complete' or order['data'][::-1][0]['status'] == 'open':
                    config.order_place_response.append({"message" : "Order placed successfully"})
                    
                    if order['data'][::-1][0]['status'] == "complete":
                        avg_price = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['averageprice']
                    else:
                        avg_price = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['price']

                    if transaction_type=="BUY":
                        executed_portfolio = ExecutedPortfolio(user_id=user_id, portfolio_name=portfolio_name,order_id=order_id,strategy_tag=strategy_tag,broker_user_id=broker_user_id,transaction_type=portfolio_leg.transaction_type,trading_symbol=tradingsymbol ,exchange=portfolio.exchange,product_type="NRML" if product_type == "CARRYFORWARD" else "MIS",netqty=portfolio_leg.quantity,symbol_token=symboltoken,variety=order_params['variety'],duration=duration,price=price,order_type=order_type,status=status,portfolio_leg_id=portfolio_leg_id,buy_price=avg_price,broker="angelone")
                    else:
                        executed_portfolio = ExecutedPortfolio(user_id=user_id, portfolio_name=portfolio_name,order_id=order_id,strategy_tag=strategy_tag,broker_user_id=broker_user_id,transaction_type=portfolio_leg.transaction_type,trading_symbol=tradingsymbol ,exchange=portfolio.exchange,product_type="NRML" if product_type == "CARRYFORWARD" else "MIS",netqty=portfolio_leg.quantity,symbol_token=symboltoken,variety=order_params['variety'],duration=duration,price=price,order_type=order_type,status=status,portfolio_leg_id=portfolio_leg_id,sell_price=avg_price,broker="angelone")
                    
                    db.session.add(executed_portfolio)
                    db.session.commit()
                    from datetime import time

                    def create_performance_record(portfolio_name, user_id, broker_user_id, max_pl, min_pl):
                        # Check if a performance record with the same portfolio_name already exists
                        existing_record = Performance.query.filter_by(portfolio_name=portfolio_name, user_id=user_id).first()
                        
                        if existing_record is None:
                            # If the record does not exist, create a new one
                            performance_record = Performance(
                                portfolio_name=portfolio_name,
                                user_id=user_id,
                                broker_user_id=broker_user_id,
                                max_pl=max_pl,
                                min_pl=min_pl,
                                max_pl_time=time(0, 0, 0),
                                min_pl_time=time(0, 0, 0)
                            )
                            db.session.add(performance_record)
                            db.session.commit()
                        else:
                            # If the record exists, you can handle it according to your needs
                            print(f"Performance record for portfolio '{portfolio_name}' already exists.")

                    # Call the function
                    create_performance_record(
                        portfolio_name=portfolio_name,
                        user_id=user_id,
                        broker_user_id=broker_user_id,
                        max_pl=float('-inf'),  
                        min_pl=float('+inf')
                    )
                    stored_in_db = True
                    
            if stored_in_db:
                response_data = ERROR_HANDLER.flask_api_errors("placeorder",config.order_place_response)
                return jsonify(response_data), 500
    
        except Exception as e:
            response_data = {'message': f'Error: {e}'}, 500
            return jsonify(response_data), 500

        return jsonify({'messages': config.order_place_response + responses}), 200

    def Store_portfolio_details(username):
        from datetime import datetime
        data = request.json
        existing_user = User.query.filter_by(username=username).first()

        if not existing_user:
            response_data = {"message": "User does not exist", "error": "user"}
            return jsonify(response_data), 404

        user_id = existing_user.id
        responses = []

        transaction_type = data.get('transaction_type')
        order_type = data.get('order_type')
        product_type = data.get('product_type')
        duration = data.get('duration')
        exchange = data.get('exchange')
        portfolio_name = data.get('portfolio_name')
        strategy_tag = data.get('strategy')
        symbol = data.get('stock_symbol')
        buy_trades_first = data.get('buy_trades_first')
        positional_portfolio = data.get('positional_portfolio')
        expiry_date = data.get('expiry_date')
        max_lots = data.get('max_lots')

        # Set quantity based on symbol
        quantity = None
        if symbol == 'NIFTY':
            quantity = str(25)
        elif symbol == 'BANKNIFTY':
            quantity = str(15)
        elif symbol == 'FINNIFTY':
            quantity = str(25)
        elif symbol == 'SENSEX':
            quantity = str(10)

        # Fetch portfolio details
        portfolio_name_test = Portfolio.query.order_by(Portfolio.id).all()
        portfolio_id = portfolio_name_test[::-1][0].id + 1 if portfolio_name_test else 0

        remarks = data.get('remarks')
        strategie_accounts = None
        strategie_accounts_id = None

        # Get strategy details
        strategie_details = Strategies.query.filter_by(user_id=user_id, strategy_tag=strategy_tag).first()
        if strategie_details:
            strategie_accounts = strategie_details.broker
            strategie_accounts_id = strategie_details.broker_user_id

        # Parse start_time and end_time (keep as time objects)
        start_time = datetime.strptime(data.get('start_time'), '%H:%M:%S').time()
        end_time = datetime.strptime(data.get('end_time'), '%H:%M:%S').time()

        # Capture square_off_time directly as a string
        square_off_time = data.get('square_off_time')  # Keep it as string

        # Create new portfolio entry
        new_portfolio = Portfolio(
            user_id=user_id,
            strategy=strategy_tag,
            strategy_accounts=strategie_accounts,
            strategy_accounts_id=strategie_accounts_id,
            order_type=order_type,
            product_type=product_type,
            duration=duration,
            buy_trades_first=buy_trades_first,
            exchange=exchange,
            portfolio_name=portfolio_name,
            remarks=remarks,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            square_off_time=square_off_time,  # Keep as string
            positional_portfolio=positional_portfolio,
            expiry_date = expiry_date,
            max_lots = max_lots
        )

        try:
            # Commit new portfolio
            db.session.add(new_portfolio)
            db.session.commit()

            # Get the latest portfolio ID
            portfolio_name_test = Portfolio.query.order_by(Portfolio.id).all()
            portfolio_id = portfolio_name_test[::-1][0].id

            # Add legs to the portfolio
            for i in data['legs']:
                transaction_type = i['transaction_type']
                option_type = i['option_type']
                lots = i['lots']
                expiry_date = i['expiry_date']
                strike = i['strike']
                quantity_legs = int(i['lots']) * int(quantity)
                target = i['target']
                trail_tgt = ','.join(str(x) for x in i['trail_tgt'])
                stop_loss = i['stop_loss']
                sl_value = i['sl_value']
                trail_sl = ','.join(str(x) for x in i['trail_sl'])
                tgt_value = i['tgt_value']
                limit_price = i['limit_price']
                start_time_leg_str = i.get('start_time')# Keep as string
                wait_sec = i['wait_sec']
                wait_action = i['wait_action']

                # Create portfolio leg
                new_portfolio_legs = Portfolio_legs(
                    Portfolio_id=portfolio_id,
                    transaction_type=transaction_type,
                    option_type=option_type,
                    lots=lots,
                    expiry_date=expiry_date,
                    strike=strike,
                    quantity=quantity_legs,
                    portfolio_name=portfolio_name,
                    target=target,
                    trail_tgt=trail_tgt,
                    stop_loss=stop_loss,
                    sl_value=sl_value,
                    trail_sl=trail_sl,
                    tgt_value=tgt_value,
                    limit_price=limit_price,
                    start_time=start_time_leg_str, # Store as string directly
                    wait_sec =wait_sec,
                    wait_action = wait_action
                )

                # Add leg to session
                db.session.add(new_portfolio_legs)

            # Commit after adding all legs
            db.session.commit()

            responses.append({
                'portfolio_name': portfolio_name,
                'strategy_tag': strategy_tag,
                'message': 'Portfolio and legs added successfully'
            })

        except Exception as e:
            # Rollback in case of error
            db.session.rollback()
            responses.append({'portfolio_name': portfolio_name, 'strategy_tag': strategy_tag, 'message': f'Error: {str(e)}'})

        print(responses)
        return jsonify(responses), 200


    def Get_portfolio_details(username):
        from datetime import datetime 
        portfolio_dict = []

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            user_id = existing_user.id
        else:
            response_data = ERROR_HANDLER.database_errors("user", 'User does not exist')
            return jsonify(response_data), 200

        if existing_user:
            existing_portfolio = Portfolio.query.filter_by(user_id=user_id).order_by(Portfolio.id).all()

            for portfolio in existing_portfolio:
                legs = Portfolio_legs.query.filter_by(Portfolio_id=portfolio.id).all()
                ourlegs = []
                for leg in legs:
                    # print("Trail TGT List :",leg.trail_tgt.split(','))
                    # print("Trail SL List :",leg.trail_sl.split(','))
                    newLeg = {
                    "id": leg.id,
                    "transaction_type": leg.transaction_type,
                    "option_type": leg.option_type,
                    "lots": leg.lots,
                    "expiry_date": leg.expiry_date,
                    "strike": leg.strike,
                    "quantity": leg.quantity,
                    "target" : leg.target,
                    "trail_tgt" : ["","","",""] if leg.trail_tgt == None else leg.trail_tgt.split(','),
                    "stop_loss" : leg.stop_loss,
                    "sl_value" : leg.sl_value,
                    "trail_sl" : ["",""] if leg.trail_sl == None else leg.trail_sl.split(','),
                    "tgt_value" : leg.tgt_value,
                    "limit_price" : leg.limit_price,
                    "start_time":leg.start_time,
                    "wait_sec": leg.wait_sec,
                    "wait_action": leg.wait_action
                    }
                    print(newLeg)
                    ourlegs.append(newLeg)
                portfolio_dict.append({
                    "portfolio_id" : portfolio.id,
                    "user_id" : portfolio.user_id,
                    "strategy" : portfolio.strategy,
                    "product_type" : portfolio.product_type,
                    "order_type" : portfolio.order_type,
                    "exchange" : portfolio.exchange,
                    "strategy_accounts" : portfolio.strategy_accounts,
                    "Strategy_accounts_id" : portfolio.strategy_accounts_id,
                    "portfolio_name": portfolio.portfolio_name,
                    "remarks": portfolio.remarks,
                    'stock_symbol' : portfolio.symbol,
                    "buy_trades_first": portfolio.buy_trades_first,
                    "enabled" : portfolio.enabled,
                    "legs" : ourlegs,
                    "start_time": portfolio.start_time.strftime('%H:%M:%S') if portfolio.start_time else None,
                    "end_time": portfolio.end_time.strftime('%H:%M:%S') if portfolio.end_time else None,
                    "square_off_time": portfolio.square_off_time,
                    "positional_portfolio":portfolio.positional_portfolio,
                    "buy_trades_first":portfolio.buy_trades_first,
                    "expiry_date":portfolio.expiry_date,
                    "max_lots": portfolio.max_lots
                })

            response_data = {'message': 'Portfolio details fetched successfully','Portfolio details':portfolio_dict}
            return jsonify(response_data), 200

        else:
            response_data = {'message': 'User does not exist'}
            return jsonify(response_data), 200


    def Fyers_websocket():
        if config.fyers_clientID and config.fyers_access_token:
            def onopen():
                data_type = "OnOrders,OnTrades,OnPositions,OnGeneral"
                fyersOrderws.subscribe(data_type=data_type)
                fyersOrderws.keep_running()
 
            def onclose(message):
                print("Connection closed:", message)
 
            def onerror(message):
                print('Error:', message)
 
            def onGeneral(message):
                print('General Response:', message)
 
            def onOrder(message):
                print('Order Response:', message)
 
            def onPosition(message):
                print('Position Response:', message)
 
            def onTrade(message):
                print('Trade Response:', message)
 
            fyersOrderws = order_ws.FyersOrderSocket(f"{config.fyers_clientID}:{config.fyers_access_token}", write_to_file=False, log_path="", on_connect=onopen, on_close=onclose, on_error=onerror, on_general=onGeneral, on_orders=onOrder, on_positions=onPosition, on_trades=onTrade, reconnect=True)
            fyersOrderws.connect()
            return fyersOrderws.is_connected()
        else:
            return False

    def fyers_place_order(username, portfolio_name,broker_user_id):     
        data =  request.json
        Qtplots=data['qtp_lots']
        # limit_price=data['limit_price']
        print("qtplots : ",Qtplots)

        try:
            config.fyers_order_place_response = []
            existing_user = User.query.filter_by(username=username).first()
            if  existing_user:
                user_id = existing_user.id
                # Strategies_details = Strategies.query.filter_by(user_id=user_id)
                portfolio_details = Portfolio.query.filter_by(user_id=user_id,portfolio_name=portfolio_name).first()
                portfolio_leg = Portfolio_legs.query.filter_by(portfolio_name=portfolio_name).first()

                print(portfolio_details.strategy_accounts_id)

                multiplier_value = StrategyMultipliers.query.filter_by(broker_user_id=broker_user_id).first()
                # broker_multiplier = multiplier_value.multiplier
                # print("broker_multiplier",broker_multiplier)
                if multiplier_value:
                    # If a multiplier value is retrieved from the database
                    broker_multiplier = multiplier_value.multiplier
                else:
                    # Default multiplier value if no multiplier is found in the database
                    broker_multiplier = 1

                broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                if broker_credentials:
                    user_broker_multiplier = broker_credentials.user_multiplier 
                    print("user_broker_multiplier:",user_broker_multiplier)
                else:
                    user_broker_multiplier = 1

                max_open_trades = int(broker_credentials.max_open_trades)
                # Count the current open trades for this user and broker combination
                if max_open_trades != 0:
                    # Count the current open trades for this user and broker combination
                    current_open_trades = ExecutedPortfolio.query.filter_by(
                        user_id=user_id,
                        broker_user_id=broker_user_id,
                        square_off=False
                    ).count()

                    # Check if placing this order would exceed max_open_trades
                    if current_open_trades >= max_open_trades:
                        return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]

                print("broker_multiplier", broker_multiplier)
                combined_lots =  (int(Qtplots) * int(broker_multiplier) * int(user_broker_multiplier))
                print("combined_lots :", combined_lots)

                try:
                    fyers = config.OBJ_fyers[broker_user_id]
                except:
                    response_data = ERROR_HANDLER.flask_api_errors("fyers_place_order")
                    response_data = {"error": response_data['message']},500
                    return jsonify(response_data), 500

                if broker_user_id in portfolio_details.strategy_accounts_id.split(','):
                    pass
                else:
                    response_data = ERROR_HANDLER.database_errors("portfolio", "Broker UserID does not exist for the portfolio !")
                    return jsonify(response_data), 500



                def get_underlying_price(symbol):
                    data = {
                        "symbols": "NSE:NIFTY50-INDEX,NSE:NIFTYBANK-INDEX,NSE:FINNIFTY-INDEX,BSE:SENSEX-INDEX"
                    }
                    response = fyers.quotes(data=data)
                    if symbol == 'NIFTY':
                        underlying_price = float(response['d'][0]['v']['lp'])
                    elif symbol == 'BANKNIFTY':
                        underlying_price = float(response['d'][1]['v']['lp'])
                    elif symbol == 'FINNIFTY':
                        underlying_price = float(response['d'][2]['v']['lp'])
                    return underlying_price

                def calculate_atm_strike(df_fyers, underlying_price, strike):
                    df_fyers["Strike price"] = pd.to_numeric(df_fyers["Strike price"])
                    atm_strike = df_fyers.loc[abs(df_fyers["Strike price"] - underlying_price).argmin(), "Strike price"]
                    if isinstance(strike, str):
                        if option_type == "CE":
                            strike = int(strike[3:])  # Assuming strike is a string with "ATM+" prefix
                            print(strike)
                            atm_strike += strike
                        else:
                            strike = int(strike[3:])  # Assuming strike is a string with "ATM-" prefix
                            print(strike)
                            atm_strike -= strike
                    return atm_strike

                def fetch_option_contracts():
                        fyers_csv_url = "https://public.fyers.in/sym_details/NSE_FO.csv"
                        with urllib.request.urlopen(fyers_csv_url) as response:
                            fyers_csv_data = response.read().decode('utf-8')
                        df_fyers = pd.read_csv(io.StringIO(fyers_csv_data))
                        df_fyers.columns = ['Fytoken', 'Symbol Details', 'Exchange Instrument type', 'Minimum lot size', 'Tick size',
                                            'Empty', 'ISIN', 'Trading Session', 'Last update date', 'Expiry date', 'Symbol ticker',
                                            'Exchange', 'Segment', 'Scrip code', 'Underlying scrip code', 'Strike price', 'Option type',
                                            'Underlying FyToken', 'EMPTY','s1','s2']
                        df_fyers.to_csv("options.csv")
                        return df_fyers
                def filter_option_contracts(df_fyers, symbol, option_type, strike):
                        underlying_price = get_underlying_price(symbol)
                        atm_strike_price = calculate_atm_strike(df_fyers, underlying_price, strike)
                        closest_option_contracts = df_fyers[df_fyers["Strike price"] == atm_strike_price]
                        closest_option_contracts = closest_option_contracts[closest_option_contracts["Scrip code"] == symbol]
                        closest_option_contracts = closest_option_contracts[closest_option_contracts["Option type"] == option_type]
        
                        return closest_option_contracts
                portfolio_legs = Portfolio_legs.query.filter_by(portfolio_name=portfolio_name).all()

                buy_trades_first = portfolio_details.buy_trades_first

                for portfolio_leg in portfolio_legs:
                    
                    if buy_trades_first and portfolio_leg.transaction_type != "BUY":
                        responses.append({"message": f"Order is not placed as buy_trades_first is true and transaction_type is {legs.transaction_type}"})
                        continue  # Skip the current leg and move to the next one

                    portfolio_strategy = portfolio_details.strategy
                    strategy = Strategies.query.filter_by(strategy_tag=portfolio_strategy).first()
                    print("strategy:", strategy)

                    if strategy:
                        allowed_trades = strategy.allowed_trades 
                        print("allowed_trades:", allowed_trades)
                    else:
                        allowed_trades = 'Both'  

                    # Map side to corresponding allowed trade type
                    side = portfolio_leg.transaction_type
                    if side == "BUY":
                        trade_type = "Long"
                    elif side == "SELL":
                        trade_type = "Short"
                    else:
                        return [{"message": "Invalid transaction type"}], 500

                    # Check if the trade is allowed by the strategy
                    if allowed_trades == 'Both' or allowed_trades == trade_type:
                        pass  
                    else:
                        return [{"message": f"Allowed Trade details do not match for strategy: {portfolio_strategy} | {allowed_trades}"}], 500

                    variety = portfolio_details.variety
                    symbol=portfolio_details.symbol
                    transaction_type = portfolio_leg.transaction_type
                    order_type = portfolio_details.order_type
                    productType = portfolio_details.product_type
                    exchange = portfolio_details.exchange
                    strategy_tag = portfolio_details.strategy
                    option_type = portfolio_leg.option_type
                    lots = (int(portfolio_leg.lots) * int(combined_lots))
                    expiry_date_str = portfolio_leg.expiry_date
                    limit_price = portfolio_leg.limit_price
                    expiry_date = datetime.datetime.strptime(expiry_date_str, "%d%b%Y")
                    today = datetime.date.today()
                    expiry_week = expiry_date.isocalendar()[1]
                    current_week = today.isocalendar()[1]  
                    weeks_difference = expiry_week - current_week
                    print("weeks_difference:", weeks_difference)
            #Another
                    # expiry_date_str = portfolio_leg.expiry_date
                    # expiry_date = datetime.strptime(expiry_date_str, "%d-%b-%y")
                    # weeks_difference = (expiry_date.date() - date.today()).days // 7
                    # print("weeks_difference:", weeks_difference)
                    if weeks_difference >= 0:
                        symbol_index = 0  # Consider it as the minimum index
                    elif weeks_difference > 20:
                        symbol_index = 20  # Consider it as the maximum index
                    else:
                        symbol_index = weeks_difference

                    strike = portfolio_leg.strike
                    if strike == 'ATM':
                        strike = 0
                    elif strike=='ATM+':  
                        strike = int(strike[3:])
                        print(type(strike))
                    elif strike=='ATM-':
                        strike = int(strike[3:])
                        print(type(strike))
    
                    option_contracts = filter_option_contracts(fetch_option_contracts(), symbol, option_type, strike)
                    print(option_contracts["Expiry date"].to_list()[symbol_index])
                    data = {
                        "symbol":option_contracts["Expiry date"].to_list()[symbol_index],
                        "qty":(option_contracts["Minimum lot size"].to_list()[0])*lots,
                        "type":1 if order_type=="LIMIT" else 2,
                        "side":1 if transaction_type == 'BUY' else -1,
                        "productType":"MARGIN" if productType=="NRML" else "INTRADAY",
                        "limitPrice":int(limit_price) if order_type=="LIMIT" else 0,
                        "stopPrice":0,
                        "validity":"DAY",
                        "disclosedQty":0,
                        "offlineOrder":False,
                        "orderTag":strategy_tag
                    }
                    print(data)
                    quantity=data['qty']
                    print("quantity : ", quantity)
                    response = fyers.place_order(data=data)
                    print("response",response)

                    
                    symbol = data['symbol']
                    productType=data['productType']
                    order_id = symbol +'-'+ productType
                    fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
                    fyers_position=config.OBJ_fyers[broker_user_id].positions()
                    fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
                    config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}

                    executed_portfolio = ExecutedPortfolio(user_id=user_id, portfolio_name=portfolio_name,order_id=order_id,strategy_tag=strategy_tag,broker_user_id=portfolio_details.strategy_accounts_id,transaction_type=portfolio_leg.transaction_type)
            #         db.session.add(executed_portfolio)
            #         db.session.commit()
            # response_data = {'message': response}
            # return jsonify(response_data), 200
                    if response['s'] == 'ok':
                        order_id = f"{data['symbol']}-{data['productType']}"
                        if transaction_type=="BUY":
                            executed_portfolio = ExecutedPortfolio(user_id=user_id, portfolio_name=portfolio_name, order_id=order_id,
                                                                strategy_tag=strategy_tag, broker_user_id=broker_user_id,
                                                                transaction_type=transaction_type,buy_price=response['tradedPrice'],product_type="MARGIN" if productType=="NRML" else "INTRADAY")
                        else:
                            executed_portfolio = ExecutedPortfolio(user_id=user_id, portfolio_name=portfolio_name, order_id=order_id,
                                                                strategy_tag=strategy_tag, broker_user_id=broker_user_id,
                                                                transaction_type=transaction_type,sell_price=response['tradedPrice'],product_type="MARGIN" if productType=="NRML" else "INTRADAY")

                        config.fyers_order_place_response.append(response)
                        db.session.add(executed_portfolio)  # Add executed portfolio to database
                        db.session.commit()

                        from datetime import time

                        def create_performance_record(portfolio_name, user_id, broker_user_id, max_pl, min_pl):
                            # Check if a performance record with the same portfolio_name already exists
                            existing_record = Performance.query.filter_by(portfolio_name=portfolio_name, user_id=user_id).first()
                            
                            if existing_record is None:
                                # If the record does not exist, create a new one
                                performance_record = Performance(
                                    portfolio_name=portfolio_name,
                                    user_id=user_id,
                                    broker_user_id=broker_user_id,
                                    max_pl=max_pl,
                                    min_pl=min_pl,
                                    max_pl_time=time(0, 0, 0),
                                    min_pl_time=time(0, 0, 0)
                                )
                                db.session.add(performance_record)
                                db.session.commit()
                            else:
                                # If the record exists, you can handle it according to your needs
                                print(f"Performance record for portfolio '{portfolio_name}' already exists.")

                        # Call the function
                        create_performance_record(
                            portfolio_name=portfolio_name,
                            user_id=user_id,
                            broker_user_id=broker_user_id,
                            max_pl=float('-inf'),  
                            min_pl=float('+inf')
                        )
                    else:
                        config.fyers_order_place_response.append(response)

                return jsonify({'messages': config.fyers_order_place_response}), 200

        except Exception as e:
                response = ERROR_HANDLER.flask_api_errors("fyers_place_order", str(e))
                return jsonify({'error': response['message']}), 500

    def edit_portfolio_details(username, portfolio_name):
        from datetime import datetime
        data = request.json

        # Check if the user exists
        user = User.query.filter_by(username=username).first()
        if not user:
            response_data = ERROR_HANDLER.database_errors("user", 'User does not exist')
            return jsonify(response_data), 404  # HTTP 404 Not Found

        # Check if the portfolio exists for the given user and portfolio_name
        portfolio = Portfolio.query.filter_by(user_id=user.id, portfolio_name=portfolio_name).first()
        portfolio_id = portfolio.id
        if not portfolio:
            response_data = ERROR_HANDLER.database_errors("portfolio", 'Portfolio does not exist for the given user and portfolio name')
            return jsonify(response_data), 404  # HTTP 404 Not Found

        # Extract updated data from the request
        updated_data = {
            'order_type': data.get('order_type', portfolio.order_type),
            'product_type': data.get('product_type', portfolio.product_type),
            'duration': data.get('duration', portfolio.duration),
            'exchange': data.get('exchange', portfolio.exchange),
            'symbol': data.get('stock_symbol', portfolio.symbol),
            'buy_trades_first': data.get('buy_trades_first', portfolio.symbol),
            'portfolio_name': data.get('portfolio_name', portfolio.portfolio_name),
            'remarks': data.get('remarks', portfolio.remarks),
            'strategy': data.get('strategy', portfolio.strategy),  # Include strategy field
            'start_time': datetime.strptime(data['start_time'], '%H:%M:%S').time() if 'start_time' in data else portfolio.start_time,
            'end_time': datetime.strptime(data['end_time'], '%H:%M:%S').time() if 'end_time' in data else portfolio.end_time,
            'square_off_time': data.get('square_off_time', portfolio.square_off_time),
            'expiry_date': data.get('expiry_date', portfolio.expiry_date),
            'max_lots': data.get('max_lots', portfolio.max_lots)
        }

        symbol = data.get('stock_symbol', portfolio.symbol)

        if symbol == 'NIFTY':
            quantity = str(25)
        elif symbol == 'BANKNIFTY':
            quantity = str(15)
        elif symbol == 'FINNIFTY':
            quantity = str(25)
        elif symbol == 'SENSEX':
            quantity = str(10)

        try:
            # Update the portfolio with the updated data
            for key, value in updated_data.items():
                setattr(portfolio, key, value)

            # Check if strategy is updated
            if 'strategy' in updated_data:
                strategy_name = updated_data['strategy']
                strategy_entry = Strategies.query.filter_by(strategy_tag=strategy_name).first()
                if strategy_entry:
                    # If the strategy is found, update portfolio with broker and broker_user_id
                    portfolio.strategy_accounts = strategy_entry.broker
                    portfolio.strategy_accounts_id = strategy_entry.broker_user_id
                
            if 'option_type' or 'transaction_type' or 'lots' or 'expiry_date' or 'strike' or 'quantity' in dict(data).keys():
                update_portfolio_legs = Portfolio_legs.query.filter_by(portfolio_name=portfolio_name).all()
                for i in update_portfolio_legs:
                    db.session.delete(i)


            if 'legs' in dict(data).keys():
                # Update existing legs and create new legs based on the data provided
                for leg_data in data['legs']:
                    # Extract leg details
                    transaction_type = leg_data.get('transaction_type')
                    option_type = leg_data.get('option_type')
                    lots = leg_data.get('lots')
                    expiry_date = leg_data.get('expiry_date')
                    strike = leg_data.get('strike')
                    quantity_legs = int(lots) * int(quantity)
                    target = leg_data.get('target')
                    trail_tgt = ','.join(str(x) for x in leg_data.get('trail_tgt'))
                    stop_loss = leg_data.get('stop_loss')
                    sl_value = leg_data.get('sl_value')
                    trail_sl = ','.join(str(x) for x in leg_data.get('trail_sl'))
                    tgt_value = leg_data.get('tgt_value')
                    limit_price = leg_data.get('limit_price')
                    start_time = leg_data.get('start_time')
                    wait_sec = leg_data.get('wait_sec')
                    wait_action = leg_data.get('wait_action')


                    # print("portfolio_name :",portfolio_name)
                    # print("transaction_type :",transaction_type)
                    # print("option_type :",option_type)
                    # print("lots :",lots)
                    # print("expiry_date :",expiry_date,'\n')


                    # Find existing leg if it exists
                    existing_leg = Portfolio_legs.query.filter_by(portfolio_name=portfolio_name,
                                                                transaction_type=transaction_type,
                                                                option_type=option_type,
                                                                lots=str(lots),
                                                                expiry_date=expiry_date,
                                                                strike=strike).first()
                
                    # if existing_leg:
                    #     # Update existing leg
                    #     existing_leg.transaction_type = transaction_type
                    #     existing_leg.option_type = option_type
                    #     existing_leg.expiry_date = expiry_date
                    #     existing_leg.lots = lots
                    #     existing_leg.strike = strike
                    #     existing_leg.quantity = quantity_legs
                    #     existing_leg.target = target
                    #     existing_leg.trail_tgt = trail_tgt
                    #     existing_leg.stop_loss = stop_loss
                    #     existing_leg.sl_value = sl_value
                    #     existing_leg.trail_sl = trail_sl
                    #     existing_leg.tgt_value = tgt_value
                    # else:
                    #     # Create new leg if it does not exist
                    new_leg = Portfolio_legs(
                        transaction_type=transaction_type,
                        option_type=option_type,
                        lots=lots,
                        expiry_date=expiry_date,
                        strike=strike,
                        portfolio_name=portfolio_name,
                        Portfolio_id=portfolio_id,
                        quantity=quantity_legs,
                        target=target,
                        trail_tgt=trail_tgt,
                        stop_loss=stop_loss,
                        sl_value=sl_value,
                        trail_sl=trail_sl,
                        tgt_value=tgt_value,
                        limit_price=limit_price,
                        start_time = start_time,
                        wait_sec = wait_sec,
                        wait_action = wait_action
                    )
                    db.session.add(new_leg)

            db.session.commit()
            response_data = [{'message': 'Portfolio updated successfully'}]
            return jsonify(response_data), 200  # HTTP 200 OK
        except Exception as e:
            # Handle database commit errors
            db.session.rollback()
            response_data = {'message': f'Error: {str(e)}'}
            return jsonify(response_data), 500  # HTTP 500 Internal Server Error
 
    def get_price_details(username):
            global instrument_list_cache
            data = request.json
            symbol = data['symbol']
            option_type = data['option_type']
            strike = data['strike']
            expiry = data['expiry']
            expiry_date = datetime.datetime.strptime(expiry, "%d%b%Y").date()

            # Default initialization
            opt_chain = None  

            def AngleOnelogin():
                SMART_API_OBJ = SmartConnect(api_key=config.apikey)
                data = SMART_API_OBJ.generateSession(config.username, config.pwd, pyotp.TOTP(config.token).now())
                config.AUTH_TOKEN = data['data']['jwtToken']
                refreshToken = data['data']['refreshToken']
                config.FEED_TOKEN = SMART_API_OBJ.getfeedToken()
                res = SMART_API_OBJ.getProfile(refreshToken)
                config.SMART_API_OBJ = SMART_API_OBJ
                logger.info(f'Login {res} {config.SMART_API_OBJ.rmsLimit()}')

            # Fetch instrument data from URL
            if instrument_list_cache is None:
                print("Loading instrument list...")
                instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = urllib.request.urlopen(instrument_url)
                instrument_list_cache = json.loads(response.read())
                print(f'Loaded instrument list with {len(instrument_list_cache)} instruments.')
                save_instrument_list_cache(instrument_list_cache)

            def token_lookup(ticker, instrument_list, exchange="NSE"):
                ticker = ticker.upper()
                logger.debug(f"Looking up token for ticker: {ticker}, exchange: {exchange}")
                for instrument in instrument_list:
                    if (instrument["symbol"].upper() == ticker or instrument["name"].upper() == ticker) and instrument["exch_seg"] == exchange:
                        logger.debug(f"Found token: {instrument['token']} for ticker: {ticker}")
                        return instrument["token"]
                logger.warning(f"Token not found for ticker: {ticker} on exchange: {exchange}")
                return None

            def fetch_ltp_data(exchange, symbol, token):
                logger.debug(f"Fetching LTP data for exchange: {exchange}, symbol: {symbol}, token: {token}")
                ltp_response = config.SMART_API_OBJ.ltpData(exchange, symbol, token)
                logger.debug(f"ltpData response: {ltp_response}")
                if ltp_response["status"]:
                    if ltp_response["data"] is not None:
                        return ltp_response["data"]["ltp"]
                    else:
                        logger.error(f"Data field is None in LTP response: {ltp_response}")
                else:
                    logger.error(f"API response status is not True: {ltp_response}")
                return None

            def option_contracts(ticker, option_type, exchange="NFO"):
                option_contracts = []
                for instrument in instrument_list_cache:
                    if instrument["name"].upper() == ticker.upper() and instrument["instrumenttype"] in ["OPTSTK", "OPTIDX", "FUTIDX", "FUTSTK"] and instrument["symbol"].upper().endswith(option_type):
                        option_contracts.append(instrument)
                return pd.DataFrame(option_contracts)

            def option_contracts_atm(ticker, underlying_price):
                # Extract option contracts for the given ticker
                df_opt_contracts = option_contracts(ticker, option_type)

                # Ensure expiry dates are parsed correctly
                df_opt_contracts["expiry"] = pd.to_datetime(df_opt_contracts["expiry"], format="%d%b%Y", errors='coerce').dt.date

                logger.debug("Option Contracts DataFrame:")
                logger.debug(df_opt_contracts)

                # Handle case where expiry dates are not parsed correctly
                if df_opt_contracts["expiry"].isnull().any():
                    logger.warning("Some expiry dates could not be parsed. Check format consistency.")

                # Calculate time to expiry as number of days
                today = datetime.date.today()
                df_opt_contracts["time_to_expiry"] = (df_opt_contracts["expiry"] - today).apply(lambda x: x.days if pd.notnull(x) else None)

                # Convert strike prices to numeric values
                df_opt_contracts["strike"] = pd.to_numeric(df_opt_contracts["strike"], errors='coerce') / 100

                # Calculate ATM strike
                atm_strike = df_opt_contracts.loc[abs(df_opt_contracts["strike"] - underlying_price).argmin(), 'strike']

                # Filter option contracts for ATM strike and sort by time to expiry
                df_opt_contracts_atm = df_opt_contracts[df_opt_contracts["strike"] == atm_strike].sort_values(by=["time_to_expiry"]).reset_index(drop=True)

                return df_opt_contracts_atm

            def format_expiry_dates(df):
                # Ensure the 'expiry' column is datetime
                df['expiry'] = pd.to_datetime(df['expiry'], format='%d%b%Y', errors='coerce')
                # Convert expiry dates to the desired format
                df['expiry'] = df['expiry'].dt.strftime('%d%b%Y').str.upper()
                return df

            today = datetime.date.today()
            expiry_week = expiry_date.isocalendar()[1]  
            current_week = today.isocalendar()[1]  
            weeks_difference = expiry_week - current_week
            logger.debug(f"weeks_difference: {weeks_difference}")

            if config.SMART_API_OBJ is None:
                AngleOnelogin()

            if option_type in ["CE", "PE"]:
                if strike == 'ATM':
                    strike = 0
                elif strike.startswith('ATM+'):
                    strike = int(strike[4:])
                elif strike.startswith('ATM-'):
                    strike = -int(strike[4:])
                else:
                    strike = int(strike)

                if symbol.upper() == "NIFTY":
                    token_symbol = "NIFTY 50"
                    token = token_lookup(token_symbol, instrument_list_cache)
                    if token is None:
                        return jsonify({"error": "Token not found"}), 500

                    underlying_price = fetch_ltp_data("NSE", token_symbol, token)
                    if underlying_price is None:
                        return jsonify({"error": "Failed to fetch underlying price"}), 500

                    if option_type == 'CE':
                        opt_chain = option_contracts_atm("NIFTY", underlying_price + strike)
                    elif option_type == 'PE':
                        opt_chain = option_contracts_atm("NIFTY", underlying_price - strike)

                elif symbol.upper() == "BANKNIFTY":
                    token_symbol = "NIFTY BANK"
                    token = token_lookup(token_symbol, instrument_list_cache)
                    if token is None:
                        return jsonify({"error": "Token not found"}), 500

                    underlying_price = fetch_ltp_data("NSE", token_symbol, token)
                    if underlying_price is None:
                        return jsonify({"error": "Failed to fetch underlying price"}), 500

                    if option_type == 'CE':
                        opt_chain = option_contracts_atm("BANKNIFTY", underlying_price + strike)
                    elif option_type == 'PE':
                        opt_chain = option_contracts_atm("BANKNIFTY", underlying_price - strike)

                elif symbol.upper() == "FINNIFTY":
                    token_symbol = "NIFTY FIN SERVICE"
                    token = token_lookup(token_symbol, instrument_list_cache)
                    if token is None:
                        return jsonify({"error": "Token not found"}), 500

                    underlying_price = fetch_ltp_data("NSE", token_symbol, token)
                    if underlying_price is None:
                        return jsonify({"error": "Failed to fetch underlying price"}), 500

                    if option_type == 'CE':
                        opt_chain = option_contracts_atm("FINNIFTY", underlying_price + strike)
                    elif option_type == 'PE':
                        opt_chain = option_contracts_atm("FINNIFTY", underlying_price - strike)

                if opt_chain is not None and not opt_chain.empty:
                    opt_chain = format_expiry_dates(opt_chain)
                    logger.debug("Expiry list: %s", opt_chain['expiry'].to_list())
                    logger.debug("Requested expiry: %s", expiry_date)

                    if expiry_date.strftime('%d%b%Y').upper() in opt_chain['expiry'].to_list():
                        expiry_index = opt_chain['expiry'].to_list().index(expiry_date.strftime('%d%b%Y').upper())
                        logger.debug(f"Expiry index: {expiry_index}")
                        price = fetch_ltp_data("NFO", opt_chain.symbol.to_list()[expiry_index], opt_chain.token.to_list()[expiry_index])
                        response_data = {
                            'Strike Price': opt_chain['strike'][0],
                            'Underlying Price': underlying_price,
                            "Price": price,
                            "Expirylist": opt_chain['expiry'].to_list()
                        }
                        return jsonify(response_data), 200
                    else:
                        return jsonify({"error": "Expiry date not found in option chain"}), 500
                else:
                    return jsonify({"error": "Unable to fetch option chain"}), 500

            elif option_type == "FUT":
                def future_contract_symbol(symbol, future_value, exch_seg, expiry):
                    global instrument_list_cache  # Access the cached variable

                    # Check if the instrument list cache is already populated
                    if instrument_list_cache is None:
                        print("Loading instrument list...")
                        instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                        try:
                            response = urllib.request.urlopen(instrument_url)
                            instrument_list_cache = json.loads(response.read())
                            print(f'Loaded instrument list with {len(instrument_list_cache)} instruments.')
                            save_instrument_list_cache(instrument_list_cache)  # Save the cache if needed
                        except Exception as e:
                            logger.error(f"Error fetching instrument list: {e}")
                            return None  # Return early if cache loading fails

                    try:
                        # Log filtering criteria for debugging
                        logger.debug(f"Filtering for symbol: {symbol}, expiry: {expiry}, exch_seg: {exch_seg}")

                        # Filter futures contracts by symbol, instrument type, expiry, and exchange segment
                        instrument_list = [
                            entry for entry in instrument_list_cache if (
                                entry['exch_seg'].upper() == exch_seg.upper() and
                                entry['instrumenttype'].upper() == future_value.upper() and
                                entry['name'].upper() == symbol.upper() and
                                entry['expiry'].upper() == expiry.upper())]

                        logger.debug(f"Found future contracts: {instrument_list}")
                        return instrument_list
                    except Exception as e:
                        logger.error(f"Error processing data: {e}")
                        return None

                response_data = future_contract_symbol(symbol, "FUTIDX", "NFO", expiry)
                logger.debug(f"Future contract data: {response_data}")

                if response_data and len(response_data) > 0:
                    symboltoken = response_data[0]['token']
                    tradingsymbol = response_data[0]['symbol']

                    price = fetch_ltp_data("NFO", tradingsymbol, symboltoken)
                    logger.debug(f"Fetched price for future contract: {price}")
                    response_data = {"Expiry": expiry, "Price": price, "symbol": tradingsymbol, "symbol_token": symboltoken}
                    return jsonify(response_data), 200

                else:
                    return jsonify({"error": "Unable to fetch future contract details"}), 500

            return jsonify({"error": "Invalid option type"}), 400

    def Delete_portfolio_details(username,portfolio_name):

        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            user_id = existing_user.id
        else:
            response_data = {'message': 'User does not exist'}
            return jsonify(response_data), 500   

        existing_portfolio = Portfolio.query.filter_by(user_id=user_id,portfolio_name=portfolio_name).first()
        existing_portfolio_legs = Portfolio_legs.query.filter_by(portfolio_name=portfolio_name).all()

        for leg in existing_portfolio_legs:
            db.session.delete(leg)

        db.session.commit()

        if existing_portfolio:
            db.session.delete(existing_portfolio)
            db.session.commit()
            response_data = {'message': 'Portfolio Deleted successfully'}
            return jsonify(response_data), 201  
        else:
            response_data = {'message': 'Portfolio Does not exist'}
            return jsonify(response_data), 500   

    def Delete_portfolio_legs(username,portfolio_legsid):
            # need to add username to the portfolio legs
    
            portfolio_legs_id = int(portfolio_legsid)
    
            delete_portfolio = Portfolio_legs.query.filter_by(id=portfolio_legs_id).first()
            print(delete_portfolio)
            db.session.delete(delete_portfolio)
            db.session.commit()
    
            response_data = {'message': 'Portfolio Deleted successfully'}
            return jsonify(response_data), 200

    def Get_expiry_list(username, symbols):
        import logging
        global instrument_list_cache  # Declare the global variable at the start of the function
        response_data = {}

        def AngleOnelogin():
            try:
                SMART_API_OBJ = SmartConnect(api_key=config.apikey)
                data = SMART_API_OBJ.generateSession(config.username, config.pwd, pyotp.TOTP(config.token).now())
                config.AUTH_TOKEN = data['data']['jwtToken']
                refreshToken = data['data']['refreshToken']
                config.FEED_TOKEN = SMART_API_OBJ.getfeedToken()
                res = SMART_API_OBJ.getProfile(refreshToken)
                config.SMART_API_OBJ = SMART_API_OBJ
                rms_limit = config.SMART_API_OBJ.rmsLimit()
                logging.info(f'Login successful: {res}, RMS Limit: {rms_limit}')
            except Exception as e:
                logging.error(f"Login failed: {e}")
                raise

        # Load instrument list only if it is not already cached or cache has expired
        if instrument_list_cache is None:
            print("Loading instrument list...")
            instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = urllib.request.urlopen(instrument_url)
            instrument_list_cache = json.loads(response.read())
            print(f'Loaded instrument list with {len(instrument_list_cache)} instruments.')
            save_instrument_list_cache(instrument_list_cache)

        if config.SMART_API_OBJ is None:
            AngleOnelogin()

        def token_lookup(ticker, instrument_list, exchange="NSE"):
            for instrument in instrument_list:
                if (instrument["name"].strip().upper() == ticker.upper() or instrument["symbol"].strip().upper() == ticker.upper()) and instrument["exch_seg"] == exchange:
                    return instrument["token"]
            logging.error(f"No token found for ticker: {ticker}")
            return None

        def option_contracts(ticker, option_type="CE", exchange="NFO"):
            option_contracts = []
            for instrument in instrument_list_cache:
                if (instrument["name"].strip().upper() == ticker.upper() or instrument["symbol"].strip().upper() == ticker.upper()) and instrument["instrumenttype"] in ["OPTSTK", "OPTIDX", "FUTIDX", "FUTSTK"] and instrument["symbol"][-2:].upper() == option_type.upper():
                    option_contracts.append(instrument)
            logging.debug(f"Option contracts for {ticker}: {option_contracts}")
            return pd.DataFrame(option_contracts)

        def option_contracts_atm(ticker, underlying_price):
            df_opt_contracts = option_contracts(ticker)
            if df_opt_contracts.empty:
                logging.warning(f"No option contracts found for ticker: {ticker}")
                return pd.DataFrame()
            
            # Handle empty expiry field
            df_opt_contracts["expiry"] = df_opt_contracts["expiry"].replace("", pd.NaT)
            
            try:
                df_opt_contracts["expiry"] = pd.to_datetime(df_opt_contracts["expiry"], format='%d%b%Y', errors='coerce')
            except Exception as e:
                logging.error(f"Date parsing error for ticker {ticker}: {e}")
                return pd.DataFrame()
            
            if df_opt_contracts["expiry"].isna().all():
                logging.warning(f"All expiry dates are missing or invalid for ticker: {ticker}")
                return pd.DataFrame()
            
            df_opt_contracts["time_to_expiry"] = (df_opt_contracts["expiry"] + dt.timedelta(0, 16 * 3600) - dt.datetime.now()).dt.total_seconds() / dt.timedelta(days=1).total_seconds()
            df_opt_contracts["strike"] = pd.to_numeric(df_opt_contracts["strike"]) / 100
            
            if df_opt_contracts.empty:
                logging.warning(f"No valid option contracts found for ticker: {ticker}")
                return pd.DataFrame()
            
            atm_strike = df_opt_contracts.loc[abs(df_opt_contracts["strike"] - underlying_price).argmin(), 'strike']
            result = df_opt_contracts[df_opt_contracts["strike"] == atm_strike].sort_values(by=["time_to_expiry"]).reset_index(drop=True)
            logging.debug(f"ATM option contracts for {ticker}: {result}")
            return result

        for symbol in symbols:
            try:
                # Use "NIFTY 50" to fetch token, and "NIFTY" to fetch contracts
                if symbol.upper() == "NIFTY":
                    token_symbol = "NIFTY 50"  
                    contract_symbol = "NIFTY"  
                else:
                    token_symbol = symbol
                    contract_symbol = symbol
                
                logging.info(f"Processing symbol: {symbol}")
                
                # Fetch token using "NIFTY 50" or the given symbol
                token = token_lookup(token_symbol, instrument_list_cache)
                if token is None:
                    logging.error(f"Token not found for symbol: {token_symbol}")
                    response_data[symbol] = []  # Handle missing token case
                    continue

                ltp_response = config.SMART_API_OBJ.ltpData("NSE", token_symbol, token)
                if ltp_response is None:
                    logging.error(f"Failed to get LTP data for symbol: {token_symbol}, response was None.")
                    response_data[symbol] = []  # Handle missing LTP data case
                    continue

                if "data" not in ltp_response or "ltp" not in ltp_response["data"]:
                    logging.error(f"LTP response format is incorrect for symbol: {token_symbol}. Response: {ltp_response}")
                    response_data[symbol] = []  # Handle incorrect response format
                    continue

                underlying_price = ltp_response["data"]["ltp"]
                logging.info(f"Underlying price for {token_symbol}: {underlying_price}")
                
                # Fetch option contracts using "NIFTY" or the given symbol
                opt_chain = option_contracts_atm(contract_symbol, underlying_price)
                if opt_chain.empty:
                    logging.warning(f"No ATM option contracts found for symbol: {contract_symbol}")
                
                expiry_list = opt_chain['expiry'].dt.strftime('%d%b%Y').to_list()
                response_data[symbol] = expiry_list

            except Exception as e:
                logging.error(f"Error processing symbol {symbol}: {e}")
                response_data[symbol] = []  # Handle processing errors

        return jsonify(response_data), 200


    def Logout_broker_accounts(broker_name,broker_username):
        if broker_name == "angelone" :
            config.angel_one_data.pop(broker_username)
            response_data = {"Message": f"{broker_username} logged out successfully"}
            return jsonify(response_data), 200
        elif broker_name == "fyers":
            config.OBJ_fyers.pop(broker_username)
            response_data = {"Message": f"{broker_username} logged out successfully"}
            return jsonify(response_data), 200
        elif broker_name == "flattrade":
            config.flattrade_api.pop(broker_username)
            config.flattrade_sessions.pop(broker_username)
            response_data = {"Message": f"{broker_username} logged out successfully"}
            return jsonify(response_data), 200

    def fyers_square_off_strategy(username, strategy_tag, broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
            response_data = {'message': "User does not exist"}
            return jsonify(response_data), 500
        
        user_id = existing_user.id
        executed_Portfolio_details = ExecutedPortfolio.query.filter_by(user_id=user_id, strategy_tag=strategy_tag, square_off=False).all()
        
        if not executed_Portfolio_details:
            response_data = {'message': f'Looks like {strategy_tag} strategy has no open positions.'}
            return jsonify(response_data), 200
        
        try:
            fyers = config.OBJ_fyers[broker_user_id]
            print(fyers)
        except KeyError:
            response_data = ERROR_HANDLER.broker_api_errors("fyers", f"Please login to the broker account, {broker_user_id}")
            return jsonify(response_data), 500

        fyers_list = []  # Initialize fyers_list here
        
        for executedPortfolio in executed_Portfolio_details:
            strategy_tag = executedPortfolio.strategy_tag
            transaction_type = config.fyers_data['Side'].get(executedPortfolio.transaction_type)
            id = executedPortfolio.order_id

            data = {
                "orderTag": strategy_tag,
                "segment": [10],
                'id': id,
                "side": [transaction_type]
            }

            square_off = fyers.exit_positions(data)
            print(square_off)
            
            if square_off and square_off.get('s') == 'ok':
                fyers_list.append(square_off)

                executedPortfolio.square_off = True
                traded_price = square_off.get('tradedPrice', None)
                
                if executedPortfolio.transaction_type == "BUY":
                    executedPortfolio.sell_price = traded_price
                else:
                    executedPortfolio.buy_price = traded_price

                db.session.commit()

                fyers_position = fyers.positions()
                fyers_order = fyers.orderbook()
                fyers_holdings = fyers.holdings()
                
                config.fyers_orders_book[broker_user_id] = {
                    "orderbook": fyers_order,
                    "positions": fyers_position,
                    "holdings": fyers_holdings
                }
                
                response_data = {'message': f'Strategy Manual square off successfully for strategy {strategy_tag}', 'Square_off': square_off}
                return jsonify(response_data), 200
            else:
                response_data = {'message': f'No open positions for {broker_user_id} under Strategy {strategy_tag}', 'error': square_off}
                return jsonify(response_data), 200

        # If no positions were squared off (edge case)
        response_data = ERROR_HANDLER.database_errors("strategies", f'No positions were squared off for strategy {strategy_tag}')
        return jsonify(response_data), 200

    def Get_executed_portfolios(username):
                try:
                    user = User.query.filter_by(username=username).first()
                    if not user:
                        response_data = ERROR_HANDLER.database_errors("user", 'User not found')
                        return jsonify({'error': response_data['message']}), 404
        
                    portfolio_list = ExecutedPortfolio.query.filter_by(user_id=user.id).filter(
                                and_(
                                    or_(ExecutedPortfolio.portfolio_Status == True, ExecutedPortfolio.portfolio_Status == None),
                                    ExecutedPortfolio.status == "COMPLETE"
                                )
                            ).all()
        
                    executed_portfolios = []
                    for portfolio in portfolio_list:
                        portfolio_data = {
                            'portfolio_name': portfolio.portfolio_name,
                            'leg_id': portfolio.portfolio_leg_id,    
                            'broker_user_id': portfolio.broker_user_id,
                            'strategy_tag': portfolio.strategy_tag,
                            'duration': portfolio.duration,
                            'exchange': portfolio.exchange,
                            'id': portfolio.id,
                            'order_id': portfolio.order_id,
                            'netqty': portfolio.netqty,
                            'buy_qty': portfolio.buy_qty,
                            'sell_qty': portfolio.sell_qty,
                            'order_type': portfolio.order_type,
                            'portfolio_Status': portfolio.portfolio_Status,
                            'price': portfolio.price,
                            'product_type': portfolio.product_type,
                            'square_off': portfolio.square_off,
                            'status': portfolio.status,                  
                            'symbol_token': portfolio.symbol_token,
                            'trading_symbol': portfolio.trading_symbol,
                            'transaction_type': portfolio.transaction_type,
                            'user_id': portfolio.user_id,
                            'variety': portfolio.variety,
                            "reached_profit": portfolio.reached_profit,
                            "locked_min_profit": portfolio.locked_min_profit,
                            "buy_price": portfolio.buy_price,
                            "sell_price": portfolio.sell_price,
                            "master_account_id":portfolio.master_account_id,
                            "broker": portfolio.broker,
                            "trailed_sl": portfolio.trailed_sl,
                            "wait_sec": portfolio.wait_sec,
                            "wait_action": portfolio.wait_action

                            # 'target': portfolio.target,
                            # 'stoploss' : portfolio.stoploss
                        }
                        executed_portfolios.append(portfolio_data)

                    equity_orders = ExecutedEquityOrders.query.filter_by(user_id=user.id).all()

                    for equity in equity_orders:
                        portfolio_data = {    
                            'broker_user_id': equity.broker_user_id,
                            'strategy_tag': equity.strategy_tag,
                            'trade_time': equity.placed_time,
                            'id': equity.id,
                            'netqty': equity.quantity,
                            'order_id': equity.order_id,    
                            'sell_order_id': equity.sell_order_id,
                            #'price': equity.price,
                            'product_type': equity.product_type,
                            'square_off': equity.square_off,              
                            'symbol_token': equity.symbol_token,
                            'trading_symbol': equity.trading_symbol,
                            'transaction_type': equity.transaction_type,
                            'user_id': equity.user_id,
                            "buy_price": equity.buy_price,
                            "sell_price": equity.sell_price,
                            "buy_qty": equity.buy_qty,
                            "sell_qty": equity.sell_qty,
                            "broker": equity.broker,
                            "placed_time":equity.placed_time
                        }

                        executed_portfolios.append(portfolio_data)

                    response_data = {'ExecutedPortfolios': executed_portfolios}
                    return jsonify(response_data), 200
                except Exception as e:
                    return jsonify({'error': str(e)}), 500

    def angelone_square_off_strategy(username, strategy_tag, broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id
            portfolio = Portfolio.query.filter_by(user_id=user_id).first()
            executed_Portfolio_details = ExecutedPortfolio.query.filter_by(user_id=user_id, strategy_tag=strategy_tag, square_off=False).all()
            print(executed_Portfolio_details)
            print(portfolio.variety)
            try:
                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
            except:
                response = ERROR_HANDLER.broker_api_errors("angelone", broker_user_id) 
                response_data = {"error": response['message']}, 500
                return jsonify(response_data), 500

            angelone_list = []  # Initialize angelone_list here

            if executed_Portfolio_details:
                for executedPortfolio in executed_Portfolio_details:
                    strategy_tag = executedPortfolio.strategy_tag
                    transaction_type = executedPortfolio.transaction_type
                    trading_symbol = executedPortfolio.trading_symbol
                    symbol_token = executedPortfolio.symbol_token
                    exchange = executedPortfolio.exchange
                    product_type = executedPortfolio.product_type
                    duration = executedPortfolio.duration
                    variety = executedPortfolio.variety
                    order_type = executedPortfolio.order_type
                    id = executedPortfolio.order_id

                    data = {
                        "variety": variety,
                        "orderTag": portfolio.strategy,
                        "tradingsymbol": trading_symbol,
                        "symboltoken": symbol_token,
                        "exchange": exchange,
                        "quantity": executedPortfolio.netqty,
                        "producttype": "INTRADAY" if executedPortfolio.product_type == "MIS" else "CARRYFORWARD",
                        "transactiontype": "SELL" if transaction_type == "BUY" else "BUY",
                        "price": 0,
                        "duration": duration,
                        "ordertype": 'MARKET'
                    }

                    angelone_square_off = angelone.placeOrderFullResponse(data)
                    if angelone_square_off and 'message' in angelone_square_off:
                        print(angelone_square_off)
                        angelone_list.append(angelone_square_off['message'])

                        positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                        order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()

                        holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                        all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                        config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions, "holdings": holdings, "all_holdings": all_holdings}

                        if len(list(set(angelone_list))) == 1 and list(set(angelone_list))[0] == 'SUCCESS':
                            response_data = {'message': f'Strategy Manual square off successfully for {strategy_tag}', 'Square_off': angelone_square_off}

                            executedPortfolio.square_off = True
                            if executedPortfolio.transaction_type == "BUY":
                                executedPortfolio.sell_price = order['data'][::-1][0]['averageprice']
                            else:
                                executedPortfolio.buy_price = order['data'][::-1][0]['averageprice']
                            db.session.commit()
                            return jsonify(response_data), 200
                    else:
                        response_data = ERROR_HANDLER.flask_api_errors("angelone_square_off_strategy", f'No open positions for {broker_user_id} under Strategy {strategy_tag}')
                        return jsonify(response_data), 200
                else:
                    response_data = ERROR_HANDLER.flask_api_errors("angelone_square_off_strategy", f'The trade has already been squared off for User {broker_user_id}')
                    return jsonify(response_data), 200
            else:
                response_data = ERROR_HANDLER.flask_api_errors("angelone_square_off_strategy", f'Looks like {strategy_tag} strategy have no open positions.')
                return jsonify(response_data), 200
        else:
            response_data = ERROR_HANDLER.database_errors("user", "User Does not exist")
            return jsonify(response_data), 500

    def Flatrade_place_order(username, portfolio_name,broker_user_id):
        global instrument_list_cache
        data =  request.json
        Qtplots=data['qtp_lots']
        # limit_price=data['limit_price']
        responses =[]

        existing_user = User.query.filter_by(username=username).first()

        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User Does not exist")
            return jsonify(response_data), 500

        def token_lookup(ticker, instrument_list, exchange="NSE"):
            for instrument in instrument_list:
                if (instrument["name"] == ticker or instrument["symbol"] == ticker) and instrument["exch_seg"] == exchange:
                    return instrument["token"]
            return None  # Return None if no matching token is found

        user_id = existing_user.id
        portfolio_details = Portfolio.query.filter_by(user_id=user_id,portfolio_name=portfolio_name).first()
        portfolio_legs = Portfolio_legs.query.filter_by(portfolio_name=portfolio_details.portfolio_name).all()

        strategy_name = portfolio_details.strategy

        strategy_details = Strategies.query.filter_by(strategy_tag=strategy_name).first()
        if strategy_details:
            multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id, broker_user_id=broker_user_id).first()
            if multiplier_record:
                multiplier = multiplier_record.multiplier
            else:
                multiplier = 1  # Default to 1 if no multiplier record found for the given strategy and broker_user_id
        else:
            multiplier = 1  

        broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
        if broker_credentials:
            user_broker_multiplier = broker_credentials.user_multiplier 
            print("user_broker_multiplier:",user_broker_multiplier)
        else:
            user_broker_multiplier = 1

        max_open_trades = int(broker_credentials.max_open_trades)
        # Count the current open trades for this user and broker combination
        if max_open_trades != 0:
            # Count the current open trades for this user and broker combination
            current_open_trades = ExecutedPortfolio.query.filter_by(
                user_id=user_id,
                broker_user_id=broker_user_id,
                square_off=False
            ).count()

            # Check if placing this order would exceed max_open_trades
            if current_open_trades >= max_open_trades:
                return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]

        combined_lots =  (int(Qtplots) * int(multiplier)* int(user_broker_multiplier))
        order_book = []

        symbol = portfolio_details.symbol
        exchange = portfolio_details.exchange
        order_type = config.flattrade_data['order_type'][portfolio_details.order_type]
        product_type = portfolio_details.product_type

        # instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        # response = urllib.request.urlopen(instrument_url)
        # instrument_list = json.loads(response.read())

        if instrument_list_cache is None:
            print("Loading instrument list...")
            instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = urllib.request.urlopen(instrument_url)
            instrument_list_cache = json.loads(response.read())  # Cache the list for later use
            save_instrument_list_cache(instrument_list_cache)

        instrument_list = instrument_list_cache

        token = token_lookup(ticker=symbol,instrument_list=instrument_list,exchange=exchange)

        if symbol == "BANKNIFTY":
            underlying_price = config.flattrade_api[broker_user_id].get_quotes(exchange="NSE", token="26009")['lp']
        elif symbol == "NIFTY":
            underlying_price = config.flattrade_api[broker_user_id].get_quotes(exchange="NSE", token="26000")['lp']
        elif symbol == "FINNIFTY":
            underlying_price = config.flattrade_api[broker_user_id].get_quotes(exchange="NSE", token="99926037")['lp']

        flattrade_api = config.flattrade_api[broker_user_id]
        quote_details = flattrade_api.get_quotes(exchange=exchange, token=token)

        order_book_list = []

        buy_trades_first = portfolio_details.buy_trades_first
        positional_portfolio = portfolio_details.positional_portfolio

        for legs in portfolio_legs:

            if buy_trades_first and legs.transaction_type != "BUY":
                responses.append({"message": f"Order is not placed as buy_trades_first is true and transaction_type is {legs.transaction_type}"})
                continue  # Skip the current leg and move to the next one


            from datetime import datetime

            # Retrieve the current datetime
            current_datetime = datetime.now().strftime('%d %b %H:%M:%S')

            if positional_portfolio:
                # Check if legs.start_time is a valid, non-empty string before parsing
                if legs.start_time:
                    try:
                        start_time = datetime.strptime(legs.start_time, '%d %b %H:%M:%S').strftime('%d %b %H:%M:%S')

                        # Check if the current datetime is greater than or equal to the start time
                        if current_datetime < start_time:
                            responses.append({"message": f"Order for {legs.portfolio_name} is skipped as start_time {legs.start_time} has not been reached."})
                            continue  # Skip this leg and move to the next one
                    except ValueError:
                        responses.append({"message": f"Invalid date format for start_time {legs.start_time}."})
                        continue  # Skip this leg if parsing fails
                else:
                    responses.append({"message": f"start_time for {legs.portfolio_name} is missing or empty"})
                    continue  # Skip this leg if start_time is empty
            else:
                pass

            portfolio_strategy = portfolio_details.strategy
            strategy = Strategies.query.filter_by(strategy_tag=portfolio_strategy).first()
            print("strategy:", strategy)

            if strategy:
                allowed_trades = strategy.allowed_trades 
                print("allowed_trades:", allowed_trades)
            else:
                allowed_trades = 'Both'  

            # Map side to corresponding allowed trade type
            side = legs.transaction_type
            if side == "BUY":
                trade_type = "Long"
            elif side == "SELL":
                trade_type = "Short"
            else:
                return [{"message": "Invalid transaction type"}], 500

            # Check if the trade is allowed by the strategy
            if allowed_trades == 'Both' or allowed_trades == trade_type:
                pass  
            else:
                return [{"message": f"Allowed Trade details do not match for strategy: {portfolio_strategy} | {allowed_trades}"}], 500

            strike = legs.strike

            quantity = (int(legs.quantity)* int(combined_lots))

            if strike == 'ATM':
                strike = 0
            elif strike.startswith('ATM+'):
                strike = int(strike[4:])
            elif strike.startswith('ATM-'):
                strike = -int(strike[4:])
            else:
                strike = int(strike)

            if symbol == "NIFTY":
                if legs.option_type == "CE":
                    strike_price = round((float(underlying_price) + strike) / 50) * 50
                elif legs.option_type == "PE":
                    strike_price = round((float(underlying_price) - strike) / 50) * 50
            elif symbol == "BANKNIFTY":
                if legs.option_type == "CE":
                    strike_price = round((float(underlying_price) + strike) / 100) * 100

                elif legs.option_type == "PE":
                    strike_price = round((float(underlying_price) - strike) / 100) * 100

            limit_price = legs.limit_price
            # expiry = re.sub("20","",legs.expiry_date)
            legs_expiry_date = legs.expiry_date
            expiry =  legs_expiry_date[:5] + legs_expiry_date[-2:]

            trade_symbol = symbol + expiry + config.flattrade_data['option_type'][legs.option_type] + str(strike_price)

            print("Order Type :",order_type)

            transaction_type = config.flattrade_data['transaction_type'][legs.transaction_type]
            flattrade_order = config.flattrade_api[broker_user_id].place_order(buy_or_sell=transaction_type, product_type="I" if product_type == "MIS" else "M",
                exchange=exchange, tradingsymbol=trade_symbol,
                quantity=quantity, discloseqty=0,price_type=order_type, price=limit_price if order_type == "LMT" else 0, trigger_price=None,
                retention='DAY', remarks= portfolio_details.strategy)
            
            trade_symbol = ''
            order_book = config.flattrade_api[broker_user_id].get_order_book()[:len(portfolio_legs)]
            positions_info = config.flattrade_api[broker_user_id].get_positions()
            holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
            order_book_send = config.flattrade_api[broker_user_id].get_order_book()

            config.all_flattrade_details[broker_user_id] = {
                'orderbook': order_book_send,
                'holdings': holdings_info,
                'positions': positions_info
            }

            executed_portfolio = ExecutedPortfolio(user_id=user_id,broker_user_id=broker_user_id,transaction_type=legs.transaction_type,strategy_tag=portfolio_details.strategy,portfolio_name=portfolio_details.portfolio_name,exchange=portfolio_details.exchange,
            portfolio_leg_id=legs.id,product_type="I" if product_type == "MIS" else "M",broker="flattrade")
            db.session.add(executed_portfolio)
            db.session.commit()


        all_executed_portfolios = ExecutedPortfolio.query.all()[::-1][:2]

        for details,executed_portfolios in zip(order_book,all_executed_portfolios):
            if details['status'] != 'REJECTED' :
                
                if details['status'] == "COMPLETE" :
                    executed_portfolios.buy_price = details['avgprc']
                elif details['status'] == "OPEN":
                    executed_portfolios.buy_price = details['rprc']

                executed_portfolios.order_id = details['norenordno']
                executed_portfolios.trading_symbol = details['tsym']
                executed_portfolios.status = details['status']
                executed_portfolios.order_type = details['prctyp']
                executed_portfolios.symbol_token = details['token']
                executed_portfolios.duration = details['ret']
                executed_portfolios.netqty = details['qty']
                executed_portfolios.broker = "flattrade"
                from datetime import time

                def create_performance_record(portfolio_name, user_id, broker_user_id, max_pl, min_pl):
                    # Check if a performance record with the same portfolio_name already exists
                    existing_record = Performance.query.filter_by(portfolio_name=portfolio_name, user_id=user_id).first()
                    
                    if existing_record is None:
                        # If the record does not exist, create a new one
                        performance_record = Performance(
                            portfolio_name=portfolio_name,
                            user_id=user_id,
                            broker_user_id=broker_user_id,
                            max_pl=max_pl,
                            min_pl=min_pl,
                            max_pl_time=time(0, 0, 0),
                            min_pl_time=time(0, 0, 0)
                        )
                        db.session.add(performance_record)
                        db.session.commit()
                    else:
                        # If the record exists, you can handle it according to your needs
                        print(f"Performance record for portfolio '{portfolio_name}' already exists.")

                # Call the function
                create_performance_record(
                    portfolio_name=portfolio_name,
                    user_id=user_id,
                    broker_user_id=broker_user_id,
                    max_pl=float('-inf'),  
                    min_pl=float('+inf')
                )
            else:
                db.session.delete(executed_portfolios)
                db.session.commit()

            try:
                db.session.add(executed_portfolios)
            except:
                pass

        db.session.commit()

        delete_portfolio = ExecutedPortfolio.query.filter_by(status="REJECTED").all()

        for i in delete_portfolio:
            db.session.delete(i)
            db.session.commit()

        response_data = {"messages": [{"message": "Order placed successfully!"}] + responses}
        return jsonify(response_data), 200    
        
    def flattrade_square_off_strategy(username, strategy_tag, broker_user_id):
        try:
            existing_user = User.query.filter_by(username=username).first()
            print("existing_user:", existing_user)
            
            if existing_user:
                user_id = existing_user.id
                print("user_id:", user_id)
                
                portfolio = Portfolio.query.filter_by(user_id=user_id).first()
                executed_Portfolio_details = ExecutedPortfolio.query.filter_by(
                    user_id=user_id,
                    strategy_tag=strategy_tag,
                    square_off=False
                ).all()
                
                print("executed_Portfolio_details:", executed_Portfolio_details)
                print("portfolio.variety:", portfolio.variety)
                
                try:
                    flattrade = config.flattrade_api[broker_user_id]
                except KeyError:
                    response = ERROR_HANDLER.broker_api_errors("flattrade", "Invalid broker_user_id") 
                    response_data = {"error": response['message']}, 500
                    return jsonify(response_data), 500

                print("flattrade instance:", flattrade)
                flattrade_list = []

                if executed_Portfolio_details:
                    for executedPortfolio in executed_Portfolio_details:
                        strategy_tag = executedPortfolio.strategy_tag
                        order_type = executedPortfolio.order_type
                        id = executedPortfolio.order_id
                        print("Order ID:", id)

                        flattrade_square_off = flattrade.place_order(
                            buy_or_sell="S" if executedPortfolio.transaction_type == "BUY" else "B",
                            product_type="I" if executedPortfolio.product_type == "MIS" else "M",
                            exchange=executedPortfolio.exchange,
                            tradingsymbol=executedPortfolio.trading_symbol,
                            quantity=executedPortfolio.netqty,
                            discloseqty=0,
                            price_type='MKT',
                            price=0,
                            trigger_price=None,
                            retention='DAY',
                            remarks=executedPortfolio.strategy_tag
                        )

                        print("Flattrade Square Off Response:", flattrade_square_off)

                        # Check if flattrade_square_off is None
                        if flattrade_square_off is None:
                            print("Error: place_order returned None.")
                            response = ERROR_HANDLER.broker_api_errors("flattrade", f'No open positions for {broker_user_id} under Strategy {strategy_tag}')
                            return jsonify(response_data), 200

                        positions_info = flattrade.get_positions()
                        order_book_send = flattrade.get_order_book()
                        holdings_info = flattrade.get_holdings()

                        config.all_flattrade_details[broker_user_id] = {
                            'order': order_book_send,
                            "holdings": holdings_info,
                            "positions": positions_info
                        }

                        flattrade_list.append(flattrade_square_off.get('stat', 'Failed'))

                    if len(set(flattrade_list)) == 1 and list(set(flattrade_list))[0] == 'Ok':
                        response_data = {'message': f'Strategy Manual square off successfully for strategy {strategy_tag}', 'Square_off': flattrade_square_off}
                        executedPortfolio.square_off = True
                        last_avgprc = order_book_send[0]['avgprc']
                        print("sell_price:", last_avgprc)
                        executedPortfolio.sell_price = last_avgprc
                        db.session.commit()
                        return jsonify(response_data), 200
                    else:
                        response = ERROR_HANDLER.broker_api_errors("flattrade", f'{strategy_tag} strategy off failed.')
                        return jsonify(response_data), 200
                else:
                    response_data = ERROR_HANDLER.broker_api_errors("flattrade", f'Looks like {strategy_tag} strategy has no open positions.')
                    return jsonify(response_data), 200
            else:
                response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                return jsonify(response_data), 500
        except SQLAlchemyError as e:
            print(f"Database error: {e}")
            response_data = {'error': 'Database error occurred'}
            return jsonify(response_data), 500
        except Exception as e:
            print(f"An error occurred: {e}")
            response_data = {'error': 'An unexpected error occurred'}
            return jsonify(response_data), 500

    def enable_portfolio(username, portfolio_name):
        data = request.json
        print("data:",data)
        existing_user = User.query.filter_by(username=username).first()

        enable_status = data['enable_status']

        if enable_status == "True":
            enable_status = True
            success_message = "Portfolio enabled successfully!"
        else:
            enable_status = False
            success_message = "Portfolio disabled successfully!"

        if existing_user:
            user_id = existing_user.id
        else:
            response_data = ERROR_HANDLER.database_errors("user", "Invalid Username")
            return jsonify(response_data), 500

        portfolio = Portfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name).first()

        if portfolio:
            portfolio.enabled = enable_status
            db.session.commit()

            response_data = {"message": success_message}
            return jsonify(response_data), 200
        else:
            response_data = ERROR_HANDLER.database_errors("portfolio", "Portfolio does not exist!")
            return jsonify(response_data), 500
 
    def enable_all_portfolios(username):
        existing_user = User.query.filter_by(username=username).first()
 
        if existing_user:
            user_id = existing_user.id
            portfolios = Portfolio.query.filter_by(user_id=user_id).all()
            for portfolio in portfolios:
                portfolio.enabled = True
                db.session.commit()
            response_data = {"message": "All portfolios enabled successfully !!"}
            return jsonify(response_data), 200
           
        else:
            response_data = ERROR_HANDLER.database_errors("user", "Invalid Username")
            return jsonify(response_data), 500
       
    def delete_all_portfolios(username):
        existing_user = User.query.filter_by(username=username).first()
 
        if existing_user:
            user_id = existing_user.id
            portfolios = Portfolio.query.all()
            for portfolio in portfolios:
                db.session.delete(portfolio)
           
            portfolio_legs = Portfolio_legs.query.all()
            for legs in portfolio_legs:
                db.session.delete(legs)
 
            db.session.commit()
 
            response_data = {"message": "All portfolios deleted successfully !!"}
            return jsonify(response_data), 200
           
        else:
            response_data = ERROR_HANDLER.database_errors("user", "Invalid Username")
            return jsonify(response_data), 500
 
    def delete_all_enabled_portfolios(username):
        existing_user = User.query.filter_by(username=username).first()
 
        if existing_user:
            user_id = existing_user.id
            portfolios = Portfolio.query.filter_by(enabled=True).all()
            for portfolio in portfolios:
                portfolio_id = portfolio.id
                db.session.delete(portfolio)
                portfolio_legs = Portfolio_legs.query.filter_by(Portfolio_id=portfolio_id).all()
                for leg in portfolio_legs:
                    db.session.delete(leg)
 
            db.session.commit()
 
            response_data = {"message": "Enabled portfolios deleted successfully !!"}
            return jsonify(response_data), 200
           
        else:
            response_data = ERROR_HANDLER.database_errors("user", "Invalid Username")
            return jsonify(response_data), 500

    def get_futures_expiry_list(username):
        from datetime import datetime, time
        data = request.json
        symbols = data['symbols']
        instrumenttype = data['FUT']
        exch_seg = data['exch_seg']  
        
        def AngleOnelogin():
            SMART_API_OBJ = SmartConnect(api_key=config.apikey)
            data = SMART_API_OBJ.generateSession(config.username, config.pwd, pyotp.TOTP(config.token).now())
            config.AUTH_TOKEN = data['data']['jwtToken']
            refreshToken = data['data']['refreshToken']
            config.FEED_TOKEN = SMART_API_OBJ.getfeedToken()
            res = SMART_API_OBJ.getProfile(refreshToken)
            config.SMART_API_OBJ = SMART_API_OBJ
            # rms_limit = config.SMART_API_OBJ.rmsLimit()
            # logger.info(f'Login {res} {config.SMART_API_OBJ.rmsLimit()}')

        def futures_expiry(symbol, instrumenttype, exch_seg):
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(url)
            if response.status_code == 200:
                json_data = response.json()
                instrument_list = [entry for entry in json_data if entry['exch_seg'] == exch_seg and entry['instrumenttype'] == instrumenttype and entry['name'] == symbol]
                index_expiry = list(set(entry['expiry'] for entry in instrument_list))  # Remove duplicates
                return index_expiry
            else:
                return None

        if config.SMART_API_OBJ is not None:
            print("Without login")
            pass
        elif config.SMART_API_OBJ is None:
            AngleOnelogin()

        expiry_data = {}
        today = datetime.now()
        for symbol in symbols:
            response_data = futures_expiry(symbol, instrumenttype, exch_seg)
            if response_data:
                # Filter and sort expiry dates
                valid_data = [date for date in response_data if datetime.strptime(date, '%d%b%Y') >= today]
                sorted_data = sorted(valid_data, key=lambda x: datetime.strptime(x, '%d%b%Y'))
                expiry_data[symbol] = sorted_data

        if expiry_data:
            return jsonify(expiry_data), 200
        else:
            response = ERROR_HANDLER.broker_api_errors("angelone", "Failed to retrieve expiry list for any symbol.")
            return jsonify({"error": response['message']}), 500

    def fyers_futures_place_order(username, portfolio_name, broker_user_id):
            data = request.json
            Qtplots = data['qtp_lots']

            try:
                config.fyers_order_place_response = []
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    user_id = existing_user.id
                    portfolio_details = Portfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name).first()
                    strategy_name = portfolio_details.strategy
                    strategy_details = Strategies.query.filter_by(strategy_tag=strategy_name).first()
                    if strategy_details:
                        multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id,
                                                                            broker_user_id=broker_user_id).first()
                        if multiplier_record:
                            multiplier = multiplier_record.multiplier
                        else:
                            multiplier = 1  # Default to 1 if no multiplier record found for the given strategy and broker_user_id
                    else:
                        multiplier = 1
                    print("multiplier:", multiplier)

                    broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                    if broker_credentials:
                        user_broker_multiplier = broker_credentials.user_multiplier 
                        print("user_broker_multiplier:",user_broker_multiplier)
                    else:
                        user_broker_multiplier = 1

                    max_open_trades = int(broker_credentials.max_open_trades)
                    # Count the current open trades for this user and broker combination
                    if max_open_trades != 0:
                        # Count the current open trades for this user and broker combination
                        current_open_trades = ExecutedPortfolio.query.filter_by(
                            user_id=user_id,
                            broker_user_id=broker_user_id,
                            square_off=False
                        ).count()

                        # Check if placing this order would exceed max_open_trades
                        if current_open_trades >= max_open_trades:
                            return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]


                    combined_lots = int(Qtplots) * int(multiplier) * int(user_broker_multiplier)
                    print("combined_lots :", combined_lots)

                    try:
                        fyers = config.OBJ_fyers[broker_user_id]
                    except:
                        response_data = ERROR_HANDLER.broker_api_errors("fyers", f"Please login to the broker account, {broker_user_id}")
                        return jsonify(response_data), 500

                    if broker_user_id in portfolio_details.strategy_accounts_id.split(','):
                        pass
                    else:
                        response_data = {'message': "Broker UserID does not exist for the portfolio !"}
                        return jsonify(response_data), 500

                    def fetch_option_contracts():
                        fyers_csv_url = "https://public.fyers.in/sym_details/NSE_FO.csv"
                        with urllib.request.urlopen(fyers_csv_url) as response:
                            fyers_csv_data = response.read().decode('utf-8')
                        df_fyers = pd.read_csv(io.StringIO(fyers_csv_data))
                        df_fyers.columns = ['Fytoken', 'Symbol Details', 'Exchange Instrument type', 'Minimum lot size',
                                            'Tick size',
                                            'Empty', 'ISIN', 'Trading Session', 'Last update date', 'Expiry date',
                                            'Symbol ticker',
                                            'Exchange', 'Segment', 'Scrip code', 'Underlying scrip code', 'Strike price',
                                            'Option type',
                                            'Underlying FyToken', 'EMPTY', 's1', 's2']
                        df_fyers.to_csv("options.csv")
                        return df_fyers

                    def filter_option_contracts(df_fyers, symbol, exchange):
                        closest_option_contracts = df_fyers[df_fyers["Exchange Instrument type"] == exchange]
                        closest_option_contracts = closest_option_contracts[closest_option_contracts["Scrip code"] == symbol]

                        return closest_option_contracts

                    portfolio_legs = Portfolio_legs.query.filter_by(portfolio_name=portfolio_name).all()
                    buy_trades_first = portfolio_details.buy_trades_first

                    for portfolio_leg in portfolio_legs:

                        if buy_trades_first and portfolio_leg.transaction_type != "BUY":
                            responses.append({"message": f"Order is not placed as buy_trades_first is true and transaction_type is {legs.transaction_type}"})
                            continue  # Skip the current leg and move to the next one

                        portfolio_strategy = portfolio_details.strategy
                        strategy = Strategies.query.filter_by(strategy_tag=portfolio_strategy).first()
                        print("strategy:", strategy)

                        if strategy:
                            allowed_trades = strategy.allowed_trades 
                            print("allowed_trades:", allowed_trades)
                        else:
                            allowed_trades = 'Both'  

                        # Map side to corresponding allowed trade type
                        side = portfolio_leg.transaction_type
                        if side == "BUY":
                            trade_type = "Long"
                        elif side == "SELL":
                            trade_type = "Short"
                        else:
                            return [{"message": "Invalid transaction type"}], 500

                        # Check if the trade is allowed by the strategy
                        if allowed_trades == 'Both' or allowed_trades == trade_type:
                            pass  
                        else:
                            return [{"message": f"Allowed Trade details do not match for strategy: {portfolio_strategy} | {allowed_trades}"}], 500

                        symbol = portfolio_details.symbol
                        transaction_type = portfolio_leg.transaction_type

                        exchange = portfolio_details.exchange
                        # print(exchange)
                        if exchange == 'NFO':
                            exchange =11
                        # print(exchange)
                        strategy_tag = portfolio_details.strategy
                        lots = int(portfolio_leg.lots) * int(combined_lots)
                        # print(lots)

                        expiry_date_str = portfolio_leg.expiry_date
                        expiry_date = datetime.datetime.strptime(expiry_date_str, "%d%b%Y")
                        today = datetime.date.today()
                        expiry_month = expiry_date.month
                        current_month = today.month
                        months_difference = expiry_month - current_month

                        if months_difference == 0:
                            symbol_index = 0  # Consider it as the minimum index
                        elif months_difference ==1:
                            symbol_index = 1  # Consider it as the maximum index
                        else:
                            symbol_index = 2

                        future_contracts = filter_option_contracts(fetch_option_contracts(), symbol, exchange)
                        # print("future_contracts   : ", future_contracts)
                        # print(option_contracts["Expiry date"].to_list()[symbol_index])
                        # print("Length of option_contracts list:", len(option_contracts["Expiry date"].to_list()))
                        # print("Symbol index:", symbol_index)

                        data = {
                            "symbol": future_contracts["Expiry date"].to_list()[symbol_index],
                            "qty": (future_contracts["Minimum lot size"].to_list()[0]) * lots,
                            "type": 2,
                            "side": 1 if transaction_type == 'BUY' else -1,
                            "productType": "MARGIN",
                            "limitPrice": 0,
                            "stopPrice": 0,
                            "validity": "DAY",
                            "disclosedQty": 0,
                            "offlineOrder": False,
                            "orderTag": strategy_tag
                        }
                        symbol=data['symbol']
                        print("symbol : ", symbol)
                        quantity = data['qty']
                        print("quantity : ", quantity)
                        response = fyers.place_order(data=data)
                        print(response)

                        symbol = data['symbol']
                        productType = data['productType']
                        order_id = symbol + '-' + productType

                        # executed_portfolio = ExecutedPortfolio(user_id=user_id, portfolio_name=portfolio_name,
                        #                                         order_id=order_id, strategy_tag=strategy_tag,
                        #                                         broker_user_id=portfolio_details.strategy_accounts_id,
                        #                                         transaction_type=portfolio_leg.transaction_type)

                        if response['s'] == 'ok':
                            order_id = f"{data['symbol']}-{data['productType']}"
                            executed_portfolio = ExecutedPortfolio(user_id=user_id, portfolio_name=portfolio_name, order_id=order_id,
                                                                strategy_tag=strategy_tag, broker_user_id=broker_user_id,
                                                                transaction_type=transaction_type)
                            config.fyers_order_place_response.append(response)
                            db.session.add(executed_portfolio)  # Add executed portfolio to database
                            db.session.commit()
                            from datetime import time

                            def create_performance_record(portfolio_name, user_id, broker_user_id, max_pl, min_pl):
                                # Check if a performance record with the same portfolio_name already exists
                                existing_record = Performance.query.filter_by(portfolio_name=portfolio_name, user_id=user_id).first()
                                
                                if existing_record is None:
                                    # If the record does not exist, create a new one
                                    performance_record = Performance(
                                        portfolio_name=portfolio_name,
                                        user_id=user_id,
                                        broker_user_id=broker_user_id,
                                        max_pl=max_pl,
                                        min_pl=min_pl,
                                        max_pl_time=time(0, 0, 0),
                                        min_pl_time=time(0, 0, 0)
                                    )
                                    db.session.add(performance_record)
                                    db.session.commit()
                                else:
                                    # If the record exists, you can handle it according to your needs
                                    print(f"Performance record for portfolio '{portfolio_name}' already exists.")

                            # Call the function
                            create_performance_record(
                                portfolio_name=portfolio_name,
                                user_id=user_id,
                                broker_user_id=broker_user_id,
                                max_pl=float('-inf'),  
                                min_pl=float('+inf')
                            )
                        else:
                            config.fyers_order_place_response.append(response)

                    fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
                    fyers_position=config.OBJ_fyers[broker_user_id].positions()
                    fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
                    config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}
                    return jsonify({'messages': config.fyers_order_place_response}), 200

            except Exception as e:
                print("Error:", str(e))  # Log any exceptions
                return jsonify({'error': str(e)}), 500

    def angleone_future_place_order(username, portfolio_name, broker_user_id):

            data = request.json
            qtp_lots = data['qtp_lots']
            print("qtp_lots:", qtp_lots)
            config.order_place_response = []
            responses = []
            stored_in_db = False
            existing_user = User.query.filter_by(username=username).first()
       
            if not existing_user:
                response_data = ERROR_HANDLER.database_errors("user", "User Does not exist")
                return jsonify(response_data), 500
       
            user_id = existing_user.id
            # portfolio_details = Portfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name).first()
            portfolio = Portfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name).first()
   
            if broker_user_id not in portfolio.strategy_accounts_id.split(','):
                response_data = ERROR_HANDLER.database_errors("portfolio", "Broker UserID does not exist for the portfolio!")
                return jsonify(response_data), 500
   
            if not portfolio:
                response_data = ERROR_HANDLER.database_errors("portfolio", "Portfolio does not exist")
                return jsonify(response_data), 500
   
            strategy_name = portfolio.strategy
   
            strategy_details = Strategies.query.filter_by(strategy_tag=strategy_name).first()
            if strategy_details:
                multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id, broker_user_id=broker_user_id).first()
                if multiplier_record:
                    multiplier = multiplier_record.multiplier
                else:
                    multiplier = 1  # Default to 1 if no multiplier record found for the given strategy and broker_user_id
            else:
                multiplier = 1  
            print("multiplier:", multiplier)

            broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
            if broker_credentials:
                user_broker_multiplier = broker_credentials.user_multiplier 
                print("user_broker_multiplier:",user_broker_multiplier)
            else:
                user_broker_multiplier = 1

            max_open_trades = int(broker_credentials.max_open_trades)
            # Count the current open trades for this user and broker combination
            if max_open_trades != 0:
                # Count the current open trades for this user and broker combination
                current_open_trades = ExecutedPortfolio.query.filter_by(
                    user_id=user_id,
                    broker_user_id=broker_user_id,
                    square_off=False
                ).count()

                # Check if placing this order would exceed max_open_trades
                if current_open_trades >= max_open_trades:
                    return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]    


            combined_lots =  (int(qtp_lots) * int(multiplier)* int(user_broker_multiplier))
            print("combined_lots :", combined_lots)
   
            # Function to handle login to external service (assuming it's needed)
            def angle_one_login():
                config.SMART_API_OBJ_angelone[broker_user_id] = SmartConnect(api_key=config.apikey)
                data = config.SMART_API_OBJ_angelone[broker_user_id].generateSession(config.username, config.pwd,
                                                                                    pyotp.TOTP(config.token).now())
                config.AUTH_TOKEN = data['data']['jwtToken']
                refreshToken = data['data']['refreshToken']
                config.FEED_TOKEN = config.SMART_API_OBJ_angelone[broker_user_id].getfeedToken()
                res = config.SMART_API_OBJ_angelone[broker_user_id].getProfile(refreshToken)
                config.config.SMART_API_OBJ_angelone[broker_user_id] = config.SMART_API_OBJ_angelone[broker_user_id]
                rms_limit = config.config.SMART_API_OBJ_angelone[broker_user_id].rmsLimit()
                order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}
                logger.info(f'Login {res} {config.config.SMART_API_OBJ_angelone[broker_user_id].rmsLimit()}')
   
       
            symbol = portfolio.symbol
            print(symbol)
            exch_seg = portfolio.exchange
            print(exch_seg)
            portfolio_leg = Portfolio_legs.query.filter_by(portfolio_name=portfolio.portfolio_name).first()
            expiry_date = portfolio_leg.expiry_date
            print(expiry_date)
            #expiry_date = datetime.datetime.strptime(expiry_date_str, "%d%b%Y")
            #print(expiry_date)
            instrumenttype = portfolio_leg.option_type
            future_value='FUTIDX' if instrumenttype=='FUT' else  ''
            def future_contact_symbol(symbol, future_value, exch_seg, expiry):
                global instrument_list_cache 
                # url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                # response = requests.get(url)
           
                # if response.status_code == 200:
                #     json_data = response.json()
                #     instrument_list = [entry for entry in json_data if entry['exch_seg'] == exch_seg
                #                     and entry['instrumenttype'] == future_value and entry['name'] == symbol
                #                     and entry['expiry'] == expiry_date]
                #     return instrument_list
                # else:
                #     return None
                # Access the cached variable

                    # Check if the instrument list cache is already populated
                if instrument_list_cache is None:
                    print("Loading instrument list...")
                    instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                    try:
                        response = urllib.request.urlopen(instrument_url)
                        instrument_list_cache = json.loads(response.read())
                        print(f'Loaded instrument list with {len(instrument_list_cache)} instruments.')
                        save_instrument_list_cache(instrument_list_cache)  # Save the cache if needed
                    except Exception as e:
                        logger.error(f"Error fetching instrument list: {e}")
                        return None  # Return early if cache loading fails
                
                instrument_list = instrument_list_cache

                try:
                    # Log filtering criteria for debugging
                    logger.debug(f"Filtering for symbol: {symbol}, expiry: {expiry}, exch_seg: {exch_seg}")

                    # Filter futures contracts by symbol, instrument type, expiry, and exchange segment
                    instrument_list = [
                        entry for entry in instrument_list_cache if (
                            entry['exch_seg'].upper() == exch_seg.upper() and
                            entry['instrumenttype'].upper() == future_value.upper() and
                            entry['name'].upper() == symbol.upper() and
                            entry['expiry'].upper() == expiry.upper())]

                    logger.debug(f"Found future contracts: {instrument_list}")
                    return instrument_list
                except Exception as e:
                    logger.error(f"Error processing data: {e}")
                    return None
   
            response_data = future_contact_symbol(symbol, future_value, exch_seg, expiry_date)
   
            if not response_data:
                response_data = {'message': "Symbol data not found"}
                return jsonify(response_data), 500
   
            symboltoken = response_data[0]['token']
            tradingsymbol = response_data[0]['symbol']
            print(tradingsymbol)
            def place_limit_order(order_params):
                response = config.SMART_API_OBJ_angelone[broker_user_id].placeOrder(order_params)
                return response
   
   
            if config.SMART_API_OBJ_angelone[broker_user_id] is None:
                angle_one_login()
   
            portfolio_legs = Portfolio_legs.query.filter_by(Portfolio_id=portfolio.id).all()

            buy_trades_first = portfolio.buy_trades_first
            positional_portfolio = portfolio.positional_portfolio
       
            for portfolio_leg in portfolio_legs:

                if buy_trades_first and portfolio_leg.transaction_type != "BUY":
                    responses.append({"message": f"Order is not placed as buy_trades_first is true and transaction_type is {legs.transaction_type}"})
                    continue  # Skip the current leg and move to the next on

                    
                from datetime import datetime

                # Retrieve the current datetime
                current_datetime = datetime.now().strftime('%d %b %H:%M:%S')

                if positional_portfolio:
                    # Check if legs.start_time is a valid, non-empty string before parsing
                    if portfolio_leg.start_time:
                        try:
                            start_time = datetime.strptime(portfolio_leg.start_time, '%d %b %H:%M:%S').strftime('%d %b %H:%M:%S')

                            # Check if the current datetime is greater than or equal to the start time
                            if current_datetime < start_time:
                                responses.append({"message": f"Order for {portfolio_leg.portfolio_name} is skipped as start_time {portfolio_leg.start_time} has not been reached."})
                                continue  # Skip this leg and move to the next one
                        except ValueError:
                            responses.append({"message": f"Invalid date format for start_time {portfolio_leg.start_time}."})
                            continue  # Skip this leg if parsing fails
                    else:
                        responses.append({"message": f"start_time for {portfolio_leg.portfolio_name} is missing or empty"})
                        continue  # Skip this leg if start_time is empty
                else:
                    pass

                portfolio_strategy = portfolio.strategy
                strategy = Strategies.query.filter_by(strategy_tag=portfolio_strategy).first()
                print("strategy:", strategy)

                if strategy:
                    allowed_trades = strategy.allowed_trades 
                    print("allowed_trades:", allowed_trades)
                else:
                    allowed_trades = 'Both'  

                # Map side to corresponding allowed trade type
                side = portfolio_leg.transaction_type
                if side == "BUY":
                    trade_type = "Long"
                elif side == "SELL":
                    trade_type = "Short"
                else:
                    return [{"message": "Invalid transaction type"}], 500

                # Check if the trade is allowed by the strategy
                if allowed_trades == 'Both' or allowed_trades == trade_type:
                    pass  
                else:
                    return [{"message": f"Allowed Trade details do not match for strategy: {portfolio_strategy} | {allowed_trades}"}], 500

                symbol = portfolio.symbol
                transaction_type = portfolio_leg.transaction_type
                lots =int(portfolio_leg.lots) * int(qtp_lots) * int(multiplier)
                expiry_date_str = portfolio_leg.expiry_date
                expiry_date = expiry_date_str
                quantity = portfolio_leg.quantity
                strategy_tag = portfolio.strategy
                order_type = portfolio.order_type
                variety = portfolio.variety
                if portfolio.symbol == "BANKNIFTY":
                    total_quantity = lots * 15
                elif portfolio.symbol == "NIFTY":
                    total_quantity = lots * 25
                elif portfolio.symbol == "FINNIFTY":
                    total_quantity = lots * 25
                order_params = {
                    "variety": "NORMAL",
                    "tradingsymbol": tradingsymbol,
                    "symboltoken": symboltoken,
                    "transactiontype": transaction_type,
                    "exchange": exch_seg,
                    "ordertype": portfolio.order_type,
                    "producttype": "CARRYFORWARD",
                    "duration": "DAY",
                    "quantity": total_quantity,
                    "ordertag": portfolio.strategy
                }
                quantity = order_params['quantity']
                print("quantity: ", quantity)
                order_id = place_limit_order(order_params)
                logger.info(f"PlaceOrder : {order_id}")
                order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                product_type = order_params["producttype"]
                duration = order_params["duration"]
   
                stored_in_db = False
                response_data = {'message': order['data'][::-1][0]['text'], 'orderstatus': order['data'][::-1][0]['status']}
   
                if order['data'][::-1][0]['status'] == 'rejected':
                    config.order_place_response.append(response_data)
               
                else:
                    config.order_place_response.append(response_data)
                    executed_portfolio = ExecutedPortfolio(user_id=user_id, portfolio_name=portfolio_name,
                                                            order_id=order_id, strategy_tag=strategy_tag,
                                                            broker_user_id=portfolio.strategy_accounts_id,
                                                            transaction_type=portfolio_leg.transaction_type,
                                                            trading_symbol=tradingsymbol, exchange=portfolio.exchange,
                                                            product_type=product_type, netqty=portfolio_leg.quantity,
                                                            symbol_token=symboltoken, variety=variety, duration=duration,
                                                            order_type=order_type)
                    db.session.add(executed_portfolio)
                    db.session.commit()
                    stored_in_db = True
                    from datetime import time

                    def create_performance_record(portfolio_name, user_id, broker_user_id, max_pl, min_pl):
                        # Check if a performance record with the same portfolio_name already exists
                        existing_record = Performance.query.filter_by(portfolio_name=portfolio_name, user_id=user_id).first()
                        
                        if existing_record is None:
                            # If the record does not exist, create a new one
                            performance_record = Performance(
                                portfolio_name=portfolio_name,
                                user_id=user_id,
                                broker_user_id=broker_user_id,
                                max_pl=max_pl,
                                min_pl=min_pl,
                                max_pl_time=time(0, 0, 0),
                                min_pl_time=time(0, 0, 0)
                            )
                            db.session.add(performance_record)
                            db.session.commit()
                        else:
                            # If the record exists, you can handle it according to your needs
                            print(f"Performance record for portfolio '{portfolio_name}' already exists.")

                    # Call the function
                    create_performance_record(
                        portfolio_name=portfolio_name,
                        user_id=user_id,
                        broker_user_id=broker_user_id,
                        max_pl=float('-inf'),  
                        min_pl=float('+inf')
                    )
   
            if stored_in_db:
                response_data = ERROR_HANDLER.broker_api_errors("angelone", config.order_place_response)
                return jsonify(response_data), 500
   
            # except Exception as e:
            #     response_data = {'message': f'Error: {e}'}, 500
            #     return jsonify(response_data), 500
   
            return jsonify({'messages': config.order_place_response + responses}), 200

    def flatrade_future_place_order(username, portfolio_name, broker_user_id):
        data = request.json
        Qtplots = data['qtp_lots']
        responses = []

        existing_user = User.query.filter_by(username=username).first()

        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User Does not exist")
            return jsonify(response_data), 500
        
        user_id = existing_user.id
        portfolio_details = Portfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name).first()
        portfolio_legs = Portfolio_legs.query.filter_by(portfolio_name=portfolio_details.portfolio_name).all()  # Retrieve all portfolio legs
        if portfolio_legs:
            expiry_date = portfolio_legs[0].expiry_date  # Assuming all legs have the same expiry date
            print(expiry_date)
        strategy_name = portfolio_details.strategy

        strategy_details = Strategies.query.filter_by(strategy_tag=strategy_name).first()
        if strategy_details:
            multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id,
                                                                broker_user_id=broker_user_id).first()
            if multiplier_record:
                multiplier = multiplier_record.multiplier
            else:
                multiplier = 1  # Default to 1 if no multiplier record found for the given strategy and broker_user_id
        else:
            multiplier = 1
        print("multiplier:", multiplier)

        print("broker_multiplier", multiplier)

        broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
        if broker_credentials:
            user_broker_multiplier = broker_credentials.user_multiplier 
            print("user_broker_multiplier:",user_broker_multiplier)
        else:
            user_broker_multiplier = 1

        max_open_trades = int(broker_credentials.max_open_trades)
        # Count the current open trades for this user and broker combination
        if max_open_trades != 0:
            # Count the current open trades for this user and broker combination
            current_open_trades = ExecutedPortfolio.query.filter_by(
                user_id=user_id,
                broker_user_id=broker_user_id,
                square_off=False
            ).count()

            # Check if placing this order would exceed max_open_trades
            if current_open_trades >= max_open_trades:
                return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]      


        combined_lots = (int(Qtplots) * int(multiplier) * int(user_broker_multiplier))
        print("combined_lots:", combined_lots)

        symbol = portfolio_details.symbol
        exchange = portfolio_details.exchange
        order_type = config.flattrade_data['order_type'][portfolio_details.order_type]

        order_book=[]
        instrumenttype = portfolio_legs[0].option_type  # Assuming all legs have the same instrument type
        future_value = 'FUTIDX' if instrumenttype == 'FUT' else ''
        def future_contact_symbol(symbol, future_value, exchange, expiry):
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(url)

            print("Expiry :",expiry)
            print("Future Value :",future_value)
            print("Symbol :",symbol)

            if response.status_code == 200:
                json_data = response.json()
                instrument_list = [entry for entry in json_data if
                                entry['exch_seg'] == exchange
                                and entry['instrumenttype'] == future_value and entry['name'] == symbol
                                and entry['expiry'] == expiry_date]
                return instrument_list
            else:
                return None

        response_data = future_contact_symbol(symbol, future_value, exchange, expiry_date)

        if not response_data:
            response_data = ERROR_HANDLER.broker_api_errors("flattrade", "Symbol data not found")
            return jsonify(response_data), 500

        symboltoken = response_data[0]['token']
        trading_symbol = response_data[0]['symbol']
        print(trading_symbol)

        # futures_symbol = "NIFTY25APR24FUT"
        future_symbol = trading_symbol[:-2]  # Remove the last two characters
        print(future_symbol)  # Output: NIFTY25APR24F

        flattrade_api = config.flattrade_api[broker_user_id]
        quote_details = flattrade_api.get_quotes(exchange=exchange, token=symboltoken)
        print("Quote Details:", quote_details)

        order_book_list = []
        buy_trades_first = portfolio_details.buy_trades_first
        positional_portfolio = portfolio_details.positional_portfolio
        for legs in portfolio_legs:  # Iterate through each leg

            if buy_trades_first and legs.transaction_type != "BUY":
                responses.append({"message": f"Order is not placed as buy_trades_first is true and transaction_type is {legs.transaction_type}"})
                continue  # Skip the current leg and move to the next one

            from datetime import datetime

            # Retrieve the current datetime
            current_datetime = datetime.now().strftime('%d %b %H:%M:%S')

            if positional_portfolio:
                # Check if legs.start_time is a valid, non-empty string before parsing
                if legs.start_time:
                    try:
                        start_time = datetime.strptime(legs.start_time, '%d %b %H:%M:%S').strftime('%d %b %H:%M:%S')

                        # Check if the current datetime is greater than or equal to the start time
                        if current_datetime < start_time:
                            responses.append({"message": f"Order for {legs.portfolio_name} is skipped as start_time {legs.start_time} has not been reached."})
                            continue  # Skip this leg and move to the next one
                    except ValueError:
                        responses.append({"message": f"Invalid date format for start_time {legs.start_time}."})
                        continue  # Skip this leg if parsing fails
                else:
                    responses.append({"message": f"start_time for {legs.portfolio_name} is missing or empty"})
                    continue  # Skip this leg if start_time is empty
            else:
                pass


            portfolio_strategy = portfolio_details.strategy
            strategy = Strategies.query.filter_by(strategy_tag=portfolio_strategy).first()
            print("strategy:", strategy)

            if strategy:
                allowed_trades = strategy.allowed_trades 
                print("allowed_trades:", allowed_trades)
            else:
                allowed_trades = 'Both'  

            # Map side to corresponding allowed trade type
            side = legs.transaction_type
            if side == "BUY":
                trade_type = "Long"
            elif side == "SELL":
                trade_type = "Short"
            else:
                return [{"message": "Invalid transaction type"}], 500

            # Check if the trade is allowed by the strategy
            if allowed_trades == 'Both' or allowed_trades == trade_type:
                pass  
            else:
                return [{"message": f"Allowed Trade details do not match for strategy: {portfolio_strategy} | {allowed_trades}"}], 500

            expiry_date = legs.expiry_date
            print(expiry_date)
            quantity = (int(legs.quantity) * int(combined_lots))
            print("quantity:", quantity)

            transaction_type = config.flattrade_data['transaction_type'][legs.transaction_type]
            print("transaction_type: ", transaction_type)
        
            flattrade_order = config.flattrade_api[broker_user_id].place_order(buy_or_sell=transaction_type, product_type='I',
                    exchange=exchange, tradingsymbol=future_symbol,
                    quantity=quantity, discloseqty=0,price_type=order_type, price=0, trigger_price=None,
                    retention='DAY', remarks= portfolio_details.strategy)
            # tradingsymbol = ''
        
        
            print("flattrade_order:",flattrade_order)

            order_book = config.flattrade_api[broker_user_id].get_order_book()[:len(portfolio_legs)]
            # order_book_send = config.flattrade_api[broker_user_id].get_order_book()
            # holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
            # positions_info = config.flattrade_api[broker_user_id].get_positions()

            # positions_info[::-1][0]["portfolio_name"] = portfolio_name
        
            config.all_flattrade_details[broker_user_id] = {'order' : order_book}
            executed_portfolio = ExecutedPortfolio(user_id=user_id, broker_user_id=broker_user_id,
                                                transaction_type=legs.transaction_type,
                                                strategy_tag=portfolio_details.strategy,
                                                portfolio_name=portfolio_details.portfolio_name,
                                                exchange=portfolio_details.exchange)
            db.session.add(executed_portfolio)
            db.session.commit()
            from datetime import time

            def create_performance_record(portfolio_name, user_id, broker_user_id, max_pl, min_pl):
                # Check if a performance record with the same portfolio_name already exists
                existing_record = Performance.query.filter_by(portfolio_name=portfolio_name, user_id=user_id).first()
                
                if existing_record is None:
                    # If the record does not exist, create a new one
                    performance_record = Performance(
                        portfolio_name=portfolio_name,
                        user_id=user_id,
                        broker_user_id=broker_user_id,
                        max_pl=max_pl,
                        min_pl=min_pl,
                        max_pl_time=time(0, 0, 0),
                        min_pl_time=time(0, 0, 0)
                    )
                    db.session.add(performance_record)
                    db.session.commit()
                else:
                    # If the record exists, you can handle it according to your needs
                    print(f"Performance record for portfolio '{portfolio_name}' already exists.")

            # Call the function
            create_performance_record(
                portfolio_name=portfolio_name,
                user_id=user_id,
                broker_user_id=broker_user_id,
                max_pl=float('-inf'),  
                min_pl=float('+inf')
            )

        all_executed_portfolios = ExecutedPortfolio.query.all()[::-1][:2]

        for details, executed_portfolios in zip(order_book, all_executed_portfolios):
            print("\n\n\n\n\n\n")
            print(details)
            if details['status'] != 'COMPLETED':
                executed_portfolios.order_id = details['norenordno']
                executed_portfolios.trading_symbol = details['tsym']
                executed_portfolios.status = details['status']
                executed_portfolios.order_type = details['prctyp']
                executed_portfolios.symbol_token = details['token']
                executed_portfolios.duration = details['ret']
                executed_portfolios.netqty = details['qty']
            else:
                db.session.delete(executed_portfolios)
                db.session.commit()

            try:
                db.session.add(executed_portfolios)
            except:
                pass

        db.session.commit()

        response_data = {"messages": [{"message": "Order placed successfully!"}] + responses}
        return jsonify(response_data), 200

    def angelone_ltp_websocket(username):
        global sws

        # Extract tokens from the request JSON
        data = request.json
        token_dict = data.get("tokens", {})

        # Ensure token_dict is a dictionary and contains valid values
        if not isinstance(token_dict, dict) or not all(isinstance(v, list) for v in token_dict.values()):
            response = ERROR_HANDLER.flask_api_errors("angelone_ltp_websocket", "Provide valid token values grouped by exchange type")
            return jsonify({"error": response['message']}), 400

        # Mapping exchange types
        exchange_type_mapping = {
            "NSE": 1,
            "NFO": 2
        }

        # Prepare token lists based on exchange types
        new_tokens_list = []
        for exchange, tokens in token_dict.items():
            exchange_type = exchange_type_mapping.get(exchange)
            if exchange_type is not None:
                new_tokens_list.append({
                    "exchangeType": exchange_type,
                    "tokens": tokens
                })

        # Close the existing WebSocket connection, if it exists
        if sws:
            sws.close_connection()
            sws = None

        # Retrieve necessary authentication and configuration details
        AUTH_TOKEN = config.AUTH_TOKEN
        API_KEY = config.API_KEY
        CLIENT_CODE = config.CLIENT_CODE
        FEED_TOKEN = config.FEED_TOKEN

        # Initialize the WebSocket connection parameters
        correlation_id = "abc123"
        mode = 1

        # Initialize SmartWebSocketV2 instance
        sws = SmartWebSocketV2(AUTH_TOKEN, API_KEY, CLIENT_CODE, FEED_TOKEN, max_retry_attempt=100,
                            retry_strategy=2, retry_delay=30, retry_duration=300)

        # Define callback functions
        def on_data(wsapp, message):
            # Update live data in storage
            token = message.get('token')
            last_traded_price = message.get('last_traded_price')
            if token and last_traded_price:
                config.angelone_live_ltp[token] = "{:.2f}".format(last_traded_price / 100)
                print(config.angelone_live_ltp)

        def on_control_message(wsapp, message):
            print(f"Control Message: {message}")

        def on_open(wsapp):
            print("WebSocket connection opened")
            sws.subscribe(correlation_id, mode, new_tokens_list)

        def on_error(wsapp, error):
            print(f"WebSocket error: {error}")

        def on_close(wsapp):
            print("WebSocket connection closed")
            time.sleep(5)
            connect_websocket()

        # Assign the callbacks
        sws.on_open = on_open
        sws.on_data = on_data
        sws.on_error = on_error
        sws.on_close = on_close
        sws.on_control_message = on_control_message

        # Connect to WebSocket in a separate thread
        def connect_websocket():
            try:
                sws.connect()
            except Exception as e:
                print(f"Error connecting to WebSocket: {e}")
                time.sleep(5)
                connect_websocket()

        websocket_thread = threading.Thread(target=connect_websocket)
        websocket_thread.start()

        return jsonify({"message": "WebSocket connection opened and tokens updated successfully"}), 200
    
    def get_ltp(username):
        get_ltp = config.angelone_live_ltp
    
        if get_ltp:
            response_data = {"message": get_ltp}
            return jsonify(response_data), 200
        else:
            response_data = ERROR_HANDLER.flask_api_errors("get_ltp", "No LTP data present !")
            return jsonify(response_data), 500

    def fyers_websocket_ltp(username,broker_user_id):
        data = request.json
        symbol = data['symbol']
        print("symbol:", symbol)
        existing_user = User.query.filter_by(username=username).first()

        user_id = existing_user.id
        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User Does not exist")
            return jsonify(response_data), 500

        def onmessage(message):
            """
            Callback function to handle incoming messages from the FyersDataSocket WebSocket.

            Parameters:
                message (dict): The received message from the WebSocket.

            """
            print("Response:", message)
            if message["ltp"] < 10000:
                config.fyers_live_ltp[message['symbol']]=message['ltp']

        
        
            # if message['symbol']== 'NSE:SBIN-EQ':
            #     # Unsubscribe from the specified symbols and data type
            #     data_type = "SymbolUpdate"
            #     symbols_to_unsubscribe = ['NSE:SBIN-EQ']
            #     fyers.unsubscribe(symbols=symbols_to_unsubscribe, data_type=data_type)

        def onerror(message):
            """
            Callback function to handle WebSocket errors.

            Parameters:
                message (dict): The error message received from the WebSocket.


            """
            print("Error:", message)


        def onclose(message):
            """
            Callback function to handle WebSocket connection close events.
            """
            print("Connection closed:", message)


        def onopen():
            """
            Callback function to subscribe to data type and symbols upon WebSocket connection.

            """
            # Specify the data type and symbols you want to subscribe to
            data_type = "SymbolUpdate"

            # Subscribe to the specified symbols and data type
            symbols =symbol
            #symbols=symbol
            print("symbols",symbols)

        
            fyers.subscribe(symbols=symbols['Subscribe'], data_type=data_type)

            fyers.unsubscribe(symbols=symbols['Unsubscribe'], data_type=data_type)
        
            # Keep the socket running to receive real-time data
            fyers.keep_running()


        # Replace the sample access token with your actual access token obtained from Fyers
        config_access_token = config.fyers_access_token[broker_user_id]
        access_token=config_access_token
        # Create a FyersDataSocket instance with the provided parameters
        fyers = data_ws.FyersDataSocket(
            access_token=access_token,       # Access token in the format "appid:accesstoken"
            log_path="",                     # Path to save logs. Leave empty to auto-create logs in the current directory.
            litemode=True,                  # Lite mode disabled. Set to True if you want a lite response.
            write_to_file=False,              # Save response in a log file instead of printing it.
            reconnect=True,                  # Enable auto-reconnection to WebSocket on disconnection.
            on_connect=onopen,               # Callback function to subscribe to data upon connection.
            on_close=onclose,                # Callback function to handle WebSocket connection close events.
            on_error=onerror,                # Callback function to handle WebSocket errors.
            on_message=onmessage             # Callback function to handle incoming messages from the WebSocket.
        )

        # Establish a connection to the Fyers WebSocket
        fyers.connect()
        #fyers.close_connection()
    
        return "WebSocket connection initiated"
    
    def get_fyers_ltp(username):
        get_ltp = config.fyers_live_ltp
    
        if get_ltp:
            response_data = {"message": get_ltp}
            return jsonify(response_data), 200
        else:
            response_data = ERROR_HANDLER.flask_api_errors("get_fyers_ltp", "No LTP data present !")
            return jsonify(response_data), 500
       
    def fetching_portfoliolevel_positions(portfolio_name):
        send_dict = []
        list_accounts = []
        data = request.json

        broker_user_ids = data['broker_user_ids']
        broker_names = data['broker_names']

        for broker_user_id, broker_name in zip(broker_user_ids, broker_names):
            executed_portfolio = ExecutedPortfolio.query.filter_by(portfolio_name=portfolio_name, broker_user_id=broker_user_id).all()

            if broker_name == "flattrade":
                flattrade_positions = config.all_flattrade_details.get(broker_user_id, {}).get("positions", []) or []
                flattrade_running_positions = []
                flattrade_completed_positions = []

                for position in flattrade_positions:
                    if ("daysellqty" in position and "daybuyqty" not in position) or ("daysellqty" not in position and "daybuyqty" in position):
                        flattrade_running_positions.append(position)
                    elif "daysellqty" in position and "daybuyqty" in position:
                        if position["daysellqty"] == position["daybuyqty"]:
                            flattrade_completed_positions.append(position)
                        else:
                            flattrade_running_positions.append(position)

                flattrade_symbols_list = [portfolio.trading_symbol for portfolio in executed_portfolio]
                flattrade_token_list = [portfolio.symbol_token for portfolio in executed_portfolio]

                flattrade_positions_info = [
                    position for position in flattrade_running_positions
                    if position['tsym'] in flattrade_symbols_list and position['token'] in flattrade_token_list
                ]

                flattrade_completed_positions_info = [
                    position for position in flattrade_completed_positions
                    if position['tsym'] in flattrade_symbols_list and position['token'] in flattrade_token_list
                ]

                list_accounts.append({broker_user_id: {"running": flattrade_positions_info, "completed": flattrade_completed_positions_info}})


            elif broker_name == "fyers":
                fyers_positions = config.fyers_orders_book.get(broker_user_id, {}).get('netPositions', []) or []
                fyers_running_positions = []
                fyers_completed_positions = []

                for position in fyers_positions:
                    if ("sellQty" in position and "buyQty" not in position) or ("sellQty" not in position and "buyQty" in position):
                        fyers_running_positions.append(position)
                    elif "sellQty" in position and "buyQty" in position:
                        if position["sellQty"] == position["buyQty"]:
                            fyers_completed_positions.append(position)
                        else:
                            fyers_running_positions.append(position)

                fyers_symbols_list = [portfolio.order_id for portfolio in executed_portfolio]

                fyers_positions_info = [position for position in fyers_running_positions if position['id'] in fyers_symbols_list]
                fyers_completed_positions_info = [position for position in fyers_completed_positions if position['id'] in fyers_symbols_list]

                list_accounts.append({broker_user_id: {"running": fyers_positions_info, "completed": fyers_completed_positions_info}})


            elif broker_name == "angelone":
                angelone_positions = config.all_angelone_details.get(broker_user_id, {}).get('positions', {}).get('data', []) or []
                angelone_running_positions = []
                angelone_completed_positions = []

                for position in angelone_positions:
                    if ("sellqty" in position and "buyqty" not in position) or ("sellqty" not in position and "buyqty" in position):
                        angelone_running_positions.append(position)
                    elif "sellqty" in position and "buyqty" in position:
                        if position["sellqty"] == position["buyqty"]:
                            angelone_completed_positions.append(position)
                        else:
                            angelone_running_positions.append(position)

                angelone_symbols_list = [portfolio.trading_symbol for portfolio in executed_portfolio]
                angelone_token_list = [portfolio.symbol_token for portfolio in executed_portfolio]

                angelone_positions_info = [
                    position for position in angelone_running_positions
                    if position['tradingsymbol'] in angelone_symbols_list and position['symboltoken'] in angelone_token_list
                ]

                angelone_completed_positions_info = [
                    position for position in angelone_completed_positions
                    if position['tradingsymbol'] in angelone_symbols_list and position['symboltoken'] in angelone_token_list
                ]

                list_accounts.append({broker_user_id: {"running": angelone_positions_info, "completed": angelone_completed_positions_info}})


            elif broker_name == "pseudo_account":
                # Pseudo_account logic
                executed_portfolios = ExecutedPortfolio.query.filter_by(portfolio_name=portfolio_name,broker_user_id=broker_user_id).all()
                print("Existing Portfolios:", executed_portfolios)
 
                running_positions = []
                completed_positions = []
 
                for executed_portfolio in executed_portfolios:
                    position_response = {
                        'productType': executed_portfolio.order_type,
                        'exchange': executed_portfolio.exchange,
                        'symbol': executed_portfolio.trading_symbol,
                        'netQty': executed_portfolio.netqty,
                        'pl': 0,
                        'buyQty': executed_portfolio.buy_qty,
                        'buyAvg': executed_portfolio.buy_price,
                        'buyVal': float(executed_portfolio.buy_price) * int(executed_portfolio.buy_qty),
                        'sellQty': executed_portfolio.sell_qty,
                        'sellAvg': executed_portfolio.sell_price,
                        'sellVal': float(executed_portfolio.sell_price) * int(executed_portfolio.sell_qty),
                        'realized_profit': 0,
                        'unrealized_profit': 0,
                        'side': "Close" if executed_portfolio.square_off else "Open",
                        'token': executed_portfolio.symbol_token
                    }
 
                    if executed_portfolio.square_off:
                        completed_positions.append(position_response)
                    else:
                        running_positions.append(position_response)
 
                list_accounts.append({broker_user_id: {"running": running_positions, "completed": completed_positions  }})
        return jsonify({portfolio_name: list_accounts}), 200

    def square_off_portfolio_level(username,portfolio_name,broker_type,broker_user_id):
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                return jsonify(response_data), 500
            
            user_id = existing_user.id
            portfolio = Portfolio.query.filter_by(user_id=user_id).first()
            executed_portfolio_details = ExecutedPortfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name,square_off=False).all()
            if not executed_portfolio_details:
                response_data = ERROR_HANDLER.database_errors("executed_portfolio", "No open positions found.")
                return jsonify(response_data), 200
            
            if broker_type == "fyers":
                try:
                    fyers = config.OBJ_fyers[broker_user_id]
                    print(fyers)
                except:
                    response_data = ERROR_HANDLER.database_errors("executed_portfolio", executedPortfolio.broker_user_id)
                    return jsonify(response_data), 500
                if executed_portfolio_details:
                    for executedPortfolio in executed_portfolio_details:
                        strategy_tag = executedPortfolio.strategy_tag
                        portfolio_name=executedPortfolio.portfolio_name
                        transaction_type = config.fyers_data['Side'][executedPortfolio.transaction_type]
                        id = executedPortfolio.order_id
                        # fyers = config.OBJ_fyers[executedPortfolio.broker_user_id]
                        data = {
                            "orderTag": strategy_tag,
                            "segment": [10],
                            'id': id,
                            "side": [transaction_type]
                        }
                        square_off = fyers.exit_positions(data)
                        print(square_off)
                    
                        if square_off['s'] == 'ok':
                            response_data = {'message': 'Portfoliolevel Manual square off  successfully','Square_off':square_off}
                            # Query executed portfolios with the same Strategy_tag and delete them
                            # portfolios_to_delete = ExecutedPortfolio.query.filter_by(strategy_tag=strategy_tag).all()
                            # for executedportfolio in portfolios_to_delete:
                            #     #db.session.delete(executedportfolio)
                            # # Commit changes to the database
                            #     #db.session.commit()
                            executedPortfolio.square_off = True
                            if executedPortfolio.transaction_type=="BUY":
                                executedPortfolio.sell_price=square_off['tradedPrice']
                            else:
                                executedPortfolio.buy_price=square_off['tradedPrice']
                            db.session.commit()
                            fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
                            fyers_position=config.OBJ_fyers[broker_user_id].positions()
                            fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
                            config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}
                            
                            return jsonify(response_data),200
                        else:
                            response_data = ERROR_HANDLER.database_errors("executed_portfolio", 'Looks like you have no open positions.')
                            return jsonify(response_data),200
                    
                    # # Query executed portfolios with the same Strategy_tag and delete them
                    # portfolios_to_delete = ExecutedPortfolio.query.filter_by(strategy_tag=strategy_tag).all()
                    # for executedportfolio in portfolios_to_delete:
                    #     db.session.delete(executedportfolio)
                    # # Commit changes to the database
                    # db.session.commit()
                else:
                    response_data = ERROR_HANDLER.database_errors("strategies", "Strategy does not exist")
                    return jsonify(response_data), 500
            
            elif broker_type == "angelone":
                try:
                    angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                except:
                    response_data = {"message": broker_user_id},500
                    return jsonify(response_data), 500
                
                if executed_portfolio_details:
                    for executedPortfolio in executed_portfolio_details:
                        strategy_tag = executedPortfolio.strategy_tag
                        transaction_type = executedPortfolio.transaction_type
                        trading_symbol = executedPortfolio.trading_symbol
                        symbol_token = executedPortfolio.symbol_token
                        exchange = executedPortfolio.exchange
                        quantity = int(executedPortfolio.netqty)
                        product_type =  executedPortfolio.product_type
                        price = executedPortfolio.price
                        duration = executedPortfolio.duration
                        variety = executedPortfolio.variety
                        order_type=executedPortfolio.order_type
                        id = executedPortfolio.order_id
            
                        data = {
                            "variety": variety,
                            "orderTag": portfolio.strategy,
                            "tradingsymbol":trading_symbol,
                            "symboltoken":symbol_token,
                            "exchange":exchange,
                            "quantity":quantity,
                            "producttype":"INTRADAY" if product_type == "MIS" else "CARRYFORWARD",
                            "transactiontype": "SELL" if transaction_type == "BUY" else "BUY",
                            "price":price,
                            "duration":duration,
                            "ordertype": 'MARKET'
                        }

                        angelone_square_off = angelone.placeOrderFullResponse(data)
                        print(angelone_square_off)
                        # order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                
                        angelone_list = []
                        angelone_list.append(angelone_square_off['message'])
                        
                        order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                        positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                        holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                        all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                        config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}
            
                        #db.session.delete(executedPortfolio)

                    if len(list(set(angelone_list))) == 1 and list(set(angelone_list))[0] == 'SUCCESS':
                        response_data = {'message': 'Portfoliolevel Manual square off successfully','Square_off':angelone_square_off}

                        executedPortfolio.square_off = True
                        if executedPortfolio.transaction_type=="BUY":
                            executedPortfolio.sell_price=order['data'][::-1][0]['averageprice']
                        else:
                            executedPortfolio.buy_price=order['data'][::-1][0]['averageprice']
                        db.session.commit()
                        #db.session.commit()
                        return jsonify(response_data),200
                    else:
                        response_data = ERROR_HANDLER.database_errors("executed_portfolio", 'Looks like you have no open positions.')
                        return jsonify(response_data),200
            
            elif broker_type == "flattrade":
                try:
                    flattrade = config.flattrade_api[broker_user_id]
                except:
                    response_data = ERROR_HANDLER.broker_api_errors("flattrade", broker_user_id)
                    return jsonify(response_data), 500
        
                print(executed_portfolio_details)
                if executed_portfolio_details:
                    for executedPortfolio in executed_portfolio_details:
                        strategy_tag = executedPortfolio.strategy_tag
                        order_type=executedPortfolio.order_type
                        id = executedPortfolio.order_id
                        print("Order ID :",id)

                        flattrade_square_off = config.flattrade_api[broker_user_id].place_order(buy_or_sell="S" if executedPortfolio.transaction_type == "BUY" else "B", product_type="I" if executedPortfolio.product_type == "MIS" else "M",
                        exchange=executedPortfolio.exchange, tradingsymbol=executedPortfolio.trading_symbol,
                        quantity=executedPortfolio.netqty, discloseqty=0,price_type='MKT', price=0, trigger_price=None,
                        retention='DAY', remarks= executedPortfolio.strategy_tag)

                        print(flattrade_square_off)
                        order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                        holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                        positions_info = config.flattrade_api[broker_user_id].get_positions()
    
                        config.all_flattrade_details[broker_user_id] = {
                            'order': order_book_send,
                            "holdings": holdings_info,
                            "positions": positions_info
                        }
                
                        flattrade_list = []
                        flattrade_list.append(flattrade_square_off['stat'])
    
                        #db.session.delete(executedPortfolio)

                    if len(list(set(flattrade_list))) == 1 and list(set(flattrade_list))[0] == 'Ok':
                        response_data = {'message': 'Portfoliolevel Manual square off successfully','Square_off':flattrade_square_off}
                        executedPortfolio.square_off = True
                        last_rprc = order_book_send[0]['avgprc']
                        print("sell_price:",last_rprc)
                        executedPortfolio.sell_price = last_rprc
                        db.session.commit()
                        return jsonify(response_data),200
                    else:
                        response_data = ERROR_HANDLER.database_errors("executed_portfolio", 'Looks like you have no open positions.')
                        return jsonify(response_data),200
        
                else:
                    response_data = ERROR_HANDLER.database_errors("executed_portfolio", 'Looks like you have no open positions.')
                    return jsonify(response_data), 500
            
            elif broker_type == "pseudo_account":
                data = {"portfolio_name" : portfolio_name, "username" : username, "broker_type" : broker_type, "broker_user_id" : broker_user_id, "exchange" : "NFO"}

                pseudo_api = PseudoAPI(data=data)

                square_off_response = pseudo_api.square_off()

                response_data = {'message': square_off_response}
                return jsonify(response_data), 200
            
            else:
                response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", "Invalid Broker type")
                return jsonify(response_data), 400

    def flatrade_websocket(username, broker_user_id):
            # Check if the user exists
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                response = ERROR_HANDLER.database_errors("user", "User does not exist")
                response_data = {'error': response['message']}
                return jsonify(response_data), 404
    
            try:
                # Get the Flatrade API instance for the given broker user ID
                flattrade = config.flattrade_api.get(broker_user_id)
                if not flattrade:
                    raise KeyError(f"Broker with ID {broker_user_id} not found")
            except KeyError as e:
                response_data = {'error': str(e)}
                return jsonify(response_data), 404
    
            # Extract symbol token and exchange type from the request data
            data = request.json
            symbol_tokens = data.get('symbol_tokens')
            exchange_types = data.get('exchange_types')
    
            # Check if symbol token and exchange type are provided
            if not symbol_tokens or not exchange_types:
                response = ERROR_HANDLER.flask_api_errors("flatrade_websocket", "Invalid data provided")
                response_data = {'error': response['message']}
                return jsonify(response_data), 400
    
            def is_market_hours():
                now = datetime.datetime.now().time()
                market_open = datetime.time(9, 15)
                market_close = datetime.time(16, 45)
                return market_open <= now <= market_close

    
            if not is_market_hours():
                response = ERROR_HANDLER.flask_api_errors("flatrade_websocket", "It's currently not market hours")
                response_data = {'error': response['message']}
                return jsonify(response_data), 400
    
            feed_opened = False
    
            # Callback function to handle tick data updates
            def event_handler_feed_update(tick_data):
                print(f"Feed update: {tick_data}")
                print(tick_data['tk'])
                print(tick_data['lp'])
                config.flattrade_live_ltp[tick_data['tk']]=tick_data['lp']
                return jsonify(tick_data), 200
    
            # Callback function to be called when the websocket connection is opened
            def open_callback():
                nonlocal feed_opened
                feed_opened = True
                for exchange_type, symbol_token in zip(exchange_types, symbol_tokens):
                    print(f"Subscribing to {exchange_type} | {symbol_token}")
                    flattrade.subscribe([f"{exchange_type}|{symbol_token}"])
    
            # Callback function to handle order updates
            def event_handler_order_update(order_data):
                print(f"Order update: {order_data}")
    
            # Start the websocket connection
            flattrade.start_websocket(
                order_update_callback=event_handler_order_update,
                subscribe_callback=event_handler_feed_update,
                socket_open_callback=open_callback
            )
    
            # Wait for the feed to open
            while not feed_opened:
                pass
    
            return jsonify({'message': "Websocket connection established"}), 200

    def get_flattrade_ltp(username):
        # get_flattrade_ltp=config.flattrade_live_ltp
        if config.flattrade_live_ltp:  # Check if there is data in flattrade_live_ltp
            response_data = {"message": config.flattrade_live_ltp}
            return jsonify(response_data), 200
        else:
            response_data = ERROR_HANDLER.broker_api_errors("flattrade", "No LTP data present!")
            return jsonify(response_data), 500

    def fetching_strategy_tag_positions(strategy_tags_data):
       
        all_strategy_positions = {}
       
        for strategy_data in strategy_tags_data:
            strategy_tag = strategy_data['strategy_tag']
            broker_names = strategy_data['broker_names']
            broker_user_ids = strategy_data['broker_user_ids']
            list_accounts = []
 
            for broker_user_id , broker_name in zip(broker_user_ids,broker_names):
               
 
 
                if broker_name == "flattrade":
                    executed_portfolio = ExecutedPortfolio.query.filter_by(strategy_tag=strategy_tag,broker_user_id=broker_user_id).all()
                    if not executed_portfolio:
                        list_accounts.append({broker_user_id: {"running": [], "completed": []}})
                        continue
                    flattrade_positions = config.all_flattrade_details[broker_user_id]["positions"]
                    print("flattrade_positions:",flattrade_positions)
                    flattrade_running_positions = []
                    flattrade_completed_positions = []
                    for position in flattrade_positions:
                        print("position :",position)
                        if ("daysellqty" in position and "daybuyqty" not in position) or ("daysellqty" not in position and "daybuyqty" in position):
 
                            flattrade_running_positions.append(position)
                        elif "daysellqty" and "daybuyqty" in position:
                            if position["daysellqty"] == position["daybuyqty"]:
                                flattrade_completed_positions.append(position)
                            elif position["daysellqty"] != position["daybuyqty"]:
                                flattrade_running_positions.append(position)
                    print(flattrade_completed_positions)
                    flattrade_symbols_list = []
                    flattrade_token_list = []
                    for portfolio in executed_portfolio:
                        print(portfolio.trading_symbol)
                        flattrade_symbols_list.append(portfolio.trading_symbol)
                        flattrade_token_list.append(portfolio.symbol_token)
 
                    print("Symbol List :",flattrade_symbols_list)
                    print("Token List :",flattrade_token_list)
           
                    flattrade_positions_info = []
                    for position in flattrade_running_positions:
                        if position['tsym'] in flattrade_symbols_list and position['token'] in flattrade_token_list:
                            flattrade_positions_info.append(position)
 
                    flattrade_completed_positions_info = []
                    for position in flattrade_completed_positions:
                        if position['tsym'] in flattrade_symbols_list and position['token'] in flattrade_token_list:
                            flattrade_completed_positions_info.append(position)
 
                    print("flattrade_completed_positions_info",flattrade_completed_positions_info)
                    # return jsonify({portfolio_name:{broker_user_id :{"running" : flattrade_positions_info,"completed" : flattrade_completed_positions_info}}}),200
                    list_accounts.append({broker_user_id :{"running" : flattrade_positions_info,"completed" : flattrade_completed_positions_info}})
 
                elif broker_name == "fyers":
   
                    executed_portfolio = ExecutedPortfolio.query.filter_by(strategy_tag=strategy_tag,broker_user_id=broker_user_id).all()
                    print("executed_portfolio:",executed_portfolio)
                    if not executed_portfolio:
                        list_accounts.append({broker_user_id: {"running": [], "completed": []}})
                        continue
                    fyers_positions = config.fyers_orders_book[broker_user_id]['netPositions']
                    print("fyers_positions:", fyers_positions)
 
                    fyers_running_positions = []
                    fyers_completed_positions = []
                    for position in fyers_positions['netPositions']:
                        if ("sellQty" in position and "buyQty" not in position) or ("sellQty" not in position and "buyQty" in position):
 
                            fyers_running_positions.append(position)
                        elif "sellQty" and "buyQty" in position:
                            if position["sellQty"] == position["buyQty"]:
                                fyers_completed_positions.append(position)
                            elif position["sellQty"] != position["buyQty"]:
                                fyers_running_positions.append(position)
 
                    fyers_symbols_list = []
                    # fyers_token_list = []
                    for portfolio in executed_portfolio:
                        fyers_symbols_list.append(portfolio.order_id)
                        # fyers_token_list.append(portfolio.symbol_token)
               
                    fyers_positions_info = []
                    for position in fyers_running_positions:
                        if position['id'] in fyers_symbols_list:
                            fyers_positions_info.append(position)
               
                    fyers_completed_positions_info = []
                    for position in fyers_completed_positions:
                        if position['id'] in fyers_symbols_list:
                            fyers_completed_positions_info.append(position)
                   
                    # return jsonify({portfolio_name:{broker_user_id :{"running" : positions_info,"completed" : completed_positions_info}}}),200
                    list_accounts.append({broker_user_id :{"running" : fyers_positions_info,"completed" : fyers_completed_positions_info}})
 
                elif broker_name == "angelone":
                    executed_portfolio = ExecutedPortfolio.query.filter_by(strategy_tag=strategy_tag,broker_user_id=broker_user_id).all()
 
                    if not executed_portfolio:
                        list_accounts.append({broker_user_id: {"running": [], "completed": []}})
                        continue
                    angelone_positions = config.all_angelone_details[broker_user_id]['positions']
                    print("angelone_positions:", angelone_positions)
                    angelone_running_positions = []
                    angelone_completed_positions = []
                    for position in angelone_positions['data']:
                        print("Position :",position)
                        if ("sellqty" in position and "buyqty" not in position) or ("sellqty" not in position and "buyqty" in position):
                            angelone_running_positions.append(position)
                        elif "sellqty" and "buyqty" in position:
                            if position["sellqty"] == position["buyqty"]:
                                angelone_completed_positions.append(position)
                            elif position["sellqty"] != position["buyqty"]:
                                angelone_running_positions.append(position)
 
                    angelone_symbols_list = []
                    angelone_token_list = []
                    for portfolio in executed_portfolio:
                        angelone_symbols_list.append(portfolio.trading_symbol)
                        angelone_token_list.append(portfolio.symbol_token)
           
                    angelone_positions_info = []
                    for position in angelone_running_positions:
                        if position['tradingsymbol'] in angelone_symbols_list and position['symboltoken'] in angelone_token_list:
                            angelone_positions_info.append(position)
 
                    angelone_completed_positions_info = []
                    for position in angelone_completed_positions:
                        if position['tradingsymbol'] in angelone_symbols_list and position['symboltoken'] in angelone_token_list:
                            angelone_completed_positions_info.append(position)
               
                    # return jsonify({portfolio_name:{broker_user_id :{"running" : positions_info,"completed" : completed_positions_info}}}),200
                    list_accounts.append({broker_user_id :{"running" : angelone_positions_info,"completed" : angelone_completed_positions_info}})
                   
                elif broker_name == "pseudo_account":
                    executed_portfolios = ExecutedPortfolio.query.filter_by(strategy_tag=strategy_tag, broker_user_id=broker_user_id).all()
                    existing_equity_orders = ExecutedEquityOrders.query.filter_by(strategy_tag=strategy_tag, broker_user_id=broker_user_id).all()
                    
                    # Dictionary to aggregate positions by trading symbol
                    aggregated_positions = {}

                    # Process executed portfolios
                    for executed_portfolio in executed_portfolios:
                        trading_symbol = executed_portfolio.trading_symbol

                        if trading_symbol not in aggregated_positions:
                            # Initialize the aggregation entry
                            aggregated_positions[trading_symbol] = {
                                'productType': executed_portfolio.order_type,
                                'exchange': executed_portfolio.exchange,
                                'symbol': trading_symbol,
                                'netQty': int(executed_portfolio.netqty),  # Initialize netQty
                                'pl': 0,
                                'buyQty': int(executed_portfolio.buy_qty),  # Initialize buyQty
                                'buyAvg': float(executed_portfolio.buy_price),  # Initialize buyAvg
                                'buyVal': float(executed_portfolio.buy_price) * int(executed_portfolio.buy_qty),  # Initialize buyVal
                                'sellQty': int(executed_portfolio.sell_qty),  # Initialize sellQty
                                'sellAvg': float(executed_portfolio.sell_price),  # Initialize sellAvg
                                'sellVal': float(executed_portfolio.sell_price) * int(executed_portfolio.sell_qty),  # Initialize sellVal
                                'realized_profit': 0,
                                'unrealized_profit': 0,
                                'side': "Open" if int(executed_portfolio.netqty) != 0 else "Close",
                                'token': executed_portfolio.symbol_token,
                                'total_buy_price': float(executed_portfolio.buy_price) * int(executed_portfolio.buy_qty),  # Initialize total_buy_price
                                'total_sell_price': float(executed_portfolio.sell_price) * int(executed_portfolio.sell_qty)  # Initialize total_sell_price
                            }
                        else:
                            # Aggregate the values
                            agg = aggregated_positions[trading_symbol]

                            # Aggregate quantities
                            agg['netQty'] += int(executed_portfolio.netqty)
                            agg['buyQty'] += int(executed_portfolio.buy_qty)
                            agg['sellQty'] += int(executed_portfolio.sell_qty)

                            # Recalculate weighted averages for buyAvg and sellAvg
                            agg['total_buy_price'] += float(executed_portfolio.buy_price) * int(executed_portfolio.buy_qty)
                            agg['total_sell_price'] += float(executed_portfolio.sell_price) * int(executed_portfolio.sell_qty)

                            agg['buyAvg'] = agg['total_buy_price'] / agg['buyQty'] if agg['buyQty'] != 0 else 0
                            agg['sellAvg'] = agg['total_sell_price'] / agg['sellQty'] if agg['sellQty'] != 0 else 0

                            # Recalculate side
                            agg['side'] = "Open" if agg['netQty'] != 0 else "Close"



                    # Process equity orders
                    for equity_orders in existing_equity_orders:
                        trading_symbol = equity_orders.trading_symbol

                        if trading_symbol not in aggregated_positions:
                            # Initialize the aggregation entry
                            aggregated_positions[trading_symbol] = {
                                'productType': equity_orders.product_type,
                                'exchange': "NSE",
                                'symbol': trading_symbol,
                                'netQty': 0,
                                'pl': 0,
                                'buyQty': int(equity_orders.quantity) if equity_orders.transaction_type == "BUY" else 0,
                                'buyAvg': float(equity_orders.buy_price) if equity_orders.transaction_type == "BUY" else 0.0,
                                'buyVal': 0.0,
                                'sellQty': int(equity_orders.quantity) if equity_orders.transaction_type == "SELL" or equity_orders.square_off else 0,
                                'sellAvg': float(equity_orders.sell_price) if equity_orders.transaction_type == "SELL" or equity_orders.square_off else 0.0,
                                'sellVal': 0.0,
                                'realized_profit': 0,
                                'unrealized_profit': 0,
                                'side': "Close" if equity_orders.square_off else "Open",
                                'token': equity_orders.symbol_token,
                                'total_buy_price': float(equity_orders.buy_price) * int(equity_orders.quantity) if equity_orders.transaction_type == "BUY" else 0.0
                            }
                        else:
                            # Aggregate the values
                            agg = aggregated_positions[trading_symbol]

                            if equity_orders.transaction_type == "BUY":
                                agg['buyQty'] += int(equity_orders.quantity)
                                agg['total_buy_price'] += float(equity_orders.buy_price) * int(equity_orders.quantity)
                                agg['netQty'] += int(equity_orders.quantity)

                            if equity_orders.transaction_type == "SELL" or equity_orders.square_off:
                                agg['sellQty'] += int(equity_orders.quantity)
                                agg['sellAvg'] = float(equity_orders.sell_price)  # Update sellAvg to reflect the latest sell
                                agg['netQty'] -= int(equity_orders.quantity)

                            agg['side'] = "Close" if equity_orders.square_off else "Open"

                    # Finalize the aggregation (calculate average buy price)
                    running_positions = []
                    completed_positions = []

                    for trading_symbol, agg in aggregated_positions.items():
                        if agg['buyQty'] > 0:
                            agg['buyAvg'] = agg['total_buy_price'] / agg['buyQty']
                        del agg['total_buy_price']  # Remove the helper field

                        if agg['side'] == "Close":
                            completed_positions.append(agg)
                        else:
                            running_positions.append(agg)

                    list_accounts.append({
                        broker_user_id: {
                            "running": running_positions,
                            "completed": completed_positions
                        }
                    })


                all_strategy_positions[strategy_tag] = list_accounts
 
        return jsonify(all_strategy_positions), 200

    def websocket_ltp(username,broker_user_id):
            data = request.json        
            symbols = data['symbol']
    
            def fetch_fyers_data():
                fyers_csv_url = "https://public.fyers.in/sym_details/NSE_FO.csv"
                try:
                    with urllib.request.urlopen(fyers_csv_url) as response:
                        fyers_csv_data = response.read().decode('utf-8')
                    df_fyers = pd.read_csv(io.StringIO(fyers_csv_data))
                    df_fyers.columns = ['Fytoken', 'Symbol Details', 'Exchange Instrument type', 'Minimum lot size', 'Tick size',
                                        'Empty', 'ISIN', 'Trading Session', 'Last update date', 'Expiry date', 'Symbol ticker',
                                        'Exchange', 'Segment', 'Scrip code', 'Underlying scrip code', 'Strike price', 'Option type',
                                        'Underlying FyToken', 'EMPTY', 's1', 's2']
                    return df_fyers
                except Exception as e:
                    return jsonify({"message" : f"Error fetching or processing CSV data: {e}"})
        
            def convert_symbol(symbol):
                if symbol.endswith("CE") or symbol.endswith("PE"):
                    month_map = {"jan": "1", "feb": "2", "mar": "3", "apr": "4", "may": "5",
                                "jun": "6", "jul": "7", "aug": "8", "sep": "9", "oct": "10",
                                "nov": "11", "dec": "12"}
        
                    match = re.search(r"^(?P<index>\w+)(?P<expiry_date>\d{2})(?P<month>\w{3})(?P<year>\d{2})(?P<strike_price>\d+)(?P<option_type>PE|CE)", symbol, flags=re.IGNORECASE)
        
                    if not match:
                        return jsonify({"message" : "No match Found !"})
        
                    month_number = month_map.get(match.group('month').lower())
        
                    if not month_number:
                        return jsonify({"message" : "No month number !"})
        
                    fyers_symbol = match.group('index') + match.group('year') + month_number + match.group('expiry_date') + match.group('strike_price') + match.group('option_type')
                    fyers_symbol = "NSE:" + fyers_symbol
            
                    return fyers_symbol
                else:
                    match = re.search(r"^(?P<index>\w+)(?P<expiry_date>\d{2})(?P<month>\w{3})(?P<year>\d{2})(?P<option_type>FUT)", symbol, flags=re.IGNORECASE)
                    fyers_symbol = match.group('index') + match.group('year') + match.group('month') + match.group('option_type')
                    fyers_symbol = "NSE:" + fyers_symbol
        
                    return fyers_symbol
        
            def check_symbol_in_fyers(symbol, df_fyers):
                return df_fyers[df_fyers['Expiry date'] == symbol]
        
            def process_broker_symbol(symbol):
                df_fyers = fetch_fyers_data()
                if df_fyers is None:
                    return jsonify({"message" : "Error processing symbol."})
        
                fyers_symbol = convert_symbol(symbol)
        
                if fyers_symbol:
                    fyers_symbol_data = check_symbol_in_fyers(fyers_symbol, df_fyers)
                    if not fyers_symbol_data.empty:
                        return fyers_symbol
                    else:
                        match = re.search(r"^(?P<index>\w+)(?P<expiry_date>\d{2})(?P<month>\w{3})(?P<year>\d{2})(?P<strike_price>\d+)(?P<option_type>PE|CE)", symbol, flags=re.IGNORECASE)
                        if match:
                            alternative_fyers_symbol = match.group('index') + match.group('year') + match.group('month') + match.group('strike_price') + match.group('option_type')
                            alternative_fyers_symbol = "NSE:" + alternative_fyers_symbol
                            alternative_fyers_symbol_data = check_symbol_in_fyers(alternative_fyers_symbol, df_fyers)
                            if not alternative_fyers_symbol_data.empty:
                                return alternative_fyers_symbol
                            else:
                                return jsonify({"message" : "Fyers symbol not available in both formats."})
                        else:
                            return jsonify({"message" : "Invalid symbol format."})
                else:
                    return jsonify({"message" : "Unable to convert symbol."})
        
            def process_symbol(symbol):
                if symbol.endswith("CE") or symbol.endswith("PE") or symbol.endswith("FUT"):
                    result = process_broker_symbol(symbol)
                    return result
                else:
                    flattrade_symbol = symbol
                    pattern_option = r"([A-Z]+)(\d{2}[A-Z]{3}\d{2})([CP])(\d+)"
                    pattern_futures = r"([A-Z]+)(\d{2}[A-Z]{3}\d{2})F"
            
                    match_option = re.search(pattern_option, flattrade_symbol)
                    if match_option:
                        index_name = match_option.group(1)
                        expiry_date = match_option.group(2)
                        option_type = match_option.group(3)
                        strike_price = match_option.group(4)
                        option_type = option_type + 'E'
                        angleone_symbol = f"{index_name}{expiry_date}{strike_price}{option_type}"
                        result = process_broker_symbol(angleone_symbol)
                        return result
                    else:
                        match_futures = re.search(pattern_futures, flattrade_symbol)
                        if match_futures:
                            index_name = match_futures.group(1)
                            expiry_date = match_futures.group(2)
                            angleone_symbol = f"{index_name}{expiry_date}FUT"
                            result = process_broker_symbol(angleone_symbol)
                            return result
                        else:
                            return jsonify({"message":"Invalid flattrade symbol format"})
        
            symbols_list = {}
            fyers_pattern = ":"
            for symbol in symbols:
                if fyers_pattern in symbol:
                    symbols_list[symbol] = symbol
                else:
                    symbols_list[process_symbol(symbol)] = symbol
    
            print("Symbol List :",list(symbols_list.keys()))

            def onmessage(message):
                print("Response:", message)
                if message["ltp"] < 10000:
                    config.all_lpt_data[symbols_list[message['symbol']]]=message['ltp']
    
    
            def onerror(message):
                print("Error:", message)
    
    
            def onclose(message):
                print("Connection closed:", message)
    
    
            def onopen():
                data_type = "SymbolUpdate"
                fyers.subscribe(symbols=list(symbols_list.keys()), data_type=data_type)
                fyers.keep_running()
    
    
            # Replace the sample access token with your actual access token obtained from Fyers
            config_access_token = config.fyers_access_token[broker_user_id]
            access_token=config_access_token
            # Create a FyersDataSocket instance with the provided parameters
            fyers = data_ws.FyersDataSocket(
                access_token=access_token,       # Access token in the format "appid:accesstoken"
                log_path="",                     # Path to save logs. Leave empty to auto-create logs in the current directory.
                litemode=True,                  # Lite mode disabled. Set to True if you want a lite response.
                write_to_file=False,              # Save response in a log file instead of printing it.
                reconnect=True,                  # Enable auto-reconnection to WebSocket on disconnection.
                on_connect=onopen,               # Callback function to subscribe to data upon connection.
                on_close=onclose,                # Callback function to handle WebSocket connection close events.
                on_error=onerror,                # Callback function to handle WebSocket errors.
                on_message=onmessage             # Callback function to handle incoming messages from the WebSocket.
            )
    
            fyers.connect()
    
            return "WebSocket connection initiated"

    def all_ltp_data():
            get_ltp = config.all_lpt_data
    
            if get_ltp:
                response_data = {"message": get_ltp}
                return jsonify(response_data), 200
            else:
                response_data = ERROR_HANDLER.flask_api_errors("all_ltp_data", "No LTP data present !")
                return jsonify(response_data), 500

    def update_portfolio_leg_profit_trail_values(username,id):
        data = request.json  # Assuming JSON data is sent with the request
        
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
            return jsonify(response_data), 404

        executed_portfolio = ExecutedPortfolio.query.filter_by(id=id).first()
        print("executed_portfolio_id:",executed_portfolio)
        if not executed_portfolio:
            response_data = ERROR_HANDLER.database_errors("portfolio", 'Portfolio leg with given ID not found')
            return jsonify(response_data), 404

        # Query current reached_profit and locked_min_profit values
        reached_profit = data.get('reached_profit', executed_portfolio.reached_profit)
        locked_min_profit = data.get('locked_min_profit', executed_portfolio.locked_min_profit)
        trailed_sl = data.get('trailed_sl', executed_portfolio.trailed_sl)

        # Update the reached_profit and locked_min_profit values
        executed_portfolio.reached_profit = reached_profit
        executed_portfolio.locked_min_profit = locked_min_profit
        executed_portfolio.trailed_sl = trailed_sl

        db.session.commit()

        return jsonify({'message': 'Portfolio profit locking updated successfully'}), 200
    
    def square_off_portfolio_leg_level(username, portfolio_name, broker_type, broker_user_id, portfolio_leg_id):
            try:
                # Fetch existing user
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                    return jsonify(response_data), 404
            
                user_id = existing_user.id
    
                # Fetch the specific executed portfolio leg
                executed_portfolio_leg = ExecutedPortfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name, portfolio_leg_id=portfolio_leg_id).first()
                print("executed_portfolio_leg:", executed_portfolio_leg)
                if not executed_portfolio_leg:
                    response_data = ERROR_HANDLER.database_errors("executed_portfolio", "No open positions found for the specified portfolio leg.")
                    return jsonify(response_data), 200
            
                try:
                    if broker_type == "flattrade":
                        try:
                            flattrade = config.flattrade_api[broker_user_id]
                        except KeyError:
                            response_data = ERROR_HANDLER.broker_api_errors("flattrade", "Broker user ID not found")
                            return jsonify(response_data), 500
    
                        if not executed_portfolio_leg.square_off:
                            flattrade_square_off = flattrade.place_order(
                                buy_or_sell="S" if executed_portfolio_leg.transaction_type == "BUY" else "B",
                                product_type="I" if executed_portfolio_leg.product_type == "MIS" else "M",
                                exchange=executed_portfolio_leg.exchange,
                                tradingsymbol=executed_portfolio_leg.trading_symbol,
                                quantity=executed_portfolio_leg.netqty,
                                discloseqty=0,
                                price_type='MKT',
                                price=0,
                                trigger_price=None,
                                retention='DAY',
                                remarks=executed_portfolio_leg.strategy_tag
                            )
                        
                            order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                            positions_info = config.flattrade_api[broker_user_id].get_positions()
                            holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                            print("\n\n\n\n")
                            print("order_book_send:", order_book_send)
                            config.all_flattrade_details[broker_user_id] = {
                                'order': order_book_send,
                                "holdings": holdings_info,
                                "positions": positions_info
                            }
    
                            if flattrade_square_off['stat'] == 'Ok':
                                executed_portfolio_leg.square_off = True
                                last_avgprc = order_book_send[0]['avgprc']
                                print("sell_price:",last_avgprc)
                                executed_portfolio_leg.sell_price = last_avgprc
                                db.session.commit()
                                response_data = {'message': 'Portfolio leg manual square off successfully', 'Square_off': flattrade_square_off}
                                return jsonify(response_data), 200
                            else:
                                response_data = {'message': 'Square off failed. No open positions found.'}
                                return jsonify(response_data), 200
    
                    elif broker_type == "fyers":
                        try:
                            fyers = config.OBJ_fyers[broker_user_id]
                            print(fyers)
                        except KeyError:
                            response_data = ERROR_HANDLER.broker_api_errors("fyers", "Broker user ID not found")
                            return jsonify(response_data), 500
                    
                        if not executed_portfolio_leg.square_off:
                            data = {
                                "orderTag": executed_portfolio_leg.strategy_tag,
                                "segment": [10],
                                'id': executed_portfolio_leg.order_id,
                                "side": [config.fyers_data['Side'][executed_portfolio_leg.transaction_type]]
                            }
                            square_off = fyers.exit_positions(data)
                            print(square_off)
                        
                            fyers_order = config.OBJ_fyers[broker_user_id].orderbook()
                            fyers_position = config.OBJ_fyers[broker_user_id].positions()
                            fyers_holdings = config.OBJ_fyers[broker_user_id].holdings()
                            config.fyers_orders_book[broker_user_id] = {"orderbook": fyers_order, "positions": fyers_position, "holdings": fyers_holdings}
    
                            if square_off['s'] == 'ok':
                                executed_portfolio_leg.square_off = True
                                if executed_portfolio_leg.transaction_type=="BUY":
                                   executed_portfolio_leg.sell_price=square_off['tradedPrice']
                                else:
                                   executed_portfolio_leg.buy_price=square_off['tradedPrice']
                                db.session.commit()
                                response_data = {'message': 'Portfolio leg manual square off successfully', 'Square_off': square_off}
                                return jsonify(response_data), 200
                            else:
                                response_data = ERROR_HANDLER.flask_api_errors("square_off_portfolio_leg_level", 'Square off failed. No open positions found.')
                                return jsonify(response_data), 200
    
                    elif broker_type == "angelone":
                            try:
                                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                            except KeyError:
                                response_data = ERROR_HANDLER.broker_api_errors("angelone", "Broker user ID not found")
                                return jsonify(response_data), 500
                            if not executed_portfolio_leg.square_off:
                                data = {
                                    "variety": executed_portfolio_leg.variety,
                                    "orderTag": executed_portfolio_leg.strategy_tag,
                                    "tradingsymbol": executed_portfolio_leg.trading_symbol,
                                    "symboltoken": executed_portfolio_leg.symbol_token,
                                    "exchange": executed_portfolio_leg.exchange,
                                    "quantity": int(executed_portfolio_leg.netqty),
                                    "producttype": "INTRADAY" if executed_portfolio_leg.product_type == "MIS" else "CARRYFORWARD",
                                    "transactiontype": "SELL" if executed_portfolio_leg.transaction_type == "BUY" else "BUY",
                                    "price": executed_portfolio_leg.price,
                                    "duration": executed_portfolio_leg.duration,
                                    "ordertype": "MARKET"
                                }
                                angelone_square_off = angelone.placeOrderFullResponse(data)
                                print(angelone_square_off)
                                order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                                positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                                holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                                all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                                config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions, "holdings": holdings, "all_holdings": all_holdings}
                                if angelone_square_off['message'] == 'SUCCESS':
                                    executed_portfolio_leg.square_off = True
                                    if executed_portfolio_leg.transaction_type=="BUY":
                                        executed_portfolio_leg.sell_price=order['data'][::-1][0]['averageprice']
                                    else:
                                        executed_portfolio_leg.buy_price=order['data'][::-1][0]['averageprice']
                                    db.session.commit()
                                    response_data = {'message': 'Portfolio leg manual square off successfully', 'Square_off': angelone_square_off}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = ERROR_HANDLER.database_errors("executed_portfolio", 'Square off failed. No open positions found.')
                                    return jsonify(response_data), 200
                
                    elif broker_type == "pseudo_account":
                        data = {"portfolio_name" : portfolio_name, "username" : username, "broker_type" : broker_type, "broker_user_id" : broker_user_id, "portfolio_leg_id" : portfolio_leg_id, "exchange" : "NFO"}

                        pseudo_api = PseudoAPI(data=data)

                        square_off_response = pseudo_api.square_off()

                        response_data = {'message': square_off_response}
                        return jsonify(response_data), 200
                
                except KeyError:
                    response_data = ERROR_HANDLER.flask_api_errors("square_off_portfolio_leg_level", "Broker user ID not found.")
                    return jsonify(response_data), 500
                
            except KeyError:
                response_data = ERROR_HANDLER.flask_api_errors("square_off_portfolio_leg_level", "Broker user ID not found.")
                return jsonify(response_data), 500
   
    def get_theta_gamma_vega_values(username):
            
            data = request.json

            iv_list = []
            for iv_data in data:
                index_symbol = iv_data['index_symbol']
                expiry_date = iv_data['expiry_date']
                ltp = iv_data['ltp']
                strike = iv_data['strike']
                strike_price = int(ltp) + int(strike[3:])

                existing_user = User.query.filter_by(username=username).first()

                if not existing_user:
                    response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                    return jsonify(response_data), 404

                # Correct URL without duplicating path
                conn = http.client.HTTPSConnection("apiconnect.angelbroking.com")

                # Correct payload and headers
                payload = json.dumps({
                    "name": index_symbol,  # Underlying stock name
                    "expirydate": expiry_date  # Expiry date of the options
                })

                headers = {
                    'X-PrivateKey': 'zG8s9Lns',
                    'Accept': 'application/json',
                    'X-SourceID': 'WEB',
                    'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
                    'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
                    'X-MACAddress': 'MAC_ADDRESS',
                    'X-UserType': 'USER',
                    'Authorization': f'{config.AUTH_TOKEN}',
                    'Accept': 'application/json',
                    'X-SourceID': 'WEB',
                    'Content-Type': 'application/json'
                }
                
                print("Header :",headers["Authorization"])

                # Correct request path
                conn.request("POST", "/rest/secure/angelbroking/marketData/v1/optionGreek", payload, headers)
                res = conn.getresponse()
                data = res.read()
                
                # Decode the response and parse the JSON
                response_json = json.loads(data.decode("utf-8"))

                # Specific strike price to search for
                specific_strike_price = str(strike_price) + ".000000"
                
                # Initialize variables to hold the required values
                delta = gamma = theta = vega = implied_volatility = None
                
                # Iterate through the JSON response to find the specific strike price
                for option in response_json.get('data', []):
                    if option.get('strikePrice') == specific_strike_price and option.get('optionType') == "PE":
                        delta = option.get('delta')
                        gamma = option.get('gamma')
                        theta = option.get('theta')
                        vega = option.get('vega')
                        implied_volatility = option.get('impliedVolatility')
                        break
                
                if delta is not None:
                    iv_list.append({'Delta': delta,"Gamma" : gamma, "Theta" : theta, "Vega" : vega, "IV" : implied_volatility})
                else:
                    print(f"Error: Data for strike price {specific_strike_price} not found")
                
                conn.close()
            
            if iv_list:
                response_data = {"message" : "Data Fetched Successfully !","Data" : iv_list}
                return jsonify(response_data), 200
            else:
                response_data = ERROR_HANDLER.flask_api_errors("get_theta_gamma_vega_values", "Unable to fetch the Data !")
                return jsonify(response_data), 200

    def add_portfolio_performance(username):
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
            return jsonify(response_data), 404  # Return 404 if user not found
        
        data = request.json
        
        if not data:
            response_data = ERROR_HANDLER.flask_api_errors("add_portfolio_performance", 'No data provided')
            return jsonify(response_data), 400
        
        portfolio_name = data.get('portfolio_name')
        broker_data = data.get('brokers')
        
        if not portfolio_name or not broker_data:
            response_data = ERROR_HANDLER.flask_api_errors("add_portfolio_performance", 'Missing required fields')
            return jsonify(response_data), 400
        
        for broker_user_id, metrics in broker_data.items():
            max_pl = metrics.get('maxPL')
            min_pl = metrics.get('minPL')
            max_pl_time = metrics.get('maxPLTime')
            min_pl_time = metrics.get('minPLTime')
            
            if max_pl is None or min_pl is None or max_pl_time is None or min_pl_time is None:
                response_data = ERROR_HANDLER.flask_api_errors("add_portfolio_performance", 'Invalid data format')
                return jsonify(response_data), 400
            
            # Check if there's an existing performance record for this portfolio and broker
            existing_performance = Performance.query.filter_by(
                portfolio_name=portfolio_name,
                broker_user_id=broker_user_id,
                user_id=existing_user.id
            ).first()
            
            if existing_performance:
                # Update existing record
                existing_performance.max_pl = max_pl
                existing_performance.min_pl = min_pl
                existing_performance.max_pl_time = str(max_pl_time)  
                existing_performance.min_pl_time = str(min_pl_time) 
            else:
                # Create new performance record
                new_performance = Performance(
                    portfolio_name=portfolio_name,
                    broker_user_id=broker_user_id,
                    max_pl=max_pl,
                    min_pl=min_pl,
                    max_pl_time=str(max_pl_time),  
                    min_pl_time=str(min_pl_time), 
                    user_id=existing_user.id
                )
                db.session.add(new_performance)
        
        try:
            db.session.commit()
            
            # Fetch updated portfolio performance data after commit
            updated_performances = Performance.query.filter_by(user_id=existing_user.id).all()
            
            # Prepare JSON response with updated performance data
            performance_data = []
            for performance in updated_performances:
                performance_data.append({
                    'portfolio_name': performance.portfolio_name,
                    'broker_user_id': performance.broker_user_id,
                    'max_pl': performance.max_pl,
                    'min_pl': performance.min_pl,
                    'max_pl_time': performance.max_pl_time.strftime('%H:%M:%S'),  
                    'min_pl_time': performance.min_pl_time.strftime('%H:%M:%S')   
                })
            
            return jsonify({
                'message': 'Portfolio performance added/updated successfully'
                # 'performance_data': performance_data
            }), 201
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Failed to add/update portfolio performance: {str(e)}'}), 500
        
    def get_portfolio_performance(username):
        try:
            # Query the user by username
            user = User.query.filter_by(username=username).first()
            if not user:
                response_data = ERROR_HANDLER.database_errors("user", 'User not found')
                return jsonify(response_data), 404
            
            # Query all performance records for the user
            performances = Performance.query.filter_by(user_id=user.id).all()
            
            # Prepare data structure for JSON response
            portfolio_data = {}
            
            # Iterate through performances
            for performance in performances:
                portfolio_name = performance.portfolio_name
                broker_user_id = performance.broker_user_id
                
                # Initialize portfolio if not already in dictionary
                if portfolio_name not in portfolio_data:
                    portfolio_data[portfolio_name] = {}
                
                # Initialize broker dictionary if not already in portfolio
                # if 'brokers' not in portfolio_data[portfolio_name]:
                #     portfolio_data[portfolio_name]['brokers'] = {}
                
                # Populate broker information
                portfolio_data[portfolio_name][broker_user_id] = {
                    'maxPL': performance.max_pl,
                    'minPL': performance.min_pl,
                    'maxPLTime': performance.max_pl_time.strftime('%H:%M:%S'),
                    'minPLTime': performance.min_pl_time.strftime('%H:%M:%S')
                }
            
            # Return JSON response
            return jsonify(portfolio_data), 200
        
        except Exception as e:
            return jsonify({'message': f'Failed to fetch portfolio performance: {str(e)}'}), 500

    def latest_details(username):
            data = request.json
    
            broker_user_id = data['broker_user_id']
            existing_user = User.query.filter_by(username=username).first()
    
            if not existing_user:
                response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                return jsonify(response_data), 404
            
            if data["broker_name"] == "angelone":
                order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}
    
            elif data['broker_name'] == "flattrade":
                positions_info = config.flattrade_api[broker_user_id].get_positions()
                holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                order_book_send = config.flattrade_api[broker_user_id].get_order_book()
    
                config.all_flattrade_details[broker_user_id] = {
                    'orderbook': order_book_send,
                    'holdings': holdings_info,
                    'positions': positions_info
                }
            
            elif data['broker_name'] == "fyers":
                fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
                fyers_position=config.OBJ_fyers[broker_user_id].positions()
                fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
                config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}
    
            response_data = {'message': f"Latest order book positions and holdings updated successfully for {broker_user_id} account !!"}
            return jsonify(response_data), 200


    def delete_all_executed_portfolios():
        # DATABASE_URI = 'postgresql://postgres:Makonis@localhost:5432/algo_project'
        from app.database.connection import Config

        DATABASE_URI = Config.SQLALCHEMY_DATABASE_URI
        
        # Create engine and session
        engine = create_engine(DATABASE_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:

            portfolio_names = session.query(ExecutedPortfolio.portfolio_name).distinct().all()
            portfolio_names = [portfolio[0] for portfolio in portfolio_names]

            for portfolio_name in portfolio_names:
                # Check if any row with square_off=False exists for this portfolio_name
                has_unsquared_off = session.query(ExecutedPortfolio).filter_by(
                    portfolio_name=portfolio_name, square_off=False
                ).count() > 0

                # Update Performance table based on presence of square_off=False in ExecutedPortfolio
                session.query(Performance).filter_by(portfolio_name=portfolio_name).update({
                    Performance.square_off: not has_unsquared_off
                }, synchronize_session=False)

            # Step 2: Delete from ExecutedPortfolio based on conditions
            session.query(ExecutedPortfolio).filter(
                ~((ExecutedPortfolio.product_type == 'NORMAL') & (ExecutedPortfolio.square_off == False))
            ).delete(synchronize_session=False)
            

            session.query(Performance).filter(
                ~((Performance.product_type != 'NORMAL') & (Performance.square_off != True))
            ).delete(synchronize_session=False)

            session.query(ExecutedEquityOrders).filter(
                ~((ExecutedEquityOrders.product_type != 'NRML') & (ExecutedEquityOrders.square_off != True))
            ).delete(synchronize_session=False)
            
     
            # session.query(ExecutedEquityOrders).delete()
            reset_profits(session)
            
            # Commit the session after all updates and deletes
            session.commit()
            print("Records updated and deleted successfully in ExecutedPortfolio and Performance.")
        
        except Exception as e:
            # Rollback in case of error
            session.rollback()
            print(f"Error occurred: {e}")
        
        finally:
            # Close the session
            session.close()

    # Schedule the job to run every day at 23:59
    schedule.every().day.at("23:59").do(delete_all_executed_portfolios)

    
            
    def pseudo_placeorder(username, portfolio_name, broker_user_id):
        input_data = request.json
 
        underlying_prices = input_data.get('underlying_prices', {})
 
        existing_user = User.query.filter_by(username=username).first()
 
        if existing_user is None:
            response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
            return jsonify(response_data), 404
 
        data = {
            "portfolio_name": portfolio_name,
            "broker_user_id": broker_user_id,
            "username": username,
            "qtp_lots": input_data.get('qtp_lots'),
            "underlying_prices": underlying_prices,
            "exchange" : "NFO"
        }
 
        pseudo_api = PseudoAPI(data)
 
        orderplace_response = pseudo_api.place_order()
 
        response_data = {"messages": orderplace_response}
        return jsonify(response_data), 200

    def pseudo_user_manual_square_off(username,broker_user_id):
        data = {"username" : username, "broker_user_id" : broker_user_id, "exchange" : "NFO"}

        pseudo_api = PseudoAPI(data=data)

        square_off_response = pseudo_api.square_off()

        response_data = {'message': square_off_response}
        return jsonify(response_data), 200

    def pseudo_manual_square_off_strategy_level(username, strategy_tag ,broker_user_id):
        data = {"strategy_tag" : strategy_tag, "username" : username, "broker_user_id" : broker_user_id, "exchange" : "NFO"}

        pseudo_api = PseudoAPI(data=data)

        square_off_response = pseudo_api.square_off()

        response_data = {'message': square_off_response}
        return jsonify(response_data), 200

def reset_profits(session):
    # Reset profits in BrokerCredentials
    session.query(BrokerCredentials).update({
        BrokerCredentials.reached_profit: 0,
        BrokerCredentials.locked_min_profit: 0,
        BrokerCredentials.utilized_margin: 0
        # BrokerCredentials.available_balance: 1000000
    })
    

    session.query(BrokerCredentials).filter(
        BrokerCredentials.broker == "pseudo_account"
    ).update({
        BrokerCredentials.available_balance: 1000000
    })
    print("All records in BrokerCredentials have been reset to 0.")
    
    # Reset profits in Strategies
    session.query(Strategies).update({
        Strategies.reached_profit: 0,
        Strategies.locked_min_profit: 0
    })

    session.query(ExecutedPortfolio).update({
        ExecutedEquityOrders.margin_req: 0
    })

    session.query(ExecutedEquityOrders).update({
        ExecutedEquityOrders.margin_req: 0
    })
    print("All records in Strategies have been reset to 0.")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

 
fyers_websocket_ltp_blueprint = Blueprint('fyers_websocket_ltp_blueprint', __name__)
@fyers_websocket_ltp_blueprint.route(MULTILEG_ROUTES.get_routes("fyers_websocket_ltp_blueprint"), methods=['POST'])
def fyers_websocket_ltp(username,broker_user_id):
    fyers_websocket_ltp_response = Multileg.fyers_websocket_ltp(username=username,broker_user_id=broker_user_id)
    return fyers_websocket_ltp_response
 
get_fyers_ltp_blueprint = Blueprint('get_fyers_ltp_blueprint', __name__)
@get_fyers_ltp_blueprint.route(MULTILEG_ROUTES.get_routes("get_fyers_ltp_blueprint"), methods=['POST'])
def get_fyers_ltp(username):
    get_fyers_ltp_response, status_code = Multileg.get_fyers_ltp(username)
    return get_fyers_ltp_response, status_code

# Flask Blueprints for all the Multileg functions
angelone_placeorder_blueprint = Blueprint('angelone_placeorder_blueprint', __name__)
@angelone_placeorder_blueprint.route(MULTILEG_ROUTES.get_routes("angelone_placeorder_blueprint"), methods=['POST'])
def angelone_options_place_order(username,portfolio_name,broker_user_id):
    angelone_options_place_order_response, status_code = Multileg.angelone_placeorder(username=username,portfolio_name=portfolio_name,broker_user_id=broker_user_id)
    return angelone_options_place_order_response, status_code

store_portfolio_blueprint = Blueprint('store_portfolio', __name__)
@store_portfolio_blueprint.route(MULTILEG_ROUTES.get_routes("store_portfolio_blueprint"), methods=['POST'])
def store_portfolio(username):
    store_portfolio_response, status_code = Multileg.Store_portfolio_details(username=username)
    return store_portfolio_response, status_code

get_portfolio_blueprint = Blueprint('get_portfolio', __name__)
@get_portfolio_blueprint.route(MULTILEG_ROUTES.get_routes("get_portfolio_blueprint"), methods=['GET'])
def get_portfolio(username):
    get_portfolio_response, status_code = Multileg.Get_portfolio_details(username=username)
    return get_portfolio_response, status_code

delete_portfolio_blueprint = Blueprint('delete_portfolio', __name__)
@delete_portfolio_blueprint.route(MULTILEG_ROUTES.get_routes("delete_portfolio_blueprint"), methods=['DELETE'])
def delete_portfolio(username,portfolio_name):
    delete_portfolio_response, status_code = Multileg.Delete_portfolio_details(username=username,portfolio_name=portfolio_name)
    return delete_portfolio_response, status_code


fyers_websocket_blueprint = Blueprint('fyers_websocket_blueprint', __name__)
@fyers_websocket_blueprint.route(MULTILEG_ROUTES.get_routes("fyers_websocket_blueprint"), methods=['POST'])
def fyers_websocket():
    fyers_websocket_response, status_code = Multileg.Fyers_websocket()
    return fyers_websocket_response, status_code


fyers_place_order_blueprint = Blueprint('fyers_place_order_blueprint', __name__)
@fyers_place_order_blueprint.route(MULTILEG_ROUTES.get_routes("fyers_place_order_blueprint"), methods=['POST'])
def fyers_place_order(username,portfolio_name,broker_user_id):
    fyers_place_order_response, status_code = Multileg.fyers_place_order(username=username, portfolio_name=portfolio_name,broker_user_id=broker_user_id)
    return fyers_place_order_response, status_code

edit_portfolio_blueprint = Blueprint('edit_portfolio_blueprint', __name__)
@edit_portfolio_blueprint.route(MULTILEG_ROUTES.get_routes("edit_portfolio_blueprint"), methods=['POST'])
def edit_portfolio(username, portfolio_name):
    edit_portfolio_response, status_code = Multileg.edit_portfolio_details(username=username, portfolio_name=portfolio_name)
    return edit_portfolio_response, status_code

get_price_details_blueprint = Blueprint('get_price_details_blueprint', __name__)
@get_price_details_blueprint.route(MULTILEG_ROUTES.get_routes("get_price_details_blueprint"), methods=['POST'])
def get_price_details(username):
    get_price_details_response = Multileg.get_price_details(username=username)
    return get_price_details_response

delete_portfolio_legs_blueprint = Blueprint('delete_portfolio_legs_blueprint', __name__)
@delete_portfolio_legs_blueprint.route(MULTILEG_ROUTES.get_routes("delete_portfolio_legs_blueprint"), methods=['POST'])
def delete_portfolio_legs(username,portfolio_legsid):
    delete_portfolio_legs_response = Multileg.Delete_portfolio_legs(username=username,portfolio_legsid=portfolio_legsid)
    return delete_portfolio_legs_response

get_expiry_list_blueprint = Blueprint('get_expiry_list_blueprint', __name__)
@get_expiry_list_blueprint.route(MULTILEG_ROUTES.get_routes("get_expiry_list_blueprint"), methods=['POST'])
def get_expiry_list(username):
    data = request.json
    symbols = data.get('symbols', [])
    get_expiry_list_response = Multileg.Get_expiry_list(username, symbols)
    return get_expiry_list_response


logout_broker_accounts_blueprint = Blueprint('logout_broker_accounts_blueprint', __name__)
@logout_broker_accounts_blueprint.route(MULTILEG_ROUTES.get_routes("logout_broker_accounts_blueprint"), methods=['POST'])
def logout_broker_accounts(broker_name,broker_username):
    logout_broker_accounts_response = Multileg.Logout_broker_accounts(broker_name=broker_name,broker_username=broker_username)
    return logout_broker_accounts_response

fyers_square_off_strategy_blueprint = Blueprint('fyers_square_off_strategy_blueprint', __name__)
@fyers_square_off_strategy_blueprint.route(MULTILEG_ROUTES.get_routes("fyers_square_off_strategy_blueprint"), methods=['POST'])
def fyers_square_off_strategy(username,strategy_tag,broker_user_id):
    fyers_square_off_strategy_response, status_code = Multileg.fyers_square_off_strategy(username, strategy_tag,broker_user_id)
    return fyers_square_off_strategy_response, status_code


get_executed_portfolios_blueprint = Blueprint('get_executed_portfolios_blueprint', __name__)
@get_executed_portfolios_blueprint.route(MULTILEG_ROUTES.get_routes("get_executed_portfolios_blueprint"), methods=['POST'])
def get_executed_portfolios(username):
    get_executed_portfolios_response = Multileg.Get_executed_portfolios(username=username)
    return get_executed_portfolios_response


angelone_square_off_strategy_blueprint = Blueprint('angelone_square_off_strategy_blueprint', __name__)
@angelone_square_off_strategy_blueprint.route(MULTILEG_ROUTES.get_routes("angelone_square_off_strategy_blueprint"), methods=['POST'])
def angelone_square_off_strategy(username,strategy_tag,broker_user_id):
    angelone_square_off_strategy_blueprint_response, status_code = Multileg.angelone_square_off_strategy(username, strategy_tag,broker_user_id)
    return angelone_square_off_strategy_blueprint_response, status_code


flatrade_place_order_blueprint = Blueprint('flatrade_place_order_blueprint', __name__)
@flatrade_place_order_blueprint.route(MULTILEG_ROUTES.get_routes("flatrade_place_order_blueprint"), methods=['POST'])
def flatrade_place_order(username,portfolio_name,broker_user_id):
    flatrade_place_order_response, status_code = Multileg.Flatrade_place_order(username, portfolio_name,broker_user_id)
    return flatrade_place_order_response, status_code

flattrade_square_off_strategy_blueprint = Blueprint('flattrade_square_off_strategy_blueprint', __name__)
@flattrade_square_off_strategy_blueprint.route(MULTILEG_ROUTES.get_routes("flattrade_square_off_strategy_blueprint"), methods=['POST'])
def flattrade_square_off_strategy(username,strategy_tag,broker_user_id):
    flattrade_square_off_strategy_blueprint_response, status_code = Multileg.flattrade_square_off_strategy(username, strategy_tag,broker_user_id)
    return flattrade_square_off_strategy_blueprint_response, status_code

enable_portfolio_blueprint = Blueprint('enable_portfolio_blueprint', __name__)
@enable_portfolio_blueprint.route(MULTILEG_ROUTES.get_routes("enable_portfolio_blueprint"), methods=['POST'])
def enable_portfolio(username,portfolio_name):
    enable_portfolio_blueprint_response, status_code = Multileg.enable_portfolio(username, portfolio_name)
    return enable_portfolio_blueprint_response, status_code
 
enable_all_portfolio_blueprint = Blueprint('enable_all_portfolio_blueprint', __name__)
@enable_all_portfolio_blueprint.route(MULTILEG_ROUTES.get_routes("enable_all_portfolio_blueprint"), methods=['POST'])
def enable_all_portfolio(username):
    enable_all_portfolio_blueprint_response, status_code = Multileg.enable_all_portfolios(username)
    return enable_all_portfolio_blueprint_response, status_code
 
delete_all_portfolio_blueprint = Blueprint('delete_all_portfolio_blueprint', __name__)
@delete_all_portfolio_blueprint.route(MULTILEG_ROUTES.get_routes("delete_all_portfolio_blueprint"), methods=['POST'])
def delete_all_portfolio(username):
    delete_all_portfolio_response, status_code = Multileg.delete_all_portfolios(username)
    return delete_all_portfolio_response, status_code
 
delete_all_enabled_portfolios_blueprint = Blueprint('delete_all_enabled_portfolios_blueprint', __name__)
@delete_all_enabled_portfolios_blueprint.route(MULTILEG_ROUTES.get_routes("delete_all_enabled_portfolios_blueprint"), methods=['POST'])
def delete_all_enabled_portfolios(username):
    delete_all_enabled_portfolios_response, status_code = Multileg.delete_all_enabled_portfolios(username)
    return delete_all_enabled_portfolios_response, status_code

get_future_expiry_list_blueprint = Blueprint('get_future_expiry_list_blueprint', __name__)
@get_future_expiry_list_blueprint.route(MULTILEG_ROUTES.get_routes("get_future_expiry_list_blueprint"), methods=['POST'])
def get_futures_expiry_list(username):
    get_future_expiry_list_response = Multileg.get_futures_expiry_list(username=username)
    return get_future_expiry_list_response

fyers_futures_place_order_blueprint = Blueprint('fyers_futures_place_order_blueprint', __name__)
@fyers_futures_place_order_blueprint.route(MULTILEG_ROUTES.get_routes("fyers_futures_place_order_blueprint"), methods=['POST'])
def fyers_futures_place_order(username,portfolio_name,broker_user_id):
    fyers_futures_place_order_blueprint_response, status_code = Multileg.fyers_futures_place_order(username=username, portfolio_name=portfolio_name,broker_user_id=broker_user_id)
    return fyers_futures_place_order_blueprint_response, status_code

angleone_future_place_order_blueprint = Blueprint('angleone_future_place_order_blueprint', __name__)
@angleone_future_place_order_blueprint.route(MULTILEG_ROUTES.get_routes("angleone_future_place_order_blueprint"), methods=['POST'])
def angleone_future_place_order(username,portfolio_name,broker_user_id):
    angleone_future_place_order_blueprint_response, status_code = Multileg.angleone_future_place_order(username=username, portfolio_name=portfolio_name,broker_user_id=broker_user_id)
    return angleone_future_place_order_blueprint_response, status_code

flatrade_future_place_order_blueprint = Blueprint('flatrade_future_place_order_blueprint', __name__)
@flatrade_future_place_order_blueprint.route(MULTILEG_ROUTES.get_routes("flatrade_future_place_order_blueprint"), methods=['POST'])
def flatrade_future_place_order(username,portfolio_name,broker_user_id):
    flatrade_future_place_order_blueprint_response, status_code = Multileg.flatrade_future_place_order(username=username, portfolio_name=portfolio_name,broker_user_id=broker_user_id)
    return flatrade_future_place_order_blueprint_response, status_code

angelone_ltp_websocket_blueprint = Blueprint('angelone_ltp_websocket_blueprint', __name__)
@angelone_ltp_websocket_blueprint.route(MULTILEG_ROUTES.get_routes("angelone_ltp_websocket_blueprint"), methods=['POST'])
def angelone_ltp_websocket(username):
    angelone_ltp_websocket_response = Multileg.angelone_ltp_websocket(username)
    if angelone_ltp_websocket_response == None:
        response_data = {"message": "Websocket Connection closed"}
        return jsonify(response_data), 500
    else:
        return angelone_ltp_websocket_response

get_ltp_blueprint = Blueprint('get_ltp_blueprint', __name__)
@get_ltp_blueprint.route(MULTILEG_ROUTES.get_routes("get_ltp_blueprint"), methods=['POST'])
def get_ltp(username):
    get_ltp_response, status_code = Multileg.get_ltp(username)
    return get_ltp_response, status_code

fyers_websocket_ltp_blueprint = Blueprint('fyers_websocket_ltp_blueprint', __name__)
@fyers_websocket_ltp_blueprint.route(MULTILEG_ROUTES.get_routes("fyers_websocket_ltp_blueprint"), methods=['POST'])
def fyers_websocket_ltp(username,broker_user_id):
    fyers_websocket_ltp_response = Multileg.fyers_websocket_ltp(username=username,broker_user_id=broker_user_id)
    return fyers_websocket_ltp_response
 
get_fyers_ltp_blueprint = Blueprint('get_fyers_ltp_blueprint', __name__)
@get_fyers_ltp_blueprint.route(MULTILEG_ROUTES.get_routes("get_fyers_ltp_blueprint"), methods=['POST'])
def get_fyers_ltp(username):
    get_fyers_ltp_response, status_code = Multileg.get_fyers_ltp(username)
    return get_fyers_ltp_response, status_code

fetching_portfoliolevel_positions_blueprint = Blueprint('fetching_portfoliolevel_positions_blueprint', __name__)
@fetching_portfoliolevel_positions_blueprint.route(MULTILEG_ROUTES.get_routes("fetching_portfoliolevel_positions_blueprint"), methods=['POST'])
def fetching_portfoliolevel_positions(portfolio_name):
    fetching_portfoliolevel_positions_response, status_code = Multileg.fetching_portfoliolevel_positions(portfolio_name)
    return fetching_portfoliolevel_positions_response, status_code

square_off_portfolio_level_blueprint = Blueprint('square_off_portfolio_level_blueprint', __name__)
@square_off_portfolio_level_blueprint.route(MULTILEG_ROUTES.get_routes("square_off_portfolio_level_blueprint"), methods=['POST'])
def square_off_portfolio_level(username,portfolio_name,broker_type,broker_user_id):
    square_off_portfolio_level_response, status_code = Multileg.square_off_portfolio_level(username,portfolio_name,broker_type,broker_user_id)
    return square_off_portfolio_level_response, status_code

flatrade_websocket_blueprint = Blueprint('flatrade_websocket_blueprint', __name__)
@flatrade_websocket_blueprint.route(MULTILEG_ROUTES.get_routes("flatrade_websocket_blueprint"), methods=['POST'])
def flatrade_websocket(username,broker_user_id):
    flatrade_websocket_response, status_code = Multileg.flatrade_websocket(username,broker_user_id)
    return flatrade_websocket_response, status_code
 
get_flattrade_ltp_blueprint = Blueprint('get_flattrade_ltp_blueprint', __name__)
@get_flattrade_ltp_blueprint.route(MULTILEG_ROUTES.get_routes("get_flattrade_ltp_blueprint"), methods=['POST'])
def get_flattrade_ltp(username):
    get_flattrade_ltp_response, status_code = Multileg.get_flattrade_ltp(username)
    return get_flattrade_ltp_response, status_code

fetching_strategy_tag_positions_blueprint = Blueprint('fetching_strategy_tag_positions_blueprint', __name__)
@fetching_strategy_tag_positions_blueprint.route(MULTILEG_ROUTES.get_routes("fetching_strategy_tag_positions_blueprint"), methods=['POST'])
def fetching_strategy_tag_positions_route():
    strategy_tags_data = request.json.get('strategy_tags_data', [])
    fetching_strategy_tag_positions_response, status_code = Multileg.fetching_strategy_tag_positions(strategy_tags_data)
    return fetching_strategy_tag_positions_response, status_code

websocket_ltp_blueprint = Blueprint('websocket_ltp_blueprint', __name__)
@websocket_ltp_blueprint.route(MULTILEG_ROUTES.get_routes("websocket_ltp_blueprint"), methods=['POST'])
def websocket_ltp(username,broker_user_id):
    websocket_ltp_response = Multileg.websocket_ltp(username,broker_user_id)
    return websocket_ltp_response

all_ltp_data_blueprint = Blueprint('all_ltp_data_blueprint', __name__)
@all_ltp_data_blueprint.route(MULTILEG_ROUTES.get_routes("all_ltp_data_blueprint"), methods=['POST'])
def all_ltp_data():
    all_ltp_data_response, status_code = Multileg.all_ltp_data()
    return all_ltp_data_response, status_code

update_portfolio_leg_profit_trail_values_blueprint = Blueprint('update_portfolio_leg_profit_trail_values', __name__)
@update_portfolio_leg_profit_trail_values_blueprint.route(MULTILEG_ROUTES.get_routes("update_portfolio_leg_profit_trail_values_blueprint"), methods=['POST'])
def update_portfolio_leg_profit_trail_values(username,id):
    update_portfolio_leg_profit_trail_values_response, status_code = Multileg.update_portfolio_leg_profit_trail_values(username,id)
    return update_portfolio_leg_profit_trail_values_response, status_code

square_off_portfolio_leg_level_blueprint = Blueprint('square_off_portfolio_leg_level_blueprint', __name__)
@square_off_portfolio_leg_level_blueprint.route(MULTILEG_ROUTES.get_routes("square_off_portfolio_leg_level_blueprint"), methods=['POST'])
def square_off_portfolio_leg_level(username, portfolio_name, broker_type, broker_user_id, portfolio_leg_id):
    square_off_portfolio_leg_level_response, status_code = Multileg.square_off_portfolio_leg_level(username, portfolio_name, broker_type, broker_user_id, portfolio_leg_id)
    return square_off_portfolio_leg_level_response, status_code

Get_theta_gamma_vega_values_blueprint = Blueprint('Get_theta_gamma_vega_values_blueprint', __name__)
@Get_theta_gamma_vega_values_blueprint.route(MULTILEG_ROUTES.get_routes("Get_theta_gamma_vega_values_blueprint"), methods=['POST'])
def Get_theta_gamma_vega_values(username):
    Get_theta_gamma_vega_values_response = Multileg.get_theta_gamma_vega_values(username)
    return Get_theta_gamma_vega_values_response

add_portfolio_performance_blueprint = Blueprint('add_portfolio_performance_blueprint', __name__)
@add_portfolio_performance_blueprint.route(MULTILEG_ROUTES.get_routes("add_portfolio_performance_blueprint"), methods=['POST'])
def add_portfolio_performance(username):
    add_portfolio_performance_blueprint_response, status_code = Multileg.add_portfolio_performance(username)
    return add_portfolio_performance_blueprint_response, status_code

get_portfolio_performance_blueprint = Blueprint('get_portfolio_performance', __name__)
@get_portfolio_performance_blueprint.route(MULTILEG_ROUTES.get_routes("get_portfolio_performance_blueprint"), methods=['GET'])
def get_portfolio_performance(username):
    get_portfolio_performance_blueprint_response, status_code = Multileg.get_portfolio_performance(username=username)
    return get_portfolio_performance_blueprint_response, status_code

Get_latest_blueprint = Blueprint('Get_latest_blueprint', __name__)
@Get_latest_blueprint.route(MULTILEG_ROUTES.get_routes("Get_latest_blueprint"), methods=['POST'])
def Get_latest(username):
    Get_latest_response = Multileg.latest_details(username)
    return Get_latest_response


pseudo_placeorderblueprint = Blueprint('pseudo_placeorderblueprint', __name__)
@pseudo_placeorderblueprint.route(MULTILEG_ROUTES.get_routes("pseudo_placeorderblueprint"), methods=['POST'])
def place_order(username,portfolio_name,broker_user_id):
    pseudo_placeorderresponse, status_code = Multileg.pseudo_placeorder(username=username,portfolio_name=portfolio_name,broker_user_id=broker_user_id)
    return pseudo_placeorderresponse, status_code

pseudo_squareoff_user_blueprint = Blueprint('pseudo_squareoff_user_blueprint', __name__)
@pseudo_squareoff_user_blueprint.route(MULTILEG_ROUTES.get_routes("pseudo_squareoff_user_blueprint"), methods=['POST'])
def pseudo_squareoff_user(username,broker_user_id):
    pseudo_squareoff_user_response, status_code = Multileg.pseudo_user_manual_square_off(username=username,broker_user_id=broker_user_id)
    return pseudo_squareoff_user_response, status_code

pseudo_squareoff_strategy_blueprint = Blueprint('pseudo_squareoff_strategy_blueprint', __name__)
@pseudo_squareoff_strategy_blueprint.route(MULTILEG_ROUTES.get_routes("pseudo_squareoff_strategy_blueprint"), methods=['POST'])
def pseudo_squareoff_strategy(username,strategy_tag,broker_user_id):
    pseudo_squareoff_strategy_response, status_code = Multileg.pseudo_manual_square_off_strategy_level(username=username,strategy_tag=strategy_tag,broker_user_id=broker_user_id)
    return pseudo_squareoff_strategy_response, status_code