#!/usr/bin/env python3
"""Take screenshots of all SAT Benchmark Suite pages using Selenium with proper wait."""
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
BASE_URL = "http://localhost:5173"

PAGES = [
    ("01_dashboard.png",        "/",               "Dashboard"),
    ("02_solvers.png",          "/solvers",         "Solvers"),
    ("03_benchmarks.png",       "/benchmarks",      "Benchmarks"),
    ("04_experiments.png",      "/experiments",      "Experiments"),
    ("04b_experiment_detail.png", "/experiments/7",  "Experiment Detail"),
    ("05_analysis.png",         "/analysis",         "Analysis"),
    ("06_visualization.png",    "/visualization",    "Visualization"),
    ("07_sat_modeler.png",      "/modeler",          "SAT Modeler"),
]

def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--force-device-scale-factor=1")
    driver = webdriver.Chrome(options=opts)
    return driver

def wait_for_page(driver, page_name, timeout=12):
    """Wait for the React SPA to fully render the page content."""
    # Wait for React root to have children (app rendered)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "return document.querySelector('#root') && document.querySelector('#root').children.length > 0"
            )
        )
    except Exception:
        print(f"  ⚠️  React root timeout for {page_name}")

    # Wait for loading spinners to disappear
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("""
                var spinners = document.querySelectorAll('.animate-spin, .animate-pulse, [class*="loading"], [class*="skeleton"]');
                return spinners.length === 0;
            """)
        )
    except Exception:
        pass

    # Additional wait for async data fetching and rendering
    time.sleep(3)

    # Wait for network idle (no pending fetch requests)
    try:
        driver.execute_script("""
            window.__pendingRequests = 0;
            var origFetch = window.fetch;
            window.fetch = function() {
                window.__pendingRequests++;
                return origFetch.apply(this, arguments).finally(function() {
                    window.__pendingRequests--;
                });
            };
        """)
        time.sleep(1)
    except Exception:
        pass

def take_screenshots():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    driver = setup_driver()

    try:
        # First, load the app once to warm up (cache JS bundles)
        print("🔄 Warming up app...")
        driver.get(BASE_URL)
        time.sleep(4)

        for filename, path, name in PAGES:
            url = f"{BASE_URL}{path}"
            filepath = os.path.join(SCREENSHOT_DIR, filename)

            print(f"📸 Capturing {name} ({path})...")
            driver.get(url)
            wait_for_page(driver, name)

            # Scroll to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)

            driver.save_screenshot(filepath)
            size_kb = os.path.getsize(filepath) / 1024
            print(f"   ✅ {filename} ({size_kb:.0f} KB)")

    finally:
        driver.quit()

    print(f"\n🎉 All {len(PAGES)} screenshots captured in {SCREENSHOT_DIR}")

if __name__ == "__main__":
    take_screenshots()
