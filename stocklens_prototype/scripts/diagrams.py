import subprocess, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
OUT = "docs/diagrams"; os.makedirs(OUT, exist_ok=True)
G = 'graph [fontname="Helvetica" dpi=170 pad=0.25 bgcolor=white]; node [fontname="Helvetica" fontsize=11 style="filled,rounded" shape=box fillcolor="#e8f3f2" color="#0b7a75" penwidth=1.2]; edge [fontname="Helvetica" fontsize=9 color="#44606b"];'
def dot(name, body):
    src = f"digraph {{ {G} {body} }}"
    subprocess.run(["dot", "-Tpng", "-o", f"{OUT}/{name}.png"], input=src.encode(), check=True)

# 1 Architecture
dot("01_architecture", '''rankdir=TB; nodesep=0.35; ranksep=0.55; compound=true;
subgraph cluster_ui{label="Presentation layer"; style="rounded,dashed"; color="#7a8b94"; UI[label="Web UI (MVP: HTML/JS served by FastAPI)\\nTarget: Next.js + TypeScript + Tailwind\\nDashboard | Screener | Company | Sector Radar"];}
subgraph cluster_api{label="Application layer - FastAPI modular monolith"; style="rounded,dashed"; color="#7a8b94";
 API[label="REST API  /api/v1\\nvalidation | routing | error handling" fillcolor="#fff3d6" color="#b7791f"];
 FIN[label="Financial Engine\\nformulas, ratios, TTM"]; SCR[label="Screener Engine\\nJSON query -> parameterised SQL"];
 MKT[label="Market Engine\\nindicators, breadth, movers"]; SEC[label="Sector Engine\\nmomentum score, rotation phase"];
 EQ[label="Quality & Guidance\\nearnings-quality rules, deviation"]; JOB[label="Ratio Refresh Job\\npoint-in-time, as_of"];}
subgraph cluster_data{label="Data layer"; style="rounded,dashed"; color="#7a8b94";
 DB[label="SQLAlchemy ORM\\nSQLite (MVP) / PostgreSQL + TimescaleDB (target)" shape=cylinder fillcolor="#dfe8f7" color="#2f5aa8"];}
subgraph cluster_src{label="Data sources (provider adapter)"; style="rounded,dashed"; color="#7a8b94";
 SRC[label="Synthetic seed generator (MVP)\\nTarget: NSE/BSE licensed feeds, filings" fillcolor="#f3e6f7" color="#7b3f98"];}
UI->API[label="HTTPS / JSON"]; API->FIN; API->SCR; API->MKT; API->SEC; API->EQ;
FIN->DB; SCR->DB; MKT->DB; SEC->DB; EQ->DB; JOB->DB; JOB->FIN[label="uses"]; SRC->JOB[label="ingest"]; SRC->DB[label="load"];''')

# 2 Use case
dot("02_use_case", '''rankdir=LR; nodesep=0.22; ranksep=1.3;
node[shape=box style="filled" fillcolor="#fff3d6" color="#b7791f"]; Investor[label="Retail Investor\\n/ Analyst"]; Admin[label="Data Admin"]; Vendor[label="Data Source\\n(Exchange / Vendor)" fillcolor="#f3e6f7" color="#7b3f98"];
subgraph cluster_s{label="StockLens System"; style="rounded"; color="#0b7a75"; node[shape=ellipse style=filled fillcolor="#e8f3f2" color="#0b7a75"];
UC1[label="View market dashboard"]; UC2[label="Search company"]; UC3[label="View financials & ratios"]; UC4[label="Build & run screen"]; UC5[label="Save / export screen"];
UC6[label="View price chart & indicators"]; UC7[label="View sector radar"]; UC8[label="Check earnings quality"]; UC9[label="Track guidance vs actual"]; UC10[label="Check data freshness"];
UC11[label="Run data ingestion"]; UC12[label="Refresh ratio snapshots"]; UC13[label="Validate data quality"];}
Investor->UC1; Investor->UC2; Investor->UC3; Investor->UC4; Investor->UC5; Investor->UC6; Investor->UC7; Investor->UC8; Investor->UC9; Investor->UC10;
Admin->UC11; Admin->UC12; Admin->UC13; Vendor->UC11 [dir=back style=dashed];
UC4->UC5 [style=dashed label="<<extend>>"]; UC3->UC2 [style=dashed label="<<include>>"];''')

