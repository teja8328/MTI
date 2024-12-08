
class ORDERBOOK_ROUTES:

    @staticmethod
    def get_routes(blueprint):

        if blueprint == "order_book_blueprint":

            path = '/order_book_blueprint/<string:username>'
            return path

        elif blueprint == "pseudo_limit_order_status_blueprint":

            path = '/update_pseudo_limit_order_status/<string:username>'
            return path

        elif blueprint == "cancel_portfolio_orders_blueprint":

            path = '/cancel_portfolio_orders/<string:username>/<string:order_id>'
            return path

        elif blueprint == "modify_portfolio_orders_blueprint":

            path = '/modify_portfolio_orders/<string:username>/<string:order_id>'
            return path

        elif blueprint == "execute_at_market_orders_blueprint":

            path = '/execute_at_market_orders/<string:username>/<string:order_id>'
            return path