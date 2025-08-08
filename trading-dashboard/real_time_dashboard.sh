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
import json
from datetime import datetime, timedelta
import time

app = FastAPI(title='BitGet Real-Time Dashboard')

# Cache system
cache = {
    'balance': {'data': None, 'timestamp': None, 'ttl': 30},  # 30 seconds TTL
    'positions': {'data': None, 'timestamp': None, 'ttl': 15},  # 15 seconds TTL
    'orders': {'data': None, 'timestamp': None, 'ttl': 10}  # 10 seconds TTL
}

class BitGetClient:
    def __init__(self):
        self.exchange = ccxt.bitget({
            'apiKey': ACCOUNTS['bitget1']['public_api'],
            'secret': ACCOUNTS['bitget1']['secret_api'],
            'password': ACCOUNTS['bitget1']['password'],
            'sandbox': False,
            'enableRateLimit': True,
        })

    async def get_cached_or_fresh(self, cache_key, fetch_func):
        now = datetime.now()
        cache_entry = cache[cache_key]
        
        # Check if cache is valid
        if (cache_entry['data'] is not None and 
            cache_entry['timestamp'] is not None and
            (now - cache_entry['timestamp']).seconds < cache_entry['ttl']):
            return {
                'data': cache_entry['data'],
                'cached': True,
                'cache_age': (now - cache_entry['timestamp']).seconds,
                'timestamp': cache_entry['timestamp'].isoformat()
            }
        
        # Fetch fresh data
        try:
            fresh_data = await fetch_func()
            cache_entry['data'] = fresh_data
            cache_entry['timestamp'] = now
            
            return {
                'data': fresh_data,
                'cached': False,
                'cache_age': 0,
                'timestamp': now.isoformat()
            }
        except Exception as e:
            # Return cached data if available, even if expired
            if cache_entry['data'] is not None:
                return {
                    'data': cache_entry['data'],
                    'cached': True,
                    'cache_age': (now - cache_entry['timestamp']).seconds,
                    'timestamp': cache_entry['timestamp'].isoformat(),
                    'error': str(e),
                    'fallback': True
                }
            raise HTTPException(status_code=500, detail=str(e))

    async def fetch_balance(self):
        balance = await self.exchange.fetch_balance()
        return balance

    async def fetch_positions(self):
        positions = await self.exchange.fetch_positions()
        return [pos for pos in positions if pos.get('contracts', 0) > 0]

    async def fetch_orders(self):
        return await self.exchange.fetch_open_orders()

bitget_client = BitGetClient()

@app.get('/')
async def root():
    return {
        'message': 'BitGet Real-Time Dashboard API',
        'status': 'running',
        'port': 8080,
        'cache_status': {key: {
            'has_data': cache[key]['data'] is not None,
            'last_update': cache[key]['timestamp'].isoformat() if cache[key]['timestamp'] else None,
            'ttl_seconds': cache[key]['ttl']
        } for key in cache},
        'current_time': datetime.now().isoformat()
    }

@app.get('/api/bitget/balance')
async def get_balance():
    return await bitget_client.get_cached_or_fresh('balance', bitget_client.fetch_balance)

@app.get('/api/bitget/positions')
async def get_positions():
    return await bitget_client.get_cached_or_fresh('positions', bitget_client.fetch_positions)

@app.get('/api/bitget/orders')
async def get_orders():
    return await bitget_client.get_cached_or_fresh('orders', bitget_client.fetch_orders)

@app.get('/api/bitget/status')
async def get_status():
    return {
        'status': 'connected',
        'exchange': 'BitGet',
        'api_key': ACCOUNTS['bitget1']['public_api'][:10] + '...',
        'server_time': datetime.now().isoformat(),
        'cache_info': {key: {
            'has_data': cache[key]['data'] is not None,
            'age_seconds': (datetime.now() - cache[key]['timestamp']).seconds if cache[key]['timestamp'] else None,
            'ttl_seconds': cache[key]['ttl']
        } for key in cache}
    }

@app.post('/api/cache/clear')
async def clear_cache():
    for key in cache:
        cache[key]['data'] = None
        cache[key]['timestamp'] = None
    return {'message': 'Cache cleared', 'timestamp': datetime.now().isoformat()}

if __name__ == '__main__':
    print('=== BitGet Real-Time Dashboard ===')
    print('Server: http://0.0.0.0:8080')
    print('External: http://15.237.204.133:8080')
    print('Features:')
    print('  - Real-time data with smart caching')
    print('  - Automatic fallback on API errors')
    print('  - Cache TTL: Balance(30s), Positions(15s), Orders(10s)')
    print('Endpoints:')
    print('  GET / - Server status & cache info')
    print('  GET /api/bitget/balance - Account balance (cached 30s)')
    print('  GET /api/bitget/positions - Open positions (cached 15s)')
    print('  GET /api/bitget/orders - Open orders (cached 10s)')
    print('  GET /api/bitget/status - Connection status')
    print('  POST /api/cache/clear - Clear cache')
    print('==================================')
    uvicorn.run(app, host='0.0.0.0', port=8080, log_level='info')
"
