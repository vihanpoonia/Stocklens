import subprocess
OUT = "docs/diagrams"
G = 'graph [fontname="Helvetica" dpi=170 pad=0.25 bgcolor=white]; node [fontname="Helvetica" fontsize=12 style="filled,rounded" shape=box fillcolor="#e8f3f2" color="#0b7a75" penwidth=1.2]; edge [fontname="Helvetica" fontsize=10 color="#44606b"];'
def dot(name, body):
    subprocess.run(["dot", "-Tpng", "-o", f"{OUT}/{name}.png"], input=f"digraph {{ {G} {body} }}".encode(), check=True)

dot("01_architecture", '''rankdir=TB; nodesep=0.3; ranksep=0.5; newrank=true;
UI[label="PRESENTATION LAYER\\nMVP: HTML/JS served by FastAPI\\nTarget: Next.js + TypeScript + Tailwind\\nDashboard | Screener | Company | Sector Radar" fillcolor="#e8f3f2"];
API[label="APPLICATION LAYER - FastAPI modular monolith\\nREST API /api/v1: routing, validation,\\nerror handling (HTTP 404 / 422)" fillcolor="#fff3d6" color="#b7791f"];
FIN[label="Financial Engine\\nratios, growth, TTM"]; SCR[label="Screener Engine\\nJSON -> parameterised SQL"]; MKT[label="Market Engine\\nindicators, breadth, movers"];
SEC[label="Sector Engine\\nmomentum score, phase"]; EQ[label="Quality & Guidance\\nearnings-quality rules"]; JOB[label="Ratio Refresh Job\\npoint-in-time (as_of)"];
{rank=same; FIN; SCR; MKT} {rank=same; SEC; EQ; JOB}
DB[label="DATA LAYER\\nSQLAlchemy ORM -> SQLite (MVP)\\nPostgreSQL + TimescaleDB (target)\\nRedis, Qdrant: planned" shape=cylinder fillcolor="#dfe8f7" color="#2f5aa8"];
SRC[label="DATA SOURCES (provider-adapter interface)\\nMVP: synthetic seed generator\\nTarget: licensed NSE/BSE feeds, filings" fillcolor="#f3e6f7" color="#7b3f98"];
UI->API[label=" HTTPS / JSON"]; API->FIN; API->SCR; API->MKT; FIN->SEC[style=invis]; SCR->EQ[style=invis]; MKT->JOB[style=invis];
API->SEC[constraint=false style=invis];
SEC->DB; EQ->DB; JOB->DB; FIN->DB[style=dashed]; SCR->DB[style=dashed]; MKT->DB[style=dashed]; DB->SRC[style=invis]; SRC->DB[constraint=false label=" ingest / load"]; ''')

dot("03_dfd_level0", '''rankdir=TB; nodesep=1.4; ranksep=1.3; node[fontsize=13]; edge[fontsize=11];
U[label="Investor / Analyst" shape=box style=filled fillcolor="#fff3d6" color="#b7791f"]; A[label="Data Admin" shape=box style=filled fillcolor="#fff3d6" color="#b7791f"];
D[label="Data Source\\n(Exchange / Vendor /\\nSeed generator)" shape=box style=filled fillcolor="#f3e6f7" color="#7b3f98"];
P[label="0\\nStockLens\\nPlatform" shape=circle width=1.9 style=filled fillcolor="#e8f3f2"];
U->P[label="screen queries,\\ncompany searches"]; P->U[label="results, charts, ratios,\\nsector ranks, quality flags"];
D->P[label="prices, financial\\nstatements, holdings"]; A->P[label="ingestion / refresh\\ncommands"]; P->A[label="job & data-quality status"];
{rank=same; U; A} P->D[style=invis]; ''')

