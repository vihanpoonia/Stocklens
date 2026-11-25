CREATE TABLE data_quality_logs (
	id INTEGER NOT NULL, 
	dataset VARCHAR(60), 
	status VARCHAR(30), 
	mode VARCHAR(20), 
	last_updated DATE, 
	note VARCHAR(200), 
	PRIMARY KEY (id)
);

CREATE TABLE saved_screens (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	query_json TEXT NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE sectors (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE companies (
	id INTEGER NOT NULL, 
	company_name VARCHAR(255) NOT NULL, 
	symbol VARCHAR(50) NOT NULL, 
	exchange VARCHAR(10), 
	isin VARCHAR(20), 
	sector_id INTEGER, 
	shares_outstanding_cr FLOAT, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (isin), 
	FOREIGN KEY(sector_id) REFERENCES sectors (id)
);

CREATE TABLE daily_prices (
	company_id INTEGER NOT NULL, 
	trading_date DATE NOT NULL, 
	close FLOAT, 
	volume BIGINT, 
	PRIMARY KEY (company_id, trading_date), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE TABLE financial_results (
	id INTEGER NOT NULL, 
	company_id INTEGER NOT NULL, 
	fiscal_year INTEGER NOT NULL, 
	period_end DATE NOT NULL, 
	filing_date DATE NOT NULL, 
	basis VARCHAR(20), 
	revision INTEGER, 
	revenue FLOAT, 
	expenses FLOAT, 
	ebitda FLOAT, 
	depreciation FLOAT, 
	interest FLOAT, 
	pbt FLOAT, 
	tax FLOAT, 
	pat FLOAT, 
	eps FLOAT, 
	total_equity FLOAT, 
	total_debt FLOAT, 
	cash FLOAT, 
	current_assets FLOAT, 
	current_liabilities FLOAT, 
	receivables FLOAT, 
	cfo FLOAT, 
	source VARCHAR(50), 
	PRIMARY KEY (id), 
	UNIQUE (company_id, fiscal_year, basis, revision), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE TABLE management_guidance (
	id INTEGER NOT NULL, 
	company_id INTEGER NOT NULL, 
	metric VARCHAR(100), 
	guidance_low FLOAT, 
	guidance_high FLOAT, 
	unit VARCHAR(30), 
	period VARCHAR(30), 
	guidance_date DATE, 
	source_note VARCHAR(200), 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE TABLE ratio_snapshots (
	company_id INTEGER NOT NULL, 
	as_of_date DATE, 
	price FLOAT, 
	market_cap FLOAT, 
	pe FLOAT, 
	pb FLOAT, 
	peg FLOAT, 
	ev_ebitda FLOAT, 
	roce FLOAT, 
	roe FLOAT, 
	debt_equity FLOAT, 
	interest_coverage FLOAT, 
	current_ratio FLOAT, 
	ebitda_margin FLOAT, 
	pat_margin FLOAT, 
	cfo_pat FLOAT, 
	sales_growth_1y FLOAT, 
	sales_growth_3y FLOAT, 
	profit_growth_1y FLOAT, 
	profit_growth_3y FLOAT, 
	promoter_holding FLOAT, 
	pledged_pct FLOAT, 
	fii_holding FLOAT, 
	dii_holding FLOAT, 
	ret_1m FLOAT, 
	ret_3m FLOAT, 
	ret_6m FLOAT, 
	rsi_14 FLOAT, 
	pct_from_52w_high FLOAT, 
	volume_ratio FLOAT, 
	PRIMARY KEY (company_id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE TABLE shareholding_patterns (
	id INTEGER NOT NULL, 
	company_id INTEGER NOT NULL, 
	period_end DATE NOT NULL, 
	promoter_pct FLOAT, 
	fii_pct FLOAT, 
	dii_pct FLOAT, 
	public_pct FLOAT, 
	pledged_pct FLOAT, 
	PRIMARY KEY (id), 
	UNIQUE (company_id, period_end), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE TABLE guidance_actuals (
	id INTEGER NOT NULL, 
	guidance_id INTEGER NOT NULL, 
	actual_value FLOAT, 
	reported_date DATE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(guidance_id) REFERENCES management_guidance (id)
);
