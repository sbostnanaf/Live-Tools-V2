# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

### Environment Setup
```bash
# Install strategy (creates virtual environment and installs dependencies)
bash install.sh <strategy_name>

# Available strategies:
# - envelopes_multi_bitget
# - trix_multi_bitmart
# - trix_multi_bitmart_lite

# Manual setup
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running Strategies
```bash
# Activate virtual environment first
source .venv/bin/activate

# Run individual strategies
python3 strategies/envelopes/multi_bitget.py
python3 strategies/trix/multi_bitmart.py
python3 strategies/trix/multi_bitmart_lite.py

# View BitMart positions
python3 viewbitmart.py
```

### Cron Job Management
The `1hcron.sh` script contains the currently active strategies and runs hourly via cron:
```bash
# View current cron configuration
cat 1hcron.sh

# The install script automatically adds cron jobs
```

## Code Architecture

### Core Components

**Trading Utilities** (`utilities/`)
- `bitget_perp.py`: BitGet perpetual futures API wrapper with order management, position tracking, and risk management
- `bitmart_perp.py`: BitMart perpetual futures API wrapper with similar functionality to BitGet
- `hyperliquid_perp.py`: HyperLiquid protocol integration
- `custom_indicators.py`: Custom technical indicators including TRIX, Choppiness Index, and helper functions
- `discord_logger.py`: Discord webhook logging for trade notifications and alerts

**Trading Strategies** (`strategies/`)
- `envelopes/`: Moving average envelope strategy implementations
  - Uses percentage-based envelopes around moving averages
  - Configurable MA periods and envelope percentages per symbol
- `trix/`: TRIX indicator-based momentum strategies
  - Multi-timeframe TRIX crossover signals
  - Portfolio-based position management with JSON persistence
  - Support for both full and lite versions

### Key Design Patterns

**Account Configuration**
All strategies use `secret.py` for account credentials with this structure:
```python
ACCOUNTS = {
    "account_name": {
        "public_api": "api_key",
        "secret_api": "secret_key", 
        "password": "passphrase"
    }
}
```

**Strategy Parameters**
Each strategy defines parameters in a nested dictionary format:
- Symbol-specific parameters (MA lengths, envelope percentages, TRIX settings)
- Position sizing and risk management settings
- Leverage and margin mode configuration

**Async Architecture**
All exchange interactions use async/await pattern with ccxt.async_support for concurrent operations.

**Position Management**
- TRIX strategies use JSON files for position state persistence (`positions_*.json`)
- Envelope strategies operate stateless with fresh calculations each run
- Both support isolated/cross margin modes and configurable leverage

### Exchange Integration

**Supported Exchanges**
- BitGet: Perpetual futures with comprehensive order management
- BitMart: Perpetual futures with portfolio tracking
- HyperLiquid: Decentralized perpetual protocol

**Common Features**
- Market/limit order execution
- Position size calculation based on account balance
- Stop-loss and take-profit management  
- Hedge mode support for simultaneous long/short positions

## Development Notes

### Adding New Strategies
1. Create strategy file in appropriate subdirectory under `strategies/`
2. Import required utilities and indicators
3. Define strategy parameters following existing patterns
4. Implement async main() function with exchange wrapper initialization
5. Add strategy to `install.sh` for deployment

### Exchange API Wrappers
The utility classes provide standardized interfaces across exchanges:
- Balance fetching and position management
- Order placement with validation
- Market data retrieval and processing
- Error handling and retry logic

### Indicator Development
Custom indicators in `custom_indicators.py` follow pandas-based calculations and can be extended with new technical analysis functions.