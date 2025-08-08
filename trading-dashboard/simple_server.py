import sys
sys.path.append('../')
from secret import ACCOUNTS
from fastapi import FastAPI, HTTPException
import ccxt
import uvicorn
import asyncio
from typing import Dict, Any

app = FastAPI(title="BitGet Dashboard API")

class BitGetClient:
    def __init__(self):
        self.exchange = ccxt.bitget({
            'apiKey': ACCOUNTS["bitget1"]["public_api"],
            'secret': ACCOUNTS["bitget1"]["secret_api"],
            'password': ACCOUNTS["bitget1"]["password"],
            'sandbox': False,
            'enableRateLimit': True,
        })

    async def get_balance(self):
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_positions(self):
        try:
            positions = await self.exchange.fetch_positions()
            return [pos for pos in positions if pos['contracts'] > 0]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

bitget_client = BitGetClient()

@app.get("/")
async def root():
    return {"message": "BitGet Dashboard API", "status": "running"}

@app.get("/api/bitget/balance")
async def get_balance():
    return await bitget_client.get_balance()

@app.get("/api/bitget/positions")
async def get_positions():
    return await bitget_client.get_positions()

@app.get("/api/bitget/status")
async def get_status():
    try:
        await bitget_client.exchange.fetch_status()
        return {"status": "connected", "exchange": "BitGet"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("Starting BitGet Dashboard API server...")
    print("Dashboard will be available at: http://localhost:8000")
    print("API endpoints:")
    print("- GET /api/bitget/balance")
    print("- GET /api/bitget/positions") 
    print("- GET /api/bitget/status")
    uvicorn.run(app, host="0.0.0.0", port=8000)