# 3 DFD L0
dot("03_dfd_level0", '''rankdir=LR; nodesep=0.8; ranksep=1.6;
U[label="Investor / Analyst" shape=box style=filled fillcolor="#fff3d6" color="#b7791f"]; D[label="Data Source\\n(Exchange / Vendor / Seed)" shape=box style=filled fillcolor="#f3e6f7" color="#7b3f98"]; A[label="Data Admin" shape=box style=filled fillcolor="#fff3d6" color="#b7791f"];
P[label="0\\nStockLens\\nPlatform" shape=circle width=1.6 style=filled fillcolor="#e8f3f2"];
U->P[label="screen queries,\\ncompany searches"]; P->U[label="results, charts,\\nratios, sector ranks,\\nquality flags"];
D->P[label="prices, financial\\nstatements, holdings"]; A->P[label="ingestion / refresh\\ncommands"]; P->A[label="job & data-quality\\nstatus"];''')

# 4 DFD L1
dot("04_dfd_level1", '''rankdir=LR; nodesep=0.35; ranksep=0.9;
node[shape=box style=filled fillcolor="#fff3d6" color="#b7791f"]; U[label="Investor"]; D[label="Data Source"];
node[shape=circle style=filled fillcolor="#e8f3f2" color="#0b7a75" width=1.15 fixedsize=true fontsize=10];
P1[label="1.0\\nIngest &\\nValidate"]; P2[label="2.0\\nCompute\\nRatios"]; P3[label="3.0\\nScreen\\nCompanies"]; P4[label="4.0\\nMarket &\\nSector\\nAnalytics"]; P5[label="5.0\\nQuality &\\nGuidance"]; P6[label="6.0\\nPresent\\nResults"];
node[shape=cylinder fixedsize=false style=filled fillcolor="#dfe8f7" color="#2f5aa8" width=0.5 fontsize=10];
S1[label="D1 Companies\\n& Sectors"]; S2[label="D2 Financial\\nResults"]; S3[label="D3 Daily Prices"]; S4[label="D4 Ratio\\nSnapshots"]; S5[label="D5 Saved Screens\\n& Guidance"];
D->P1[label="raw data"]; P1->S1; P1->S2; P1->S3;
S2->P2; S3->P2; P2->S4[label="ratios"]; U->P6[label="requests"]; P6->P3[label="query JSON"]; S4->P3; S1->P3; P3->P6[label="rows"];
S3->P4; S2->P4; P4->P6[label="sector scores,\\nmovers"]; S2->P5; P5->S5; S5->P6; P6->U[label="pages / JSON"];''')

# 5 ER
dot("05_er_diagram", '''rankdir=LR; nodesep=0.35; ranksep=0.9; node[shape=record fontsize=10 style=filled fillcolor="#fbfdfd"];
sectors[label="{sectors|PK id\\lname\\l}"];
companies[label="{companies|PK id\\lcompany_name\\lsymbol, exchange\\lisin (unique)\\lFK sector_id\\lshares_outstanding_cr\\lis_active\\l}"];
fin[label="{financial_results|PK id\\lFK company_id\\lfiscal_year, period_end\\lfiling_date, basis, revision\\lrevenue, ebitda, depreciation\\linterest, pbt, tax, pat, eps\\lequity, debt, cash, cfo\\lreceivables, current_assets/liab.\\l}"];
px[label="{daily_prices|PK,FK company_id\\lPK trading_date\\lclose, volume\\l}"];
sh[label="{shareholding_patterns|PK id\\lFK company_id\\lperiod_end\\lpromoter, fii, dii, public\\lpledged_pct\\l}"];
snap[label="{ratio_snapshots|PK,FK company_id\\las_of_date\\lprice, market_cap, pe, pb, peg\\lroce, roe, debt_equity\\lmargins, growth, cfo_pat\\lreturns, rsi_14, volume_ratio\\l}"];
mg[label="{management_guidance|PK id\\lFK company_id\\lmetric, low, high, unit\\lperiod, guidance_date\\l}"]; ga[label="{guidance_actuals|PK id\\lFK guidance_id\\lactual_value\\lreported_date\\l}"];
ss[label="{saved_screens|PK id\\lname\\lquery_json\\lcreated_at\\l}"]; dq[label="{data_quality_logs|PK id\\ldataset, status, mode\\llast_updated, note\\l}"];
sectors->companies[label="1 : N" arrowhead=crow]; companies->fin[label="1 : N" arrowhead=crow]; companies->px[label="1 : N" arrowhead=crow]; companies->sh[label="1 : N" arrowhead=crow];
companies->snap[label="1 : 1" arrowhead=tee]; companies->mg[label="1 : N" arrowhead=crow]; mg->ga[label="1 : N" arrowhead=crow];''')

