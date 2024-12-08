from flask import Blueprint, jsonify, request, abort, Flask, send_file
from app.models.main import db
import urllib.request
import json
import pandas as pd
import requests
import json
import pandas as pd
import time


class OptionChain:
    def Getoptionchain():

        data = request.json
        print(data)
        symbol = data['symbol']
        expiry_dt = data['expiry_date']

        new_url = f'https://www.nseindia.com/api/option-chain-indices?symbol={symbol}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(new_url,headers=headers)
        dajs = json.loads(page.text)
        
        ce_values = [data['CE'] for data in dajs['records']['data'] if "CE" in data and data['expiryDate'] == expiry_dt]
        pe_values = [data['PE'] for data in dajs['records']['data'] if "PE" in data and data['expiryDate'] == expiry_dt]

        ce_dt = pd.DataFrame(ce_values).sort_values(['strikePrice'])
        pe_dt = pd.DataFrame(pe_values).sort_values(['strikePrice'])

        ce_dt = ce_dt[['openInterest','changeinOpenInterest','totalTradedVolume','impliedVolatility','lastPrice','strikePrice']]
        pe_dt = pe_dt[['openInterest','changeinOpenInterest','totalTradedVolume','impliedVolatility','lastPrice','strikePrice']]
        
        option_chain = pd.merge(ce_dt,pe_dt,on='strikePrice',suffixes=("_CE","_PE"))
        option_chain.to_csv('./app/api/optionchain/OptionChain.csv')
        option_chain.to_json('./app/api/optionchain/optionchain_data.json', orient='records')
        
        # ce_dt.to_csv('./app/api/optionchain/CE_data.csv')
        # ce_dt.to_json('./app/api/optionchain/CE_data.json', orient='records')

        # pe_dt.to_csv('./app/api/optionchain/PE_data.csv')
        # pe_dt.to_json('./app/api/optionchain/PE_data.json', orient='records')

        # CE_file_path = './app/api/optionchain/CE_data.json'
        # with open(CE_file_path, 'r') as file:
        #     CE_data = json.load(file)

        # PE_file_path = './app/api/optionchain/PE_data.json'
        # with open(PE_file_path, 'r') as file:
        #     PE_data = json.load(file)

        optionchain_file_path = './app/api/optionchain/optionchain_data.json'
        with open(optionchain_file_path, 'r') as file:
            optionchain_data = json.load(file)

        return jsonify({'Option Chain Data': optionchain_data}), 200
        
get_option_chain_blueprint = Blueprint('get_option_chain_blueprint', __name__) 
@get_option_chain_blueprint.route('/get_option_chain/', methods=['POST'])
def get_option_chain():
    get_option_chain_response, status_code = OptionChain.Getoptionchain()
    return get_option_chain_response, status_code