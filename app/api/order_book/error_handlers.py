
class ERROR_HANDLER:

    # Note: Errors related to Database
    @staticmethod
    def database_errors(dbtype, message):
        
        if dbtype == "user":
            return {"message" : message}
        
        elif dbtype == "portfolio":
            return {"message" : message}
        
        elif dbtype == "strategies":
            return {"message" : message}
        
        elif dbtype == "executed_portfolio":
            return {"message" : message}
        
    
    # Note: Errors related to broker API's
    @staticmethod
    def broker_api_errors(broker, message):

        if broker == "angelone":
            return {"message" : message}
        
        elif broker == "fyers":
            return {"message" : message}
        
        elif broker == "flattrade":
            return {"message" : message}
        
        elif broker == "pseudo_account":
            return {"message" : message}
        
        
    # Note: Errors related to Application API's
    @staticmethod
    def flask_api_errors(flask_api, message):

        if flask_api == "placeorder":
            return {"message" : message}
        
        elif flask_api == "fyers_place_order":
            return {"message" : message}
        
        elif flask_api == "get_price_details":
            return {"message" : message}
        
        elif flask_api == "fyers_square_off_strategy":
            return {"message" : message}
        
        elif flask_api == "Get_executed_portfolios":
            return {"message" : message}
        
        elif flask_api == "flattrade_square_off_strategy":
            return {"message" : message}
        
        elif flask_api == "fyers_futures_place_order":
            return {"message" : message}
        
        elif flask_api == "get_ltp":
            return {"message" : message}
        
        elif flask_api == "get_fyers_ltp":
            return {"message" : message}
        
        elif flask_api == "flatrade_websocket":
            return {"message" : message}
        
        elif flask_api == "get_flattrade_ltp":
            return {"message" : message}
        
        elif flask_api == "all_ltp_data":
            return {"message" : message}
        
        elif flask_api == "square_off_portfolio_leg_level":
            return {"message" : message}
        
        elif flask_api == "add_portfolio_performance":
            return {"message" : message}
        
        elif flask_api == "get_portfolio_performance":
            return {"message" : message}
        
        elif flask_api == "latest_details":
            return {"message" : message}

        elif flask_api == "cancel_portfolio_orders":
            return {"message" : message}

        elif flask_api == "modify_portfolio_orders":
            return {"message" : message}
    
        elif flask_api == "execute_at_market_orders":
            return {"message" : message}