dot("04_dfd_level1", '''rankdir=TB; nodesep=0.55; ranksep=0.5; node[fontsize=11]; edge[fontsize=10];
node[shape=box style=filled fillcolor="#fff3d6" color="#b7791f"]; D[label="Data Source"]; U[label="Investor"];
node[shape=circle style=filled fillcolor="#e8f3f2" color="#0b7a75" width=1.25 fixedsize=true];
P1[label="1.0\\nIngest &\\nValidate"]; P2[label="2.0\\nCompute\\nRatios"]; P3[label="3.0\\nScreen\\nCompanies"]; P4[label="4.0\\nMarket &\\nSector\\nAnalytics"]; P5[label="5.0\\nQuality &\\nGuidance"]; P6[label="6.0\\nPresent\\nResults"];
node[shape=cylinder fixedsize=false style=filled fillcolor="#dfe8f7" color="#2f5aa8" width=0.5];
S1[label="D1 Companies\\n& Sectors"]; S2[label="D2 Financial\\nResults"]; S3[label="D3 Daily\\nPrices"]; S4[label="D4 Ratio\\nSnapshots"]; S5[label="D5 Saved Screens\\n& Guidance"];
D->P1[label="raw data"]; P1->S1; P1->S2; P1->S3; S2->P2; S3->P2; P2->S4[label="ratios"];
S4->P3; S1->P3; S3->P4; S2->P4; S2->P5; P5->S5;
P3->P6[label="rows"]; P4->P6[label="sector scores,\\nmovers"]; S5->P6; U->P6[label="requests"]; P6->U[label="pages / JSON" constraint=false];
{rank=same; S1; S2; S3} {rank=same; P2; P4; P5}''')

dot("05_er_diagram", '''rankdir=TB; nodesep=0.3; ranksep=0.7; node[shape=record fontsize=11 style=filled fillcolor="#fbfdfd"];
sectors[label="{sectors|PK id\\lname\\l}"];
companies[label="{companies|PK id\\lcompany_name, symbol\\lexchange, isin (unique)\\lFK sector_id\\lshares_outstanding_cr\\l}"];
fin[label="{financial_results|PK id, FK company_id\\lfiscal_year, period_end\\lfiling_date, basis, revision\\lrevenue, ebitda, pbt, pat, eps\\lequity, debt, cash, cfo\\lreceivables, current assets/liab.\\l}"];
px[label="{daily_prices|PK,FK company_id\\lPK trading_date\\lclose, volume\\l}"];
sh[label="{shareholding_patterns|PK id, FK company_id\\lperiod_end\\lpromoter, fii, dii, public\\lpledged_pct\\l}"];
snap[label="{ratio_snapshots|PK,FK company_id\\las_of_date, price, market_cap\\lpe, pb, peg, roce, roe\\ldebt_equity, margins, growth\\lcfo_pat, returns, rsi_14\\l}"];
mg[label="{management_guidance|PK id, FK company_id\\lmetric, low, high, unit\\lperiod, guidance_date\\l}"]; ga[label="{guidance_actuals|PK id\\lFK guidance_id\\lactual_value, reported_date\\l}"];
ss[label="{saved_screens|PK id\\lname, query_json\\lcreated_at\\l}"]; dq[label="{data_quality_logs|PK id\\ldataset, status, mode\\llast_updated, note\\l}"];
sectors->companies[label=" 1:N" arrowhead=crow]; companies->fin[label=" 1:N" arrowhead=crow]; companies->px[label=" 1:N" arrowhead=crow]; companies->sh[label=" 1:N" arrowhead=crow];
companies->snap[label=" 1:1" arrowhead=tee]; companies->mg[label=" 1:N" arrowhead=crow]; mg->ga[label=" 1:N" arrowhead=crow];
{rank=same; fin; px; sh} {rank=same; snap; mg}
fin->snap[style=invis]; px->mg[style=invis]; sh->ga[style=invis]; ga->dq[style=invis]; snap->ss[style=invis];''')

dot("10_flow_sector_score", '''rankdir=TB; nodesep=0.4; ranksep=0.35; node[fontsize=11];
A[label="Daily closes + volumes per company"]; B[label="Component metrics per sector:\\nR1, R3, R6 (equal-weight returns) | Breadth (% above 50-DMA)\\nEarnings (median PAT growth) | Volume (20d / 100d) | RS vs universe"];
C[label="Min-max normalise each component to 0-100"]; D[label="Weighted sum: SMS = .25 R1 + .20 R3 + .10 R6 + .15 B + .15 E + .10 V + .05 RS"]; E[label="Rank sectors by score"];
F[label="RS now > 0 ?  RS rising vs 1 month ago ?" shape=diamond fillcolor="#fff3d6" color="#b7791f"]; G[label="Phase: Leading / Improving / Weakening / Lagging"];
A->B->C->D->E->F->G;''')
