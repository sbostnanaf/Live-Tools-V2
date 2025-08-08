#\!/bin/bash
cd /home/ubuntu/Live-Tools-V2
source .venv/bin/activate

python3 -c "
import sys
sys.path.append('../')
from secret import ACCOUNTS
from fastapi import FastAPI, HTTPException
import ccxt
import uvicorn
import asyncio

app = FastAPI(title='BitGet Dashboard API')

class BitGetClient:
    def __init__(self):
        self.exchange = ccxt.bitget({
            'apiKey': ACCOUNTS['bitget1']['public_api'],
            'secret': ACCOUNTS['bitget1']['secret_api'],
            'password': ACCOUNTS['bitget1']['password'],
            'sandbox': False,
            'enableRateLimit': True,
        })

    async def get_balance(self):
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

bitget_client = BitGetClient()

@app.get('/')
async def root():
    return {'message': 'BitGet Dashboard API', 'status': 'running', 'port': 8080}

@app.get('/api/bitget/balance')
async def get_balance():
    return await bitget_client.get_balance()

@app.get('/api/bitget/status')
async def get_status():
    return {'status': 'connected', 'exchange': 'BitGet', 'api_key': ACCOUNTS['bitget1']['public_api'][:10] + '...'}

if __name__ == '__main__':
    print('=== BitGet Dashboard Server ===')
    print('Server: http://0.0.0.0:8080')
    print('External: http://15.237.204.133:8080')
    print('Endpoints:')
    print('  GET / - Server status')
    print('  GET /api/bitget/balance - Account balance')
    print('  GET /api/bitget/status - Connection status')
    print('===============================')
    uvicorn.run(app, host='0.0.0.0', port=8080, log_level='info')
"
