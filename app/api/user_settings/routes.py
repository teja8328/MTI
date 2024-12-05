
class USERSETTING_ROUTES:

    @staticmethod
    def get_routes(blueprint):

        if blueprint == "validation_blueprint":

            path = '/datavalidation'
            return path
        
        elif blueprint == "delete_broker_account_blueprint":

            path = '/delete_credentials/<string:username>/<string:broker_user_id>/<string:broker>'
            return path

        elif blueprint == "update_password_blueprint":

            path = '/update_password/<string:username>/<string:broker_user_id>'
            return path

        elif blueprint == "logout_blueprint":

            path = '/logout/<string:username>/<string:broker_user_id>'
            return path

        elif blueprint == "forgot_password_blueprint":

            path = '/forgot_password/<string:username>'
            return path
        
        elif blueprint == "verify_otp_blueprint":

            path = '/verify_otp/<string:username>'
            return path

        elif blueprint == "change_user_password_blueprint":

            path = '/change_user_password/<string:username>'
            return path

        elif blueprint == "get_startegy_account_blueprint":

            path = '/get_startegy_account/<string:username>'
            return path

        elif blueprint == "update_user_profit_locking_blueprint":

            path = '/update_user_profit_locking/<string:username>/<string:broker_user_id>'
            return path

        elif blueprint == "update_user_data_blueprint":

            path = '/update_user_data/<string:username>/<string:broker_user_id>'
            return path

        elif blueprint == "update_user_profit_trail_values_blueprint":

            path = '/update_user_profit_trail_values/<string:username>/<string:broker_user_id>'
            return path

        elif blueprint == "update_pseudo_balance_blueprint":

            path = '/<string:username>/<string:broker_user_id>/update_pseudo_balance'
            return path

        elif blueprint == "update_displayname_blueprint":

            path = '/update_displayname/<string:username>/<string:broker_user_id>'
            return path
        
        elif blueprint == "square_off_maxloss_per_trade_blueprint":

            path = '/square_off_maxloss_per_trade/<string:username>/<string:trading_symbol>/<string:broker_type>/<string:broker_user_id>'
            return path
        
        elif blueprint == "square_off_equity_maxloss_per_trade_level_blueprint":

            path = '/square_off_equity_maxloss_per_trade/<string:username>/<string:trading_symbol>/<string:broker_type>/<string:broker_user_id>'
            return path
        
        
        