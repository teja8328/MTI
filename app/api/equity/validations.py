import pandas as pd
from datetime import datetime,time 
import threading
from  time import sleep
from logzero import logger
import pyotp
import json
import urllib
import datetime as dt
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
from app.models.user import Portfolio , BrokerCredentials , Strategies , Portfolio_legs ,ExecutedEquityOrders
from app.models.user import User
from app.models.main import db
from SmartApi import SmartConnect
from pyotp import TOTP
from fyers_apiv3.FyersWebsocket import order_ws
from fyers_apiv3 import fyersModel
from app.api.brokers import config
import re
from datetime import time
from datetime import datetime
import time
import pytz
from fyers_apiv3 import fyersModel
from datetime import datetime,time
import pytz
import pandas as pd
import urllib.request
import io
import json
import numpy as np
import datetime
from sqlalchemy import func
import re
import os
import csv
import requests
from datetime import datetime
import time
from datetime import datetime, time
# from datetime import datetime, time
from app.models.user import ExecutedEquityOrders , StrategyMultipliers
from app.api.brokers.pseudoAPI import PseudoAPI
from app.api.multileg.validations import save_instrument_list_cache

instrument_list_cache = None

class Equity:

    def fyers_equity_symbols(username, broker_user_id):
        data = request.json
        exchange = data.get('exchange')  # Use get() method to safely access dictionary keys
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            try:
                fyers = config.OBJ_fyers[broker_user_id]
            except KeyError:  # Correct exception name
                response_data = {"message": f"Please login to the broker account, {broker_user_id}"}
                return jsonify(response_data), 500

            
            def extract_data_from_csv(url, column_indices):
                response = requests.get(url)
                if response.status_code == 200:
                    lines = response.text.splitlines()
                    reader = csv.reader(lines)
                    extracted_data = []
                    for row in reader:
                        if len(row) >= max(column_indices):  # Ensure row has enough columns
                            row_data = [row[i] for i in column_indices]
                            extracted_data.append(row_data)
                    return extracted_data
                else:
                    print("Failed to fetch data from the URL.")
                    return None

            def market_data():
                # URL for NSE and BSE Equity Market CSVs
                nse_url = "https://public.fyers.in/sym_details/NSE_CM.csv"
                bse_url = "https://public.fyers.in/sym_details/BSE_CM.csv"

                # Define column indices to extract
                column_indices = [9]  # Assuming index starts from 0

                # Extract data for specified exchange or both if not specified
                nse = None
                bse = None
                if exchange == 'NSE' or not exchange:
                    nse_data = extract_data_from_csv(nse_url, column_indices)
                    nse = pd.DataFrame(nse_data, columns=['Symbol']) if nse_data else None

                if exchange == 'BSE' or not exchange:
                    bse_data = extract_data_from_csv(bse_url, column_indices)
                    bse = pd.DataFrame(bse_data, columns=['Symbol']) if bse_data else None

                response_data = {
                    "fyers_nse_equity_symbols_data": nse.to_dict(orient='records') if nse is not None else None,
                    "fyers_bse_equity_symbols_data": bse.to_dict(orient='records') if bse is not None else None
                }
                return response_data, 200

            # Call the market_data function and return its result
            return market_data()
        else:
            return {"error": "User Not Found."}, 200
    
    def get_equity_price_details(username, broker_user_id):
        data = request.json
        symbol = data['symbol']
        # exchange = data['exchange']

        try:
            from_pesudo = data['from_pseudo']
        except:
            from_pseudo = False

        existing_user = User.query.filter_by(username=username).first()
        broker_credentials = BrokerCredentials.query.filter_by(user_id=existing_user.id, broker_user_id=broker_user_id).first()
        if existing_user:
            try:
                fyers = config.OBJ_fyers[broker_credentials.broker_user_id]
            except KeyError:
                response_data = {"message": f"Please login to the broker account, {broker_user_id}"}
                return jsonify(response_data), 500

            except Exception as e:
                response_data = {"error": str(e)}, 500
                return jsonify(response_data), 500
            data={
                "symbols": symbol
            }
            try:
                equity_response = fyers.quotes(data=data)
                print(equity_response)

                if from_pesudo:
                    ltp = equity_response['d'][0]['v']['lp']
                else:
                    ltp = equity_response['d'][0]['v']['cmd']['c']
                
                response_data = {'symbol': symbol, "ltp": ltp}
                return jsonify(response_data), 200
            
            except Exception as e:
                response_data = {"error": str(e)}, 500
                return jsonify(response_data), 500
        else:
            response_data = {"error": "User not found"}
            return jsonify(response_data), 200
    
    def fyers_place_equity_order(username, broker_user_id):
        data = request.json
        symbol = data['symbol']
        quantity = data['quantity']
        strategy = data['strategy']
        transaction_type = data['transaction_type']
        product_type = data['product_type']
        order_type = data['order_type']
        limitPrice = data['limitPrice']
        config.fyers_order_place_response = []
        existing_user = User.query.filter_by(username=username).first()
 
        if existing_user:
            try:
                fyers = config.OBJ_fyers[broker_user_id]
            except KeyError:
                response_data = {"message": f"Please login to the broker account, {broker_user_id}"}
                return jsonify(response_data), 500

 
            broker_credentials = BrokerCredentials.query.filter_by(user_id=existing_user.id,
                                                                broker_user_id=broker_user_id).first()
            strategy_details = Strategies.query.filter_by(strategy_tag=strategy,broker_user_id=broker_user_id).first()
            if strategy_details:
                multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id, broker_user_id=broker_user_id).first()
                print(multiplier_record)
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
                current_open_trades = ExecutedEquityOrders.query.filter_by(
                    user_id=user_id,
                    broker_user_id=broker_user_id,
                    square_off=False
                ).count()

                # Check if placing this order would exceed max_open_trades
                if current_open_trades >= max_open_trades:
                    return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]    
            
            strategy = Strategies.query.filter_by(strategy_tag=strategy).first()
            print("strategy:", strategy)

            if strategy:
                allowed_trades = strategy.allowed_trades 
                print("allowed_trades:", allowed_trades)
            else:
                allowed_trades = 'Both'  

            # Map side to corresponding allowed trade type
        
            if transaction_type == "BUY":
                trade_type = "Long"
            elif transaction_type == "SELL":
                trade_type = "Short"
            else:
                return [{"message": "Invalid transaction type"}], 500

            # Check if the trade is allowed by the strategy
            if allowed_trades == 'Both' or allowed_trades == trade_type:
                pass  
            else:
                return [{"message": f"Allowed Trade details do not match for strategy: {strategy} | {allowed_trades}"}], 500
 
            overallquantity=(int(quantity) * int( multiplier) * int(user_broker_multiplier))
            print(overallquantity)
            equity_data = {
                "symbol": symbol,
                "qty": overallquantity,
                "type": 1 if order_type =="LIMIT" else 2,   # 2 == MARKET or LIMIT == 1
                "side": 1 if transaction_type == 'BUY' else -1,    # BUY or SELL
                "productType": "INTRADAY" if product_type=="MIS" else "CNC",  # NRML  = CNC   ---->Used to place orders only in stocks which will be carried forward.
                                                # MIS = INTRADAY ----->Used to place orders which will be bought and sold the same day
                                                #   Order type can be anything (Market, Limit, Stop, and Stop Limit)
                "limitPrice": limitPrice,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False,
                "orderTag": strategy
            }
 
            response = fyers.place_order(equity_data)
            fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
            fyers_position=config.OBJ_fyers[broker_user_id].positions()
            fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
            config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}
            if response['s'] != 'ok':
                # Check if there's an existing order with the same symbol, broker_user_id, and broker
                existing_order = ExecutedEquityOrders.query.filter_by(user_id=existing_user.id,
                                                                    trading_symbol=symbol,
                                                                    broker=broker_credentials.broker,
                                                                    broker_user_id=broker_credentials.broker_user_id,
                                                                    product_type=product_type).first()
 
                if existing_order:
                    # Check if there's sufficient quantity for SELL order
                    if transaction_type == 'SELL' and int(existing_order.quantity) < quantity:
 
                        response_data = {'message': "Insufficient quantity for SELL order", "response": response}
                        return jsonify(response_data), 200
 
                    # # Check if the existing order has opposite transaction type and same quantity
                    # if transaction_type == 'SELL' and existing_order.transaction_type == 'BUY' and existing_order.quantity == quantity:
                    #     # Delete the existing order
                    #     db.session.delete(existing_order)
                    #     db.session.commit()
                    #     response_data = {'message': "Existing BUY order deleted because of matching SELL order", "response": response}
                    #     return jsonify(response_data), 200
 
                    # If there's a match and same transaction type, update the existing order
                    if transaction_type == 'BUY':
                         existing_order.buy_price = str(response['tradedPrice'])
                         existing_order.quantity = int(existing_order.quantity) + quantity
                    elif transaction_type == 'SELL':
                        existing_order.sell_price = str(response['tradedPrice'])
                        existing_order.quantity = int(existing_order.quantity) - quantity
 
                    # Check if the resulting quantity is zero
                    if existing_order.quantity == 0:
                        # Delete the existing order
                        #db.session.delete(existing_order)
                        existing_order.square_off=True
                        db.session.commit()
                        response_data = {'message': "Existing BUY order updated because of matching SELL order", "response": response}
                        return jsonify(response_data), 200
                    else:
                        # Otherwise, commit the changes to the database
                        db.session.commit()
                    response_data = {'message': "Existing order updated successfully", "response": response}
                    return jsonify(response_data), 200
               
                else:
                    try:
                        buy_price = response['tradedPrice']
                    except:
                        response_data = {'message': "Failed to place the order", "response": response}
                        return jsonify(response_data), 200
                    equity_orders = ExecutedEquityOrders(user_id=existing_user.id, trading_symbol=symbol,
                                                        broker=broker_credentials.broker,
                                                        broker_user_id=broker_credentials.broker_user_id,
                                                        quantity=quantity, transaction_type=transaction_type,
                                                        product_type=product_type,strategy_tag=strategy,buy_price=buy_price)
                    db.session.add(equity_orders)
                    db.session.commit()
                    response_data = {'message': "New order placed successfully", "response": response}
                    return jsonify(response_data), 200
            else:
                response_data = {'message': "Failed to place the order.", "response": response}
                return jsonify(response_data), 200
        else:
            response_data = {'message': 'User Doesnt exist.'}
            return jsonify(response_data), 200
 
    def angelone_equity_symbols(username, broker_user_id):
            global instrument_list_cache  # Access the cache variable

            data = request.json
            exchange = data['exchange']
            existing_user = User.query.filter_by(username=username).first()

            if existing_user:
                try:
                    angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                except KeyError:  # Correct exception name
                    response_data = {"Message": f"Please login to the broker account, {broker_user_id}"}
                    return jsonify(response_data), 500

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
                    return jsonify({"error": "Failed to load instrument list"}), 500

            nse_symbols = []
            bse_symbols = []

            # Symbols to exclude
            exclude_symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']

            # Function to check if symbol ends with a valid suffix
            def is_valid_symbol(symbol):
                valid_suffixes = ("-EQ", "-BE", "-SM", "-NO", "-BE", "-IV", "-SG", "-MF", "-GS", "-NF", "-NH", "-ST")
                return symbol.endswith(valid_suffixes)

            # Iterate through the cached instrument list
            for instrument in instrument_list_cache:
                symbol = instrument.get('symbol')
                if symbol and symbol.upper() not in exclude_symbols and is_valid_symbol(symbol):
                    if exchange == 'NSE' and instrument.get('exch_seg', '').upper() == 'NSE':
                        nse_symbols.append(symbol)
                    elif exchange == 'BSE' and instrument.get('exch_seg', '').upper() == 'BSE':
                        bse_symbols.append(symbol)

            # Create dataframes for NSE and BSE symbols
            nse_df = pd.DataFrame(nse_symbols, columns=['Symbol'])
            bse_df = pd.DataFrame(bse_symbols, columns=['Symbol'])

            response_data = {
                "angelone_nse_equity_symbols_data": nse_df.to_dict(orient='records'),
                "angelone_bse_equity_symbols_data": bse_df.to_dict(orient='records')
            }
            return response_data, 200

    def get_angelone_equity_price_details(username, broker_user_id):
            global instrument_list_cache
            try:
                # Parse request data
                data = request.json
                symbol = data.get('symbol')

                if not symbol:
                    response_data = {"error": "Symbol not provided"}
                    return jsonify(response_data), 500

                # Assuming User and BrokerCredentials are properly defined
                existing_user = User.query.filter_by(username=username).first()
                broker_credentials = BrokerCredentials.query.filter_by(
                    user_id=existing_user.id, broker_user_id=broker_user_id
                ).first()

                if not existing_user or not broker_credentials:
                    response_data = {"message": "Invalid user or broker credentials"}
                    return jsonify(response_data), 500

                # Accessing Angel One API
                try:
                    angelone = config.SMART_API_OBJ_angelone[broker_credentials.broker_user_id]
                except KeyError:
                    response_data = {"message": f"Please login to the broker account, {broker_user_id}"}
                    return jsonify(response_data), 500

                # Check and load instrument list cache
                if instrument_list_cache is None:
                    print("Loading instrument list...")
                    try:
                        instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                        response = urllib.request.urlopen(instrument_url)
                        instrument_list_cache = json.loads(response.read())  # Properly initialize cache
                        print(f"Loaded instrument list with {len(instrument_list_cache)} instruments.")
       
                        save_instrument_list_cache(instrument_list_cache)
                    except Exception as e:
                        response_data = {"error": f"Failed to load instrument list: {str(e)}"}
                        return jsonify(response_data), 500

                # Find instrument details
                for instrument in instrument_list_cache:
                    if instrument.get("symbol") == symbol:
                        exchange = instrument.get("exch_seg")
                        token = instrument.get("token")
                        break
                else:
                    response_data = {"error": "Symbol not found"}
                    return jsonify(response_data), 500

                # Fetching Equity Price
                try:
                    ltp = angelone.ltpData(exchange, symbol, token)["data"]["ltp"]
                    response_data = {'symbol': symbol, "ltp": ltp}
                    return jsonify(response_data), 200
                except Exception as e:
                    response_data = {"error": f"Failed to fetch equity price: {str(e)}"}
                    return jsonify(response_data), 500

            except Exception as e:
                response_data = {"error": str(e)}
                return jsonify(response_data), 500

    def angelone_place_equity_order(username, broker_user_id):
        global instrument_list_cache
        data = request.json
        # symbol = data['symbol'][4:]
        symbol = data['symbol']
        quantity = data['quantity']
        transaction_type = data['transaction_type']
        order_type = data['order_type']
        strategy_tag = data['strategy']
        product_type=data['product_type']
        limitPrice = data['limitPrice']

        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            return jsonify({"message": f"Please login to the broker account, {broker_user_id}"}), 500
            
        user_id = existing_user.id
 
        broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id,
                                                                broker_user_id=broker_user_id).first()
        if not broker_credentials:
            return jsonify({'message': 'Broker credentials not found'}), 500

        # broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
        if broker_credentials:
            user_broker_multiplier = broker_credentials.user_multiplier 
            print("user_broker_multiplier:",user_broker_multiplier)
        else:
            user_broker_multiplier = 1

        max_open_trades = int(broker_credentials.max_open_trades)
        # Count the current open trades for this user and broker combination
        if max_open_trades != 0:
            # Count the current open trades for this user and broker combination
            current_open_trades = ExecutedEquityOrders.query.filter_by(
                user_id=user_id,
                broker_user_id=broker_user_id,
                square_off=False
            ).count()

            # Check if placing this order would exceed max_open_trades
            if current_open_trades >= max_open_trades:
                return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]    

        strategy = Strategies.query.filter_by(strategy_tag=strategy_tag).first()
        print("strategy:", strategy)

        if strategy:
            allowed_trades = strategy.allowed_trades 
            print("allowed_trades:", allowed_trades)
        else:
            allowed_trades = 'Both'  

        # Map side to corresponding allowed trade type
    
        if transaction_type == "BUY":
            trade_type = "Long"
        elif transaction_type == "SELL":
            trade_type = "Short"
        else:
            return [{"message": "Invalid transaction type"}], 500

        # Check if the trade is allowed by the strategy
        if allowed_trades == 'Both' or allowed_trades == trade_type:
            pass  
        else:
            return [{"message": f"Allowed Trade details do not match for strategy: {strategstrategy_tagy} | {allowed_trades}"}], 500
 
        def angle_one_login():
            config.SMART_API_OBJ_angelone[broker_user_id] = SmartConnect(api_key=config.apikey)
            data = config.SMART_API_OBJ_angelone[broker_user_id].generateSession(config.username, config.pwd, pyotp.TOTP(config.token).now())
            config.AUTH_TOKEN = data['data']['jwtToken']
            refreshToken = data['data']['refreshToken']
            config.FEED_TOKEN = config.SMART_API_OBJ_angelone[broker_user_id].getfeedToken()
            res = config.SMART_API_OBJ_angelone[broker_user_id].getProfile(refreshToken)
            config.config.SMART_API_OBJ_angelone[broker_user_id] = config.SMART_API_OBJ_angelone[broker_user_id]
            rms_limit = config.config.SMART_API_OBJ_angelone[broker_user_id].rmsLimit()
            logger.info(f'Login {res} {config.config.SMART_API_OBJ_angelone[broker_user_id].rmsLimit()}')
 
        def place_limit_order(order_params):
           
            response = config.SMART_API_OBJ_angelone[broker_user_id].placeOrder(order_params)
       
            return response
 
        if config.SMART_API_OBJ_angelone.get(broker_user_id) is None:
            angle_one_login()
 
        if instrument_list_cache is None:
            print("Loading instrument list...")
            instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = urllib.request.urlopen(instrument_url)
            instrument_list_cache = json.loads(response.read())  # Cache the list for later use
    
            save_instrument_list_cache(instrument_list_cache)

        instrument_list = instrument_list_cache
 
        for instrument in instrument_list:
            if instrument.get("symbol") == symbol:
                token = instrument.get("token")
                exchange = instrument.get('exch_seg')
 
                break
        else:
            return jsonify({'message': 'Invalid symbol'}), 400
        print(exchange)
        print(token)
        strategy_details = Strategies.query.filter_by(strategy_tag=strategy_tag,broker_user_id=broker_user_id).first()
        if strategy_details:
            multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id, broker_user_id=broker_user_id).first()
            print(multiplier_record)
            if multiplier_record:
                multiplier = multiplier_record.multiplier
            else:
                multiplier = 1  # Default to 1 if no multiplier record found for the given strategy and broker_user_id
        else:
            multiplier = 1  
        print("multiplier:", multiplier)
 
        overallquantity=(int(quantity) * int( multiplier) * int(user_broker_multiplier))

        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": token,
            "transactiontype": transaction_type,
            "exchange": exchange,
            "ordertype": order_type,
            "producttype": "INTRADAY" if product_type == "MIS" else "DELIVERY",
            "duration": "DAY",
            "price": 0,
            "limitPrice": limitPrice,  # Assuming you want to set limit price to 0 for market orders
            "quantity": overallquantity,
            "ordertag": strategy_tag
        }
        response = place_limit_order(order_params)
        logger.info(f"PlaceOrder : {response}")
        order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
        print("order: ", order)
        order_response_data = {'message': order['data'][::-1][0]['text'],'orderstatus':order['data'][::-1][0]['status']}
        positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
        holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
        all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
        config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}
        if order['data'][::-1][0]['status'] == 'rejected':
            response_data = {'message': "Failed to place the order.", "response": order_response_data}
            return jsonify(response_data), 200  
        else:
            print("\n\n\n\n\n\n\n\n")
            avg_price=str(order['data'][::-1][0]['averageprice'])
            # Check if there's an existing order with the same symbol, broker_user_id, and broker
            existing_order = ExecutedEquityOrders.query.filter_by(user_id=existing_user.id,
                                                                trading_symbol=symbol,
                                                                broker=broker_credentials.broker,
                                                                broker_user_id=broker_credentials.broker_user_id,
                                                                product_type=product_type,buy_price=avg_price).first()
            
            if existing_order:
                # Check if there's sufficient quantity for SELL order
                if transaction_type == 'SELL' and int(existing_order.quantity) < quantity:

                    response_data = {'message': "Insufficient quantity for SELL order", "response": order_response_data}
                    return jsonify(response_data), 200

                # # Check if the existing order has opposite transaction type and same quantity
                # if transaction_type == 'SELL' and existing_order.transaction_type == 'BUY' and existing_order.quantity == quantity:
                #     # Delete the existing order
                #     db.session.delete(existing_order)
                #     db.session.commit()
                #     response_data = {'message': "Existing BUY order deleted because of matching SELL order", "response": response}
                #     return jsonify(response_data), 200

                # If there's a match and same transaction type, update the existing order
                if transaction_type == 'BUY':
                    existing_order.buy_price = avg_price
                    existing_order.quantity = int(existing_order.quantity) + quantity
                elif transaction_type == 'SELL':
                    existing_order.sell_price = avg_price
                    existing_order.quantity = int(existing_order.quantity) - quantity

                # Check if the resulting quantity is zero
                if existing_order.quantity == 0:
                    # Delete the existing order
                    #db.session.delete(existing_order)
                    existing_order.square_off=True
                    db.session.commit()
                    response_data = {'message': "Existing BUY order updated because of matching SELL order", "response": response}
                    return jsonify(response_data), 200
                else:
                    # Otherwise, commit the changes to the database
                    db.session.commit()
                response_data = {'message': "Existing order updated successfully", "response": order_response_data}
                return jsonify(response_data), 200
            
            else:
                equity_orders = ExecutedEquityOrders(user_id=existing_user.id, trading_symbol=symbol,
                                                    broker=broker_credentials.broker,
                                                    broker_user_id=broker_credentials.broker_user_id,
                                                    quantity=quantity, transaction_type=transaction_type,
                                                    product_type=product_type,strategy_tag=strategy_tag,buy_price=avg_price)
                db.session.add(equity_orders)
                db.session.commit()
                response_data = {'message': "New order placed successfully", "response": order_response_data}
                return jsonify(response_data), 200

    def angelone_equity_square_off_loggedIn(username, broker_user_id):
        global instrument_list_cache
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id

            executedEquityOrders_details = ExecutedEquityOrders.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).all()

            if executedEquityOrders_details:
                try:
                    angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                except:
                    response_data = {"Message": f"Please login to the broker account, {broker_user_id}"}
                    return jsonify(response_data), 500

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

                angelone_list = []
                for executedEquityOrder in executedEquityOrders_details:
                    symbol = executedEquityOrder.trading_symbol

                    # Find instrument details for the symbol
                    for instrument in instrument_list:
                        if instrument.get("symbol") == symbol:
                            token = instrument.get("token")
                            exchange = instrument.get('exch_seg')
                            break
                    else:
                        return jsonify({'message': 'Invalid symbol'}), 200

                    strategy_tag = executedEquityOrder.strategy_tag
                    quantity = int(executedEquityOrder.quantity)
                    product_type = executedEquityOrder.product_type

                    data = {
                        "variety": "NORMAL",
                        "orderTag": strategy_tag,
                        "tradingsymbol": symbol,
                        "symboltoken": token,
                        "exchange": exchange,
                        "ordertype": "MARKET",
                        "quantity": quantity,
                        "producttype": "DELIVERY" if product_type == "NRML" else "INTRADAY",
                        "transactiontype": "SELL",
                        "price": 0,
                        "duration": "DAY",
                    }

                    # Place order
                    angelone_square_off = angelone.placeOrderFullResponse(data)

                    angelone_list.append(angelone_square_off['message'])
            
                if len(list(set(angelone_list))) == 1 and list(set(angelone_list))[0] == 'SUCCESS':
                    response_data = {'message': f'Equity Trades Square off successfully for {broker_user_id}', 'Square_off': angelone_list}
                    #db.session.delete(executedEquityOrder)
                    order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                    positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                    holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                    all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                    config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}
                    
                    sell_price = str(order['data'][::-1][0]['averageprice'])
                    executedEquityOrder.sell_price = sell_price
                    
                    executedEquityOrder.squareoff=True
                    db.session.commit()
                    return jsonify(response_data), 200
                else:
                    response_data = {'message': f'Failed to square off some orders for {broker_user_id}'}
                    return jsonify(response_data), 500
            else:
                response_data = {'message': f'Looks like, {broker_user_id} have no Equity open positions .'}
                return jsonify(response_data), 200
        else:
            response_data = {'message': f"User Does not exist, {username}"}
            return jsonify(response_data), 200

    def flattrade_equity_place_order(username,broker_user_id):
        global instrument_list_cache
        data = request.json
        symbol = data['symbol'][4:]
        print("Symbol :",symbol)
        quantity = data['quantity']
        transaction_type = data['transaction_type']
        order_type = data['order_type']
        strategy_tag = data['strategy']
        product_type=data['product_type']
        limitPrice = data['limitPrice']
        #order_place_response = []
        existing_user = User.query.filter_by(username=username).first()
        print(existing_user)
        if existing_user:
            #config.flattrade_order_place_response = []
            broker_credentials = BrokerCredentials.query.filter_by(user_id=existing_user.id,broker_user_id=broker_user_id).first()

            print("Broker Credentials :",broker_credentials)
            try:
                flattrade = config.flattrade_api[broker_credentials.broker_user_id]
               
            except:
                response_data = {"Message": f"Please login to the broker account, {broker_user_id}"}, 500
                return jsonify(response_data), 500

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
                current_open_trades = ExecutedEquityOrders.query.filter_by(
                    user_id=user_id,
                    broker_user_id=broker_user_id,
                    square_off=False
                ).count()

                # Check if placing this order would exceed max_open_trades
                if current_open_trades >= max_open_trades:
                    return [{"message": f"Cannot place order for {broker_user_id}: max open trades limit reached!"}]   

            strategy = Strategies.query.filter_by(strategy_tag=strategy_tag).first()
            print("strategy:", strategy)

            if strategy:
                allowed_trades = strategy.allowed_trades 
                print("allowed_trades:", allowed_trades)
            else:
                allowed_trades = 'Both'  

            # Map side to corresponding allowed trade type
        
            if transaction_type == "BUY":
                trade_type = "Long"
            elif transaction_type == "SELL":
                trade_type = "Short"
            else:
                return [{"message": "Invalid transaction type"}], 500

            # Check if the trade is allowed by the strategy
            if allowed_trades == 'Both' or allowed_trades == trade_type:
                pass  
            else:
                return [{"message": f"Allowed Trade details do not match for strategy: {strategstrategy_tagy} | {allowed_trades}"}], 500
           
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


            for instrument in instrument_list:
                if instrument["symbol"] == symbol:
                    token = instrument["token"]
                    print(token)
                    exchange = instrument['exch_seg']
                    break
            else:
                print("Invalid symbol")
                return
            strategy_details = Strategies.query.filter_by(strategy_tag=strategy_tag,broker_user_id=broker_user_id).first()
            if strategy_details:
                multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id, broker_user_id=broker_user_id).first()
                print(multiplier_record)
                if multiplier_record:
                    multiplier = multiplier_record.multiplier
                else:
                    multiplier = 1  # Default to 1 if no multiplier record found for the given strategy and broker_user_id
            else:
                multiplier = 1  
            print("multiplier:", multiplier)
  
            overallquantity=(int(quantity) * int( multiplier) * int(user_broker_multiplier))

            response = flattrade.place_order(buy_or_sell="B" if transaction_type == "BUY" else "S", product_type='I' if product_type == 'MIS' else "C",
                        exchange=exchange, tradingsymbol=symbol,
                        quantity=overallquantity, discloseqty=0,price_type="MKT" if order_type == "MARKET" else "LMT", price=0, trigger_price=limitPrice,
                        retention='DAY', remarks=strategy_tag)
            logger.info(f"PlaceOrder : {response}")
            print(response)
            order_book = config.flattrade_api[broker_user_id].get_order_book()
            print("Order Book :",order_book,"\n\n\n\n\n\n\n")
            order_response_data=order_book[0]
            print(order_response_data)
            if order_book[0]['status'] == 'REJECTED':
                order_response_data = {'message': order_book[0]['rejreason'] }
                return jsonify(order_response_data), 200
            else:
            # Check if there's an existing order with the same symbol, broker_user_id, and broker
                existing_order = ExecutedEquityOrders.query.filter_by(user_id=existing_user.id,
                                                                    trading_symbol=symbol,
                                                                    broker=broker_credentials.broker,
                                                                    broker_user_id=broker_credentials.broker_user_id,
                                                                    product_type=product_type).first()
                order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                positions_info = config.flattrade_api[broker_user_id].get_positions()
                config.all_flattrade_details[broker_user_id] = {'orderbook' : order_book_send,"holdings" : holdings_info,"positions" : positions_info}
                print(config.all_flattrade_details[broker_user_id])
                if existing_order:
                    # Check if there's sufficient quantity for SELL order
                    if transaction_type == 'SELL' and int(existing_order.quantity) < quantity:
                        response_data = {'message': "Insufficent quantity for sell order"}
                        return jsonify(response_data), 200
 
                    # If there's a match and same transaction type, update the existing order
                    if transaction_type == 'BUY':
                         last_avgprc = str(order_response_data['avgprc'])
                         existing_order.buy_price = last_avgprc
                         existing_order.quantity = int(existing_order.quantity) + quantity
                    elif transaction_type == 'SELL':
                        last_avgprc = str(order_response_data['avgprc'])
                        existing_order.sell_price = last_avgprc
                        existing_order.quantity = int(existing_order.quantity) - quantity
 
                    # Check if the resulting quantity is zero
                    if existing_order.quantity == 0:
                        # Delete the existing order
                        #db.session.delete(existing_order)
                        existing_order.square_off=True
                        db.session.commit()
                        response_data = {'message': "Existing BUY order updated because of matching SELL order",}
                        return jsonify(response_data), 200
                    else:
                        # Otherwise, commit the changes to the database
                        db.session.commit()
                    response_data = {'message': "Existing order updated successfully"}
                    return jsonify(response_data), 200
               
                else:
                    last_avgprc = order_response_data['avgprc']
                    equity_orders = ExecutedEquityOrders(user_id=existing_user.id, trading_symbol=symbol,
                                                        broker=broker_credentials.broker,
                                                        broker_user_id=broker_credentials.broker_user_id,
                                                        quantity=quantity, transaction_type=transaction_type,
                                                        product_type=product_type,strategy_tag=strategy_tag,buy_price=last_avgprc)
                    db.session.add(equity_orders)
                    db.session.commit()
                    response_data = {'message': f"New order placed successfully {symbol} with quantity {quantity}"}
                    return jsonify(response_data), 200
        
    def pseudo_equity_place_order(username, broker_user_id):
        
        data = request.json

        existing_user = User.query.filter_by(username=username).first()

        data.update({"exchange" : "NSE"})
        data.update({"user_id" : existing_user.id})
        data.update({"username" : username})
        data.update({"broker_user_id" : broker_user_id})

        if not existing_user:
            response_data = {"message": "User does not exist !"}
            return jsonify(response_data), 500

        pseudo_api = PseudoAPI(data=data)

        equity_response = pseudo_api.place_order()

        response_data = {"message": equity_response}
        return jsonify(response_data), 200

    def flattrade_equity_square_off_loggedIn(username,broker_user_id): 
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id
            executedEquityOrders_details = ExecutedEquityOrders.query.filter_by(user_id=user_id,broker_user_id=broker_user_id).all()
            if executedEquityOrders_details:
                try:
                    flattrade = config.flattrade_api[broker_user_id]
                except KeyError:
                    response_data = {"Message": f"Please login to the broker account, {broker_user_id}"}, 500
                    return jsonify(response_data), 500
                    
                instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = urllib.request.urlopen(instrument_url)
                instrument_list = json.loads(response.read())

                for executedEquityOrder in executedEquityOrders_details:
                    symbol = executedEquityOrder.trading_symbol

                    for instrument in instrument_list:
                        if instrument.get("symbol") == symbol:
                            exchange = instrument.get('exch_seg')
                            break
                    else:
                        return jsonify({'message': 'Invalid symbol'}), 400

                    strategy_tag = executedEquityOrder.strategy_tag
                    quantity = int(executedEquityOrder.quantity)
                    product_type = executedEquityOrder.product_type

                    limitPrice=0
                    order_type="MKT"
                    transaction_type="S"
                    response = flattrade.place_order(buy_or_sell=transaction_type, product_type='I' if product_type == 'MIS' else "C",
                            exchange=exchange, tradingsymbol=symbol,
                            quantity=quantity, discloseqty=0,price_type=order_type, price=0, trigger_price=limitPrice,
                            retention='DAY', remarks=strategy_tag)
                    logger.info(f"PlaceOrder : {response}")
                    print(response)
                    
                    order_book = config.flattrade_api[broker_user_id].get_order_book()
                    order_response_data = order_book[0]
                    
                    if order_response_data['status'] == 'REJECTED':
                        return jsonify({'message': order_response_data['rejreason']}), 200
                    elif order_response_data['status'] == 'COMPLETE':
                        order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                        holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                        positions_info = config.flattrade_api[broker_user_id].get_positions()
                        config.all_flattrade_details[broker_user_id] = {'order' : order_book_send,"holdings" : holdings_info,"positions" : positions_info}
                        avg_price = order_book_send[0]['avgprc']
                        executedEquityOrder.sell_price = avg_price
                        executedEquityOrder.square_off=True
                        #db.session.delete(executedEquityOrder)
                        db.session.commit()
                        return jsonify({'message': f'Equity orders squareOff successfully for strategy  {broker_user_id} .'}), 200
                    
                    else:
                        return jsonify({'message': f'Failed to squareOff Equity orders for strategy {broker_user_id} .'}), 200
                else:
                    response_data = {'message': f'Looks like, {broker_user_id} have no Equity open positions .'}
                    return jsonify(response_data), 200
            else:
                    response_data = {'message': f'Looks like, {broker_user_id} have no Equity open positions .'}
                    return jsonify(response_data), 200
        else:
            return jsonify({'message': 'User not found.'}), 200

    def fyers_equity_square_off_loggedIn(username, broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id
            executed_EquityOrder_details = ExecutedEquityOrders.query.filter_by(user_id=user_id,
                                                                                broker_user_id=broker_user_id).all()
            try:
                fyers = config.OBJ_fyers[broker_user_id]
                print(fyers)
            except:
                response_data = {"message": f"Please login to the broker account, {broker_user_id}"}, 500
                return jsonify(response_data), 500
            if executed_EquityOrder_details:
                for equityOrders in executed_EquityOrder_details:
                 
                    symbol = equityOrders.trading_symbol
                    product_type = equityOrders.product_type
                    symbol_id=symbol +'-'+ product_type
                    data = {
                        "id":symbol_id
                    }
                    fyers_square_off = fyers.exit_positions(data=data)
                    print(fyers_square_off)

                if fyers_square_off['s'] == 'ok':
                    sell_price = str(fyers_square_off['tradedPrice'])
                    response_data = {'message': f'Equity Orders Square off successfully for {broker_user_id}',
                                    'Square_off': fyers_square_off}
                    fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
                    fyers_position=config.OBJ_fyers[broker_user_id].positions()
                    fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
                    config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}
                    print(config.fyers_orders_book[broker_user_id])
                    equityorders_to_delete = ExecutedEquityOrders.query.filter_by(broker_user_id=broker_user_id).all()
                    for equityorders in equityorders_to_delete:
                        equityorders.square_off=True
                        equityorders.sell_price = sell_price
                    db.session.commit()
                    return jsonify(response_data), 200
 
                else:
                    response_data = {'message': f'Looks like, {broker_user_id} have no Equity open positions .'}
                    return jsonify(response_data), 200
 
            else:
                response_data = {'message': f'Looks like, {broker_user_id} have no Equity open positions .'}
                return jsonify(response_data), 200
        else:
            response_data = {'message': f"User Does not exist, {username}"}
            return jsonify(response_data), 200

    def angelone_equity_strategy_square_off(username,strategy_tag,broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id

            executedEquityOrders_details = ExecutedEquityOrders.query.filter_by(user_id=user_id, broker_user_id=broker_user_id,strategy_tag=strategy_tag).all()

            if executedEquityOrders_details:
                try:
                    angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                except:
                    response_data = {"message": f"Please login to the broker account, {broker_user_id}"}
                    return jsonify(response_data), 500

                instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = urllib.request.urlopen(instrument_url)
                instrument_list = json.loads(response.read())

                angelone_list = []
                for executedEquityOrder in executedEquityOrders_details:
                    symbol = executedEquityOrder.trading_symbol

                    # Find instrument details for the symbol
                    for instrument in instrument_list:
                        if instrument.get("symbol") == symbol:
                            token = instrument.get("token")
                            exchange = instrument.get('exch_seg')
                            break
                    else:
                        return jsonify({'message': 'Invalid symbol'}), 400

                    strategy_tag = executedEquityOrder.strategy_tag
                    quantity = int(executedEquityOrder.quantity)
                    product_type = executedEquityOrder.product_type

                    data = {
                        "variety": "NORMAL",
                        "orderTag": strategy_tag,
                        "tradingsymbol": symbol,
                        "symboltoken": token,
                        "exchange": exchange,
                        "ordertype": "MARKET",
                        "quantity": quantity,
                        "producttype": "DELIVERY" if product_type == "NRML" else "INTRADAY",
                        "transactiontype": "SELL",
                        "price": 0,
                        "duration": "DAY",
                    }

                    # Place order
                    angelone_square_off = angelone.placeOrderFullResponse(data)
                    print(angelone_square_off)

                    
                    angelone_list.append(angelone_square_off['message'])
            
                    #db.session.delete(executedEquityOrder)
 
                if len(list(set(angelone_list))) == 1 and list(set(angelone_list))[0] == 'SUCCESS':
                    response_data = {'message': f'Equity Trades Square off successfully for strategy {strategy_tag}', 'Square_off': angelone_list}
                    order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                    positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                    holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                    all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                    config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}
                    print(config.all_angelone_details[broker_user_id])
                    sell_price = order['data'][::-1][0]['averageprice']
                    executedEquityOrder.sell_price = sell_price
                    executedEquityOrder.square_off=True
                    db.session.commit()
                    
                    return jsonify(response_data), 200
                else:
                    response_data = {'message': f'Failed to square off some orders for {strategy_tag} strategy'}
                    return jsonify(response_data), 500
            else:
                response_data = {'message': f'Looks like, {strategy_tag} strategy have no Equity open positions .'}
                return jsonify(response_data), 200
        else:
            response_data = {'message': f"User Does not exist, {username}"}
            return jsonify(response_data), 200

    def flattrade_equity_strategy_square_off(username,strategy_tag,broker_user_id): 
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id
            executedEquityOrders_details = ExecutedEquityOrders.query.filter_by(user_id=user_id,strategy_tag=strategy_tag,broker_user_id=broker_user_id).all()
            if executedEquityOrders_details:
                try:
                    flattrade = config.flattrade_api[broker_user_id]
                except KeyError:
                    response_data = {"message": f"Please login to the broker account, {broker_user_id}"}, 500
                    return jsonify(response_data), 500
                    
                instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = urllib.request.urlopen(instrument_url)
                instrument_list = json.loads(response.read())

                for executedEquityOrder in executedEquityOrders_details:
                    symbol = executedEquityOrder.trading_symbol

                    for instrument in instrument_list:
                        if instrument.get("symbol") == symbol:
                            exchange = instrument.get('exch_seg')
                            break
                    else:
                        return jsonify({'message': 'Invalid symbol'}), 400

                    strategy_tag = executedEquityOrder.strategy_tag
                    quantity = int(executedEquityOrder.quantity)
                    product_type = executedEquityOrder.product_type

                    limitPrice=0
                    order_type="MKT"
                    transaction_type="S"
                    response = flattrade.place_order(buy_or_sell=transaction_type, product_type='I' if product_type == 'MIS' else "C",
                            exchange=exchange, tradingsymbol=symbol,
                            quantity=quantity, discloseqty=0,price_type=order_type, price=0, trigger_price=limitPrice,
                            retention='DAY', remarks=strategy_tag)
                    logger.info(f"PlaceOrder : {response}")
                    print(response)
                    
                    order_book = config.flattrade_api[broker_user_id].get_order_book()
                    order_response_data = order_book[0]

                    if order_response_data['status'] == 'REJECTED':
                        return jsonify({'message': order_response_data['rejreason']}), 200
                    elif order_response_data['status'] == 'COMPLETE':
                        order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                        holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                        positions_info = config.flattrade_api[broker_user_id].get_positions()
                        config.all_flattrade_details[broker_user_id] = {'order' : order_book_send,"holdings" : holdings_info,"positions" : positions_info}
                        sell_price = order_response_data['avgprc']
                        executedEquityOrder.square_off=True
                        executedEquityOrder.sell_price = sell_price
                        db.session.commit()
                        #db.session.delete(executedEquityOrder)
                        db.session.commit()
                        return jsonify({'message': f'Equity orders squareOff successfully for strategy  {strategy_tag}.'}), 200
                    
                    else:
                        return jsonify({'message': f'Failed to squareOff Equity orders for strategy {strategy_tag} .'}), 200
                else:
                    response_data = {'message': f'Looks like, {strategy_tag} strategy have no Equity open positions .'}
                    return jsonify(response_data), 200
            else:
                    response_data = {'message': f'Looks like, {strategy_tag} strategy have no Equity open positions .'}
                    return jsonify(response_data), 200
        else:
            return jsonify({'message': 'User not found.'}), 200

    def fyers_equity_strategy_square_off(username,strategy_tag, broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id
            executed_EquityOrder_details = ExecutedEquityOrders.query.filter_by(user_id=user_id,strategy_tag=strategy_tag,
                                                                                broker_user_id=broker_user_id).all()
            try:
                fyers = config.OBJ_fyers[broker_user_id]
                print(fyers)
            except:
                response_data = {"message": f"Please login to the broker account, {broker_user_id}"}, 500
                return jsonify(response_data), 500
            if executed_EquityOrder_details:
                for equityOrders in executed_EquityOrder_details:
                 
                    symbol = equityOrders.trading_symbol
                    product_type = equityOrders.product_type
                    symbol_id=symbol +'-'+ product_type
                    data = {
                        "id":symbol_id
                    }
                    fyers_square_off = fyers.exit_positions(data=data)
                    print(fyers_square_off)
 
                if fyers_square_off['s'] == 'ok':
                    sell_price = fyers_square_off['tradedPrice']
                    response_data = {'message': f'Equity Orders Square off successfully for strategy {strategy_tag}',
                                    'Square_off': fyers_square_off}
                    fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
                    fyers_position=config.OBJ_fyers[broker_user_id].positions()
                    fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
                    config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}
                    print(config.fyers_orders_book[broker_user_id])
                    equityorders_to_delete = ExecutedEquityOrders.query.filter_by(strategy_tag=strategy_tag).all()
                    for equityorders in equityorders_to_delete:
                        equityOrders.sell_price = sell_price
                        equityorders.square_off=True
                    db.session.commit()
                    return jsonify(response_data), 200
 
                else:
                    response_data = {'message': f'Looks like, {strategy_tag} strategy have no Equity open positions .'}
                    return jsonify(response_data), 200
 
            else:
                response_data = {'message': f'Looks like, {strategy_tag} strategy have no Equity open positions .'}
                return jsonify(response_data), 200
        else:
            response_data = {'message': f"User Does not exist, {username}"}
            return jsonify(response_data), 200  

    def pseudo_equity_square_off(username,broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            response_data = {"message": "User does not exist !"}
            return jsonify(response_data), 500
        
        data = {
            "exchange" : "NSE",
            "username" : username,
            "broker_user_id" : broker_user_id,
            "type" : "user_level"
        }

        pseudo_api = PseudoAPI(data=data)

        square_off_user_response = pseudo_api.square_off()
        
        response_data = {"message": square_off_user_response}
        return jsonify(response_data), 200  

    def pseudo_equity_strategy_square_off(username,strategy_tag, broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            response_data = {"message": "User does not exist !"}
            return jsonify(response_data), 500
        
        data = {
            "exchange" : "NSE",
            "username" : username,
            "broker_user_id" : broker_user_id,
            "strategy_tag" : strategy_tag,
            "type" : "strategy_level"
        }

        pseudo_api = PseudoAPI(data=data)

        square_off_strategy_response = pseudo_api.square_off()
        
        response_data = {"message": square_off_strategy_response}
        return jsonify(response_data), 200


fyers_equity_symbols_blueprint = Blueprint('fyers_equity_symbols_blueprint', __name__)
@fyers_equity_symbols_blueprint.route('/fyers_equity_symbols/<string:username>/<string:broker_user_id>', methods=['POST'])
def fyers_equity_symbols(username,broker_user_id):
    fyers_equity_symbols_response = Equity.fyers_equity_symbols(username=username,broker_user_id=broker_user_id)
    return fyers_equity_symbols_response

get_equity_price_details_blueprint = Blueprint('get_equity_price_details_blueprint', __name__)
@get_equity_price_details_blueprint.route('/get_fyers_equity_price_details/<string:username>/<string:broker_user_id>', methods=['POST'])
def get_equity_price_details(username,broker_user_id):
   get_equity_price_details_response = Equity.get_equity_price_details(username=username,broker_user_id=broker_user_id)
   return get_equity_price_details_response

angelone_equity_symbols_blueprint = Blueprint('angelone_equity_symbols_blueprint', __name__)
@angelone_equity_symbols_blueprint.route('/angelone_equity_symbols/<string:username>/<string:broker_user_id>', methods=['POST'])
def angelone_equity_symbols(username,broker_user_id):
    angelone_equity_symbols_response = Equity.angelone_equity_symbols(username=username,broker_user_id=broker_user_id)
    return angelone_equity_symbols_response


get_angelone_equity_price_details_blueprint = Blueprint('get_angelone_equity_price_details_blueprint', __name__)
@get_angelone_equity_price_details_blueprint.route('/get_angelone_equity_price_details/<string:username>/<string:broker_user_id>', methods=['POST'])
def get_angelone_equity_price_details(username,broker_user_id):
    get_angelone_equity_price_details_response = Equity.get_angelone_equity_price_details(username=username,broker_user_id=broker_user_id)
    return get_angelone_equity_price_details_response


fyers_place_equity_order_blueprint = Blueprint('fyers_place_equity_order_blueprint', __name__)
@fyers_place_equity_order_blueprint.route('/fyers_place_equity_order/fyers/<string:username>/<string:broker_user_id>', methods=['POST'])
def fyers_place_equity_order(username,broker_user_id):
    fyers_place_equity_order_response = Equity.fyers_place_equity_order(username=username,broker_user_id=broker_user_id)
    return fyers_place_equity_order_response
    

angelone_place_equity_order_blueprint = Blueprint('angelone_place_equity_order_blueprint', __name__)
@angelone_place_equity_order_blueprint.route('/angelone_place_equity_order/angelone/<string:username>/<string:broker_user_id>', methods=['POST'])
def angelone_place_equity_order(username,broker_user_id):
    angelone_place_equity_order_response = Equity.angelone_place_equity_order(username=username,broker_user_id=broker_user_id)
    return angelone_place_equity_order_response

flattrade_equity_place_order_blueprint = Blueprint('flattrade_equity_place_order_blueprint', __name__)
@flattrade_equity_place_order_blueprint.route('/flattrade_equity_place_order/flattrade/<string:username>/<string:broker_user_id>', methods=['POST'])
def flattrade_equity_place_order(username,broker_user_id):
    flattrade_equity_place_order_response = Equity.flattrade_equity_place_order(username=username,broker_user_id=broker_user_id)
    return flattrade_equity_place_order_response

pseudo_equity_place_order_blueprint = Blueprint('pseudo_equity_place_order_blueprint', __name__)
@pseudo_equity_place_order_blueprint.route('/pseudo_equity_place_order/pseudo/<string:username>/<string:broker_user_id>', methods=['POST'])
def pseudo_equity_place_order(username,broker_user_id):
    pseudo_equity_place_order_response = Equity.pseudo_equity_place_order(username=username,broker_user_id=broker_user_id)
    return pseudo_equity_place_order_response

fyers_equity_square_off_loggedIn_blueprint = Blueprint('fyers_equity_square_off_loggedIn_blueprint', __name__)
@fyers_equity_square_off_loggedIn_blueprint.route('/fyers_user_equity_sqoff/<string:username>/<string:broker_user_id>', methods=['POST'])
def fyers_equity_square_off_loggedIn(username,broker_user_id):
    fyers_equity_square_off_loggedIn_response = Equity.fyers_equity_square_off_loggedIn(username=username,broker_user_id=broker_user_id)
    return fyers_equity_square_off_loggedIn_response

angelone_equity_square_off_loggedIn_blueprint = Blueprint('angelone_equity_square_off_loggedIn_blueprint', __name__)
@angelone_equity_square_off_loggedIn_blueprint.route('/angelone_user_equity_sqoff/<string:username>/<string:broker_user_id>', methods=['POST'])
def angelone_equity_square_off_loggedIn(username,broker_user_id):
    angelone_equity_square_off_loggedIn_response = Equity.angelone_equity_square_off_loggedIn(username=username,broker_user_id=broker_user_id)
    return angelone_equity_square_off_loggedIn_response

flattrade_equity_place_order_blueprint = Blueprint('flattrade_equity_place_order_blueprint', __name__)
@flattrade_equity_place_order_blueprint.route('/flattrade_equity_place_order/flattrade/<string:username>/<string:broker_user_id>', methods=['POST'])
def flattrade_equity_place_order(username,broker_user_id):
    flattrade_equity_place_order_response = Equity.flattrade_equity_place_order(username=username,broker_user_id=broker_user_id)
    return flattrade_equity_place_order_response


flattrade_equity_square_off_loggedIn_blueprint = Blueprint('flattrade_equity_square_off_loggedIn_blueprint', __name__)
@flattrade_equity_square_off_loggedIn_blueprint.route('/flattrade_user_equity_sqoff/<string:username>/<string:broker_user_id>', methods=['POST'])
def flattrade_equity_square_off_loggedIn(username,broker_user_id):
    flattrade_equity_square_off_loggedIn_response = Equity.flattrade_equity_square_off_loggedIn(username=username,broker_user_id=broker_user_id)
    return flattrade_equity_square_off_loggedIn_response

angelone_equity_strategy_square_off_blueprint = Blueprint('angelone_equity_strategy_square_off_blueprint', __name__)
@angelone_equity_strategy_square_off_blueprint.route('/angelone_strategy_equity_sqoff/<string:username>/<string:strategy_tag>/<string:broker_user_id>', methods=['POST'])
def angelone_equity_strategy_square_off(username,strategy_tag,broker_user_id):
    angelone_equity_strategy_square_off_response = Equity.angelone_equity_strategy_square_off(username=username,strategy_tag=strategy_tag,broker_user_id=broker_user_id)
    return angelone_equity_strategy_square_off_response

flattrade_equity_strategy_square_off_blueprint = Blueprint('flattrade_equity_strategy_square_off_blueprint', __name__)
@flattrade_equity_strategy_square_off_blueprint.route('/flattrade_strategy_equity_sqoff/<string:username>/<string:strategy_tag>/<string:broker_user_id>', methods=['POST'])
def flattrade_equity_strategy_square_off(username,strategy_tag,broker_user_id):
   flattrade_equity_strategy_square_off_response = Equity.flattrade_equity_strategy_square_off(username=username,strategy_tag=strategy_tag,broker_user_id=broker_user_id)
   return flattrade_equity_strategy_square_off_response

fyers_equity_strategy_square_off_blueprint = Blueprint('fyers_equity_strategy_square_off_blueprint', __name__)
@fyers_equity_strategy_square_off_blueprint.route('/fyers_strategy_equity_sqoff/<string:username>/<string:strategy_tag>/<string:broker_user_id>', methods=['POST'])
def fyers_equity_strategy_square_off(username,strategy_tag,broker_user_id):
   fyers_equity_strategy_square_off_response = Equity.fyers_equity_strategy_square_off(username=username,strategy_tag=strategy_tag,broker_user_id=broker_user_id)
   return fyers_equity_strategy_square_off_response

pseudo_equity_square_off_blueprint = Blueprint('pseudo_equity_square_off_blueprint', __name__)
@pseudo_equity_square_off_blueprint.route('/pseudo_user_equity_sqoff/<string:username>/<string:broker_user_id>', methods=['POST'])
def pseudo_equity_square_off(username, broker_user_id):
   pseudo_equity_square_off_response = Equity.pseudo_equity_square_off(username=username,broker_user_id=broker_user_id)
   return pseudo_equity_square_off_response

pseudo_equity_strategy_square_off_blueprint = Blueprint('pseudo_equity_strategy_square_off_blueprint', __name__)
@pseudo_equity_strategy_square_off_blueprint.route('/pseudo_strategy_equity_sqoff/<string:username>/<string:strategy_tag>/<string:broker_user_id>', methods=['POST'])
def pseudo_equity_strategy_square_off(username,strategy_tag,broker_user_id):
   pseudo_equity_strategy_square_off_response = Equity.pseudo_equity_strategy_square_off(username=username,strategy_tag=strategy_tag,broker_user_id=broker_user_id)
   return pseudo_equity_strategy_square_off_response