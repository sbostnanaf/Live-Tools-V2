from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
import enum
from datetime import datetime

class TradeStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class TradeType(enum.Enum):
    LONG = "long"
    SHORT = "short"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    trading_accounts = relationship("TradingAccount", back_populates="user")

class TradingAccount(Base):
    __tablename__ = "trading_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    exchange = Column(String(50), nullable=False)  # bitget, bitmart, etc.
    api_key_encrypted = Column(Text)  # Encrypted API key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="trading_accounts")
    trades = relationship("Trade", back_populates="account")
    balance_history = relationship("BalanceHistory", back_populates="account")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)
    
    # Trade identification
    external_id = Column(String(100))  # ID from exchange
    strategy = Column(String(50), nullable=False)  # trix, envelope, etc.
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)  # BTCUSDT, ETHUSDT
    trade_type = Column(Enum(TradeType), nullable=False)
    status = Column(Enum(TradeStatus), nullable=False, index=True)
    
    # Price and quantity
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    quantity = Column(Float, nullable=False)
    leverage = Column(Float, default=1.0)
    
    # P&L calculation
    pnl_usd = Column(Float)
    pnl_percentage = Column(Float)
    fees_usd = Column(Float, default=0.0)
    
    # Timestamps
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    account = relationship("TradingAccount", back_populates="trades")

    # Indexes for performance
    __table_args__ = (
        Index('ix_trades_symbol_status', 'symbol', 'status'),
        Index('ix_trades_entry_time', 'entry_time'),
        Index('ix_trades_account_strategy', 'account_id', 'strategy'),
    )

class BalanceHistory(Base):
    __tablename__ = "balance_history"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)
    
    # Balance data
    total_balance_usd = Column(Float, nullable=False)
    available_balance_usd = Column(Float, nullable=False)
    unrealized_pnl_usd = Column(Float, default=0.0)
    
    # Additional metrics
    total_positions = Column(Integer, default=0)
    daily_pnl_usd = Column(Float, default=0.0)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    account = relationship("TradingAccount", back_populates="balance_history")

    # Indexes
    __table_args__ = (
        Index('ix_balance_history_account_timestamp', 'account_id', 'timestamp'),
    )

class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    
    # OHLCV data
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Timeframe (1h, 4h, 1d, etc.)
    timeframe = Column(String(10), nullable=False)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indexes
    __table_args__ = (
        Index('ix_market_data_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp'),
    )

class SystemMetrics(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    
    # System metrics
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    
    # Application metrics
    active_trades = Column(Integer, default=0)
    total_accounts = Column(Integer, default=0)
    api_requests_per_minute = Column(Integer, default=0)
    
    # Error tracking
    error_count_last_hour = Column(Integer, default=0)
    last_error_message = Column(Text)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Action details
    action = Column(String(100), nullable=False)  # login, trade_created, etc.
    resource = Column(String(100))  # trades, accounts, etc.
    resource_id = Column(String(100))
    
    # Request details
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Additional data
    details = Column(Text)  # JSON string with additional info
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index('ix_audit_logs_action_timestamp', 'action', 'timestamp'),
        Index('ix_audit_logs_user_timestamp', 'user_id', 'timestamp'),
    )