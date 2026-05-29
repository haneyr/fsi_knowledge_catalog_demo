#!/usr/bin/env python3
"""Creates NEXUS market data database, tables, synthetic data, and Horizon tags in Snowflake.

Requires SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD env vars.
The user must have FSI_KC_SETUP_ROLE (CREATE DATABASE, CREATE WAREHOUSE, APPLY TAG).

Usage: python3 snowflake/00_setup_nexus_data.py
"""

import logging
import random

from common_snowflake import (
    DATABASE, WAREHOUSE, SCHEMAS, TABLES, HORIZON_TAGS, TAG_ASSIGNMENTS,
    generate_cusip, generate_isin, us_business_days, get_snowflake_connection,
    CUSIP_SEED_RANGE,
)

logger = logging.getLogger(__name__)

BENCHMARKS = [
    "S&P 500", "Russell 2000", "MSCI EAFE", "Bloomberg US Agg",
    "MSCI Emerging Markets", "FTSE 100", "Nikkei 225",
]

RATE_INSTRUMENTS = [
    ("SOFR", "Secured Overnight Financing Rate"),
    ("FED_FUNDS", "Federal Funds Effective Rate"),
    ("UST_2Y", "US Treasury 2-Year Yield"),
    ("UST_5Y", "US Treasury 5-Year Yield"),
    ("UST_10Y", "US Treasury 10-Year Yield"),
    ("UST_30Y", "US Treasury 30-Year Yield"),
]

SECTORS = [
    "Technology", "Healthcare", "Financials", "Energy",
    "Consumer Discretionary", "Industrials", "Utilities", "Real Estate",
]

CURRENCIES = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD", "USD/CNY", "USD/MXN"]

ECONOMIC_SERIES = [
    ("GDP_GROWTH_QOQ", "GDP Growth Rate (QoQ)", "Quarterly"),
    ("CPI_YOY", "Consumer Price Index (YoY)", "Monthly"),
    ("UNEMPLOYMENT_RATE", "Unemployment Rate", "Monthly"),
    ("HOUSING_STARTS", "Housing Starts (thousands)", "Monthly"),
    ("RETAIL_SALES_MOM", "Retail Sales (MoM)", "Monthly"),
    ("PMI_MANUFACTURING", "PMI Manufacturing Index", "Monthly"),
]


def create_infrastructure(cur):
    logger.info("Creating warehouse and database...")
    cur.execute(f"CREATE WAREHOUSE IF NOT EXISTS {WAREHOUSE} WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE")
    cur.execute(f"USE WAREHOUSE {WAREHOUSE}")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    cur.execute(f"USE DATABASE {DATABASE}")
    for schema in SCHEMAS:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


