"""
Selenium fixtures.

`live_server` (from pytest-django) starts the real Django app in a background thread on a
random port, with a fresh test database. Django also serves the built React app there,
so the browser exercises the whole stack: React -> Redux -> fetch -> DRF -> database.
"""
import os
from pathlib import Path

import pytest
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"


def pytest_collection_modifyitems(items):
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def _require_frontend_build():
    if not (settings.FRONTEND_DIST / "index.html").exists():
        pytest.skip("Frontend not built. Run `npm run build` in /frontend first.")


@pytest.fixture(scope="session")
def browser(_require_frontend_build):
    opts = webdriver.ChromeOptions()
    if os.environ.get("HEADED") != "1":          # HEADED=1 pytest -m e2e  -> watch it run
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,900")
    if os.environ.get("CHROME_BINARY"):          # e.g. Chromium in the Docker test image
        opts.binary_location = os.environ["CHROME_BINARY"]
    # Normally Selenium Manager downloads the right chromedriver automatically.
    # CHROMEDRIVER_PATH lets CI (or an offline machine) point at a specific driver.
    service = None
    if os.environ.get("CHROMEDRIVER_PATH"):
        extra = os.environ.get("CHROMEDRIVER_ARGS", "").split()
        service = Service(os.environ["CHROMEDRIVER_PATH"], service_args=extra)
    driver = webdriver.Chrome(options=opts, service=service)
    yield driver
    driver.quit()


@pytest.fixture
def base_url(live_server, browser):
    yield live_server.url
    # Leave the app before the server shuts down, so the page can't fire requests
    # into a test database that is being torn down (a classic source of flaky errors).
    browser.get("about:blank")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Save a screenshot when a browser test fails - invaluable when debugging CI."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed and "browser" in item.fixturenames:
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        item.funcargs["browser"].save_screenshot(str(SCREENSHOT_DIR / f"{item.name}.png"))
