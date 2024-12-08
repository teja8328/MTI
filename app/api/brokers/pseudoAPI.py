from flask import Blueprint, jsonify, request, abort, Flask
from app.models.user import Portfolio , BrokerCredentials, Strategies, Portfolio_legs, ExecutedPortfolio,StrategyMultipliers,Performance, User, ExecutedEquityOrders
from app.models.main import db
import random
import urllib
import json
from datetime import datetime
from app.api.brokers import config
import re
import requests

instrument_list_cache = None

class PseudoAPI:
    def __init__(self, data):
        self.data = data

    def place_order(self):
        exchange = self.data['exchange']
        global instrument_list_cache

        # Note: Equity Place order !!
        if exchange == "NSE":
            user_id = self.data['user_id']
            symbol = self.data['symbol']

            if "NSE" in symbol:
                symbol = symbol[4:]
            else:
                symbol = symbol

            quantity = self.data['quantity']
            transaction_type = self.data['transaction_type']
            order_type = self.data['order_type']
            strategy_tag = self.data['strategy']
            product_type= self.data['product_type']
            limitPrice = self.data['limitPrice'] if 'limitPrice' in self.data else 0
            username = self.data['username']
            broker_user_id = self.data['broker_user_id']

            broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
            if broker_credentials:
                user_broker_multiplier = broker_credentials.user_multiplier 
                print("user_broker_multiplier:",user_broker_multiplier)
            else:
                user_broker_multiplier = 1

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
                return [{"message": "Invalid transaction type"}] 

            # Check if the trade is allowed by the strategy
            if allowed_trades == 'Both' or allowed_trades == trade_type:
                pass  
            else:
                return [{"message": f"Allowed Trade details do not match for strategy: {strategy_tag} | {allowed_trades}"}]
                

            # instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            # response = urllib.request.urlopen(instrument_url)
            # instrument_list = json.loads(response.read())
            if instrument_list_cache is None:
                print("Loading instrument list...")
                instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = urllib.request.urlopen(instrument_url)
                instrument_list = json.loads(response.read())
                print(f'Loaded instrument list with {len(instrument_list)} instruments.')
                from app.api.multileg.validations import save_instrument_list_cache
                save_instrument_list_cache(instrument_list)
            
            for instrument in instrument_list:
                if instrument["symbol"] == symbol:
                    token = instrument["token"]
                    exchange = instrument['exch_seg']
                    break

            if "NSE" in symbol:
                fyers_broker_id = list(config.OBJ_fyers.keys())[0]
                url = f'http://127.0.0.1:1919/get_fyers_equity_price_details/{username}/{fyers_broker_id}'

                data = {
                    "symbol" : symbol,
                    "from_pseudo" : True
                    }

            else:
                angelone_broker_id = list(config.SMART_API_OBJ_angelone.keys())[0]
                url = f'http://127.0.0.1:1919/get_angelone_equity_price_details/{username}/{angelone_broker_id}'

                data = {
                        "symbol" : symbol,
                        "from_pseudo" : True
                        }
            
            response = requests.post(url, json=data)

            if order_type == 'LIMIT' or order_type == 'SL_LIMIT':
                order_status = 'OPEN'
                print("order_status:", order_status)
                buy_price = limitPrice
                total_quantity = quantity * int(user_broker_multiplier) * int(multiplier)

                total_price = buy_price * total_quantity
            
            else:
                order_status = 'COMPLETE'
                buy_price = str(response.json()["ltp"])
                total_quantity = quantity * int(user_broker_multiplier) * int(multiplier)

                total_price = response.json()["ltp"] * total_quantity
            

            
            # total_quantity = quantity * int(user_broker_multiplier)

            # total_price = response.json()["ltp"] * total_quantity

                        # Check for sufficient funds
            broker_account = BrokerCredentials.query.filter_by(username=username, broker_user_id=broker_user_id).first()
    
            if float(broker_account.available_balance) < total_price:
                return [{"message": f"Insufficient Funds Available: {broker_user_id}"}]

            order_id = random.randint(10**14, 10**15 - 1)
            from datetime import datetime

            executed_equity_orders = ExecutedEquityOrders(user_id=user_id, 
                                                          trading_symbol=instrument['symbol'], 
                                                          broker="pseudo_account", 
                                                          broker_user_id=broker_user_id, 
                                                          quantity= total_quantity,
                                                          transaction_type=transaction_type,
                                                          product_type=product_type,
                                                          strategy_tag=strategy_tag,
                                                          buy_price=buy_price if transaction_type =="BUY" else "0",
                                                          sell_price = buy_price if transaction_type =="SELL" else "0",
                                                    
                                                          buy_qty = quantity if transaction_type =="BUY" else "0",
                                                          sell_qty = quantity if transaction_type =="SELL" else "0",
                                                          symbol_token=token,
                                                          order_id=order_id,
                                                          placed_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                          status = order_status,
                                                          order_type = order_type,
                                                          margin_req = total_price       
                                                          )

            db.session.add(executed_equity_orders)
            db.session.commit()


    
            # Deduct the total price from the available balance
            broker_account.available_balance = str(float(broker_account.available_balance) - total_price)

            broker_account.utilized_margin = float(broker_account.utilized_margin) + total_price
            db.session.add(broker_account)
            db.session.commit()

            return f"Equity order for {self.data['symbol']} placed successfully !"

        # Futures and Options !!
        else:
            # Extract data from self
            portfolio_name = self.data['portfolio_name']
            broker_user_id = self.data['broker_user_id']
            username = self.data['username']
            qtp_lots = self.data['qtp_lots']
            underlying_prices = self.data.get('underlying_prices', {})
    
            # Retrieve user and portfolio details
            user_id = User.query.filter_by(username=username).first().id
            portfolio_details = Portfolio.query.filter_by(portfolio_name=portfolio_name, user_id=user_id).first()
            portfolioleg_details = Portfolio_legs.query.filter_by(Portfolio_id=portfolio_details.id).all()
    
            if broker_user_id not in portfolio_details.strategy_accounts_id:
                return {"message": "Broker User ID is not linked with the portfolio!"}
            
            broker_credentials = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
            if broker_credentials:
                user_broker_multiplier = broker_credentials.user_multiplier 
                print("user_broker_multiplier:",user_broker_multiplier)
            else:
                user_broker_multiplier = 1

            strategy_name = portfolio_details.strategy
            strategy_details = Strategies.query.filter_by(strategy_tag=strategy_name).first()

            if strategy_details:
                multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy_details.id, broker_user_id=broker_user_id).first()
                multiplier = multiplier_record.multiplier if multiplier_record else 1
            else:
                multiplier = 1

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

    
            # quantity = int(qtp_lots) * int(config.index_data.get(portfolio_details.symbol, 1)) * int(user_broker_multiplier)
            # print("total_quantity:", quantity)
            # Map symbol to access_symbol
            symbol_mapping = {
                "NIFTY": "nifty50",
                "BANKNIFTY": "niftybank",
                "FINNIFTY": "finnifty"
            }
            access_symbol = symbol_mapping.get(portfolio_details.symbol, portfolio_details.symbol)
    
            # Fetch instrument data
            # instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            # try:
            #     response = urllib.request.urlopen(instrument_url)
            #     instrument_list = json.loads(response.read())
            # except Exception as e:
            #     return {"message": f"Error fetching instrument data: {str(e)}"}
            if instrument_list_cache is None:
                print("Loading instrument list...")
                instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
                response = urllib.request.urlopen(instrument_url)
                instrument_list = json.loads(response.read())
                print(f'Loaded instrument list with {len(instrument_list)} instruments.')
                from app.api.multileg.validations import save_instrument_list_cache
                save_instrument_list_cache(instrument_list_cache)
    
            # Functions to filter instruments and lookup token
            def filter_instruments():
                instrument_type = "FUTIDX" if legs.option_type == "FUT" else "OPTIDX"
                return [inst for inst in instrument_list
                        if inst['exch_seg'] == portfolio_details.exchange and
                        inst['name'] == portfolio_details.symbol and
                        inst['instrumenttype'] == instrument_type]
    
            def token_lookup(expiry, trading_symbol, instruments):
                for newinstrument in instruments:
                    if newinstrument['expiry'] == expiry and newinstrument['symbol'] == trading_symbol:
                        return newinstrument
                return None
    
            responses = []
            orderbook = []
            positions = []
            total_price = 0.0

            buy_trades_first = portfolio_details.buy_trades_first
            positional_portfolio = portfolio_details.positional_portfolio
    
            for legs in portfolioleg_details:
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
                            responses.append({"message": f"Invalid date format for start_time {legs.start_time}. Skipping this entry."})
                            continue  # Skip this leg if parsing fails
                    else:
                        responses.append({"message": f"start_time for {legs.portfolio_name} is missing or empty. Skipping this entry."})
                        continue  # Skip this leg if start_time is empty
                else:
                    pass

                underlying_price = underlying_prices.get(portfolio_details.symbol, 0)
                print("underlying_price:", underlying_price)

                # Adjust rounding logic based on the symbol
                if portfolio_details.symbol in ["NIFTY", "FINNIFTY"]:
                    atm_price = round(underlying_price / 50) * 50  # Nearest to 50
                elif portfolio_details.symbol == "BANKNIFTY":
                    atm_price = round(underlying_price / 100) * 100  # Nearest to 100
                else:
                    atm_price = round(underlying_price)  # Default rounding if not NIFTY/BANKNIFTY/FINNIFTY

                strike = legs.strike.upper()  # Ensure input is uppercase
                if strike.startswith("ATM"):
                    if "+" in strike:
                        offset = int(strike.split("+")[1])
                        # Adjust strike based on option type
                        if legs.option_type == "CE":
                            final_strike = atm_price + offset
                        elif legs.option_type == "PE":
                            final_strike = atm_price + offset  # For PE, ATM+100 means higher strike
                    elif "-" in strike:
                        offset = int(strike.split("-")[1])
                        # Adjust strike based on option type
                        if legs.option_type == "CE":
                            final_strike = atm_price - offset
                        elif legs.option_type == "PE":
                            final_strike = atm_price - offset  # For PE, ATM-100 means lower strike
                    else:
                        # No adjustment, just use ATM price
                        final_strike = atm_price
                else:
                    final_strike = int(strike)  # Directly use the provided strike if not ATM

                strike_price = str(final_strike)

                max_lots = portfolio_details.max_lots
                if max_lots != '0':
                    max_lots = int(max_lots)

                leg_lots = int(legs.lots)

                order_lots = 0
                
                if max_lots != '0':
                    # Step 1: Determine order lots
                    max_lots = int(max_lots)
                    leg_lots = int(legs.lots)

                    order_lots = min(leg_lots, max_lots)
                    print("order_lots:", order_lots)

                    # Step 2: Calculate initial final_lots
                    final_lots = order_lots * int(qtp_lots) * int(user_broker_multiplier) * int(multiplier)

                    # Step 3: Ensure final_lots does not exceed max_lots
                    final_lots = min(final_lots, max_lots)

                    # Step 4: Calculate quantity
                    quantity = final_lots * int(config.index_data.get(portfolio_details.symbol, 1))
                else:
                    # If max_lots is None, calculate based on legs.lots only
                    quantity = int(legs.lots) * int(qtp_lots) * int(user_broker_multiplier) * int(multiplier) * int(config.index_data.get(portfolio_details.symbol, 1))

                # Print quantity for debugging
                    print("quantity:", quantity)

                # Cap the order lots at max_lots
                # order_lots = min(leg_lots, max_lots)
                # quantity = int(qtp_lots) * order_lots * int(config.index_data.get(portfolio_details.symbol, 1)) * int(user_broker_multiplier) * int(multiplier)

                print(f"Placing order: {order_lots} lots, Quantity: {quantity}")

                # Fetch price details
                url = f'http://127.0.0.1:1919/get_price_details/{username}'
                data = {
                    "symbol": portfolio_details.symbol,
                    "option_type": legs.option_type,
                    "strike": strike_price,
                    "expiry": legs.expiry_date,
                    "from_pseudo": True
                }
                print("data:", data)
                print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
    
                try:
                    response = requests.post(url, json=data)
                    response_data = response.json()
                    strike_price = str(int(response_data.get('Strike Price', 0)))  # Default to 0 if not found
                    fetched_price = float(response_data.get('Price', 0))  # Default to 0 if not found
                    print("fetched_price:",fetched_price)
                except Exception as e:
                    return {"message": f"Error fetching price details: {str(e)}"}

                price = fetched_price if legs.limit_price in [None, '', "0"] else float(legs.limit_price)
                wait_sec = legs.wait_sec
                wait_action = legs.wait_action
    
                print("Strike Price:", strike_price)
                print("Price:", price)
    
                # Construct the trading symbol
                year = legs.expiry_date[5:][2:]
                date = legs.expiry_date[:5]
                if legs.option_type == "FUT":
                    trading_symbol = f"{portfolio_details.symbol}{date}{year}{legs.option_type}"
                else:
                    trading_symbol = f"{portfolio_details.symbol}{date}{year}{strike_price}{legs.option_type}"
    
                print("trading_symbol:", trading_symbol)
                expiry_date = legs.expiry_date
                print("expiry_date:", expiry_date)
    
                # Filter instruments and lookup token
                filtered_instruments = filter_instruments()
                trade_details = token_lookup(expiry_date, trading_symbol, filtered_instruments)
            
                if not trade_details:
                    return ({"message": f"Trade details not found for symbol: {trading_symbol}"})


    
                token = trade_details['token']
                order_id = random.randint(10**14, 10**15 - 1)

                

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
                    return [{"message": "Invalid transaction type"}] 

                # Check if the trade is allowed by the strategy
                if allowed_trades == 'Both' or allowed_trades == trade_type:
                    pass
                    # if buy_trades_first and side != "BUY":
                    #     return [{"message": "Order not placed as buy_trades_first is true and transcation is not BUY"}]
                else:
                    return [{"message": f"Allowed Trade details do not match for strategy: {portfolio_strategy} | {allowed_trades}"}]
                    
            
                broker_account = BrokerCredentials.query.filter_by(username=username, broker_user_id=broker_user_id).first()
                if float(broker_account.available_balance) < total_price:
                    return [{"message": f"Insufficient Funds Available: {broker_user_id}"}]
                
                total_price = price * quantity    
                broker_credentials.utilized_margin = str(float(broker_credentials.utilized_margin) + float(total_price))
                broker_credentials.available_balance = str(float(broker_credentials.available_balance) - total_price)
                db.session.add(broker_account)
                db.session.commit()
            
    
                if portfolio_details.order_type == 'LIMIT' or portfolio_details.order_type == 'SL_LIMIT' :
                    order_status = 'OPEN'
                    print("order_status:", order_status)
            
                else:
                    order_status = 'COMPLETE'

                if order_status == 'COMPLETE':

                    # Only add to positions if it's not a LIMIT order
                    position_response = {
                        'productType': portfolio_details.order_type,
                        'exchange': portfolio_details.exchange,
                        'symbol': trading_symbol,
                        'netQty': quantity,
                        'ltp': price,
                        'pl': 0,
                        'buyQty': quantity,
                        'buyAvg': price,
                        'buyVal': 0,
                        'sellQty': 0,
                        'sellAvg': 0,
                        'sellVal': 0,
                        'realized_profit': 0,
                        'unrealized_profit': 0,
                        'side': legs.transaction_type,
                        'token': token
                    }
                    positions.append(position_response)

                order_response = {
                    'orderTag': portfolio_details.strategy,
                    'symbol': trading_symbol,
                    'exchange': portfolio_details.exchange,
                    'orderDateTime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'qty': quantity,
                    'side': legs.transaction_type,
                    'tradedPrice': price,
                    'id': order_id,
                    'status': order_status,  # Set status to 'OPEN' if it's a LIMIT order
                    'token':token
                }
    
                responses.append({"message": f"Order Placed Successfully | order_id: {order_id} !"})
                orderbook.append(order_response)
                # positions.append(position_response)
    
                # Add executed order to database
                executed_orders = ExecutedPortfolio(
                    broker_user_id=broker_user_id,
                    user_id=user_id,
                    transaction_type=legs.transaction_type,
                    strategy_tag=portfolio_details.strategy,
                    portfolio_name=portfolio_name,
                    trading_symbol=trading_symbol,
                    order_id=order_id,
                    status=order_status,
                    portfolio_leg_id=legs.id,
                    netqty=quantity,
                    exchange=portfolio_details.exchange,
                    symbol_token=token,
                    buy_price=0 if legs.transaction_type == "SELL" else price,
                    sell_price=0 if legs.transaction_type == "BUY" else price,
                    placed_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    broker="pseudo_account",
                    buy_qty = quantity if legs.transaction_type == "BUY" else 0,
                    sell_qty = quantity if legs.transaction_type == "SELL" else 0,
                    order_type = portfolio_details.order_type,
                    product_type = portfolio_details.product_type,
                    margin_req = total_price,
                    wait_sec = wait_sec,
                    wait_action = wait_action 
                )
    
                db.session.add(executed_orders)

 
            # Commit all executed orders
            db.session.commit()
 
            from datetime import time
 
            def create_performance_record(portfolio_name, user_id, broker_user_id, max_pl, min_pl,product_type):
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
                        min_pl_time=time(0, 0, 0),
                        product_type=product_type
                    )
                    db.session.add(performance_record)
                    db.session.commit()
                else:
                    # If the record exists, you can handle it according to your needs
                    print(f"Performance record for portfolio '{portfolio_name}' already exists.")
 
            # Call the function
            if not (portfolio_details.order_type == "LIMIT" or  portfolio_details.order_type == "SL_LIMIT" and order_status == "OPEN"):
                create_performance_record(
                    portfolio_name=portfolio_name,
                    user_id=user_id,
                    broker_user_id=broker_user_id,
                    max_pl=float('-inf'),  
                    min_pl=float('+inf'),
                    product_type = portfolio_details.product_type
                )

            # Update pseudo API object
            config.PSEUDO_API_OBJ[broker_user_id] = {"orderbook": orderbook, "positions": positions}
   
            return responses



    def square_off(self):
        username = self.data['username']
        print(self.data)
        existing_user = User.query.filter_by(username=username).first()
        user_id = existing_user.id
        exchange = self.data['exchange']
        
        # Note: Equity  Square off !!
        if exchange == "NSE" :
            square_off_type = self.data['type']
            broker_user_id = self.data['broker_user_id']

            if square_off_type == "user_level":
                existing_equity_orders = ExecutedEquityOrders.query.filter_by(user_id=user_id, broker_user_id=broker_user_id,square_off=False).all()
                sell_order_id = random.randint(10**14, 10**15 - 1)

                for equity_orders in existing_equity_orders:
                    token = equity_orders.symbol_token
                    sell_price = config.angelone_live_ltp[token]
                    equity_orders.sell_price = sell_price
                    equity_orders.squared_off_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    equity_orders.square_off = True
                    equity_orders.sell_order_id = sell_order_id
                    equity_orders.sell_qty = equity_orders.buy_qty
                    db.session.commit()
                
                return "Equity Square Off Successfull !!"
            
            elif square_off_type == "strategy_level":
                strategy_tag = self.data['strategy_tag']

                existing_equity_orders = ExecutedEquityOrders.query.filter_by(user_id=user_id, broker_user_id=broker_user_id, strategy_tag=strategy_tag,square_off=False).all()
                print(existing_equity_orders,"\n\n\n\n\n\n")
                sell_order_id = random.randint(10**14, 10**15 - 1)

                for equity_orders in existing_equity_orders:
                    token = equity_orders.symbol_token
                    sell_price = config.angelone_live_ltp[token]
                    equity_orders.sell_price = sell_price
                    equity_orders.squared_off_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    equity_orders.square_off = True
                    equity_orders.sell_order_id = sell_order_id
                    db.session.commit()



                return "Equity Square Off Successfull ( Strategy Level ) !!"
 
        
        # Futures and Options !!
        else:
            if "strategy_tag" in self.data.keys():
                strategy_tag = self.data['strategy_tag']
                broker_user_id = self.data['broker_user_id']
                
                existing_user = User.query.filter_by(username=username).first()
                user_id = existing_user.id
                sell_order_id = random.randint(10**14, 10**15 - 1)

                executed_portfolio = ExecutedPortfolio.query.filter_by(user_id=user_id, strategy_tag=strategy_tag, broker_user_id=broker_user_id,square_off=False).all()

                for executed in executed_portfolio:
                    token = executed.symbol_token
                    sell_price = config.angelone_live_ltp[token]
                    executed.sell_price = sell_price
                    executed.square_off = True
                    executed.sell_order_id = sell_order_id
                    executed.squared_off_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executed.netqty = 0 
                    executed.sell_qty = executed.buy_qty
                    # executed.locked_min_profit = 0
                    # executed.reached_profit = 0
           
                    
                    db.session.commit()

                executed_portfolios = ExecutedPortfolio.query.filter_by(user_id=user_id, strategy_tag=strategy_tag, broker_user_id=broker_user_id,square_off=False).first()
                if executed_portfolios:
                    executed_portfolios.locked_min_profit = 0
                    executed_portfolios.reached_profit = 0
                    db.session.commit()

                strategy = Strategies.query.filter_by(user_id=user_id, strategy_tag=strategy_tag).first()
                if strategy:
                    strategy.locked_min_profit = 0
                    strategy.reached_profit = 0
                    db.session.commit()

                broker = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                if broker:
                    broker.locked_min_profit = 0
                    broker.reached_profit = 0
                    db.session.commit()


                return "Square off done ( Strategy Level ) !"
            
            elif "portfolio_leg_id" in self.data.keys():
                portfolio_name = self.data['portfolio_name']
                portfolio_leg_id = self.data['portfolio_leg_id']
                broker_type = self.data['broker_type']
                broker_user_id = self.data['broker_user_id']
                sell_order_id = random.randint(10**14, 10**15 - 1)

                existing_portfolio = ExecutedPortfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name, portfolio_leg_id=portfolio_leg_id, broker=broker_type, broker_user_id=broker_user_id,square_off=False).all()

                if existing_portfolio == None:
                    return "There are no open positions for this Portfolio !"
                
                for executed in existing_portfolio:
                    token = executed.symbol_token
                    sell_price = config.angelone_live_ltp[token]
                    executed.sell_price = sell_price
                    executed.square_off = True
                    executed.sell_order_id = sell_order_id
                    executed.squared_off_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executed.netqty = 0 
                    executed.sell_qty = executed.buy_qty
                    # executed.locked_min_profit = 0
                    # executed.reached_profit = 0
                
                existing_portfolios = ExecutedPortfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name, portfolio_leg_id=portfolio_leg_id, broker=broker_type, broker_user_id=broker_user_id,square_off=False).first()

                if existing_portfolios:
                        strategy_tag = existing_portfolios.strategy_tag
                        existing_portfolios.locked_min_profit = 0
                        existing_portfolios.reached_profit = 0
                        db.session.commit()

                        # Update strategy related to this strategy_tag
                        strategy = Strategies.query.filter_by(user_id=user_id, strategy_tag=strategy_tag).first()
                        if strategy:
                            strategy.locked_min_profit = 0
                            strategy.reached_profit = 0
                            db.session.commit()

                broker = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                if broker:
                    broker.locked_min_profit = 0
                    broker.reached_profit = 0
                    db.session.commit()
                    
                    db.session.commit()


                return "Square off done ( Portfolio Leg Level ) !"  

            elif "portfolio_name" in self.data.keys() and "portfolio_leg_id" not in self.data.keys():
                portfolio_name = self.data['portfolio_name']
                broker_type = self.data['broker_type']
                broker_user_id = self.data['broker_user_id']
                sell_order_id = random.randint(10**14, 10**15 - 1)

                existing_portfolio = ExecutedPortfolio.query.filter_by(user_id=user_id, portfolio_name=portfolio_name, broker=broker_type, broker_user_id=broker_user_id,square_off=False).all()

                for executed in existing_portfolio:
                    token = executed.symbol_token
                    sell_price = config.angelone_live_ltp[token]
                    executed.sell_price = sell_price
                    executed.square_off = True
                    executed.sell_order_id = sell_order_id
                    executed.squared_off_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executed.netqty = 0 
                    executed.sell_qty = executed.buy_qty
                    
                    db.session.commit()

                return "Square off done ( Portfolio Level ) !"

  

            elif "broker_user_id" and "trading_symbol" in self.data.keys():
                broker_user_id = self.data['broker_user_id']
                trading_symbol = self.data['trading_symbol']
                sell_order_id = random.randint(10**14, 10**15 - 1)
                existing_portfolio = ExecutedPortfolio.query.filter_by(user_id=user_id, broker_user_id=broker_user_id,trading_symbol=trading_symbol,square_off=False).all()

                for executed in existing_portfolio:
                    token = executed.symbol_token
                    sell_price = config.angelone_live_ltp[token]
                    executed.sell_price = sell_price
                    executed.square_off = True
                    executed.sell_order_id = sell_order_id
                    executed.squared_off_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executed.netqty = 0 
                    executed.sell_qty = executed.buy_qty
                    
                    db.session.commit()

                return "Square off done ( Max loss per trade ) !" 

            else:
                broker_user_id = self.data['broker_user_id']
                sell_order_id = random.randint(10**14, 10**15 - 1)
                existing_portfolio = ExecutedPortfolio.query.filter_by(user_id=user_id, broker_user_id=broker_user_id,square_off=False).all()

                for executed in existing_portfolio:
                    token = executed.symbol_token
                    sell_price = config.angelone_live_ltp[token]
                    executed.sell_price = sell_price
                    executed.square_off = True
                    executed.sell_order_id = sell_order_id
                    executed.squared_off_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executed.netqty = 0 
                    executed.sell_qty = executed.buy_qty
                    # executed.locked_min_profit = 0
                    # executed.reached_profit = 0
                    
                    db.session.commit()

                broker = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                if broker:
                    broker.locked_min_profit = 0
                    broker.reached_profit = 0
                    db.session.commit()

                existing_portfolios = ExecutedPortfolio.query.filter_by(user_id=user_id, broker_user_id=broker_user_id,square_off=False).first()
                if existing_portfolios:
                        strategy_tag = existing_portfolios.strategy_tag
                        existing_portfolios.locked_min_profit = 0
                        existing_portfolios.reached_profit = 0
                        db.session.commit()

                        # Update strategy related to this strategy_tag
                        strategy = Strategies.query.filter_by(user_id=user_id, strategy_tag=strategy_tag).first()
                        if strategy:
                            strategy.locked_min_profit = 0
                            strategy.reached_profit = 0
                            db.session.commit()

                return "Square off done ( User Level ) !"     