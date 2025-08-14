from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    trade_type = Column(String(4), nullable=False)  # 'BUY' or 'SELL'
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    investment_amount = Column(Float, nullable=False)
    reason = Column(String(50))  # 'initial', 'profit_target', 'stop_loss', 'eod_close'
    portfolio_value = Column(Float)  # Total portfolio value after this trade
    pnl = Column(Float, default=0.0)  # Profit/Loss for this trade
    position_id = Column(Integer, ForeignKey('positions.id'))  # Link to position
    
class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, unique=True)
    quantity = Column(Float, nullable=False, default=0)
    average_cost = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)  # Entry price for PnL calculation
    exit_price = Column(Float)  # Exit price when position is closed
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)  # When position was closed
    is_active = Column(Boolean, default=True)
    realized_pnl = Column(Float, default=0.0)  # Realized profit/loss when closed
    
class Portfolio(Base):
    __tablename__ = 'portfolio'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cash_balance = Column(Float, nullable=False, default=10000.0)
    total_value = Column(Float, nullable=False, default=10000.0)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    daily_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)

class TradingLog(Base):
    __tablename__ = 'trading_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    message = Column(Text, nullable=False)
    log_type = Column(String(20), default='INFO')  # 'INFO', 'ERROR', 'TRADE'

# Database setup
def create_tables():
    """Create all database tables"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("Warning: DATABASE_URL not found, using in-memory SQLite")
        database_url = 'sqlite:///:memory:'
    
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Get database session"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        database_url = 'sqlite:///:memory:'
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()