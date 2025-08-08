# pip install ccxt pandas pydantic ta
from typing import List, Optional
import ccxt.async_support as ccxt
import pandas as pd
from pydantic import BaseModel
from decimal import Decimal, getcontext, ROUND_DOWN
import math
import ta
import time

class UsdtBalance(BaseModel):
    total: float
    free: float
    used: float


class Info(BaseModel):
    success: bool
    message: str


class Order(BaseModel):
    id: str
    pair: str
    type: str
    side: str
    price: float
    size: float
    reduce: bool
    filled: float
    remaining: float
    timestamp: int


class TriggerOrder(BaseModel):
    id: str
    pair: str
    type: str
    side: str
    price: float
    trigger_price: float
    size: float
    reduce: bool
    timestamp: int


class Position(BaseModel):
    pair: str
    side: str
    size: float
    usd_size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    liquidation_price: float
    margin_mode: str
    leverage: int
    hedge_mode: bool
    open_timestamp: int = 0
    take_profit_price: float | None = None
    stop_loss_price: float | None = None

# class Market(BaseModel):
#     internal_pair: str
#     base: str
#     quote: str
#     price_precision: float
#     contract_precision: float
#     contract_size: Optional[float] = 1.0
#     min_contracts: float
#     max_contracts: Optional[float] = float('inf')
#     min_cost: Optional[float] = 0.0
#     max_cost: Optional[float] = float('inf')
#     coin_index: Optional[int] = 0
#     market_price: Optional[float] = 0.0


def get_price_precision(price: float) -> float:
    log_price = math.log10(price)
    order = math.floor(log_price)
    precision = 10 ** (order - 4)
    return precision
    
def number_to_str(n: float) -> str:
    s = format(n, 'f')
    s = s.rstrip('0')
    if s.endswith('.'):
        s = s[:-1]
    
    return s