# 6 Class diagram
dot("06_class_diagram", '''rankdir=TB; nodesep=0.4; ranksep=0.6; node[shape=record fontsize=10 style=filled fillcolor="#fbfdfd"];
FE[label="{FinancialEngine|+ safe_divide(n, d)\\l+ growth(cur, prev)\\l+ cagr(end, start, yrs)\\l+ roe(), roce()\\l+ debt_equity(), pe_ratio()\\l+ ttm(quarters)\\l+ compute_company_ratios()\\l}"];
SE[label="{ScreenerEngine|FIELDS: dict\\lOPS: set\\l|+ validate_query(q)\\l+ run_screen(db, q)\\l}"]; QE[label="{QueryError|ValueError\\l}" fillcolor="#fde8e6"];
RJ[label="{RatioRefreshJob|+ load_prices(as_of)\\l+ point_in_time_results()\\l+ refresh_ratios(as_of)\\l}"];
IND[label="{Indicators|+ sma(s, n)\\l+ ema(s, n)\\l+ rsi(close, n)\\l+ period_return()\\l}"];
SS[label="{SectorScorer|WEIGHTS\\l|+ minmax_0_100()\\l+ classify_phase()\\l+ sector_scores()\\l}"];
EQ[label="{EarningsQuality|+ assess(results)\\l}"]; GD[label="{Guidance|+ deviation(low, high, actual)\\l}"];
API[label="{FastAPI app|+ GET /companies/...\\l+ POST /screener/query\\l+ GET /sectors/rankings\\l+ GET /market/overview\\l}" fillcolor="#fff3d6"];
ORM[label="{ORM models|Sector, Company\\lFinancialResult, DailyPrice\\lShareholding, RatioSnapshot\\lSavedScreen, Guidance*\\l}" fillcolor="#dfe8f7"];
API->SE; API->SS; API->EQ; API->GD; API->IND; SE->QE[label="raises" style=dashed]; SE->ORM; RJ->FE; RJ->IND; RJ->ORM; SS->IND [style=invis]; EQ->FE; API->RJ[style=dashed label="admin"];''')

# 8 Flowchart screener
dot("08_flow_screener", '''rankdir=TB; nodesep=0.4; ranksep=0.38; node[fontsize=10];
S[label="Start" shape=oval fillcolor="#d9f3e3"]; A[label="User sets filters, logic, sort"]; B[label="UI builds Query JSON"]; C[label="POST /api/v1/screener/query"];
D[label="Valid structure?\\n(fields, operators,\\nnumeric values, limit)" shape=diamond fillcolor="#fff3d6" color="#b7791f"]; E[label="Return HTTP 422\\n+ error message" fillcolor="#fde8e6" color="#c8372d"];
F[label="Map fields to whitelisted columns"]; G[label="Build parameterised SQLAlchemy query\\n(AND / OR, NULLs excluded)"]; H[label="Apply sort + limit"]; I[label="Execute on ratio_snapshots JOIN companies"]; J[label="Return rows as JSON"]; K[label="UI renders results table\\n(save / export CSV)"]; Z[label="End" shape=oval fillcolor="#d9f3e3"];
S->A->B->C->D; D->E[label="No"]; D->F[label="Yes"]; F->G->H->I->J->K->Z; E->Z;''')

