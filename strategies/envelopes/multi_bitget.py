import datetime
import sys
import json
import os
from pathlib import Path

sys.path.append("./Live-Tools-V2")

import asyncio
from utilities.bitget_perp import PerpBitget
from secret import ACCOUNTS
import ta

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configuration du tracking PnL
TRACKING_FILE = "strategies/envelopes/bitget_tracking.json"
CRONLOG_FILE = "cronlog.log"

def load_tracking_data():
    """Charger les données de tracking PnL global et par crypto"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "initial_balance": None,
        "last_balance": None,
        "start_date": None,
        "trades": [],
        "daily_snapshots": [],
        "stats": {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "winrate": 0.0
        },
        "crypto_stats": {}  # Nouveau: stats par crypto
    }

def save_tracking_data(data):
    """Sauvegarder les données de tracking PnL"""
    os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_timeframe_stats(trades, days):
    """Calculer les stats pour une période donnée"""
    if not trades:
        return {"trades": 0, "pnl": 0.0, "winrate": 0.0}
    
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    recent_trades = [
        trade for trade in trades 
        if datetime.datetime.fromisoformat(trade["timestamp"]) > cutoff_date
    ]
    
    if not recent_trades:
        return {"trades": 0, "pnl": 0.0, "winrate": 0.0}
    
    total_trades = len(recent_trades)
    winning_trades = sum(1 for trade in recent_trades if trade["pnl"] > 0)
    total_pnl = sum(trade["pnl"] for trade in recent_trades)
    winrate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    return {
        "trades": total_trades,
        "pnl": total_pnl,
        "winrate": winrate
    }

def log_to_cronlog(message):
    """Écrire dans cronlog.log"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(CRONLOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")

def initialize_crypto_stats(crypto_stats, pair):
    """Initialiser les stats pour une crypto si elle n'existe pas"""
    if pair not in crypto_stats:
        crypto_stats[pair] = {
            "trades": [],
            "stats": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "winrate": 0.0,
                "last_position_size": 0.0,
                "last_unrealized_pnl": 0.0
            },
            "daily_snapshots": []
        }

def calculate_crypto_timeframe_stats(crypto_data, days):
    """Calculer les stats pour une crypto sur une période donnée"""
    trades = crypto_data.get("trades", [])
    if not trades:
        return {"trades": 0, "pnl": 0.0, "winrate": 0.0}
    
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    recent_trades = [
        trade for trade in trades 
        if datetime.datetime.fromisoformat(trade["timestamp"]) > cutoff_date
    ]
    
    if not recent_trades:
        return {"trades": 0, "pnl": 0.0, "winrate": 0.0}
    
    total_trades = len(recent_trades)
    winning_trades = sum(1 for trade in recent_trades if trade["pnl"] > 0)
    total_pnl = sum(trade["pnl"] for trade in recent_trades)
    winrate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    return {
        "trades": total_trades,
        "pnl": total_pnl,
        "winrate": winrate
    }

