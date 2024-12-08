# /run.py
# from app import app,socketio
from app import app
import threading
from flask import Blueprint, jsonify, request, abort, Flask
# from app.api.brokers.angelone import retrieve_fyers_live_feed, print_fyers_live_feed
from app.api.brokers.angelone import retrieve_live_feed
from app.api.multileg.validations import run_scheduler
# from flask_socketio import SocketIO, disconnect



import time

# socketio = SocketIO(app)


if __name__ == '__main__':

    # threading.Thread(target=retrieve_fyers_live_feed, args=('eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3MzE5MDQ1MDEsImV4cCI6MTczMTk3NjIwMSwibmJmIjoxNzMxOTA0NTAxLCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbk9zUDFIbkt5c255cXlmZGkxVkpqTGlBbzBwZ1dNWjNGOVp6bEVyRDRsakQ4dncyLV9aS0RxUXJoRXNMODZKb0FYU25PYy0zejBQeWxLaXdnTVg4NzlLOW5jbGk5WmhYZzhMVDROaE1lMXZsQzVCTT0iLCJkaXNwbGF5X25hbWUiOiJTQUkgR0FORVNIIEtBTlVQQVJUSEkiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIwYTgzNjI0ZmEwYjA1ZmViODJmNDBlMDdiY2Y3MmYxYWEwMGY1ODFhMTIxOTNkNWM3Y2ZlZTI2YiIsImZ5X2lkIjoiWVMxNzE5NSIsImFwcFR5cGUiOjEwMCwicG9hX2ZsYWciOiJOIn0.JEk_DcZdr935tREqXXJj86lpfYDRrsE21oDR_nQ8vK0',)).start()
    # threading.Thread(target=print_fyers_live_feed).start()
    threading.Thread(target=retrieve_live_feed, daemon=True).start()
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()


    app.run(debug=True, port=1919, host="0.0.0.0")
    # threading.Thread(target=retrieve_live_feed).start()
    # socketio.run(app, debug=True, port=1919, host="0.0.0.0")