# 9 Flowchart ingestion/ratio refresh
dot("09_flow_ratio_refresh", '''rankdir=TB; nodesep=0.4; ranksep=0.36; node[fontsize=10];
S[label="Start: refresh_ratios(as_of)" shape=oval fillcolor="#d9f3e3"]; A[label="Load prices up to as_of"]; B[label="For each company"];
C[label="Select financial results\\nWHERE filing_date <= as_of\\n(no look-ahead bias)"]; D[label="Latest shareholding <= as_of"]; E[label="Price, market cap"];
F[label="Compute ratios via Financial Engine\\n(None if input missing / zero / negative base)"]; G[label="Compute RSI, returns, 52W position, volume ratio"];
H[label="Upsert ratio_snapshot row"]; I[label="More companies?" shape=diamond fillcolor="#fff3d6" color="#b7791f"]; J[label="Commit transaction" ]; Z[label="End" shape=oval fillcolor="#d9f3e3"];
S->A->B->C->D->E->F->G->H->I; I->B[label="Yes"]; I->J[label="No"]; J->Z;''')

# 10 Sector flow
dot("10_flow_sector_score", '''rankdir=LR; nodesep=0.3; ranksep=0.5; node[fontsize=10];
A[label="Daily closes\\n+ volumes"]; B[label="Component metrics per sector\\nR1, R3, R6, Breadth(>50DMA),\\nEarnings (median PAT growth),\\nVolume (20d/100d), RS vs universe"]; C[label="Min-max normalise\\nto 0-100"]; D[label="Weighted sum\\n.25 .20 .10 .15 .15 .10 .05"]; E[label="Rank sectors"];
F[label="RS now vs RS 1M ago" shape=diamond fillcolor="#fff3d6" color="#b7791f"]; G[label="Phase: Leading / Improving\\n/ Weakening / Lagging"]; A->B->C->D->E->F->G;''')

# 7 Sequence diagram (matplotlib)
fig, ax = plt.subplots(figsize=(10, 5.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 7.2); ax.axis("off")
actors = ["User / Browser", "FastAPI\\n/screener/query", "Screener\\nEngine", "SQLAlchemy\\nSession", "Database\\n(ratio_snapshots)"]
xs = [1, 3.2, 5.4, 7.2, 9.0]
for x, a in zip(xs, actors):
    ax.add_patch(FancyBboxPatch((x - 0.85, 6.25), 1.7, 0.75, boxstyle="round,pad=0.03", fc="#e8f3f2", ec="#0b7a75")); ax.text(x, 6.62, a.replace("\\n", "\n"), ha="center", va="center", fontsize=8.5)
    ax.plot([x, x], [0.3, 6.25], ls="--", color="#9aa8b3", lw=0.9)
msgs = [(0, 1, 5.6, "1. POST query JSON"), (1, 2, 4.9, "2. run_screen(db, query)"), (2, 2, 4.35, "3. validate_query()"),
        (2, 3, 3.75, "4. build SELECT (whitelisted cols)"), (3, 4, 3.15, "5. execute parameterised SQL"), (4, 3, 2.6, "6. rows"),
        (3, 2, 2.1, "7. ORM rows -> dicts"), (2, 1, 1.6, "8. results list"), (1, 0, 1.05, "9. 200 OK {count, results}")]
for a, b, y, t in msgs:
    if a == b:
        ax.annotate("", xy=(xs[a] + .02, y - .2), xytext=(xs[a] + .02, y + .2), arrowprops=dict(arrowstyle="-|>", color="#14202b", connectionstyle="arc3,rad=-1.6")); ax.text(xs[a] + 0.55, y, t, fontsize=8, va="center"); continue
    ret = b < a
    ax.annotate("", xy=(xs[b], y), xytext=(xs[a], y), arrowprops=dict(arrowstyle="-|>", color="#b7791f" if ret else "#14202b", ls="--" if ret else "-"))
    ax.text((xs[a] + xs[b]) / 2, y + 0.12, t, ha="center", fontsize=8)
ax.text(5, 0.08, "Alt: invalid field / operator / value at step 3 -> QueryError -> HTTP 422 returned to browser", ha="center", fontsize=8, color="#c8372d")
plt.savefig(f"{OUT}/07_sequence_screener.png", dpi=170, bbox_inches="tight", facecolor="white"); plt.close()
print(sorted(os.listdir(OUT)))
