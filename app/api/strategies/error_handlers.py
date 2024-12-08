
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

        if flask_api == "Store_broker_and_strategy_info":
            return {"message" : message}
        
        elif flask_api == "delete_strategy_tag":
            return {"message" : message}
        
        elif flask_api == "retrieve_strategy_info":
            return {"message" : message}
        
        elif flask_api == "update_strategy_profit_locking":
            return {"message" : message}
        
        elif flask_api == "Get_executed_portfolios":
            return {"message" : message}
        
        elif flask_api == "flattrade_square_off_strategy":
            return {"message" : message}