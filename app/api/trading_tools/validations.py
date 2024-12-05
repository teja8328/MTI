from app.models.user import Portfolio , BrokerCredentials , Strategies , Portfolio_legs , ExecutedPortfolio 
from app.models.user import User
from app.models.main import db
from SmartApi import SmartConnect
from fyers_apiv3 import fyersModel
from app.api.brokers import config
from flask import Blueprint, jsonify, request, abort, Flask
from flask import Blueprint, jsonify, abort, request
# from app.api.trading_tools import config
from app.api.brokers import config

class TradingTools:

    def square_off_fyers_loggedIn(username, broker_user_id):
        print("hello")
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id
            portfolio = Portfolio.query.filter_by(user_id=user_id).first()
            executed_Portfolio_details = ExecutedPortfolio.query.filter_by(user_id=user_id, broker_user_id=broker_user_id,square_off=False).all()
            print(executed_Portfolio_details)
            print(portfolio.variety)
            try:
                fyers = config.OBJ_fyers[broker_user_id]
                print(fyers)
            except:
                response_data = {"message": f"Please login to the broker account, {broker_user_id}"}
                return jsonify(response_data), 500
            
            fyers_list = []  # Initialize fyers_list here

            if executed_Portfolio_details:
                for executedPortfolio in executed_Portfolio_details:
                    strategy_tag = executedPortfolio.strategy_tag
                    transaction_type = config.fyers_data['Side'][executedPortfolio.transaction_type]
                    id = executedPortfolio.order_id
            
                    data = {
                        "orderTag": strategy_tag,
                        "segment": [10],
                        'id': id,
                        "side": [transaction_type]
                    }

                    fyers_square_off = fyers.exit_positions(data)
                    print(fyers_square_off)
                    fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
                    fyers_position=config.OBJ_fyers[broker_user_id].positions()
                    fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
                    config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}
                    # order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                
                    if fyers_square_off['s'] == 'ok':
                        response_data = {'message': f'Square off successfully for {broker_user_id}','Square_off':fyers_square_off}
                        # Query executed portfolios with the same Strategy_tag and delete them
                        portfolios_to_delete = ExecutedPortfolio.query.filter_by(broker_user_id=broker_user_id).all()
                        # for executedportfolio in portfolios_to_delete:
                        #     db.session.delete(executedportfolio)
                        executedPortfolio.square_off = True
                        if executedPortfolio.transaction_type=="BUY":
                            executedPortfolio.sell_price=fyers_square_off['tradedPrice']
                        else:
                            executedPortfolio.buy_price=fyers_square_off['tradedPrice']
                        db.session.commit()
                        return jsonify(response_data),200
                    
                    else:
                        response_data = {'message': f'Looks like, {broker_user_id} have no open positions .'}
                        return jsonify(response_data),200
                else:
                    response_data = {'message': f'The trade has already been squared off for User {broker_user_id}'}
                    return jsonify(response_data), 200
            
            else:
                response_data = {'message': f'Looks like, {broker_user_id} have no open positions .'}
                return jsonify(response_data), 200
        else:
            response_data = {'message': f"User Does not exist, {username}"}
            return jsonify(response_data), 500


        # except Exception as e:
        #         print("Error:", str(e))  # Log any exceptions
        #         return jsonify({'error': str(e)}), 500
        
    def square_off_angelone_loggedIn(username, broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id
            portfolio = Portfolio.query.filter_by(user_id=user_id).first()
            executed_Portfolio_details = ExecutedPortfolio.query.filter_by(user_id=user_id, broker_user_id=broker_user_id,square_off=False).all()
            print(executed_Portfolio_details)
            print(portfolio.variety)
            try:
                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
            except:
                response_data = {"message": f"Please login to the broker account, {broker_user_id}"}
                return jsonify(response_data), 500
                    
            angelone_list = []  # Initialize angelone_list here

            if executed_Portfolio_details:
                for executedPortfolio in executed_Portfolio_details:
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
                    order_type = executedPortfolio.order_type
                    id = executedPortfolio.order_id
                
                    data = {
                        "variety": variety,
                        "orderTag": strategy_tag,
                        "tradingsymbol":trading_symbol,
                        "symboltoken":symbol_token,
                        "exchange":exchange,
                        "quantity":quantity,
                        "producttype":"INTRADAY" if product_type == "MIS" else "CARRYFORWARD",
                        "transactiontype": "SELL" if transaction_type == "BUY" else "BUY",
                        "price":price,
                        "duration":duration,
                        "ordertype": "MARKET"
                    }

                    angelone_square_off = angelone.placeOrderFullResponse(data)
                    print(angelone_square_off)
                    order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                    positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                    holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                    all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                    config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}
                    # order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                    
                    angelone_list.append(angelone_square_off['message'])
                
                    # db.session.delete(executedPortfolio)
    
                if len(list(set(angelone_list))) == 1 and list(set(angelone_list))[0] == 'SUCCESS':
                    response_data = {'message': f'Square off successfully for {broker_user_id}','Square_off':angelone_square_off}
                    executedPortfolio.square_off = True
                    if executedPortfolio.transaction_type=="BUY":
                        executedPortfolio.sell_price=order['data'][::-1][0]['averageprice']
                    else:
                        executedPortfolio.buy_price=order['data'][::-1][0]['averageprice']
                    db.session.commit()
                    return jsonify(response_data), 200
                else:
                    response_data = {'message': f'Looks like, {broker_user_id} have no open positions .'}
                    return jsonify(response_data), 200
            else:
                response_data = {'message': f'Looks like, {broker_user_id} have no open positions .'}
                return jsonify(response_data), 200
        else:
            response_data = {'message': f"User Does not exist, {username}"}
            return jsonify(response_data), 500

       
        # response_data = {'message': 'Strategy Manual square off  successfully','Square_off':data}
        # return jsonify(response_data),200
    
    def square_off_flattrade_loggedIn(username, broker_user_id):
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            user_id = existing_user.id
            portfolio = Portfolio.query.filter_by(user_id=user_id).first()
            executed_Portfolio_details = ExecutedPortfolio.query.filter_by(user_id=user_id, broker_user_id=broker_user_id,square_off=False).all()
            print("executed_Portfolio_details:", executed_Portfolio_details)
            try:
                flattrade = config.flattrade_api[broker_user_id]
                print(flattrade)
            except:
                response_data = {"Message": f"Please login to the broker account, {broker_user_id}"}
                return jsonify(response_data), 500
            
            flattrade_list = []  # Initialize flattrade_list here

            if executed_Portfolio_details:
                for executedPortfolio in executed_Portfolio_details:
                    print(executedPortfolio)
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
                    order_type = executedPortfolio.order_type
                    id = executedPortfolio.order_id
                    
                    flattrade_square_off = config.flattrade_api[broker_user_id].place_order(
                        buy_or_sell="S" if transaction_type == "BUY" else "B", 
                        product_type="I" if product_type == "MIS" else "M",
                        exchange=exchange, 
                        tradingsymbol=trading_symbol,
                        quantity=quantity, 
                        discloseqty=0,
                        price_type='MKT', 
                        price=0, 
                        trigger_price=None,
                        retention='DAY', 
                        remarks=strategy_tag
                    )

                    print(flattrade_square_off)
                    # order = config.flattrade_api[broker_user_id].get_order_book()
                    order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                    holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                    positions_info = config.flattrade_api[broker_user_id].get_positions()

                    config.all_flattrade_details[broker_user_id] = {
                        'order': order_book_send,
                        "holdings": holdings_info,
                        "positions": positions_info
                    }

                    flattrade_list.append(flattrade_square_off['stat'])

                        # db.session.delete(executedPortfolio)

                if len(list(set(flattrade_list))) == 1 and list(set(flattrade_list))[0] == 'Ok':
                    response_data = {
                        'message': f'Strategy Manual square off successfully loggedIn User {broker_user_id}',
                        'Square_off': flattrade_square_off
                    }
                    executedPortfolio.square_off = True
                    last_rprc = order_book_send[0]['avgprc']
                    print("sell_price:",last_rprc)
                    executedPortfolio.sell_price = last_rprc
                    db.session.commit()
                    return jsonify(response_data), 200
                else:
                    response_data = {'message': f'Looks like, {broker_user_id} have no open positions .'}
                    return jsonify(response_data), 200
            else:
                response_data = {'message': f'The trade has already been squared off for User {broker_user_id}'}
                return jsonify(response_data), 200
        else:
            response_data = {'message': "User Does not exist"}
            return jsonify(response_data), 500
        

