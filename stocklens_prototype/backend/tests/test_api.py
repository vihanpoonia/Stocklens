import pytest

def test_TC50_health(client):
    j = client.get("/api/v1/health").json(); assert j["api"] == "healthy" and j["database"] == "connected" and j["companies"] == 40
def test_TC51_company_search_by_name(client):
    assert any("HELIX" in c["symbol"] for c in client.get("/api/v1/companies", params={"q": "helix"}).json())
def test_TC52_company_search_by_sector(client):
    r = client.get("/api/v1/companies", params={"sector": "Auto"}).json(); assert len(r) == 5 and all(c["sector"] == "Auto" for c in r)
def test_TC53_unknown_company_404(client): assert client.get("/api/v1/companies/NOSUCH/overview").status_code == 404
def test_TC54_overview_contains_data_mode_and_ratios(client):
    sym = client.get("/api/v1/companies").json()[0]["symbol"]
    j = client.get(f"/api/v1/companies/{sym}/overview").json()
    assert "Historical" in j["data_mode"] and j["ratios"]["market_cap"] > 0 and j["as_of"]
def test_TC55_financials_six_years_with_filing_dates(client):
    sym = client.get("/api/v1/companies").json()[0]["symbol"]
    j = client.get(f"/api/v1/companies/{sym}/financials").json()
    assert [r["fiscal_year"] for r in j] == list(range(2021, 2027)) and all(r["filing_date"] for r in j)
def test_TC56_prices_with_indicators(client):
    sym = client.get("/api/v1/companies").json()[0]["symbol"]
    j = client.get(f"/api/v1/companies/{sym}/prices", params={"days": 120}).json()
    assert len(j) == 120 and j[-1]["sma50"] is not None and 0 <= j[-1]["rsi14"] <= 100
def test_TC57_prices_days_validation(client):
    assert client.get("/api/v1/companies/X/prices", params={"days": 2}).status_code == 422
def test_TC58_screener_fields_catalogue(client):
    j = client.get("/api/v1/screener/fields").json(); assert len(j) >= 25 and {"key", "label", "category"} <= set(j[0])
def test_TC59_screener_query_ok(client):
    r = client.post("/api/v1/screener/query", json={"filters": [{"field": "roce", "operator": ">", "value": 10}], "limit": 10})
    assert r.status_code == 200 and r.json()["count"] <= 10
def test_TC60_screener_bad_query_422(client):
    assert client.post("/api/v1/screener/query", json={"filters": [{"field": "zzz", "operator": ">", "value": 1}]}).status_code == 422
def test_TC61_save_and_list_screen(client):
    body = {"name": "t1", "query": {"filters": [{"field": "pe", "operator": "<", "value": 20}], "limit": 50}}
    assert client.post("/api/v1/screener/saved", json=body).status_code == 201
    assert any(s["name"] == "t1" for s in client.get("/api/v1/screener/saved").json())
def test_TC62_cannot_save_invalid_screen(client):
    assert client.post("/api/v1/screener/saved", json={"name": "bad", "query": {"filters": [{"field": "x", "operator": ">", "value": 1}]}}).status_code == 422
def test_TC63_sector_rankings_eight_sectors(client):
    j = client.get("/api/v1/sectors/rankings").json(); assert len(j["sectors"]) == 8 and "fund-flow" in j["note"]
def test_TC64_market_overview(client):
    j = client.get("/api/v1/market/overview").json()
    assert j["advancers"] + j["decliners"] <= 40 and len(j["gainers"]) == 5 and len(j["index"]) == 250
    assert j["gainers"][0]["change_pct"] >= j["gainers"][-1]["change_pct"]
def test_TC65_shareholding_sums_to_100(client):
    sym = client.get("/api/v1/companies").json()[0]["symbol"]
    for r in client.get(f"/api/v1/companies/{sym}/shareholding").json():
        assert abs(r["promoter"] + r["fii"] + r["dii"] + r["public"] - 100) < 0.05
def test_TC66_data_quality_includes_unlicensed_live_feed(client):
    assert any(d["dataset"] == "Live market feed" and d["status"] == "Not licensed" for d in client.get("/api/v1/data-quality").json())
def test_TC67_guidance_statuses_valid(client):
    seen = 0
    for c in client.get("/api/v1/companies", params={"limit": 50}).json():
        for g in client.get(f"/api/v1/companies/{c['symbol']}/guidance").json():
            assert g["status"] in ("beat", "met", "missed"); seen += 1
    assert seen >= 10
