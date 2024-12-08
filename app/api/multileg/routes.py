
class MULTILEG_ROUTES:

    @staticmethod
    def get_routes(blueprint):

        if blueprint == "fyers_websocket_ltp_blueprint":

            path = '/fyers_websocket_ltp/<string:username>/<string:broker_user_id>'
            return path
        
        elif blueprint == "get_fyers_ltp_blueprint":

            path = '/get_fyers_ltp/fyers/<string:username>'
            return path

        elif blueprint == "angelone_placeorder_blueprint":

            path = '/angelone_options_place_order/<string:username>/<string:portfolio_name>/<string:broker_user_id>'
            return path
        
        elif blueprint == "store_portfolio_blueprint":

            path = '/store_portfolio/<string:username>'
            return path

        elif blueprint == "get_portfolio_blueprint":

            path = '/get_portfolio/<string:username>'
            return path

        elif blueprint == "delete_portfolio_blueprint":

            path = '/delete_portfolio/<string:username>/<string:portfolio_name>'
            return path

        elif blueprint == "fyers_websocket_blueprint":

            path = '/fyers_websocket'
            return path

        elif blueprint == "quick_trade_panel_blueprint":

            path = '/quick_trade_panel'
            return path
        
        elif blueprint == "fyers_place_order_blueprint":

            path = '/place_order/fyers/<string:username>/<string:portfolio_name>/<string:broker_user_id>'
            return path
        
        elif blueprint == "edit_portfolio_blueprint":

            path = '/edit_portfolio/<string:username>/<string:portfolio_name>'
            return path
        
        elif blueprint == "get_price_details_blueprint":

            path = '/get_price_details/<string:username>'
            return path
        
        elif blueprint == "delete_portfolio_legs_blueprint":

            path = '/delete_portfolio_legs/<string:username>/<string:portfolio_legsid>'
            return path
        
        elif blueprint == "order_book_blueprint":

            path = '/order_book_blueprint/<string:username>'
            return path
        
        elif blueprint == "logout_broker_accounts_blueprint":

            path = '/logout_broker_accounts/<string:broker_name>/<string:broker_username>'
            return path
        
        elif blueprint == "fyers_square_off_strategy_blueprint":

            path = '/fyers_strategy_options_sqoff/<string:username>/<string:strategy_tag>/<string:broker_user_id>'
            return path
        
        elif blueprint == "get_executed_portfolios_blueprint":

            path = '/get_executed_portfolios/<string:username>'
            return path
        
        elif blueprint == 'angelone_square_off_strategy_blueprint':

            path = '/angelone_strategy_options_sqoff/<string:username>/<string:strategy_tag>/<string:broker_user_id>'
            return path
        
        elif blueprint == "flatrade_place_order_blueprint":

            path = '/flatrade_place_order/<string:username>/<string:portfolio_name>/<string:broker_user_id>'
            return path
        
        elif blueprint == "flattrade_square_off_strategy_blueprint":

            path = '/flattrade_strategy_options_sqoff/<string:username>/<string:strategy_tag>/<string:broker_user_id>'
            return path
        
        elif blueprint == "enable_portfolio_blueprint":

            path = '/enable_portfolio/<string:username>/<string:portfolio_name>'
            return path
        
        elif blueprint == "enable_all_portfolio_blueprint":

            path = '/enable_all_portfolios/<string:username>'
            return path
        
        elif blueprint == "delete_all_portfolio_blueprint":

            path = '/delete_all_portfolios/<string:username>'
            return path
        
        elif blueprint == "delete_all_enabled_portfolios_blueprint":

            path = '/delete_all_enabled_portfolios/<string:username>'
            return path
        
        elif blueprint == "get_future_expiry_list_blueprint":

            path = '/get_future_expiry_list_blueprint/<string:username>'
            return path
        
        elif blueprint == "fyers_futures_place_order_blueprint":

            path = '/fyers_futures_place_order/fyers/<string:username>/<string:portfolio_name>/<string:broker_user_id>'
            return path
        
        elif blueprint == "angleone_future_place_order_blueprint":

            path = '/angleone_future_place_order/angelone/<string:username>/<string:portfolio_name>/<string:broker_user_id>'
            return path
        
        elif blueprint == "flatrade_future_place_order_blueprint":

            path = '/flatrade_future_place_order/flattrade/<string:username>/<string:portfolio_name>/<string:broker_user_id>'
            return path
        
        elif blueprint == "angelone_ltp_websocket_blueprint":

            path = '/angelone_ltp_websocket/<string:username>'
            return path
        
        elif blueprint == "get_ltp_blueprint":

            path = '/get_ltp/<string:username>'
            return path
        
        elif blueprint == "fyers_websocket_ltp_blueprint":

            path = '/fyers_websocket_ltp/<string:username>/<string:broker_user_id>'
            return path
        
        elif blueprint == "get_fyers_ltp_blueprint":

            path = '/get_fyers_ltp/fyers/<string:username>'
            return path
        
        elif blueprint == "fetching_portfoliolevel_positions_blueprint":

            path = '/fetching_portfoliolevel_positions/<string:portfolio_name>'
            return path
        
        elif blueprint == "square_off_portfolio_level_blueprint":

            path = '/square_off_portfolio_level/<string:username>/<string:portfolio_name>/<string:broker_type>/<string:broker_user_id>'
            return path
        
        elif blueprint == "flatrade_websocket_blueprint":

            path = '/flatrade_websocket/<string:username>/<string:broker_user_id>'
            return path
        
        elif blueprint == "get_flattrade_ltp_blueprint":

            path = '/get_flattrade_ltp/flatrade/<string:username>'
            return path
        
        elif blueprint == "fetching_strategy_tag_positions_blueprint":

            path = '/fetching_strategy_tag_positions'
            return path
        
        elif blueprint == "websocket_ltp_blueprint":

            path = '/websocket_ltp/<string:username>/<string:broker_user_id>'
            return path
        
        elif blueprint == "all_ltp_data_blueprint":

            path = '/all_ltp_data'
            return path
        
        elif blueprint == "update_portfolio_leg_profit_trail_values_blueprint":

            path = '/update_portfolio_leg_profit_trail_values/<string:username>/<int:id>'
            return path
        
        elif blueprint == "square_off_portfolio_leg_level_blueprint":

            path = '/square_off_portfolio_leg_level/<string:username>/<string:portfolio_name>/<string:broker_type>/<string:broker_user_id>/<int:portfolio_leg_id>'
            return path
        
        elif blueprint == "Get_theta_gamma_vega_values_blueprint":

            path = '/get_theta_gamma_vega_values/<string:username>'
            return path
        
        elif blueprint == "add_portfolio_performance_blueprint":

            path = '/add_portfolio_performance/<string:username>'
            return path
        
        elif blueprint == "get_portfolio_performance_blueprint":

            path = '/get_portfolio_performance/<string:username>'
            return path
        
        elif blueprint == "Get_latest_blueprint":

            path = '/get_latest/<string:username>'
            return path
        
        elif blueprint == "cancel_portfolio_orders_blueprint":

            path = '/cancel_portfolio_orders/<string:username>/<string:order_id>'
            return path
        
        elif blueprint == "pseudo_placeorderblueprint":

            path = '/pseudo_placeorder/<string:username>/<string:portfolio_name>/<string:broker_user_id>'
            return path
        
        elif blueprint == "pseudo_squareoff_user_blueprint":

            path = '/pseudo_user_options_sqoff/<string:username>/<string:broker_user_id>'
            return path
        
        elif blueprint == "get_expiry_list_blueprint":

            path = '/get_expiry_list_blueprint/<string:username>'
            return path
        
        elif blueprint == "pseudo_squareoff_strategy_blueprint":

            path ='/pseudo_strategy_options_sqoff/<string:username>/<string:strategy_tag>/<string:broker_user_id>'
            return path