def create_tables(cur):
    logger.info("Creating tables...")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.SECURITIES.SECURITY_PRICES (
        price_date       DATE NOT NULL,
        cusip            VARCHAR(9) NOT NULL,
        isin             VARCHAR(12),
        ticker           VARCHAR(10),
        security_name    VARCHAR(100),
        close_price      DECIMAL(18,4),
        open_price       DECIMAL(18,4),
        high_price       DECIMAL(18,4),
        low_price        DECIMAL(18,4),
        volume           BIGINT,
        market_cap_mm    DECIMAL(18,2),
        currency         VARCHAR(3) DEFAULT 'USD',
        exchange         VARCHAR(20),
        as_of_timestamp  TIMESTAMP_TZ
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.SECURITIES.SECURITY_PRICES IS 'Daily closing prices by CUSIP/ISIN from NEXUS market data feed. Join to BigQuery silver_holdings on CUSIP for portfolio valuation.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.SECURITIES.SECURITY_FUNDAMENTALS (
        as_of_date       DATE NOT NULL,
        cusip            VARCHAR(9) NOT NULL,
        pe_ratio         DECIMAL(10,2),
        eps              DECIMAL(10,4),
        market_cap_mm    DECIMAL(18,2),
        dividend_yield   DECIMAL(8,4),
        beta             DECIMAL(8,4),
        sector           VARCHAR(50),
        industry         VARCHAR(100),
        sp_rating        VARCHAR(5)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.SECURITIES.SECURITY_FUNDAMENTALS IS 'Fundamental metrics per security: P/E, EPS, market cap, dividend yield, beta.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.SECURITIES.CORPORATE_ACTIONS (
        action_date      DATE NOT NULL,
        cusip            VARCHAR(9) NOT NULL,
        action_type      VARCHAR(20),
        description      VARCHAR(200),
        ratio            DECIMAL(10,4),
        amount           DECIMAL(18,4),
        currency         VARCHAR(3) DEFAULT 'USD'
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.SECURITIES.CORPORATE_ACTIONS IS 'Corporate actions: stock splits, dividend declarations, mergers and acquisitions.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.INDICES.BENCHMARK_RETURNS (
        return_date      DATE NOT NULL,
        benchmark_name   VARCHAR(50) NOT NULL,
        daily_return     DECIMAL(10,6),
        mtd_return       DECIMAL(10,6),
        qtd_return       DECIMAL(10,6),
        ytd_return       DECIMAL(10,6),
        trailing_1y      DECIMAL(10,6)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.INDICES.BENCHMARK_RETURNS IS 'Daily and period returns for major benchmark indices. Join to BigQuery gold_portfolio_performance on benchmark name.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.INDICES.INDEX_CONSTITUENTS (
        as_of_date       DATE NOT NULL,
        benchmark_name   VARCHAR(50) NOT NULL,
        cusip            VARCHAR(9) NOT NULL,
        weight_pct       DECIMAL(8,4),
        sector           VARCHAR(50)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.INDICES.INDEX_CONSTITUENTS IS 'Constituent securities and weights for each benchmark index.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.ECONOMICS.INTEREST_RATE_CURVES (
        rate_date        DATE NOT NULL,
        instrument       VARCHAR(20) NOT NULL,
        instrument_name  VARCHAR(100),
        rate_pct         DECIMAL(8,4),
        change_bps       DECIMAL(8,2),
        as_of_timestamp  TIMESTAMP_TZ
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.ECONOMICS.INTEREST_RATE_CURVES IS 'SOFR, Fed Funds Effective, and Treasury yields (2Y/5Y/10Y/30Y). Join to BigQuery gold_net_interest_margin on date for NIM sensitivity analysis.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.ECONOMICS.ECONOMIC_INDICATORS (
        report_date      DATE NOT NULL,
        series_id        VARCHAR(30) NOT NULL,
        series_name      VARCHAR(100),
        value            DECIMAL(12,4),
        period_type      VARCHAR(10),
        revision         VARCHAR(20) DEFAULT 'Final'
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.ECONOMICS.ECONOMIC_INDICATORS IS 'Key economic indicators: GDP, CPI, unemployment, housing starts, retail sales, PMI.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.ECONOMICS.FX_SPOT_RATES (
        rate_date        DATE NOT NULL,
        currency_pair    VARCHAR(10) NOT NULL,
        mid_rate         DECIMAL(12,6),
        bid              DECIMAL(12,6),
        ask              DECIMAL(12,6),
        daily_change_pct DECIMAL(8,4)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.ECONOMICS.FX_SPOT_RATES IS 'Spot FX rates for major currency pairs. Complements BigQuery bronze_fx_rates with intraday snapshots.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.RISK_ANALYTICS.CREDIT_SPREADS (
        spread_date      DATE NOT NULL,
        rating           VARCHAR(5) NOT NULL,
        sector           VARCHAR(50) NOT NULL,
        spread_bps       DECIMAL(10,2),
        change_1d_bps    DECIMAL(8,2),
        change_1w_bps    DECIMAL(8,2),
        change_1m_bps    DECIMAL(8,2)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.RISK_ANALYTICS.CREDIT_SPREADS IS 'Corporate bond spreads by credit rating and sector. Join to BigQuery gold_market_risk_var for credit spread exposure analysis.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.RISK_ANALYTICS.VOLATILITY_SURFACES (
        as_of_date       DATE NOT NULL,
        underlying_cusip VARCHAR(9),
        expiry_days      INT,
        strike_pct       DECIMAL(8,2),
        implied_vol      DECIMAL(8,4),
        delta            DECIMAL(8,4)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.RISK_ANALYTICS.VOLATILITY_SURFACES IS 'Implied volatility surfaces for options pricing across maturities and strikes.'")

    # Add column comments for key join columns
    cur.execute(f"COMMENT ON COLUMN {DATABASE}.SECURITIES.SECURITY_PRICES.CUSIP IS 'CUSIP identifier — matches BigQuery ref_cusip_master.cusip and silver_holdings.cusip'")
    cur.execute(f"COMMENT ON COLUMN {DATABASE}.SECURITIES.SECURITY_PRICES.ISIN IS 'ISIN identifier — matches BigQuery ref_isin_mapping.isin'")
    cur.execute(f"COMMENT ON COLUMN {DATABASE}.INDICES.BENCHMARK_RETURNS.BENCHMARK_NAME IS 'Benchmark name — matches BigQuery gold_portfolio_performance.benchmark_name'")
    cur.execute(f"COMMENT ON COLUMN {DATABASE}.ECONOMICS.INTEREST_RATE_CURVES.INSTRUMENT IS 'Rate instrument code: SOFR, FED_FUNDS, UST_2Y, UST_5Y, UST_10Y, UST_30Y'")


def populate_data(cur):
    logger.info("Populating synthetic data...")
    rng = random.Random(42)
    biz_days = us_business_days("2024-01-02", 250)  # ~12 months of business days, overlaps BQ data ranges

    # SECURITY_PRICES: 500 CUSIPs x 120 days = 60,000 rows (batched)
    logger.info("  SECURITY_PRICES...")
    cusips = [(n, generate_cusip(n), generate_isin(n)) for n in CUSIP_SEED_RANGE]
    batch = []
    for day in biz_days:
        for n, cusip, isin in cusips:
            base = 20 + (n % 300)
            close = round(base + rng.gauss(0, base * 0.02), 4)
            open_p = round(close * (1 + rng.gauss(0, 0.005)), 4)
            high_p = round(max(close, open_p) * (1 + abs(rng.gauss(0, 0.003))), 4)
            low_p = round(min(close, open_p) * (1 - abs(rng.gauss(0, 0.003))), 4)
            vol = int(abs(rng.gauss(500000, 300000)))
            mcap = round(close * vol * rng.uniform(50, 200) / 1e6, 2)
            exch = ["NYSE", "NASDAQ", "OTC"][n % 3]
            ticker = f"TK{n:04d}"
            name = f"Security-{n}"
            batch.append(f"('{day}','{cusip}','{isin}','{ticker}','{name}',{close},{open_p},{high_p},{low_p},{vol},{mcap},'USD','{exch}','{day} 16:00:00 -0400')")
            if len(batch) >= 5000:
                cur.execute(f"INSERT INTO {DATABASE}.SECURITIES.SECURITY_PRICES VALUES {','.join(batch)}")
                batch = []
    if batch:
        cur.execute(f"INSERT INTO {DATABASE}.SECURITIES.SECURITY_PRICES VALUES {','.join(batch)}")
    logger.info("    %d CUSIPs x %d days", len(cusips), len(biz_days))

    # SECURITY_FUNDAMENTALS: 500 rows (latest)
    logger.info("  SECURITY_FUNDAMENTALS...")
    batch = []
    for n, cusip, _ in cusips:
        pe = round(rng.uniform(5, 50), 2)
        eps = round(rng.uniform(0.5, 20), 4)
        mcap = round(rng.uniform(100, 50000), 2)
        div_yield = round(rng.uniform(0, 0.06), 4)
        beta = round(rng.gauss(1.0, 0.3), 4)
        sector = SECTORS[n % len(SECTORS)]
        rating = ["AAA", "AA", "A", "BBB", "BB"][n % 5]
        batch.append(f"('{biz_days[-1]}','{cusip}',{pe},{eps},{mcap},{div_yield},{beta},'{sector}','Industry-{n % 20}','{rating}')")
    cur.execute(f"INSERT INTO {DATABASE}.SECURITIES.SECURITY_FUNDAMENTALS VALUES {','.join(batch)}")

    # CORPORATE_ACTIONS: ~200 events
    logger.info("  CORPORATE_ACTIONS...")
    batch = []
    for i in range(200):
        n = rng.choice(range(1, 501))
        cusip = generate_cusip(n)
        day = rng.choice(biz_days)
        atype = rng.choice(["DIVIDEND", "DIVIDEND", "SPLIT", "MERGER"])
        desc = {"DIVIDEND": f"Quarterly dividend ${rng.uniform(0.1, 2.0):.2f}/share", "SPLIT": f"{rng.choice([2,3,4])}:1 stock split", "MERGER": "Merger announcement"}[atype]
        ratio = {"DIVIDEND": 1.0, "SPLIT": float(rng.choice([2, 3, 4])), "MERGER": round(rng.uniform(1.1, 1.5), 4)}[atype]
        amt = round(rng.uniform(0.1, 5.0), 4) if atype == "DIVIDEND" else 0
        batch.append(f"('{day}','{cusip}','{atype}','{desc}',{ratio},{amt},'USD')")
    cur.execute(f"INSERT INTO {DATABASE}.SECURITIES.CORPORATE_ACTIONS VALUES {','.join(batch)}")

    # BENCHMARK_RETURNS: 7 benchmarks x 120 days
    logger.info("  BENCHMARK_RETURNS...")
    batch = []
    for day in biz_days:
        for bm in BENCHMARKS:
            daily = round(rng.gauss(0.0003, 0.012), 6)
            mtd = round(rng.gauss(0.005, 0.03), 6)
            qtd = round(rng.gauss(0.02, 0.05), 6)
            ytd = round(rng.gauss(0.08, 0.10), 6)
            t1y = round(rng.gauss(0.10, 0.12), 6)
            batch.append(f"('{day}','{bm}',{daily},{mtd},{qtd},{ytd},{t1y})")
    cur.execute(f"INSERT INTO {DATABASE}.INDICES.BENCHMARK_RETURNS VALUES {','.join(batch)}")

    # INDEX_CONSTITUENTS: latest date, 7 benchmarks x ~50 securities each
    logger.info("  INDEX_CONSTITUENTS...")
    batch = []
    latest = biz_days[-1]
    for bm in BENCHMARKS:
        members = rng.sample(range(1, 501), 50)
        total_w = 0
        for i, n in enumerate(members):
            w = round(rng.uniform(0.5, 5.0), 4)
            total_w += w
            batch.append(f"('{latest}','{bm}','{generate_cusip(n)}',{w},'{SECTORS[n % len(SECTORS)]}')")
    cur.execute(f"INSERT INTO {DATABASE}.INDICES.INDEX_CONSTITUENTS VALUES {','.join(batch)}")

    # INTEREST_RATE_CURVES: 6 instruments x 120 days
    logger.info("  INTEREST_RATE_CURVES...")
    batch = []
    base_rates = {"SOFR": 4.55, "FED_FUNDS": 4.58, "UST_2Y": 3.95, "UST_5Y": 3.80, "UST_10Y": 4.25, "UST_30Y": 4.50}
    for day in biz_days:
        for code, name in RATE_INSTRUMENTS:
            base = base_rates[code]
            rate = round(base + rng.gauss(0, 0.05), 4)
            change = round(rng.gauss(0, 3), 2)
            batch.append(f"('{day}','{code}','{name}',{rate},{change},'{day} 16:00:00 -0400')")
    cur.execute(f"INSERT INTO {DATABASE}.ECONOMICS.INTEREST_RATE_CURVES VALUES {','.join(batch)}")

    # ECONOMIC_INDICATORS: 6 series x ~6 months
    logger.info("  ECONOMIC_INDICATORS...")
    batch = []
    monthly_dates = [d for d in biz_days if d.endswith(("01", "02", "03")) and d[8:10] <= "03"]
    if len(monthly_dates) < 6:
        monthly_dates = biz_days[::20][:6]
    for series_id, series_name, period in ECONOMIC_SERIES:
        base_vals = {"GDP_GROWTH_QOQ": 2.5, "CPI_YOY": 3.2, "UNEMPLOYMENT_RATE": 4.1, "HOUSING_STARTS": 1400, "RETAIL_SALES_MOM": 0.3, "PMI_MANUFACTURING": 52.0}
        for date in monthly_dates:
            val = round(base_vals[series_id] + rng.gauss(0, base_vals[series_id] * 0.05), 4)
            batch.append(f"('{date}','{series_id}','{series_name}',{val},'{period}','Final')")
    cur.execute(f"INSERT INTO {DATABASE}.ECONOMICS.ECONOMIC_INDICATORS VALUES {','.join(batch)}")

    # FX_SPOT_RATES: 6 pairs x 120 days
    logger.info("  FX_SPOT_RATES...")
    batch = []
    base_fx = {"EUR/USD": 1.08, "GBP/USD": 1.27, "USD/JPY": 155.0, "USD/CHF": 0.88, "AUD/USD": 0.65, "USD/CAD": 1.37, "USD/CNY": 7.24, "USD/MXN": 17.15}
    for day in biz_days:
        for pair in CURRENCIES:
            mid = round(base_fx[pair] * (1 + rng.gauss(0, 0.003)), 6)
            spread = mid * 0.0002
            batch.append(f"('{day}','{pair}',{mid},{round(mid - spread, 6)},{round(mid + spread, 6)},{round(rng.gauss(0, 0.3), 4)})")
    cur.execute(f"INSERT INTO {DATABASE}.ECONOMICS.FX_SPOT_RATES VALUES {','.join(batch)}")

    # CREDIT_SPREADS: 5 ratings x 8 sectors x 120 days
    logger.info("  CREDIT_SPREADS...")
    batch = []
    ratings = ["AAA", "AA", "A", "BBB", "BB"]
    base_spreads = {"AAA": 30, "AA": 50, "A": 80, "BBB": 150, "BB": 300}
    for day in biz_days:
        for rating in ratings:
            for sector in SECTORS:
                base = base_spreads[rating]
                spread = round(base + rng.gauss(0, base * 0.1), 2)
                d1 = round(rng.gauss(0, 2), 2)
                d1w = round(rng.gauss(0, 5), 2)
                d1m = round(rng.gauss(0, 10), 2)
                batch.append(f"('{day}','{rating}','{sector}',{spread},{d1},{d1w},{d1m})")
                if len(batch) >= 5000:
                    cur.execute(f"INSERT INTO {DATABASE}.RISK_ANALYTICS.CREDIT_SPREADS VALUES {','.join(batch)}")
                    batch = []
    if batch:
        cur.execute(f"INSERT INTO {DATABASE}.RISK_ANALYTICS.CREDIT_SPREADS VALUES {','.join(batch)}")

    # VOLATILITY_SURFACES: 50 underlyings x 5 expiries x 5 strikes
    logger.info("  VOLATILITY_SURFACES...")
    batch = []
    latest = biz_days[-1]
    expiries = [30, 60, 90, 180, 365]
    strikes = [0.90, 0.95, 1.00, 1.05, 1.10]
    for n in rng.sample(range(1, 501), 50):
        cusip = generate_cusip(n)
        for exp in expiries:
            for strike in strikes:
                iv = round(0.20 + rng.gauss(0, 0.05) + (abs(strike - 1.0) * 0.5), 4)
                delta = round(rng.uniform(-1, 1) * (1 - abs(strike - 1.0)), 4)
                batch.append(f"('{latest}','{cusip}',{exp},{strike},{iv},{delta})")
    cur.execute(f"INSERT INTO {DATABASE}.RISK_ANALYTICS.VOLATILITY_SURFACES VALUES {','.join(batch)}")


def create_horizon_tags(cur):
    logger.info("Creating Horizon governance tags...")
    cur.execute(f"USE DATABASE {DATABASE}")

    for tag_name, tag_def in HORIZON_TAGS.items():
        values = ", ".join(f"'{v}'" for v in tag_def["allowed_values"])
        cur.execute(f"CREATE TAG IF NOT EXISTS {DATABASE}.SECURITIES.{tag_name} ALLOWED_VALUES {values}")
        logger.info("  Tag: %s", tag_name)

    logger.info("Applying tags to tables...")
    for schema in SCHEMAS:
        for table_name, _ in TABLES[schema]:
            tags = TAG_ASSIGNMENTS.get(table_name, {})
            for tag_name, tag_value in tags.items():
                cur.execute(f"ALTER TABLE {DATABASE}.{schema}.{table_name} SET TAG {DATABASE}.SECURITIES.{tag_name} = '{tag_value}'")
            logger.info("  %s.%s: %d tags", schema, table_name, len(tags))


def main():
    logger.info("=== Setting up NEXUS Market Data in Snowflake ===")
    conn = get_snowflake_connection()
    cur = conn.cursor()
    try:
        create_infrastructure(cur)
        create_tables(cur)
        populate_data(cur)
        create_horizon_tags(cur)
        logger.info("=== NEXUS setup complete ===")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