class PerpHyperliquid:
    def __init__(self, public_api=None, secret_api=None):
        hyperliquid_auth_object = {
            "apiKey": public_api,
            "secret": secret_api,
        }
        self.public_api = public_api
        getcontext().prec = 10
        if hyperliquid_auth_object["secret"] == None:
            self._auth = False
            self._session = ccxt.hyperliquid()
        else:
            self._auth = True
            self._session = ccxt.hyperliquid(hyperliquid_auth_object)
        
     async def load_markets(self):
        self.market = await self._session.load_markets()

    async def close(self):
        await self._session.close()

    def ext_pair_to_pair(self, ext_pair) -> str:
        return f"{ext_pair}:USDT"

    def pair_to_ext_pair(self, pair) -> str:
        return pair+"/USD"
    
    # def ext_pair_to_base(self, ext_pair) -> str:
    #     return ext_pair.split("/")[0]

    def get_pair_info(self, ext_pair) -> str:
        pair = self.ext_pair_to_pair(ext_pair)
        if pair in self.market:
            return self.market[pair]
        else:
            return None
        
   def amount_to_precision(self, pair: str, amount: float) -> float:
        pair = self.ext_pair_to_pair(pair)
        try:
            return self._session.amount_to_precision(pair, amount)
        except Exception as e:
            return 0
    
    def price_to_precision(self, pair: str, price: float) -> float:
        pair = self.ext_pair_to_pair(pair)
        return self._session.price_to_precision(pair, price)

    async def get_last_ohlcv(self, pair, timeframe, limit=1000) -> pd.DataFrame:
        if limit > 5000:
            limit = 5000
        base_pair = self.ext_pair_to_base(pair)
        ts_dict = {
            "1m": 1 * 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "2h": 2 * 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
        }
        end_ts = int(time.time() * 1000)
        start_ts = end_ts - ((limit) * ts_dict[timeframe])
        current_ts = start_ts
        tasks = []
        while current_ts < end_ts:
            req_end_ts = min(current_ts + (hyperliquid_limit * ts_dict[timeframe]), end_ts)
            tasks.append(
                self._session.fetch_ohlcv(
                    pair,
                    timeframe,
                    params={
                        "limit": hyperliquid_limit,
                        "startTime": str(current_ts),
                        "endTime": str(req_end_ts),
                    },
                )
            )
            current_ts += (hyperliquid_limit * ts_dict[timeframe]) + 1
        ohlcv_unpack = await asyncio.gather(*tasks)
        ohlcv_list = list(itertools.chain.from_iterable(ohlcv_unpack))
        df = pd.DataFrame(
            ohlcv_list, columns=["date", "open", "high", "low", "close", "volume"]
        )
        df = df.set_index(df["date"])
        df.index = pd.to_datetime(df.index, unit="ms")
        df = df.sort_index()
        del df["date"]
        return df

    async def get_balance(self) -> UsdtBalance:
        data = await self._session.publicPostInfo(params={
            "type": "clearinghouseState",
            "user": self.public_api,
        })
        total = float(data["marginSummary"]["accountValue"])
        used = float(data["marginSummary"]["totalMarginUsed"])
        free = total - used
        return UsdtBalance(
            total=total,
            free=free,
            used=used,
        )

    async def set_margin_mode_and_leverage(self, pair, margin_mode, leverage):
        if margin_mode not in ["cross", "isolated"]:
            raise Exception("Margin mode must be either 'cross' or 'isolated'")
        asset_index = self.market[pair].coin_index
        try:
            nonce = int(time.time() * 1000)
            req_body = {}
            action = {
                "type": "updateLeverage",
                "asset": asset_index,
                "isCross": margin_mode == "cross",
                "leverage": leverage,
            }
            signature = self._session.sign_l1_action(action, nonce)
            req_body["action"] = action
            req_body["nonce"] = nonce
            req_body["signature"] = signature
            await self._session.private_post_exchange(params=req_body)
        except Exception as e:
            raise e

        return Info(
            success=True,
            message=f"Margin mode and leverage set to {margin_mode} and {leverage}x",
        )

    async def get_open_positions(self, pairs=[]) -> List[Position]:
        data = await self._session.publicPostInfo(params={
            "type": "clearinghouseState",
            "user": self.public_api,
        })
        # return data
        positions_data = data["assetPositions"]
        positions = []
        for position_data in positions_data:
            position = position_data["position"]
            if self.pair_to_ext_pair(position["coin"]) not in pairs and len(pairs) > 0:
                continue
            type_mode = position_data["type"]
            hedge_mode = True if type_mode != "oneWay" else False
            size = float(position["szi"])
            side = "long" if size > 0 else "short"
            size = abs(size)
            usd_size = float(position["positionValue"])
            current_price = usd_size / size
            positions.append(
                Position(
                    pair=self.pair_to_ext_pair(position["coin"]),
                    side=side,
                    size=size,
                    usd_size=usd_size,
                    entry_price=float(position["entryPx"]),
                    current_price=current_price,
                    unrealized_pnl=float(position["unrealizedPnl"]),
                    liquidation_price=float(position["liquidationPx"]),
                    margin_mode=position["leverage"]["type"],
                    leverage=position["leverage"]["value"],
                    hedge_mode=hedge_mode,
                )
            )

        return positions

    async def place_order(
        self,
        pair,
        side,
        price,
        size,
        type="limit",
        reduce=False,
        error=True,
        market_max_spread=0.1,
    ) -> Order:
        if price is None:
            price = self.market[pair].market_price
        try:
            asset_index = self.market[pair].coin_index
            nonce = int(time.time() * 1000)
            is_buy = side == "buy"
            req_body = {}
            if type == "market":
                if side == "buy":
                    price = price * (1 + market_max_spread)
                else:
                    price = price * (1 - market_max_spread)

            print(number_to_str(self.price_to_precision(pair, price)))
            action = {
                "type": "order",
                "orders": [{
                    "a": asset_index,
                    "b": is_buy,
                    "p": number_to_str(self.price_to_precision(pair, price)),
                    "s": number_to_str(self.size_to_precision(pair, size)),
                    "r": reduce,
                    "t": {"limit":{"tif": "Gtc"}}
                }],
                "grouping": "na",
                "brokerCode": 1,
            }
            signature = self._session.sign_l1_action(action, nonce)
            req_body["action"] = action
            req_body["nonce"] = nonce
            req_body["signature"] = signature
            resp = await self._session.private_post_exchange(params=req_body)
            
            order_resp = resp["response"]["data"]["statuses"][0]
            order_key = list(order_resp.keys())[0]
            order_id = resp["response"]["data"]["statuses"][0][order_key]["oid"]

            order = await self.get_order_by_id(order_id)

            if order_key == "filled":
                order_price = resp["response"]["data"]["statuses"][0][order_key]["avgPx"]
                order.price = float(order_price)
            
            return order
        except Exception as e:
            if error:
                raise e
            else:
                print(e)
                return None


    async def get_order_by_id(self, order_id) -> Order:
        order_id = int(order_id)
        data = await self._session.publicPostInfo(params={
            "user": self.public_api,
            "type": "orderStatus",
            "oid": order_id,
        })
        order = data["order"]["order"]
        side_map = {
            "A": "sell",
            "B": "buy",
        }
        return Order(
            id=str(order_id),
            pair=self.pair_to_ext_pair(order["coin"]),
            type=order["orderType"].lower(),
            side=side_map[order["side"]],
            price=float(order["limitPx"]),
            size=float(order["origSz"]),
            reduce=order["reduceOnly"],
            filled=float(order["origSz"]) - float(order["sz"]),
            remaining=float(order["sz"]),
            timestamp=int(order["timestamp"]),
        )

   async def cancel_orders(self, pair, ids=[]):
        try:
            pair = self.ext_pair_to_pair(pair)
            resp = await self._session.cancel_orders(
                ids=ids,
                symbol=pair,
            )
            return Info(success=True, message=f"{len(resp)} Orders cancelled")
        except Exception as e:
            return Info(success=False, message="Error or no orders to cancel")

    async def cancel_trigger_orders(self, pair, ids=[]):
        try:
            pair = self.ext_pair_to_pair(pair)
            resp = await self._session.cancel_orders(
                ids=ids, symbol=pair, params={"stop": True}
            )
            return Info(success=True, message=f"{len(resp)} Trigger Orders cancelled")
        except Exception as e:
            return Info(success=False, message="Error or no orders to cancel")