def update_performance_stats(tracking_data, current_balance, positions):
    """Mettre à jour les statistiques de performance"""
    now = datetime.datetime.now()
    
    # Initialisation si première exécution
    if tracking_data["initial_balance"] is None:
        tracking_data["initial_balance"] = current_balance
        tracking_data["start_date"] = now.isoformat()
    
    # Calculer le PnL depuis le dernier snapshot
    last_balance = tracking_data["last_balance"] or tracking_data["initial_balance"]
    balance_change = current_balance - last_balance
    
    # Ajouter un snapshot quotidien
    today = now.strftime('%Y-%m-%d')
    snapshots = tracking_data["daily_snapshots"]
    
    # Mettre à jour ou ajouter le snapshot d'aujourd'hui
    today_snapshot = next((s for s in snapshots if s["date"] == today), None)
    if today_snapshot:
        today_snapshot["balance"] = current_balance
        today_snapshot["positions"] = len(positions)
    else:
        snapshots.append({
            "date": today,
            "balance": current_balance,
            "positions": len(positions),
            "timestamp": now.isoformat()
        })
    
    # Garder seulement les 365 derniers jours
    cutoff_date = (now - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    tracking_data["daily_snapshots"] = [
        s for s in snapshots if s["date"] >= cutoff_date
    ]
    
    # Détecter les trades fermés (changement de positions)
    if abs(balance_change) > 0.01:  # Seuil minimal pour détecter un trade
        trade = {
            "timestamp": now.isoformat(),
            "pnl": balance_change,
            "balance_before": last_balance,
            "balance_after": current_balance,
            "positions_count": len(positions)
        }
        tracking_data["trades"].append(trade)
        
        # Mettre à jour les stats globales
        stats = tracking_data["stats"]
        stats["total_trades"] += 1
        stats["total_pnl"] += balance_change
        
        if balance_change > 0:
            stats["winning_trades"] += 1
        else:
            stats["losing_trades"] += 1
        
        stats["winrate"] = (stats["winning_trades"] / stats["total_trades"]) * 100
    
    tracking_data["last_balance"] = current_balance
    return tracking_data

def update_crypto_performance_stats(tracking_data, positions):
    """Mettre à jour les statistiques de performance par crypto"""
    now = datetime.datetime.now()
    
    # S'assurer que crypto_stats existe
    if "crypto_stats" not in tracking_data:
        tracking_data["crypto_stats"] = {}
    
    crypto_stats = tracking_data["crypto_stats"]
    
    # Traiter chaque position
    for position in positions:
        pair = position.pair
        initialize_crypto_stats(crypto_stats, pair)
        
        crypto_data = crypto_stats[pair]
        last_unrealized_pnl = crypto_data["stats"]["last_unrealized_pnl"]
        last_position_size = crypto_data["stats"]["last_position_size"]
        
        # Détecter un changement de PnL significatif pour cette crypto
        pnl_change = position.unrealizedPnl - last_unrealized_pnl
        size_change = position.size - last_position_size
        
        # Si changement significatif (fermeture partielle/totale ou nouveau trade)
        if abs(pnl_change) > 0.1 or abs(size_change) > 0.001:
            # Enregistrer le trade pour cette crypto
            crypto_trade = {
                "timestamp": now.isoformat(),
                "pnl": pnl_change,
                "position_size": position.size,
                "unrealized_pnl": position.unrealizedPnl,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "side": position.side
            }
            crypto_data["trades"].append(crypto_trade)
            
            # Mettre à jour les stats de cette crypto
            crypto_stats_data = crypto_data["stats"]
            crypto_stats_data["total_trades"] += 1
            crypto_stats_data["total_pnl"] += pnl_change
            
            if pnl_change > 0:
                crypto_stats_data["winning_trades"] += 1
            else:
                crypto_stats_data["losing_trades"] += 1
            
            if crypto_stats_data["total_trades"] > 0:
                crypto_stats_data["winrate"] = (crypto_stats_data["winning_trades"] / crypto_stats_data["total_trades"]) * 100
        
        # Mettre à jour les dernières valeurs
        crypto_data["stats"]["last_position_size"] = position.size
        crypto_data["stats"]["last_unrealized_pnl"] = position.unrealizedPnl
        
        # Ajouter snapshot quotidien pour cette crypto
        today = now.strftime('%Y-%m-%d')
        crypto_snapshots = crypto_data["daily_snapshots"]
        
        today_crypto_snapshot = next((s for s in crypto_snapshots if s["date"] == today), None)
        if today_crypto_snapshot:
            today_crypto_snapshot["unrealized_pnl"] = position.unrealizedPnl
            today_crypto_snapshot["position_size"] = position.size
            today_crypto_snapshot["entry_price"] = position.entry_price
        else:
            crypto_snapshots.append({
                "date": today,
                "unrealized_pnl": position.unrealizedPnl,
                "position_size": position.size,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "side": position.side,
                "timestamp": now.isoformat()
            })
        
        # Garder seulement les 365 derniers jours
        cutoff_date = (now - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        crypto_data["daily_snapshots"] = [
            s for s in crypto_snapshots if s["date"] >= cutoff_date
        ]
    
    return tracking_data


async def main():
    account = ACCOUNTS["bitget1"]

    margin_mode = "isolated"  # isolated or crossed
    leverage = 2
    hedge_mode = True # Warning, set to False if you are in one way mode

    tf = "1h"
    sl = 0.5
    params = {
       "INJ/USDT": {
            "src": "close",
            "ma_base_window": 20,
            "envelopes": [0.077],
            "size": 0.0312,
            "sides": ["long"],
        },
         "XRP/USDT": {
            "src": "close",
            "ma_base_window": 12,
            "envelopes": [0.036],
            "size": 0.0312,
            "sides": ["long"],
        },
        "PYTH/USDT": {
            "src": "close",
            "ma_base_window": 17,
            "envelopes": [0.07],
            "size": 0.0312,
            "sides": ["long"],
        },
        "TIA/USDT": {
            "src": "close",
            "ma_base_window": 13,
            "envelopes": [0.059],
            "size": 0.0312,
            "sides": ["long"],
        },
        "SUI/USDT": {
            "src": "close",
            "ma_base_window": 17,
            "envelopes": [0.05],
            "size": 0.0312,
            "sides": ["long"],
        },
        "KSM/USDT": {
            "src": "close",
            "ma_base_window": 16,
            "envelopes": [0.06],
            "size": 0.0312,
            "sides": ["long"],
        },
        "AVAX/USDT": {
            "src": "close",
            "ma_base_window": 15,
            "envelopes": [0.065],
            "size": 0.0312,
            "sides": ["long"],
        },
        "RENDER/USDT": {
            "src": "close",
            "ma_base_window": 16,
            "envelopes": [0.042],
            "size": 0.0312,
            "sides": ["long"],
        },
        "VET/USDT": {
            "src": "close",
            "ma_base_window": 19,
            "envelopes": [0.056],
            "size": 0.0312,
            "sides": ["long"],
        },
        "ALGO/USDT": {
            "src": "close",
            "ma_base_window": 17,
            "envelopes": [0.056],
            "size": 0.0312,
            "sides": ["long"],
        },
        "DYM/USDT": {
            "src": "close",
            "ma_base_window": 14,
            "envelopes": [0.075],
            "size": 0.0312,
            "sides": ["long"],
        },
        "ADA/USDT": {
            "src": "close",
            "ma_base_window": 15,
            "envelopes": [0.05],
            "size": 0.0312,
            "sides": ["long"],
        },
        "GRASS/USDT": {
            "src": "close",
            "ma_base_window": 31,
            "envelopes": [0.14],
            "size": 0.0312,
            "sides": ["long"],
        },
         "NEAR/USDT": {
            "src": "close",
            "ma_base_window": 19,
            "envelopes": [0.037],
            "size": 0.0312,
            "sides": ["long"],
        },
        "SOL/USDT": {
            "src": "close",
            "ma_base_window": 14,
            "envelopes": [0.05],
            "size": 0.0312,
            "sides": ["long"],
        },
        "OM/USDT": {
            "src": "close",
            "ma_base_window": 16,
            "envelopes": [0.046],
            "size": 0.0312,
            "sides": ["long"],
        },
        "PEPE/USDT": {
            "src": "close",
            "ma_base_window": 9,
            "envelopes": [0.062],
            "size": 0.0312,
            "sides": ["long"],
        },
        "HBAR/USDT": {
            "src": "close",
            "ma_base_window": 22,
            "envelopes": [0.053],
            "size": 0.0312,
            "sides": ["long"],
        },
        "DOGE/USDT": {
            "src": "close",
            "ma_base_window": 14,
            "envelopes": [0.051],
            "size": 0.0312,
            "sides": ["long"],
        },
        "DOT/USDT": {
            "src": "close",
            "ma_base_window": 30,
            "envelopes": [0.057],
            "size": 0.0312,
            "sides": ["long"],
        },
        "KAS/USDT": {
            "src": "close",
            "ma_base_window": 22,
            "envelopes": [0.066],
            "size": 0.0312,
            "sides": ["long"],
        },
        "GRT/USDT": {
            "src": "close",
            "ma_base_window": 19,
            "envelopes": [0.053],
            "size": 0.0312,
            "sides": ["long"],
        },
        "TAO/USDT": {
            "src": "close",
            "ma_base_window": 22,
            "envelopes": [0.054],
            "size": 0.0312,
            "sides": ["long"],
        },
        "ETH/USDT": {
            "src": "close",
            "ma_base_window": 20,
            "envelopes": [0.052],
            "size": 0.0312,
            "sides": ["long"],
        },
        "FIL/USDT": {
            "src": "close",
            "ma_base_window": 40,
            "envelopes": [0.06],
            "size": 0.0312,
            "sides": ["long"],
        },
         "ICP/USDT": {
            "src": "close",
            "ma_base_window": 18,
            "envelopes": [0.061],
            "size": 0.0312,
            "sides": ["long"],
        },
         "HYPE/USDT": {
            "src": "close",
            "ma_base_window": 15,
            "envelopes": [0.069],
            "size": 0.0312,
            "sides": ["long"],
        },
         "ONDO/USDT": {
            "src": "close",
            "ma_base_window": 17,
            "envelopes": [0.051],
            "size": 0.0312,
            "sides": ["long"],
        },
         "SEI/USDT": {
            "src": "close",
            "ma_base_window": 13,
            "envelopes": [0.065],
            "size": 0.0312,
            "sides": ["long"],
        },
         "FET/USDT": {
            "src": "close",
            "ma_base_window": 15,
            "envelopes": [0.056],
            "size": 0.0312,
            "sides": ["long"],
        },
         "TON/USDT": {
            "src": "close",
            "ma_base_window": 17,
            "envelopes": [0.061],
            "size": 0.0312,
            "sides": ["long"],
        },
         "JUP/USDT": {
            "src": "close",
            "ma_base_window": 17,
            "envelopes": [0.083],
            "size": 0.0312,
            "sides": ["long"],
        },
    }

    exchange = PerpBitget(
        public_api=account["public_api"],
        secret_api=account["secret_api"],
        password=account["password"],
    )
    invert_side = {"long": "sell", "short": "buy"}
    print(
        f"--- Execution started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
    )
    try:
        await exchange.load_markets()

        for pair in params.copy():
            info = exchange.get_pair_info(pair)
            if info is None:
                print(f"Pair {pair} not found, removing from params...")
                del params[pair]

        pairs = list(params.keys())

        try:
            print(
                f"Setting {margin_mode} x{leverage} on {len(pairs)} pairs..."
            )
            tasks = [
                exchange.set_margin_mode_and_leverage(
                    pair, margin_mode, leverage
                )
                for pair in pairs
            ]
            await asyncio.gather(*tasks)  # set leverage and margin mode for all pairs
        except Exception as e:
            print(e)

        print(f"Getting data and indicators on {len(pairs)} pairs...")
        tasks = [exchange.get_last_ohlcv(pair, tf, 50) for pair in pairs]
        dfs = await asyncio.gather(*tasks)
        df_list = dict(zip(pairs, dfs))

        for pair in df_list:
            current_params = params[pair]
            df = df_list[pair]
            if current_params["src"] == "close":
                src = df["close"]
            elif current_params["src"] == "ohlc4":
                src = (df["close"] + df["high"] + df["low"] + df["open"]) / 4

            df["ma_base"] = ta.trend.sma_indicator(
                close=src, window=current_params["ma_base_window"]
            )
            high_envelopes = [
                round(1 / (1 - e) - 1, 3) for e in current_params["envelopes"]
            ]
            for i in range(1, len(current_params["envelopes"]) + 1):
                df[f"ma_high_{i}"] = df["ma_base"] * (1 + high_envelopes[i - 1])
                df[f"ma_low_{i}"] = df["ma_base"] * (
                    1 - current_params["envelopes"][i - 1]
                )

            df_list[pair] = df

        usdt_balance = await exchange.get_balance()
        usdt_balance = usdt_balance.total
        print(f"Balance: {round(usdt_balance, 2)} USDT")
        
        # Charger les données de tracking
        tracking_data = load_tracking_data()

        tasks = [exchange.get_open_trigger_orders(pair) for pair in pairs]
        print(f"Getting open trigger orders...")
        trigger_orders = await asyncio.gather(*tasks)
        trigger_order_list = dict(
            zip(pairs, trigger_orders)
        )  # Get all open trigger orders by pair

        tasks = []
        for pair in df_list:
            params[pair]["canceled_orders_buy"] = len(
                [
                    order
                    for order in trigger_order_list[pair]
                    if (order.side == "buy" and order.reduce is False)
                ]
            )
            params[pair]["canceled_orders_sell"] = len(
                [
                    order
                    for order in trigger_order_list[pair]
                    if (order.side == "sell" and order.reduce is False)
                ]
            )
            tasks.append(
                exchange.cancel_trigger_orders(
                    pair, [order.id for order in trigger_order_list[pair]]
                )
            )
        print(f"Canceling trigger orders...")
        await asyncio.gather(*tasks)  # Cancel all trigger orders

        tasks = [exchange.get_open_orders(pair) for pair in pairs]
        print(f"Getting open orders...")
        orders = await asyncio.gather(*tasks)
        order_list = dict(zip(pairs, orders))  # Get all open orders by pair

        tasks = []
        for pair in df_list:
            params[pair]["canceled_orders_buy"] = params[pair][
                "canceled_orders_buy"
            ] + len(
                [
                    order
                    for order in order_list[pair]
                    if (order.side == "buy" and order.reduce is False)
                ]
            )
            params[pair]["canceled_orders_sell"] = params[pair][
                "canceled_orders_sell"
            ] + len(
                [
                    order
                    for order in order_list[pair]
                    if (order.side == "sell" and order.reduce is False)
                ]
            )
            tasks.append(
                exchange.cancel_orders(pair, [order.id for order in order_list[pair]])
            )

        print(f"Canceling limit orders...")
        await asyncio.gather(*tasks)  # Cancel all orders

        print(f"Getting live positions...")
        positions = await exchange.get_open_positions(pairs)
        
        # Mettre à jour les statistiques de performance globales
        tracking_data = update_performance_stats(tracking_data, usdt_balance, positions)
        
        # Mettre à jour les statistiques de performance par crypto
        tracking_data = update_crypto_performance_stats(tracking_data, positions)
        
        # Calculer le PnL total unrealized des positions ouvertes
        total_unrealized_pnl = sum(pos.unrealizedPnl for pos in positions)
        
        tasks_close = []
        tasks_open = []
        for position in positions:
            print(
                f"Current position on {position.pair} {position.side} - {position.size} ~ {position.usd_size} $ (PnL: {position.unrealizedPnl})"
            )
            row = df_list[position.pair].iloc[-2]
            tasks_close.append(
                exchange.place_order(
                    pair=position.pair,
                    side=invert_side[position.side],
                    price=row["ma_base"],
                    size=exchange.amount_to_precision(position.pair, position.size),
                    type="limit",
                    reduce=True,
                    margin_mode=margin_mode,
                    hedge_mode=hedge_mode,
                    error=False,
                )
            )
            if position.side == "long":
                sl_side = "sell"
                sl_price = exchange.price_to_precision(
                    position.pair, position.entry_price * (1 - sl)
                )
            elif position.side == "short":
                sl_side = "buy"
                sl_price = exchange.price_to_precision(
                    position.pair, position.entry_price * (1 + sl)
                )
            tasks_close.append(
                exchange.place_trigger_order(
                    pair=position.pair,
                    side=sl_side,
                    trigger_price=sl_price,
                    price=None,
                    size=exchange.amount_to_precision(position.pair, position.size),
                    type="market",
                    reduce=True,
                    margin_mode=margin_mode,
                    hedge_mode=hedge_mode,
                    error=False,
                )
            )
            for i in range(
                len(params[position.pair]["envelopes"])
                - params[position.pair]["canceled_orders_buy"],
                len(params[position.pair]["envelopes"]),
            ):
                tasks_open.append(
                    exchange.place_trigger_order(
                        pair=position.pair,
                        side="buy",
                        price=exchange.price_to_precision(
                            position.pair, row[f"ma_low_{i+1}"]
                        ),
                        trigger_price=exchange.price_to_precision(
                            position.pair, row[f"ma_low_{i+1}"] * 1.005
                        ),
                        size=exchange.amount_to_precision(
                            position.pair,
                            (
                                (params[position.pair]["size"] * usdt_balance)
                                / len(params[position.pair]["envelopes"])
                                * leverage
                            )
                            / row[f"ma_low_{i+1}"],
                        ),
                        type="limit",
                        reduce=False,
                        margin_mode=margin_mode,
                        hedge_mode=hedge_mode,
                        error=False,
                    )
                )
            for i in range(
                len(params[position.pair]["envelopes"])
                - params[position.pair]["canceled_orders_sell"],
                len(params[position.pair]["envelopes"]),
            ):
                tasks_open.append(
                    exchange.place_trigger_order(
                        pair=position.pair,
                        side="sell",
                        trigger_price=exchange.price_to_precision(
                            position.pair, row[f"ma_high_{i+1}"] * 0.995
                        ),
                        price=exchange.price_to_precision(
                            position.pair, row[f"ma_high_{i+1}"]
                        ),
                        size=exchange.amount_to_precision(
                            position.pair,
                            (
                                (params[position.pair]["size"] * usdt_balance)
                                / len(params[position.pair]["envelopes"])
                                * leverage
                            )
                            / row[f"ma_high_{i+1}"],
                        ),
                        type="limit",
                        reduce=False,
                        margin_mode=margin_mode,
                        hedge_mode=hedge_mode,
                        error=False,
                    )
                )

        print(f"Placing {len(tasks_close)} close SL / limit order...")
        await asyncio.gather(*tasks_close)  # Limit orders when in positions

        pairs_not_in_position = [
            pair
            for pair in pairs
            if pair not in [position.pair for position in positions]
        ]
        for pair in pairs_not_in_position:
            row = df_list[pair].iloc[-2]
            for i in range(len(params[pair]["envelopes"])):
                if "long" in params[pair]["sides"]:
                    tasks_open.append(
                        exchange.place_trigger_order(
                            pair=pair,
                            side="buy",
                            price=exchange.price_to_precision(
                                pair, row[f"ma_low_{i+1}"]
                            ),
                            trigger_price=exchange.price_to_precision(
                                pair, row[f"ma_low_{i+1}"] * 1.005
                            ),
                            size=exchange.amount_to_precision(
                                pair,
                                (
                                    (params[pair]["size"] * usdt_balance)
                                    / len(params[pair]["envelopes"])
                                    * leverage
                                )
                                / row[f"ma_low_{i+1}"],
                            ),
                            type="limit",
                            reduce=False,
                            margin_mode=margin_mode,
                            hedge_mode=hedge_mode,
                            error=False,
                        )
                    )
                if "short" in params[pair]["sides"]:
                    tasks_open.append(
                        exchange.place_trigger_order(
                            pair=pair,
                            side="sell",
                            trigger_price=exchange.price_to_precision(
                                pair, row[f"ma_high_{i+1}"] * 0.995
                            ),
                            price=exchange.price_to_precision(
                                pair, row[f"ma_high_{i+1}"]
                            ),
                            size=exchange.amount_to_precision(
                                pair,
                                (
                                    (params[pair]["size"] * usdt_balance)
                                    / len(params[pair]["envelopes"])
                                    * leverage
                                )
                                / row[f"ma_high_{i+1}"],
                            ),
                            type="limit",
                            reduce=False,
                            margin_mode=margin_mode,
                            hedge_mode=hedge_mode,
                            error=False,
                        )
                    )

        print(f"Placing {len(tasks_open)} open limit order...")
        await asyncio.gather(*tasks_open)  # Limit orders when not in positions

        # Sauvegarder les données de tracking
        save_tracking_data(tracking_data)
        
        # Calculer les statistiques par timeframe
        stats_1w = calculate_timeframe_stats(tracking_data["trades"], 7)
        stats_1m = calculate_timeframe_stats(tracking_data["trades"], 30)
        stats_all = tracking_data["stats"]
        
        # Calculer le PnL total (réalisé + non réalisé)
        total_pnl = stats_all["total_pnl"] + total_unrealized_pnl
        initial_balance = tracking_data["initial_balance"] or usdt_balance
        pnl_percentage = ((usdt_balance + total_unrealized_pnl) / initial_balance - 1) * 100
        
        # Log des performances dans cronlog.log
        performance_log = f"""
=== BITGET ENVELOPES STRATEGY PERFORMANCE ===
Execution: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Balance: {usdt_balance:.2f} USDT
Unrealized PnL: {total_unrealized_pnl:.2f} USDT
Active Positions: {len(positions)}
Initial Balance: {initial_balance:.2f} USDT
Total PnL: {total_pnl:.2f} USDT ({pnl_percentage:+.2f}%)

=== PERFORMANCE BY TIMEFRAME ===
📊 ALL TIME:
  - Trades: {stats_all['total_trades']}
  - Win Rate: {stats_all['winrate']:.1f}%
  - Total PnL: {stats_all['total_pnl']:.2f} USDT
  
📊 LAST 30 DAYS:
  - Trades: {stats_1m['trades']}
  - Win Rate: {stats_1m['winrate']:.1f}%
  - PnL: {stats_1m['pnl']:.2f} USDT
  
📊 LAST 7 DAYS:
  - Trades: {stats_1w['trades']}
  - Win Rate: {stats_1w['winrate']:.1f}%
  - PnL: {stats_1w['pnl']:.2f} USDT

=== PERFORMANCE PAR CRYPTOMONNAIE ==="""
        
        # Ajouter les stats par crypto
        crypto_stats = tracking_data.get("crypto_stats", {})
        if crypto_stats:
            # Trier les cryptos par PnL total (descendant)
            sorted_cryptos = sorted(
                crypto_stats.items(), 
                key=lambda x: x[1]["stats"]["total_pnl"], 
                reverse=True
            )
            
            for pair, crypto_data in sorted_cryptos:
                c_stats = crypto_data["stats"]
                c_stats_1w = calculate_crypto_timeframe_stats(crypto_data, 7)
                c_stats_1m = calculate_crypto_timeframe_stats(crypto_data, 30)
                
                if c_stats["total_trades"] > 0 or c_stats["last_unrealized_pnl"] != 0:
                    performance_log += f"\\n🔸 {pair}:\\n"
                    performance_log += f"  All Time: {c_stats['total_trades']} trades, {c_stats['winrate']:.1f}% WR, {c_stats['total_pnl']:+.2f} USDT\\n"
                    performance_log += f"  Last 30d: {c_stats_1m['trades']} trades, {c_stats_1m['winrate']:.1f}% WR, {c_stats_1m['pnl']:+.2f} USDT\\n"
                    performance_log += f"  Last 7d:  {c_stats_1w['trades']} trades, {c_stats_1w['winrate']:.1f}% WR, {c_stats_1w['pnl']:+.2f} USDT"
                    if c_stats["last_unrealized_pnl"] != 0:
                        performance_log += f" | Current: {c_stats['last_position_size']:.4f} ({c_stats['last_unrealized_pnl']:+.2f} USDT)"
                    performance_log += "\\n"
        else:
            performance_log += "\\nAucune donnée par crypto pour le moment\\n"
            
        performance_log += "\\n=== POSITION DETAILS ==="""

        if positions:
            for pos in positions:
                performance_log += f"\\n  {pos.pair}: {pos.side} {pos.size:.4f} @ {pos.entry_price:.4f} (PnL: {pos.unrealizedPnl:+.2f} USDT)"
        else:
            performance_log += "\\n  No active positions"
            
        performance_log += f"\\n{'='*50}\\n"
        
        # Écrire dans cronlog.log
        log_to_cronlog("STRATEGY_PERFORMANCE")
        log_to_cronlog(performance_log)
        
        # Afficher les stats dans la console
        print(f"\\n🎯 Performance Summary:")
        print(f"Balance: {usdt_balance:.2f} USDT | Unrealized PnL: {total_unrealized_pnl:+.2f} USDT")
        print(f"All Time: {stats_all['total_trades']} trades, {stats_all['winrate']:.1f}% WR, {stats_all['total_pnl']:+.2f} USDT")
        print(f"Last 30d: {stats_1m['trades']} trades, {stats_1m['winrate']:.1f}% WR, {stats_1m['pnl']:+.2f} USDT")
        print(f"Last 7d: {stats_1w['trades']} trades, {stats_1w['winrate']:.1f}% WR, {stats_1w['pnl']:+.2f} USDT")
        
        # Afficher top/bottom cryptos
        crypto_stats = tracking_data.get("crypto_stats", {})
        if crypto_stats:
            active_cryptos = {
                k: v for k, v in crypto_stats.items() 
                if v["stats"]["total_pnl"] != 0 or v["stats"]["last_unrealized_pnl"] != 0
            }
            
            if active_cryptos:
                sorted_cryptos = sorted(active_cryptos.items(), key=lambda x: x[1]["stats"]["total_pnl"], reverse=True)
                
                if len(sorted_cryptos) > 0:
                    best_pair, best_data = sorted_cryptos[0]
                    print(f"🚀 Best: {best_pair} ({best_data['stats']['total_pnl']:+.2f} USDT, {best_data['stats']['winrate']:.1f}% WR)")
                    
                    if len(sorted_cryptos) > 1:
                        worst_pair, worst_data = sorted_cryptos[-1]
                        print(f"📉 Worst: {worst_pair} ({worst_data['stats']['total_pnl']:+.2f} USDT, {worst_data['stats']['winrate']:.1f}% WR)")

        await exchange.close()
        print(
            f"--- Execution finished at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
        )
    except Exception as e:
        await exchange.close()
        raise e


if __name__ == "__main__":
    asyncio.run(main())