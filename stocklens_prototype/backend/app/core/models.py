from datetime import datetime
from sqlalchemy import (Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey,
                        UniqueConstraint, Text, BigInteger, Index)
from sqlalchemy.orm import relationship
from app.core.database import Base

class Sector(Base):
    __tablename__ = "sectors"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(10), default="NSE")
    isin = Column(String(20), unique=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"))
    shares_outstanding_cr = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sector = relationship("Sector")

class FinancialResult(Base):
    """Annual consolidated statements (P&L + balance sheet + cash-flow items in one row for the MVP)."""
    __tablename__ = "financial_results"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    period_end = Column(Date, nullable=False)
    filing_date = Column(Date, nullable=False)
    basis = Column(String(20), default="consolidated")
    revision = Column(Integer, default=0)
    revenue = Column(Float); expenses = Column(Float); ebitda = Column(Float)
    depreciation = Column(Float); interest = Column(Float); pbt = Column(Float)
    tax = Column(Float); pat = Column(Float); eps = Column(Float)
    total_equity = Column(Float); total_debt = Column(Float); cash = Column(Float)
    current_assets = Column(Float); current_liabilities = Column(Float)
    receivables = Column(Float); cfo = Column(Float)
    source = Column(String(50), default="synthetic_seed")
    __table_args__ = (UniqueConstraint("company_id", "fiscal_year", "basis", "revision"),)

class DailyPrice(Base):
    __tablename__ = "daily_prices"
    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)
    trading_date = Column(Date, primary_key=True)
    close = Column(Float); volume = Column(BigInteger)
    __table_args__ = (Index("ix_price_date", "trading_date"),)

class Shareholding(Base):
    __tablename__ = "shareholding_patterns"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    period_end = Column(Date, nullable=False)
    promoter_pct = Column(Float); fii_pct = Column(Float); dii_pct = Column(Float)
    public_pct = Column(Float); pledged_pct = Column(Float)
    __table_args__ = (UniqueConstraint("company_id", "period_end"),)

class RatioSnapshot(Base):
    """Materialised, screener-ready ratios (one row per company), refreshed by the ratio job."""
    __tablename__ = "ratio_snapshots"
    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)
    as_of_date = Column(Date)
    price = Column(Float); market_cap = Column(Float); pe = Column(Float); pb = Column(Float)
    peg = Column(Float); ev_ebitda = Column(Float)
    roce = Column(Float); roe = Column(Float); debt_equity = Column(Float)
    interest_coverage = Column(Float); current_ratio = Column(Float)
    ebitda_margin = Column(Float); pat_margin = Column(Float); cfo_pat = Column(Float)
    sales_growth_1y = Column(Float); sales_growth_3y = Column(Float)
    profit_growth_1y = Column(Float); profit_growth_3y = Column(Float)
    promoter_holding = Column(Float); pledged_pct = Column(Float)
    fii_holding = Column(Float); dii_holding = Column(Float)
    ret_1m = Column(Float); ret_3m = Column(Float); ret_6m = Column(Float)
    rsi_14 = Column(Float); pct_from_52w_high = Column(Float); volume_ratio = Column(Float)

class SavedScreen(Base):
    __tablename__ = "saved_screens"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    query_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ManagementGuidance(Base):
    __tablename__ = "management_guidance"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    metric = Column(String(100)); guidance_low = Column(Float); guidance_high = Column(Float)
    unit = Column(String(30)); period = Column(String(30)); guidance_date = Column(Date)
    source_note = Column(String(200))

class GuidanceActual(Base):
    __tablename__ = "guidance_actuals"
    id = Column(Integer, primary_key=True)
    guidance_id = Column(Integer, ForeignKey("management_guidance.id"), nullable=False)
    actual_value = Column(Float); reported_date = Column(Date)

class DataQualityLog(Base):
    __tablename__ = "data_quality_logs"
    id = Column(Integer, primary_key=True)
    dataset = Column(String(60)); status = Column(String(30)); mode = Column(String(20))
    last_updated = Column(Date); note = Column(String(200))
