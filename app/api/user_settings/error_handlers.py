
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
        
        elif dbtype == "broker_credentials":
            return {"message" : message}
        
    # Note: Errors related to Application API's
    @staticmethod
    def flask_api_errors(flask_api, message):

        if flask_api == "get_strategy_account":
            return {"message" : message}
        
        elif flask_api == "delete_broker_account":
            return {"message" : message}
        
        elif flask_api == "update_password":
            return {"message" : message}
        
        elif flask_api == "update_user_profit_locking":
            return {"message" : message}
        
        elif flask_api == "square_off_maxloss_per_trade":
            return {"message" : message}
        
        elif flask_api == "square_off_equity_maxloss_per_trade":
            return {"message" : message}