import requests
import time
import hashlib
import hmac

# Remplacez par vos informations d'API
API_KEY = '6770c5dc49bd53ebe7c4918e1819f99e63c0d23a'
SECRET_KEY = 'c0d59bd634b1ca756aed55da4086d8caa5aef86997e9e3eda01ee967aa852002'
PASSPHRASE = 'SERVEUR_TRIX_V2'

def generate_signature(api_key, secret_key, timestamp, method, request_path, query_string=''):
    message = f'{timestamp}#{api_key}#{PASSPHRASE}#{method.upper()}#{request_path}#{query_string}'
    return hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

def get_futures_balance():
    url = 'https://api-cloud-v2.bitmart.com/contract/private/assets-detail'
    timestamp = str(int(time.time()))
    method = 'GET'
    request_path = '/contract/private/assets-detail'
    
    headers = {
        'X-BM-KEY': API_KEY,
        'X-BM-SIGN': generate_signature(API_KEY, SECRET_KEY, timestamp, method, request_path),
        'X-BM-TIMESTAMP': timestamp,
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print("Erreur:", response.status_code, response.text)
        return None

balance = get_futures_balance()
if balance:
    print(balance)
