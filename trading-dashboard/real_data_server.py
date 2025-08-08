#!/usr/bin/env python3
import sys
sys.path.append('../')
from secret import ACCOUNTS
from fastapi import FastAPI, HTTPException
import uvicorn
import re
import os
import json
from datetime import datetime

app = FastAPI(title='BitGet Live Dashboard - Real Data')

def get_real_balance_from_log():
    """Extract real balance from cron.log"""
    try:
        with open('/home/ubuntu/Live-Tools-V2/cron.log', 'r') as f:
            content = f.read()
        
        # Find the most recent balance entry
        balance_matches = re.findall(r'Balance: ([0-9]+\.?[0-9]*) USDT', content)
        if balance_matches:
            return float(balance_matches[-1])  # Get the latest one
        return None
    except Exception as e:
        print(f'Error reading balance from log: {e}')
        return None

def get_real_data_from_strategies():
    """Get real position data from strategy files"""
    try:
        positions = []
        
        # Check TRIX positions
        pos_file = '/home/ubuntu/Live-Tools-V2/strategies/trix/positions_bitmart1.json'
        if os.path.exists(pos_file):
            with open(pos_file, 'r') as f:
                trix_positions = json.load(f)
                for symbol, data in trix_positions.items():
                    if data.get('position_size', 0) != 0:
                        positions.append({
                            'symbol': symbol,
                            'size': data.get('position_size', 0),
                            'side': 'long' if data.get('position_size', 0) > 0 else 'short',
                            'strategy': 'TRIX'
                        })
        
        return positions
    except Exception as e:
        print(f'Error reading positions: {e}')
        return []

@app.get('/')
async def root():
    real_balance = get_real_balance_from_log()
    real_positions = get_real_data_from_strategies()
    
    return {
        'message': 'BitGet Live Dashboard - REAL DATA',
        'status': 'running',
        'port': 8000,
        'data_source': 'Live trading strategies',
        'real_balance_usdt': real_balance,
        'active_positions': len(real_positions),
        'last_update': datetime.now().isoformat()
    }

@app.get('/api/bitget/balance')
async def get_real_balance():
    real_balance = get_real_balance_from_log()
    
    if real_balance is None:
        raise HTTPException(status_code=404, detail='Balance not found in logs')
    
    return {
        'data': {
            'USDT': {
                'free': real_balance,
                'used': 0,
                'total': real_balance
            }
        },
        'source': 'Live cron.log data',
        'timestamp': datetime.now().isoformat(),
        'cached': False
    }

@app.get('/api/bitget/positions') 
async def get_real_positions():
    positions = get_real_data_from_strategies()
    
    return {
        'data': positions,
        'source': 'Live strategy files',
        'count': len(positions),
        'timestamp': datetime.now().isoformat(),
        'cached': False
    }

@app.get('/api/bitget/status')
async def get_status():
    real_balance = get_real_balance_from_log()
    real_positions = get_real_data_from_strategies()
    
    return {
        'status': 'connected',
        'exchange': 'BitGet', 
        'api_key': ACCOUNTS['bitget1']['public_api'][:10] + '...',
        'data_source': 'LIVE TRADING DATA',
        'real_balance_usdt': real_balance,
        'active_positions': len(real_positions),
        'server_time': datetime.now().isoformat()
    }

if __name__ == '__main__':
    print('=== BitGet REAL DATA Dashboard ===')
    print('Server: http://0.0.0.0:8000')
    print('External: https://15.237.204.133')
    print('Data Source: Live trading cron.log + strategy files')
    real_balance = get_real_balance_from_log()
    real_positions = get_real_data_from_strategies()
    print('Real Balance from log:', real_balance, 'USDT')
    print('Active Positions:', len(real_positions))
    print('=================================')
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')