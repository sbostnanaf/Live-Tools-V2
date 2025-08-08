from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
import ccxt
import asyncio
from datetime import datetime
from pydantic import BaseModel

from ...config import settings

router = APIRouter(prefix="/bitget", tags=["BitGet Trading"])
security = HTTPBearer()

class BitGetClient:
    def __init__(self):
        self.exchange = ccxt.bitget({
            'apiKey': settings.BITGET_API_KEY,
            'secret': settings.BITGET_SECRET_KEY,
            'password': settings.BITGET_PASSPHRASE,
            'sandbox': settings.BITGET_SANDBOX,
            'enableRateLimit': True,
        })

    async def get_balance(self) -> Dict[str, Any]:
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch balance: {str(e)}")

    async def get_positions(self) -> List[Dict[str, Any]]:
        try:
            positions = await self.exchange.fetch_positions()
            return [pos for pos in positions if pos['contracts'] > 0]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch positions: {str(e)}")

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        try:
            orders = await self.exchange.fetch_open_orders()
            return orders
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch open orders: {str(e)}")

    async def get_trading_history(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            if symbol:
                trades = await self.exchange.fetch_my_trades(symbol, limit=limit)
            else:
                trades = await self.exchange.fetch_my_trades(limit=limit)
            return trades
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch trading history: {str(e)}")

    async def get_account_info(self) -> Dict[str, Any]:
        try:
            account = await self.exchange.fetch_account()
            return account
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch account info: {str(e)}")

bitget_client = BitGetClient()

@router.get("/balance")
async def get_balance(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await bitget_client.get_balance()

@router.get("/positions")
async def get_positions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await bitget_client.get_positions()

@router.get("/orders")
async def get_open_orders(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await bitget_client.get_open_orders()

@router.get("/trades")
async def get_trading_history(
    symbol: Optional[str] = None,
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    return await bitget_client.get_trading_history(symbol, limit)

@router.get("/account")
async def get_account_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await bitget_client.get_account_info()

@router.get("/status")
async def get_connection_status():
    try:
        status = await bitget_client.exchange.fetch_status()
        return {"status": "connected", "exchange_status": status}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}
EOF < /dev/null
