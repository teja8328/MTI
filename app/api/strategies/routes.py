
class STRATEGIE_ROUTES:

    @staticmethod
    def get_routes(blueprint):

        if blueprint == "store_broker_and_strategy_info_blueprint":

            path = '/store_broker_and_strategy_info/<string:username>'
            return path
        
        elif blueprint == "retrieve_strategy_info_blueprint":

            path = '/retrieve_strategy_info/<string:username>'
            return path

        elif blueprint == "delete_strategy_tag_blueprint":

            path = '/delete_strategy_tag/<string:username>/<string:strategy_tag>'
            return path

        elif blueprint == "update_max_profit_loss_blueprint":

            path = '/<string:username>/<string:strategy_tag>/max_profit_loss'
            return path

        elif blueprint == "update_strategy_profit_locking_blueprint":

            path = '/update_strategy_profit_locking/<string:username>/<string:strategy_tag>'
            return path
        
        elif blueprint == "update_strategy_profit_trail_values_blueprint":

            path = '/update_strategy_profit_trail_values/<string:username>/<string:strategy_tag>'
            return path
        
        elif blueprint == "update_wait_time_blueprint":

            path = '/<string:username>/<string:strategy_tag>/update_wait_time'
            return path