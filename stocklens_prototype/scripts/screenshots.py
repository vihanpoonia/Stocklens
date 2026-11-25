from playwright.sync_api import sync_playwright
import sys
out = "docs/screenshots"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1360, "height": 900})
    pg.goto("http://localhost:8000/"); pg.wait_for_timeout(900)
    pg.screenshot(path=f"{out}/01_dashboard.png", full_page=True)
    pg.click("nav button[data-t=screener]"); pg.wait_for_timeout(1200)
    pg.screenshot(path=f"{out}/02_screener.png", full_page=True)
    pg.click("text=Value + momentum"); pg.wait_for_timeout(800)
    pg.screenshot(path=f"{out}/03_screener_value_momentum.png", full_page=True)
    pg.goto("http://localhost:8000/"); pg.wait_for_timeout(500)
    pg.evaluate("openCo('VERITAST')"); pg.wait_for_timeout(1500)
    pg.screenshot(path=f"{out}/04_company_flagged.png", full_page=True)
    pg.evaluate("openCo('AURORAIN')"); pg.wait_for_timeout(1500)
    pg.screenshot(path=f"{out}/05_company_overview.png", full_page=True)
    pg.click("nav button[data-t=sectors]"); pg.wait_for_timeout(1200)
    pg.screenshot(path=f"{out}/06_sector_radar.png", full_page=True)
    b.close()
