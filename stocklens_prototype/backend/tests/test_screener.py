import pandas as pd, pytest
from sqlalchemy import select
from app.core import models as m
from app.screener.engine import run_screen, QueryError, validate_query, FIELDS

@pytest.fixture()
def df(db):
    rows = db.execute(select(m.Company.symbol, m.Sector.name.label("sector"), m.RatioSnapshot)
                      .join(m.RatioSnapshot, m.RatioSnapshot.company_id == m.Company.id).join(m.Sector)).all()
    out = []
    for r in rows:
        d = {k: getattr(r.RatioSnapshot, k) for k in FIELDS}; d["symbol"] = r.symbol; d["sector"] = r.sector; out.append(d)
    return pd.DataFrame(out)

def syms(res): return sorted(r["symbol"] for r in res)
def q(filters, **k): return {"filters": filters, "limit": 500} | k

def test_TC30_greater_than_matches_oracle(db, df):
    assert syms(run_screen(db, q([{"field": "roce", "operator": ">", "value": 20}]))) == sorted(df[df.roce > 20].symbol)
def test_TC31_less_than_matches_oracle(db, df):
    assert syms(run_screen(db, q([{"field": "debt_equity", "operator": "<", "value": 0.3}]))) == sorted(df[df.debt_equity < 0.3].symbol)
def test_TC32_between_inclusive(db, df):
    assert syms(run_screen(db, q([{"field": "rsi_14", "operator": "between", "value": [40, 60]}]))) == sorted(df[(df.rsi_14 >= 40) & (df.rsi_14 <= 60)].symbol)
def test_TC33_and_logic(db, df):
    f = [{"field": "roce", "operator": ">", "value": 15}, {"field": "pe", "operator": "<", "value": 30}]
    assert syms(run_screen(db, q(f))) == sorted(df[(df.roce > 15) & (df.pe < 30)].symbol)
def test_TC34_or_logic(db, df):
    f = [{"field": "roce", "operator": ">", "value": 30}, {"field": "pe", "operator": "<", "value": 18}]
    assert syms(run_screen(db, q(f, logic="OR"))) == sorted(df[(df.roce > 30) | (df.pe < 18)].symbol)
def test_TC35_sort_descending(db):
    r = run_screen(db, q([], sort={"field": "roce", "direction": "DESC"}))
    v = [x["roce"] for x in r]; assert v == sorted(v, reverse=True)
def test_TC36_sort_ascending(db):
    v = [x["pe"] for x in run_screen(db, q([], sort={"field": "pe", "direction": "ASC"}))]; assert v == sorted(v)
def test_TC37_limit_respected(db): assert len(run_screen(db, q([], limit=7))) == 7
def test_TC38_sector_filter(db, df):
    got = run_screen(db, q([{"field": "sector", "operator": "==", "value": "Pharma"}]))
    assert syms(got) == sorted(df[df.sector == "Pharma"].symbol)
def test_TC39_null_values_never_match(db, df):
    got = run_screen(db, q([{"field": "peg", "operator": "<", "value": 1e9}]))
    assert len(got) == df.peg.notna().sum()
def test_TC40_empty_filters_returns_universe(db): assert len(run_screen(db, q([]))) == 40
def test_TC41_unknown_field_rejected(db):
    with pytest.raises(QueryError): run_screen(db, q([{"field": "password", "operator": ">", "value": 1}]))
def test_TC42_unknown_operator_rejected(db):
    with pytest.raises(QueryError): run_screen(db, q([{"field": "roce", "operator": "LIKE", "value": 1}]))
def test_TC43_sql_injection_value_rejected(db):
    with pytest.raises(QueryError): run_screen(db, q([{"field": "roce", "operator": ">", "value": "1; DROP TABLE companies;--"}]))
    assert db.query(m.Company).count() == 40
def test_TC44_sql_injection_field_rejected(db):
    with pytest.raises(QueryError): run_screen(db, q([{"field": "roce; DROP TABLE x", "operator": ">", "value": 1}]))
def test_TC45_bool_value_rejected(db):
    with pytest.raises(QueryError): run_screen(db, q([{"field": "roce", "operator": ">", "value": True}]))
def test_TC46_limit_bounds():
    for bad in (0, 501, -1, "10"):
        with pytest.raises(QueryError): validate_query({"filters": [], "limit": bad})
def test_TC47_between_needs_two_numbers():
    with pytest.raises(QueryError): validate_query({"filters": [{"field": "roce", "operator": "between", "value": [1]}]})
def test_TC48_blueprint_example_query_runs(db):
    r = run_screen(db, {"filters": [{"field": "market_cap", "operator": ">", "value": 500}, {"field": "sales_growth_3y", "operator": ">", "value": 20},
        {"field": "roce", "operator": ">", "value": 20}, {"field": "debt_equity", "operator": "<", "value": 0.5}],
        "logic": "AND", "sort": {"field": "roce", "direction": "DESC"}, "limit": 100})
    assert all(x["roce"] > 20 and x["debt_equity"] < 0.5 and x["sales_growth_3y"] > 20 for x in r)
