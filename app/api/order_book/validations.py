
from flask import Blueprint, jsonify, request, abort, Flask
from app.api.brokers import config
from .error_handlers import ERROR_HANDLER
from .routes import ORDERBOOK_ROUTES
from app.models.main import db
from app.api.brokers import config
from urllib.parse import quote_plus
from sqlalchemy.orm import sessionmaker
from app.models.user import Portfolio , BrokerCredentials, Strategies, Portfolio_legs, ExecutedPortfolio,StrategyMultipliers,Performance, ExecutedEquityOrders
from app.models.user import User
from sqlalchemy import or_


class OrderBook:

        def get_orderbook(username):
            data = request.json
            existing_user = User.query.filter_by(username=username).first()

            if not existing_user:
                response_data = ERROR_HANDLER.database_errors("user", "User Does not exist")
                return jsonify(response_data), 404

            angelone_list = []
            for broker_id in data.get('angelone', []):
                try:
                    if len(config.SMART_API_OBJ_angelone) != 0:
                        if broker_id not in config.all_angelone_details.keys():
                            config.all_angelone_details[broker_id] = {}
                        response_data = {broker_id: config.all_angelone_details[broker_id]}
                    else:
                        response_data = {broker_id: {"Message": f"Please login to the broker account {broker_id}"}}
                except Exception as e:
                    response_data = {broker_id: {"Message": str(e)}}
                angelone_list.append(response_data)

            fyers_list = []
            for broker_id in data.get('fyers', []):
                try:
                    if len(config.OBJ_fyers) != 0:
                        if broker_id not in config.fyers_orders_book.keys():
                            config.fyers_orders_book[broker_id] = {}
                        response_data = {broker_id: config.fyers_orders_book[broker_id]}
                    else:
                        response_data = {broker_id: {"Message": f"Please login to the broker account {broker_id}"}}
                except Exception as e:
                    response_data = {broker_id: {"Error": str(e)}}
                fyers_list.append(response_data)

            flattrade_list = []
            for broker_id in data.get('flattrade', []):
                try:
                    if len(config.flattrade_api) != 0:
                        if broker_id not in config.all_flattrade_details.keys():
                            config.all_flattrade_details[broker_id] = {}
                        response_data = {broker_id: config.all_flattrade_details[broker_id]}
                    else:
                        response_data = {broker_id: {"Message": f"Please login to the broker account {broker_id}"}}
                except Exception as e:
                    response_data = {broker_id: {"Message": str(e)}}
                flattrade_list.append(response_data)

            order_list = []
            position_dict = {}
            pseudo_account_data = {}
            pseudo_list = []

            for broker_id in data.get('pseudo_account', []):
                print(broker_id)
                existing_executed_portfolios = ExecutedPortfolio.query.filter_by(user_id=existing_user.id, broker_user_id=broker_id).all()
                existing_equity_orders = ExecutedEquityOrders.query.filter_by(user_id=existing_user.id, broker_user_id=broker_id).all()

                for executed_portfolios in existing_executed_portfolios:
                    # Ensure netqty and prices are treated as integers or floats
                    net_qty = int(executed_portfolios.netqty) if executed_portfolios.netqty is not None else 0
                    buy_qty = int(executed_portfolios.buy_qty) if executed_portfolios.buy_qty is not None else 0
                    sell_qty = int(executed_portfolios.sell_qty) if executed_portfolios.sell_qty is not None else 0
                    buy_price = float(executed_portfolios.buy_price) if executed_portfolios.buy_price is not None else 0.0
                    sell_price = float(executed_portfolios.sell_price) if executed_portfolios.sell_price is not None else 0.0

                    # Order response handling
                    order_response1 = {
                        'orderTag': executed_portfolios.strategy_tag,
                        'symbol': executed_portfolios.trading_symbol,
                        'exchange': executed_portfolios.exchange,
                        'orderDateTime': executed_portfolios.placed_time,
                        'qty': buy_qty if executed_portfolios.transaction_type == "BUY" else sell_qty,
                        'side': executed_portfolios.transaction_type,
                        'tradedPrice': buy_price if executed_portfolios.transaction_type == "BUY" else sell_price,
                        'id': executed_portfolios.order_id,
                        'status': executed_portfolios.status,
                        'token': executed_portfolios.symbol_token,
                        'broker_user_id': executed_portfolios.broker_user_id,
                        'order_type': executed_portfolios.order_type,
                        'wait_sec': executed_portfolios.wait_sec,
                        'wait_action': executed_portfolios.wait_action
                        
                    }
                    order_list.append(order_response1)


                    if executed_portfolios.status != 'OPEN' and executed_portfolios.status != 'CANCELLED':
                        if executed_portfolios.square_off:
                            order_response2 = {
                                'orderTag': executed_portfolios.strategy_tag,
                                'symbol': executed_portfolios.trading_symbol,
                                'exchange': executed_portfolios.exchange,
                                'orderDateTime': executed_portfolios.squared_off_time,
                                'qty': buy_qty if executed_portfolios.transaction_type == "BUY" else sell_qty,
                                'side': executed_portfolios.transaction_type,
                                'tradedPrice': buy_price if executed_portfolios.transaction_type == "BUY" else sell_price,
                                'id': executed_portfolios.sell_order_id,
                                'status': executed_portfolios.status,
                                'order_type': executed_portfolios.order_type
                            }
                            order_list.append(order_response2)

                        # Position response handling
                        if executed_portfolios.trading_symbol not in position_dict:
                            position_dict[executed_portfolios.trading_symbol] = {
                                'productType': executed_portfolios.product_type,
                                'exchange': executed_portfolios.exchange,
                                'symbol': executed_portfolios.trading_symbol,
                                'netQty': net_qty,  # Set initial netQty
                                'buyQty': buy_qty,  # Set initial buyQty
                                'buyAvg': buy_price if buy_qty > 0 else 0.0,
                                'buyVal': buy_price * buy_qty,
                                'sellQty': sell_qty,  # Set initial sellQty
                                'sellAvg': sell_price if sell_qty > 0 else 0.0,
                                'sellVal': sell_price * sell_qty,
                                'realized_profit': 0,
                                'unrealized_profit': 0,
                                'side': "Open" if net_qty != 0 else "Close",
                                'token': executed_portfolios.symbol_token
                                
                            }
                        else:
                            # Update the position entry with the latest executed portfolio data
                            position_entry = position_dict[executed_portfolios.trading_symbol]

                            if not (executed_portfolios.order_type == "LIMIT" or executed_portfolios.order_type == "SL_LIMIT" and executed_portfolios.status == "OPEN"):

                                if executed_portfolios.transaction_type == "BUY":
                                    # Update buyQty, buyVal, and buyAvg
                                    position_entry['buyQty'] += buy_qty
                                    position_entry['buyVal'] += buy_price * buy_qty
                                    position_entry['buyAvg'] = position_entry['buyVal'] / position_entry['buyQty']
                                    position_entry['netQty'] += buy_qty

                                if executed_portfolios.square_off:
                                    # Update sellQty, sellVal, and sellAvg
                                    position_entry['sellQty'] += sell_qty
                                    position_entry['sellVal'] += sell_price * sell_qty
                                    position_entry['sellAvg'] = position_entry['sellVal'] / position_entry['sellQty']
                                    position_entry['netQty'] -= sell_qty

                                    # If netQty becomes 0, set side to Close
                                    if position_entry['netQty'] == 0:
                                        position_entry['side'] = "Close"
                                    else:
                                        position_entry['side'] = "Open"
                                else:
                                    # Ensure netQty is always the difference between buyQty and sellQty
                                    position_entry['netQty'] = position_entry['buyQty'] - position_entry['sellQty']
                                    position_entry['side'] = "Close" if position_entry['netQty'] == 0 else "Open"


                # Process each equity order
                for equity_orders in existing_equity_orders:
                    quantity = int(equity_orders.quantity) if equity_orders.quantity is not None else 0
                    buy_price = float(equity_orders.buy_price) if equity_orders.buy_price is not None else 0.0
                    sell_price = float(equity_orders.sell_price) if equity_orders.sell_price is not None else 0.0

                    # Add the buy order to the order list
                    order_response1 = {
                        'orderTag': equity_orders.strategy_tag,
                        'symbol': equity_orders.trading_symbol,
                        'exchange': "NSE",
                        'orderDateTime': equity_orders.placed_time,
                        'qty': quantity,
                        'side': equity_orders.transaction_type,
                        'tradedPrice': buy_price if equity_orders.transaction_type == "BUY" else sell_price,
                        'id': equity_orders.order_id,
                        'status': equity_orders.status,
                        'order_type':equity_orders.order_type,
                        'token': equity_orders.symbol_token,
                        'broker_user_id': equity_orders.broker_user_id
                    }
                    order_list.append(order_response1)

                    # If the order was squared off, add the sell order to the order list
                    if equity_orders.status != 'OPEN' and equity_orders.status != 'CANCELLED':
                        if equity_orders.square_off:
                            order_response2 = {
                                'orderTag': equity_orders.strategy_tag,
                                'symbol': equity_orders.trading_symbol,
                                'exchange': "NSE",
                                'orderDateTime': equity_orders.squared_off_time,
                                'qty': quantity,
                                'side': "SELL",
                                'tradedPrice': sell_price,
                                'id': equity_orders.sell_order_id,
                                'status': "COMPLETE",
                                'order_type': equity_orders.order_type
                            }
                            order_list.append(order_response2)

                        # Initialize position entry if not already present
                        if equity_orders.trading_symbol not in position_dict:
                            position_dict[equity_orders.trading_symbol] = {
                                'productType': equity_orders.product_type,
                                'exchange': "NSE",
                                'symbol': equity_orders.trading_symbol,
                                'netQty': 0,
                                'buyQty': 0,
                                'buyAvg': 0.0,
                                'buyVal': 0.0,
                                'sellQty': 0,
                                'sellAvg': 0.0,
                                'sellVal': 0.0,
                                'realized_profit': 0,
                                'unrealized_profit': 0,
                                'side': "Open",
                                'token': equity_orders.symbol_token
                            }

                        # Update the position entry with the current equity order details
                        position_entry = position_dict[equity_orders.trading_symbol]

                        if equity_orders.transaction_type == "BUY":
                            # Update buyQty and calculate new average buy price
                            position_entry['buyQty'] += quantity
                            position_entry['netQty'] += quantity
                            position_entry['buyVal'] += buy_price * quantity
                            position_entry['buyAvg'] = position_entry['buyVal'] / position_entry['buyQty']

                        if equity_orders.square_off:
                            # Update sellQty and calculate new average sell price
                            position_entry['sellQty'] += quantity
                            position_entry['netQty'] -= quantity
                            position_entry['sellVal'] += sell_price * quantity
                            position_entry['sellAvg'] = position_entry['sellVal'] / position_entry['sellQty']

                        # Update the side to Close if netQty is zero
                        position_entry['side'] = "Close" if position_entry['netQty'] == 0 else "Open"

                    # Final aggregation after processing all orders
                    for position in position_dict:
                        buy_equity = ExecutedEquityOrders.query.filter_by(trading_symbol=position, transaction_type="BUY").all()
                        
                        if buy_equity:
                            buy_qty_sum = sum(int(equity_orders.quantity) for equity_orders in buy_equity)
                            buy_avg = sum(float(equity_orders.buy_price) * int(equity_orders.quantity) for equity_orders in buy_equity) / buy_qty_sum
                            position_dict[position]['buyQty'] = buy_qty_sum
                            position_dict[position]['buyAvg'] = buy_avg

                        sell_equity = ExecutedEquityOrders.query.filter_by(trading_symbol=position, transaction_type="SELL").all()
                        
                        if sell_equity:
                            sell_qty_sum = sum(int(equity_orders.quantity) for equity_orders in sell_equity)
                            sell_avg = sum(float(equity_orders.sell_price) * int(equity_orders.quantity) for equity_orders in sell_equity) / sell_qty_sum
                            position_dict[position]['sellQty'] = sell_qty_sum
                            position_dict[position]['sellAvg'] = sell_avg
                        
                        position_dict[position]['netQty'] = position_dict[position]['buyQty'] - position_dict[position]['sellQty']
                        position_dict[position]['side'] = "Close" if position_dict[position]['netQty'] == 0 else "Open"
                        
                position_list = list(position_dict.values())

                pseudo_account_data.update({broker_id : {"orderbook": order_list, "positions": position_list}})
                order_list = []
                position_dict = {}
        
            for pseudo_data in pseudo_account_data:
                pseudo_list.append({pseudo_data : pseudo_account_data[pseudo_data]})

            return jsonify({"angelone": angelone_list, "fyers": fyers_list, "flattrade": flattrade_list, "pseudo_account": pseudo_list}), 200



        def update_pseudo_limit_order_status(username):
            try:
                # Get the input data (assuming order_id is passed in the request)
                data = request.json
                order_id = data.get('order_id')
                broker_user_id = data.get('broker_user_id')
                exchange = data.get('exchange')
                existing_user = User.query.filter_by(username=username).first()

                if not existing_user:
                    response_data = ERROR_HANDLER.database_errors("user", "User Does not exist")
                    return jsonify(response_data), 404

                if exchange == 'NSE':
                    limit_order = ExecutedEquityOrders.query.filter_by(order_id=order_id, status='OPEN', order_type='LIMIT').first()

                    if not limit_order:
                       return jsonify({"message": "No open limit order found with this ID"}), 404 

                    from datetime import datetime
                    # Update the limit order status to COMPLETE
                    limit_order.status = 'COMPLETE'
                    limit_order.placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    db.session.commit()

                    return jsonify({
                        "message": f"Order {order_id} placed successfully."
                    })

                else:

                    # Retrieve the existing limit order from the database
                    # limit_order = ExecutedPortfolio.query.filter_by(order_id=order_id, status='OPEN', order_type='LIMIT').first()
                    limit_order = ExecutedPortfolio.query.filter_by(order_id=order_id, status='OPEN').filter(
                        or_(ExecutedPortfolio.order_type == 'LIMIT', ExecutedPortfolio.order_type == 'SL_LIMIT')
                    ).first()
                    
                    if not limit_order:
                        return jsonify({"message": "No open order found with this ID"}), 404                                     
    
                    from datetime import datetime
                    # Update the limit order status to COMPLETE
                    limit_order.status = 'COMPLETE'
                    limit_order.placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    db.session.commit()

                    portfolio_name = limit_order.portfolio_name
                    broker_user_id_from_order = limit_order.broker_user_id
                    product_type = limit_order.product_type
                    user_id = limit_order.user_id

                    from datetime import datetime, time

                    def create_performance_record(portfolio_name, user_id, broker_user_id, max_pl, min_pl, product_type):
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

                    create_performance_record(
                                portfolio_name=portfolio_name,
                                user_id=user_id,
                                broker_user_id=broker_user_id_from_order,
                                max_pl=float('-inf'),  # Set initial max profit and loss values
                                min_pl=float('+inf'),
                                product_type=product_type
                            )

                            # Commit all changes to the database
                    db.session.commit()

                    # Add position response to the final output
                    return jsonify({
                        "message": f"Order {order_id} placed successfully."
                    })

            except Exception as e:
                return jsonify({"message": f"Error occurred: {str(e)}"}), 500



        def cancel_portfolio_orders(username,order_id):
            
            try:
                data = request.json
                exchange = data.get('exchange')
                # Fetch existing user
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                    return jsonify(response_data), 404
            
                user_id = existing_user.id

                if exchange == "NSE":

                    executed_order = ExecutedEquityOrders.query.filter_by(user_id=user_id,order_id=order_id).first()
                    print("executed_order:", executed_order)
                    if not executed_order:
                        response_data = ERROR_HANDLER.database_errors("executed_portfolio", "No open positions found.")
                        return jsonify(response_data), 200
                    broker_type = executed_order.broker
                    broker_user_id = executed_order.broker_user_id

                    try:
                        if broker_type == "pseudo_account":
                            try:
                                pseudo = broker_user_id
                                print("pseudo:", pseudo)

                            except KeyError:
                                response_data = {'message': "Broker user ID not found"}  # Set response_data in case of KeyError
                                return jsonify(response_data), 500
                
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                    executed_order.square_off = True
                                    executed_order.status = 'CANCELLED'
                                    from datetime import datetime
                                    executed_order.placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                    broker_credential = BrokerCredentials.query.filter_by(user_id=user_id,broker_user_id=broker_user_id).first()
                                    if not broker_credential:
                                        return jsonify({"message": "Broker credentials not found"}), 404

                                    # Parse margin_req
                                    margin_req = float(executed_order.margin_req) if executed_order.margin_req else 0.0

                                    # Update broker credentials
                                    current_utilized_margin = float(broker_credential.utilized_margin) if broker_credential.utilized_margin else 0.0
                                    current_available_balance = float(broker_credential.available_balance) if broker_credential.available_balance else 0.0

                                    # Adjust margins
                                    broker_credential.utilized_margin = str(max(current_utilized_margin - margin_req, 0))
                                    broker_credential.available_balance = str(current_available_balance + margin_req)
                                    db.session.commit()
                                    response_data = {'message': f"Order cancelled {order_id} successfully"}
                                    return jsonify(response_data), 200
                            else:
                                response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", 'order cancelling failed.')
                                return jsonify(response_data), 200

                    except KeyError:
                        response_data = ERROR_HANDLER.flask_api_errors("cancel_portfolio_orders", "Broker user ID not found.")
                        return jsonify(response_data), 500

                else:

                    executed_order = ExecutedPortfolio.query.filter_by(user_id=user_id,order_id=order_id).first()
                    print("executed_order:", executed_order)
                    if not executed_order:
                        response_data = ERROR_HANDLER.database_errors("executed_portfolio", "No open positions found.")
                        return jsonify(response_data), 200
                    broker_type = executed_order.broker
                    broker_user_id = executed_order.broker_user_id
                
                
                    try:
                        if broker_type == "flattrade":
                            try:
                                flattrade = config.flattrade_api[broker_user_id]
                            except KeyError:
                                response = ERROR_HANDLER.broker_api_errors("flattrade", "Broker user ID not found") 
                                response_data = {"error": response['message']}
                                return jsonify(response_data), 500
        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                flattrade_cancel_order = flattrade.cancel_order(orderno=order_id)
                            
                                order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                                positions_info = config.flattrade_api[broker_user_id].get_positions()
                                holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                            
                                config.all_flattrade_details[broker_user_id] = {
                                    'orderbook': order_book_send,
                                    "holdings": holdings_info,
                                    "positions": positions_info
                                }
        
                                if flattrade_cancel_order['stat'] == 'Ok':
                                    executed_order.square_off = True
                                    executed_order.status = 'CANCELLED'
                                    db.session.commit()
                                    response_data = {'message': 'order cancelled successfully', 'order_cancelled': flattrade_cancel_order}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = ERROR_HANDLER.broker_api_errors("flattrade", 'order cancelling failed.')
                                    return jsonify(response_data), 200
        
                        elif broker_type == "angelone":
                            try:
                                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                            except KeyError:
                                response = ERROR_HANDLER.broker_api_errors("angelone", "Broker user ID not found")
                                response_data = {"error": response['message']}
                                return jsonify(response_data), 500
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                orderid = executed_order.order_id    
                                variety = executed_order.variety    
                                angelone_cancel_order = angelone.cancelOrder(orderid, variety)
                                print(angelone_cancel_order)
                            
                                order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                                positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                                holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                                all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                                config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions, "holdings": holdings, "all_holdings": all_holdings}
        
                                if angelone_cancel_order['message'] == 'SUCCESS':
                                    executed_order.square_off = True
                                    executed_order.status = 'CANCELLED'
                                    db.session.commit()
                                    response_data = {'message': 'order cancelled successfully', 'order_cancelled': angelone_cancel_order}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = {'message': 'order cancelling failed.'}
                                    return jsonify(response_data), 200
        
                        elif broker_type == "fyers":
                            try:
                                fyers = config.OBJ_fyers[broker_user_id]
                                print(fyers)
                            except KeyError:
                                response =  ERROR_HANDLER.broker_api_errors("fyers", "Broker user ID not found")
                                return jsonify(response_data), 500
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                data = {
                                    'id': order_id
                                }
                                square_off = fyers.cancel_order(data)
                                print(square_off)
                            
                                fyers_order = config.OBJ_fyers[broker_user_id].orderbook()
                                fyers_position = config.OBJ_fyers[broker_user_id].positions()
                                fyers_holdings = config.OBJ_fyers[broker_user_id].holdings()
                                config.fyers_orders_book[broker_user_id] = {"orderbook": fyers_order, "positions": fyers_position, "holdings": fyers_holdings}
        
                                if square_off['s'] == 'ok':
                                    executed_order.square_off = True
                                    executed_order.status = 'CANCELLED'
                                    db.session.commit()
                                    response_data = {'message': 'order cancelled successfully', 'order_cancelled': square_off}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = ERROR_HANDLER.broker_api_errors("fyers", 'order cancelling failed.')
                                    return jsonify(response_data), 200

                        elif broker_type == "pseudo_account":
                            try:
                                pseudo = broker_user_id
                                print("pseudo:", pseudo)

                            except KeyError:
                                response_data = {'message': "Broker user ID not found"}  # Set response_data in case of KeyError
                                return jsonify(response_data), 500
                
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                    executed_order.square_off = True
                                    executed_order.status = 'CANCELLED'
                                    from datetime import datetime
                                    executed_order.placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                    broker_credential = BrokerCredentials.query.filter_by(user_id=user_id,broker_user_id=broker_user_id).first()
                                    if not broker_credential:
                                        return jsonify({"message": "Broker credentials not found"}), 404

                                    # Parse margin_req
                                    margin_req = float(executed_order.margin_req) if executed_order.margin_req else 0.0

                                    # Update broker credentials
                                    current_utilized_margin = float(broker_credential.utilized_margin) if broker_credential.utilized_margin else 0.0
                                    current_available_balance = float(broker_credential.available_balance) if broker_credential.available_balance else 0.0

                                    # Adjust margins
                                    broker_credential.utilized_margin = str(max(current_utilized_margin - margin_req, 0))
                                    broker_credential.available_balance = str(current_available_balance + margin_req)

                                    db.session.commit()
                                    response_data = {'message': f"Order cancelled {order_id} successfully"}
                                    return jsonify(response_data), 200
                            else:
                                response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", 'order cancelling failed.')
                                return jsonify(response_data), 200
        
                    except KeyError:
                        response_data = ERROR_HANDLER.flask_api_errors("cancel_portfolio_orders", "Broker user ID not found.")
                        return jsonify(response_data), 500
            
            except KeyError:
                response_data = ERROR_HANDLER.flask_api_errors("cancel_portfolio_orders", "Broker user ID not found.")
                return jsonify(response_data), 500


        def modify_portfolio_orders(username,order_id):
            
            try:
                index_data = config.index_data
                data = request.json
                # order_id = data.get('order_id')
                # broker_user_id = data.get('broker_user_id')
                new_price = data.get('new_price')
                new_quantity = data.get('new_quantity')
                exchange = data.get('exchange')
                # Fetch existing user
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                    return jsonify(response_data), 404
            
                user_id = existing_user.id

                if exchange == "NSE":
                    executed_order = ExecutedEquityOrders.query.filter_by(user_id=user_id,order_id=order_id).first()
                    print("executed_order:", executed_order)
                    if not executed_order:
                        response_data = {'message': "No open positions found"}
                        
                        return jsonify(response_data), 200
                    broker_type = executed_order.broker
                    broker_user_id = executed_order.broker_user_id
                    transaction_type = executed_order.transaction_type

                    try:

                        if broker_type == "pseudo_account":
                            try:
                                pseudo = broker_user_id
                                print("pseudo:", pseudo)
                            except KeyError:
                                response_data = {'message': "Broker user ID not found"}  # Set response_data in case of KeyError
                                return jsonify(response_data), 500

                            
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                    executed_order.buy_qty = new_quantity if transaction_type == "BUY" else 0
                                    executed_order.sell_qty = new_quantity if transaction_type == "SELL" else 0
                                    executed_order.quantity = new_quantity
                                    executed_order.buy_price = new_price if transaction_type == "BUY" else 0
                                    executed_order.sell_price = new_price if transaction_type == "SELL" else 0

                                    from datetime import datetime
                                    executed_order.placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                    try:
                                        # Calculate new margin requirement
                                        margin_req = float(new_price) * int(new_quantity)
                                        old_margin_req = float(executed_order.margin_req) if executed_order.margin_req else 0.0
                                        executed_order.margin_req = margin_req
                                        print(f"Old Margin Requirement: {old_margin_req}")
                                        print(f"New Margin Requirement: {margin_req}")

                                        # Fetch broker credentials
                                        broker_credential = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                                        if not broker_credential:
                                            return jsonify({"message": "Broker credentials not found"}), 404

                                        # Retrieve current margins
                                        current_utilized_margin = float(broker_credential.utilized_margin) if broker_credential.utilized_margin else 0.0
                                        current_available_balance = float(broker_credential.available_balance) if broker_credential.available_balance else 0.0

                                        print(f"Current Utilized Margin: {current_utilized_margin}")
                                        print(f"Current Available Balance: {current_available_balance}")

                                        # Adjust margins: subtract old margin and add new margin
                                        new_current_utilized_margin = current_utilized_margin - old_margin_req + margin_req
                                        new_current_available_balance = current_available_balance + old_margin_req - margin_req

                                        print(f"Adjusted Utilized Margin: {new_current_utilized_margin}")
                                        print(f"Adjusted Available Balance: {new_current_available_balance}")

                                        # Update broker credentials
                                        broker_credential.utilized_margin = str(max(new_current_utilized_margin, 0))
                                        broker_credential.available_balance = str(new_current_available_balance)

                                        print(f"Updated Utilized Margin: {broker_credential.utilized_margin}")
                                        print(f"Updated Available Balance: {broker_credential.available_balance}")

                                        # Commit changes to the database
                                        db.session.commit()
                                        print("Changes committed to the database.")

                                    except (ValueError, TypeError) as e:
                                        # Rollback in case of error
                                        db.session.rollback()
                                        response_data = {'message': f"Error calculating margin requirement: {str(e)}"}
                                        return jsonify(response_data), 400

                                    
                                    # db.session.commit()
                                    response_data = {'message': f"Limit order Modified {order_id} successfully"}
                                    return jsonify(response_data), 200
                            else:
                                response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", 'order Modification failed.')
                                return jsonify(response_data), 200
                            
        
                    except KeyError:
                        response_data = ERROR_HANDLER.flask_api_errors("modify_portfolio_orders", "Broker user ID not found.")
                        return jsonify(response_data), 500

            
                else:
    
                    executed_order = ExecutedPortfolio.query.filter_by(user_id=user_id,order_id=order_id).first()
                    print("executed_order:", executed_order)
                    if not executed_order:
                        response_data = ERROR_HANDLER.database_errors("executed_portfolio", "No open positions found.")
                        return jsonify(response_data), 200
                    broker_type = executed_order.broker
                    broker_user_id = executed_order.broker_user_id
                    portfolio_name = executed_order.portfolio_name
                    transaction_type = executed_order.transaction_type


                    executed_portfolio = Portfolio.query.filter_by(portfolio_name=portfolio_name).first()
                    executed_portfoliolegs = Portfolio_legs.query.filter_by(portfolio_name=portfolio_name).first()
                    print("executed_portfoliolegs:",executed_portfoliolegs)
        
                    if not executed_portfolio or not executed_portfoliolegs:
                        response_data = ERROR_HANDLER.database_errors("portfolio", "No portfolio found.")
                        return jsonify(response_data), 200

                    leg_quantity = executed_portfoliolegs.quantity
                
                
                    try:
                        if broker_type == "flattrade":
                            try:
                                flattrade = config.flattrade_api[broker_user_id]
                            except KeyError:
                                response = ERROR_HANDLER.broker_api_errors("flattrade", "Broker user ID not found") 
                                response_data = {"error": response['message']}
                                return jsonify(response_data), 500
        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                flattrade_cancel_order = flattrade.cancel_order(orderno=order_id)
                            
                                order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                                positions_info = config.flattrade_api[broker_user_id].get_positions()
                                holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                            
                                config.all_flattrade_details[broker_user_id] = {
                                    'orderbook': order_book_send,
                                    "holdings": holdings_info,
                                    "positions": positions_info
                                }
        
                                if flattrade_cancel_order['stat'] == 'Ok':
                                    # executed_order.square_off = True
                                    # executed_order.status = 'CANCELLED'
                                    # db.session.commit()
                                    response_data = {'message': 'order cancelled successfully', 'order_cancelled': flattrade_cancel_order}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = ERROR_HANDLER.broker_api_errors("flattrade", 'order cancelling failed.')
                                    return jsonify(response_data), 200
        
                        elif broker_type == "angelone":
                            try:
                                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                            except KeyError:
                                response = ERROR_HANDLER.broker_api_errors("angelone", "Broker user ID not found")
                                response_data = {"error": response['message']}
                                return jsonify(response_data), 500
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                orderid = executed_order.order_id    
                                variety = executed_order.variety    
                                angelone_cancel_order = angelone.cancelOrder(orderid, variety)
                                print(angelone_cancel_order)
                            
                                order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                                positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                                holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                                all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                                # config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions, "holdings": holdings, "all_holdings": all_holdings}
        
                                # if angelone_cancel_order['message'] == 'SUCCESS':
                                #     executed_order.square_off = True
                                #     executed_order.status = 'CANCELLED'
                                #     db.session.commit()
                                #     response_data = {'message': 'order cancelled successfully', 'order_cancelled': angelone_cancel_order}
                                #     return jsonify(response_data), 200
                                # else:
                                #     response_data = {'message': 'order cancelling failed.'}
                                #     return jsonify(response_data), 200
        
                        elif broker_type == "fyers":
                            try:
                                fyers = config.OBJ_fyers[broker_user_id]
                                print(fyers)
                            except KeyError:
                                response =  ERROR_HANDLER.broker_api_errors("fyers", "Broker user ID not found")
                                return jsonify(response_data), 500
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                data = {
                                    'id': order_id
                                }
                                # square_off = fyers.cancel_order(data)
                                # print(square_off)
                            
                                # fyers_order = config.OBJ_fyers[broker_user_id].orderbook()
                                # fyers_position = config.OBJ_fyers[broker_user_id].positions()
                                # fyers_holdings = config.OBJ_fyers[broker_user_id].holdings()
                                # config.fyers_orders_book[broker_user_id] = {"orderbook": fyers_order, "positions": fyers_position, "holdings": fyers_holdings}
        
                                # if square_off['s'] == 'ok':
                                #     executed_order.square_off = True
                                #     executed_order.status = 'CANCELLED'
                                #     db.session.commit()
                                #     response_data = {'message': 'order cancelled successfully', 'order_cancelled': square_off}
                                #     return jsonify(response_data), 200
                                # else:
                                #     response_data = ERROR_HANDLER.broker_api_errors("fyers", 'order cancelling failed.')
                                #     return jsonify(response_data), 200

                        elif broker_type == "pseudo_account":
                            try:
                                pseudo = broker_user_id
                                print("pseudo:", pseudo)
                            except KeyError:
                                response_data = {'message': "Broker user ID not found"}  # Set response_data in case of KeyError
                                return jsonify(response_data), 500

                            
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                    executed_order.buy_qty = new_quantity if transaction_type == "BUY" else 0
                                    executed_order.sell_qty = new_quantity if transaction_type == "SELL" else 0
                                    executed_order.buy_price = new_price if transaction_type == "BUY" else 0
                                    executed_order.sell_price = new_price if transaction_type == "SELL" else 0
                                    executed_order.netqty = new_quantity
                                    executed_portfoliolegs.quantity = new_quantity
                                    executed_portfoliolegs.limit_price = new_price

                                    from datetime import datetime
                                    executed_order.placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                    try:
                                        # Calculate new margin requirement
                                        margin_req = float(new_price) * int(new_quantity)
                                        old_margin_req = float(executed_order.margin_req) if executed_order.margin_req else 0.0
                                        executed_order.margin_req = margin_req
                                        print(f"Old Margin Requirement: {old_margin_req}")
                                        print(f"New Margin Requirement: {margin_req}")

                                        # Fetch broker credentials
                                        broker_credential = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                                        if not broker_credential:
                                            return jsonify({"message": "Broker credentials not found"}), 404

                                        # Retrieve current margins
                                        current_utilized_margin = float(broker_credential.utilized_margin) if broker_credential.utilized_margin else 0.0
                                        current_available_balance = float(broker_credential.available_balance) if broker_credential.available_balance else 0.0

                                        print(f"Current Utilized Margin: {current_utilized_margin}")
                                        print(f"Current Available Balance: {current_available_balance}")

                                        # Adjust margins: subtract old margin and add new margin
                                        new_current_utilized_margin = current_utilized_margin - old_margin_req + margin_req
                                        new_current_available_balance = current_available_balance + old_margin_req - margin_req

                                        print(f"Adjusted Utilized Margin: {new_current_utilized_margin}")
                                        print(f"Adjusted Available Balance: {new_current_available_balance}")

                                        # Update broker credentials
                                        broker_credential.utilized_margin = str(max(new_current_utilized_margin, 0))
                                        broker_credential.available_balance = str(new_current_available_balance)

                                        print(f"Updated Utilized Margin: {broker_credential.utilized_margin}")
                                        print(f"Updated Available Balance: {broker_credential.available_balance}")

                                        # Commit changes to the database
                                        db.session.commit()
                                        print("Changes committed to the database.")

                                    except (ValueError, TypeError) as e:
                                        # Rollback in case of error
                                        db.session.rollback()
                                        response_data = {'message': f"Error calculating margin requirement: {str(e)}"}
                                        return jsonify(response_data), 400

                                    
                                    exchange_type = executed_portfolio.symbol

                                    # List of valid indices
                                    valid_indices = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX']
                                    exchange_name = None

                                    # Loop through valid indices and check if the trading symbol starts with any of them
                                    for index in valid_indices:
                                        if exchange_type.startswith(index):
                                            exchange_name = index
                                            break  # Exit the loop once a match is found

                                    # If no valid exchange name is found, return an error
                                    if exchange_name is None:
                                        response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", "Invalid trading symbol.")
                                        return jsonify(response_data), 400

                                    print(f"Exchange Type: {exchange_name}")

                                    if exchange_name in index_data:
                                        lot_size = int(index_data[exchange_name])
                                        # Update lots based on new quantity and lot size
                                        executed_portfoliolegs.lots = str(new_quantity // lot_size)
                                    else:
                                        response_data = {'message': "Lot size not found for the given exchange"}
                                        return jsonify(response_data), 400
                                        

                                    db.session.commit()
                                    response_data = {'message': f"order Modified {order_id} successfully"}
                                    return jsonify(response_data), 200
                            else:
                                response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", 'order Modification failed.')
                                return jsonify(response_data), 200
                            
        
                    except KeyError:
                        response_data = ERROR_HANDLER.flask_api_errors("modify_portfolio_orders", "Broker user ID not found.")
                        return jsonify(response_data), 500
            
            except KeyError:
                response_data = ERROR_HANDLER.flask_api_errors("modify_portfolio_orders", "Broker user ID not found.")
                return jsonify(response_data), 500

        def execute_at_market_orders(username,order_id):
            
            try:
                index_data = config.index_data
                data = request.json
                # order_id = data.get('order_id')
                # broker_user_id = data.get('broker_user_id')
                current_ltp = data.get('current_ltp')
                new_quantity = data.get('new_quantity')
                exchange = data.get('exchange')
                # Fetch existing user
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                    return jsonify(response_data), 404
            
                user_id = existing_user.id

                if exchange == 'NSE':
                    executed_order = ExecutedEquityOrders.query.filter_by(user_id=user_id,order_id=order_id).first()
                    print("executed_order:", executed_order)
                    if not executed_order:
                        response_data = {'message': "No open positions found"}
                        return jsonify(response_data), 200

                    broker_type = executed_order.broker
                    broker_user_id = executed_order.broker_user_id
                    transaction_type = executed_order.transaction_type

                    try:    
                        if broker_type == 'pseudo_account':
                            try:
                                pseudo = broker_user_id
                                print("pseudo:", pseudo)

                            except KeyError:
                                response_data = {'message': "Broker user ID not found"}  # Set response_data in case of KeyError
                                return jsonify(response_data), 500
                               
                            
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                executed_order.buy_qty = new_quantity if transaction_type == 'BUY' else 0
                                executed_order.sell_qty = new_quantity if transaction_type == 'SELL' else 0
                                executed_order.buy_price = current_ltp if transaction_type == 'BUY' else 0
                                executed_order.sell_price = current_ltp if transaction_type == 'SELL' else 0
                    
                                executed_order.quantity = new_quantity
                                executed_order.status = "COMPLETE"
                                executed_order.order_type = "MARKET"
                                
                            
                                from datetime import datetime
                                executed_order.placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                db.session.commit()


                                try:
                                    # Calculate new margin requirement
                                    margin_req = float(current_ltp) * int(new_quantity)
                                    old_margin_req = float(executed_order.margin_req) if executed_order.margin_req else 0.0
                                    executed_order.margin_req = margin_req
                                    print(f"Old Margin Requirement: {old_margin_req}")
                                    print(f"New Margin Requirement: {margin_req}")

                                    # Fetch broker credentials
                                    broker_credential = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                                    if not broker_credential:
                                        return jsonify({"message": "Broker credentials not found"}), 404

                                    # Retrieve current margins
                                    current_utilized_margin = float(broker_credential.utilized_margin) if broker_credential.utilized_margin else 0.0
                                    current_available_balance = float(broker_credential.available_balance) if broker_credential.available_balance else 0.0

                                    print(f"Current Utilized Margin: {current_utilized_margin}")
                                    print(f"Current Available Balance: {current_available_balance}")

                                    # Adjust margins: subtract old margin and add new margin
                                    new_current_utilized_margin = current_utilized_margin - old_margin_req + margin_req
                                    new_current_available_balance = current_available_balance + old_margin_req - margin_req

                                    print(f"Adjusted Utilized Margin: {new_current_utilized_margin}")
                                    print(f"Adjusted Available Balance: {new_current_available_balance}")

                                    # Update broker credentials
                                    broker_credential.utilized_margin = str(max(new_current_utilized_margin, 0))
                                    broker_credential.available_balance = str(new_current_available_balance)

                                    print(f"Updated Utilized Margin: {broker_credential.utilized_margin}")
                                    print(f"Updated Available Balance: {broker_credential.available_balance}")

                                    # Commit changes to the database
                                    db.session.commit()
                                    print("Changes committed to the database.")

                                except (ValueError, TypeError) as e:
                                    # Rollback in case of error
                                    db.session.rollback()
                                    response_data = {'message': f"Error calculating margin requirement: {str(e)}"}
                                    return jsonify(response_data), 400

                                response_data = {'message': f"Order executed at Market Price {order_id} successfully"}
                                return jsonify(response_data), 200
                            else:
                                response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", 'order Modification failed.')
                                return jsonify(response_data), 200

                    except KeyError:
                        response_data = ERROR_HANDLER.flask_api_errors("execute_at_market_orders", "Broker user ID not found.")
                        return jsonify(response_data), 500
                        

                else:
    
                    executed_order = ExecutedPortfolio.query.filter_by(user_id=user_id,order_id=order_id).first()
                    print("executed_order:", executed_order)
                    if not executed_order:
                        response_data = ERROR_HANDLER.database_errors("executed_portfolio", "No open positions found.")
                        return jsonify(response_data), 200
                    broker_type = executed_order.broker
                    broker_user_id = executed_order.broker_user_id
                    portfolio_name = executed_order.portfolio_name


                    executed_portfolio = Portfolio.query.filter_by(portfolio_name=portfolio_name).first()
                    executed_portfoliolegs = Portfolio_legs.query.filter_by(portfolio_name=portfolio_name).first()
                    print("executed_portfoliolegs:",executed_portfoliolegs)
        
                    if not executed_portfolio or not executed_portfoliolegs:
                        response_data = ERROR_HANDLER.database_errors("portfolio", "No portfolio found.")
                        return jsonify(response_data), 200

                    leg_quantity = executed_portfoliolegs.quantity
                
                
                    try:
                        if broker_type == "flattrade":
                            try:
                                flattrade = config.flattrade_api[broker_user_id]
                            except KeyError:
                                response = ERROR_HANDLER.broker_api_errors("flattrade", "Broker user ID not found") 
                                response_data = {"error": response['message']}
                                return jsonify(response_data), 500
        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                flattrade_cancel_order = flattrade.cancel_order(orderno=order_id)
                            
                                order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                                positions_info = config.flattrade_api[broker_user_id].get_positions()
                                holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                            
                                config.all_flattrade_details[broker_user_id] = {
                                    'orderbook': order_book_send,
                                    "holdings": holdings_info,
                                    "positions": positions_info
                                }
        
                                if flattrade_cancel_order['stat'] == 'Ok':
                                    # executed_order.square_off = True
                                    # executed_order.status = 'CANCELLED'
                                    # db.session.commit()
                                    response_data = {'message': 'order cancelled successfully', 'order_cancelled': flattrade_cancel_order}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = ERROR_HANDLER.broker_api_errors("flattrade", 'order cancelling failed.')
                                    return jsonify(response_data), 200
        
                        elif broker_type == "angelone":
                            try:
                                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                            except KeyError:
                                response = ERROR_HANDLER.broker_api_errors("angelone", "Broker user ID not found")
                                response_data = {"error": response['message']}
                                return jsonify(response_data), 500
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                orderid = executed_order.order_id    
                                variety = executed_order.variety    
                                angelone_cancel_order = angelone.cancelOrder(orderid, variety)
                                print(angelone_cancel_order)
                            
                                order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                                positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                                holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                                all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                                # config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions, "holdings": holdings, "all_holdings": all_holdings}
        
                                # if angelone_cancel_order['message'] == 'SUCCESS':
                                #     executed_order.square_off = True
                                #     executed_order.status = 'CANCELLED'
                                #     db.session.commit()
                                #     response_data = {'message': 'order cancelled successfully', 'order_cancelled': angelone_cancel_order}
                                #     return jsonify(response_data), 200
                                # else:
                                #     response_data = {'message': 'order cancelling failed.'}
                                #     return jsonify(response_data), 200
        
                        elif broker_type == "fyers":
                            try:
                                fyers = config.OBJ_fyers[broker_user_id]
                                print(fyers)
                            except KeyError:
                                response =  ERROR_HANDLER.broker_api_errors("fyers", "Broker user ID not found")
                                return jsonify(response_data), 500
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                data = {
                                    'id': order_id
                                }
                                # square_off = fyers.cancel_order(data)
                                # print(square_off)
                            
                                # fyers_order = config.OBJ_fyers[broker_user_id].orderbook()
                                # fyers_position = config.OBJ_fyers[broker_user_id].positions()
                                # fyers_holdings = config.OBJ_fyers[broker_user_id].holdings()
                                # config.fyers_orders_book[broker_user_id] = {"orderbook": fyers_order, "positions": fyers_position, "holdings": fyers_holdings}
        
                                # if square_off['s'] == 'ok':
                                #     executed_order.square_off = True
                                #     executed_order.status = 'CANCELLED'
                                #     db.session.commit()
                                #     response_data = {'message': 'order cancelled successfully', 'order_cancelled': square_off}
                                #     return jsonify(response_data), 200
                                # else:
                                #     response_data = ERROR_HANDLER.broker_api_errors("fyers", 'order cancelling failed.')
                                #     return jsonify(response_data), 200

                        elif broker_type == "pseudo_account":
                            try:
                                pseudo = broker_user_id
                                print("pseudo:", pseudo)
                            except KeyError:
                                response_data = {'message': "Broker user ID not found"}  # Set response_data in case of KeyError
                                return jsonify(response_data), 500

                            
                        
                            if not executed_order.square_off and executed_order.status.upper() == 'OPEN':
                                    executed_order.buy_qty = new_quantity
                                    executed_order.buy_price = current_ltp
                                    executed_order.netqty = new_quantity
                                    executed_portfoliolegs.quantity = new_quantity
                                    executed_order.status = "COMPLETE"
                                    executed_order.order_type = "MARKET"
                                    executed_portfoliolegs.limit_price = 0
                                    executed_portfolio.order_type = "MARKET"
                                    

                                    from datetime import datetime
                                    executed_order.placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
                                    try:
                                        # Calculate new margin requirement
                                        margin_req = float(current_ltp) * int(new_quantity)
                                        old_margin_req = float(executed_order.margin_req) if executed_order.margin_req else 0.0
                                        executed_order.margin_req = margin_req
                                        print(f"Old Margin Requirement: {old_margin_req}")
                                        print(f"New Margin Requirement: {margin_req}")

                                        # Fetch broker credentials
                                        broker_credential = BrokerCredentials.query.filter_by(user_id=user_id, broker_user_id=broker_user_id).first()
                                        if not broker_credential:
                                            return jsonify({"message": "Broker credentials not found"}), 404

                                        # Retrieve current margins
                                        current_utilized_margin = float(broker_credential.utilized_margin) if broker_credential.utilized_margin else 0.0
                                        current_available_balance = float(broker_credential.available_balance) if broker_credential.available_balance else 0.0

                                        print(f"Current Utilized Margin: {current_utilized_margin}")
                                        print(f"Current Available Balance: {current_available_balance}")

                                        # Adjust margins: subtract old margin and add new margin
                                        new_current_utilized_margin = current_utilized_margin - old_margin_req + margin_req
                                        new_current_available_balance = current_available_balance + old_margin_req - margin_req

                                        print(f"Adjusted Utilized Margin: {new_current_utilized_margin}")
                                        print(f"Adjusted Available Balance: {new_current_available_balance}")

                                        # Update broker credentials
                                        broker_credential.utilized_margin = str(max(new_current_utilized_margin, 0))
                                        broker_credential.available_balance = str(new_current_available_balance)

                                        print(f"Updated Utilized Margin: {broker_credential.utilized_margin}")
                                        print(f"Updated Available Balance: {broker_credential.available_balance}")

                                        # Commit changes to the database
                                        db.session.commit()
                                        print("Changes committed to the database.")

                                    except (ValueError, TypeError) as e:
                                        # Rollback in case of error
                                        db.session.rollback()
                                        response_data = {'message': f"Error calculating margin requirement: {str(e)}"}
                                        return jsonify(response_data), 400

                                    exchange_type = executed_portfolio.symbol

                                    # List of valid indices
                                    valid_indices = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX']
                                    exchange_name = None

                                    # Loop through valid indices and check if the trading symbol starts with any of them
                                    for index in valid_indices:
                                        if exchange_type.startswith(index):
                                            exchange_name = index
                                            break  # Exit the loop once a match is found

                                    # If no valid exchange name is found, return an error
                                    if exchange_name is None:
                                        response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", "Invalid trading symbol.")
                                        return jsonify(response_data), 400

                                    print(f"Exchange Type: {exchange_name}")

                                    if exchange_name in index_data:
                                        lot_size = int(index_data[exchange_name])
                                        # Update lots based on new quantity and lot size
                                        executed_portfoliolegs.lots = str(new_quantity // lot_size)
                                    else:
                                        response_data = {'message': "Lot size not found for the given exchange"}
                                        return jsonify(response_data), 400
                                        

                                    db.session.commit()
                                    response_data = {'message': f"Order executed at Market {order_id} successfully"}
                                    return jsonify(response_data), 200
                            else:
                                response_data = ERROR_HANDLER.broker_api_errors("pseudo_account", 'order Modification failed.')
                                return jsonify(response_data), 200
                            
        
                    except KeyError:
                        response_data = ERROR_HANDLER.flask_api_errors("execute_at_market_orders", "Broker user ID not found.")
                        return jsonify(response_data), 500
            
            except KeyError:
                response_data = ERROR_HANDLER.flask_api_errors("execute_at_market_orders", "Broker user ID not found.")
                return jsonify(response_data), 500


order_book_blueprint = Blueprint('order_book_blueprint', __name__)
@order_book_blueprint.route(ORDERBOOK_ROUTES.get_routes("order_book_blueprint"), methods=['POST'])
def order_book(username):
    order_book_response = OrderBook.get_orderbook(username=username)
    return order_book_response




pseudo_limit_order_status_blueprint = Blueprint('pseudo_limit_order_status_blueprint', __name__)
@pseudo_limit_order_status_blueprint.route(ORDERBOOK_ROUTES.get_routes("pseudo_limit_order_status_blueprint"), methods=['POST'])
def pseudo_limit_order_status(username):
    update_pseudo_limit_order_status_response = OrderBook.update_pseudo_limit_order_status(username=username)
    return update_pseudo_limit_order_status_response


cancel_portfolio_orders_blueprint = Blueprint('cancel_portfolio_orders_blueprint', __name__)
@cancel_portfolio_orders_blueprint.route(ORDERBOOK_ROUTES.get_routes("cancel_portfolio_orders_blueprint"), methods=['POST'])
def cancel_portfolio_orders(username,order_id):
    cancel_portfolio_orders_response, status_code = OrderBook.cancel_portfolio_orders(username,order_id)
    return cancel_portfolio_orders_response, status_code


modify_portfolio_orders_blueprint = Blueprint('modify_portfolio_orders_blueprint', __name__)
@modify_portfolio_orders_blueprint.route(ORDERBOOK_ROUTES.get_routes("modify_portfolio_orders_blueprint"), methods=['POST'])
def modify_portfolio_orders(username,order_id):
    modify_portfolio_orders_response, status_code = OrderBook.modify_portfolio_orders(username,order_id)
    return modify_portfolio_orders_response, status_code

execute_at_market_orders_blueprint = Blueprint('execute_at_market_orders_blueprint', __name__)
@execute_at_market_orders_blueprint.route(ORDERBOOK_ROUTES.get_routes("execute_at_market_orders_blueprint"), methods=['POST'])
def execute_at_market_orders(username,order_id):
    execute_at_market_orders_response, status_code = OrderBook.execute_at_market_orders(username,order_id)
    return execute_at_market_orders_response, status_code