square_off_fyers_loggedIn_blueprint = Blueprint('square_off_fyers_loggedIn_blueprint', __name__)
@square_off_fyers_loggedIn_blueprint.route('/fyers_user_options_sqoff/<string:username>/<string:broker_user_id>', methods=['POST'])
def square_off_fyers_loggedIn(username,broker_user_id):
    square_off_fyers_loggedIn_blueprint_response, status_code = TradingTools.square_off_fyers_loggedIn(username=username,broker_user_id=broker_user_id)
    return square_off_fyers_loggedIn_blueprint_response, status_code


square_off_angelone_loggedIn_blueprint = Blueprint('square_off_angelone_loggedIn_blueprint', __name__)
@square_off_angelone_loggedIn_blueprint.route('/angelone_user_options_sqoff/<string:username>/<string:broker_user_id>', methods=['POST'])
def square_off_angelone_loggedIn(username,broker_user_id):
    square_off_angelone_loggedIn_blueprint_response, status_code = TradingTools.square_off_angelone_loggedIn(username=username,broker_user_id=broker_user_id)
    return square_off_angelone_loggedIn_blueprint_response, status_code

square_off_flattrade_loggedIn_blueprint = Blueprint('square_off_flattrade_loggedIn_blueprint', __name__)
@square_off_flattrade_loggedIn_blueprint.route('/flattrade_user_options_sqoff/<string:username>/<string:broker_user_id>', methods=['POST'])
def square_off_flattrade_loggedIn(username,broker_user_id):
    square_off_flattrade_loggedIn_blueprint_response, status_code = TradingTools.square_off_flattrade_loggedIn(username,broker_user_id)
    return square_off_flattrade_loggedIn_blueprint_response, status_code