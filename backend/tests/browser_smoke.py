from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
PAGES = [
    "index.html",
    "shop.html",
    "cart.html",
    "gallery.html",
    "live.html",
    "contact.html",
    "us.html",
    "404.html",
]


def main() -> None:
    base_url = os.getenv("KOSMIK_BASE_URL", "http://127.0.0.1:8080")
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page_errors: list[str] = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        for path in PAGES:
            page_errors.clear()
            url = f"{base_url}/{path}"
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                if response is None or response.status != 200:
                    failures.append(f"{path}: HTTP {response.status if response else 'no response'}")
                    continue

                title = page.title()
                if "Kosmik Circles" not in title:
                    failures.append(f"{path}: unexpected title {title!r}")

                if page.locator("header.site-header").count() != 1:
                    failures.append(f"{path}: site header missing")

                main = page.locator("main#main-content")
                if main.count() != 1:
                    failures.append(f"{path}: main content missing")

                if page_errors:
                    failures.append(f"{path}: page errors: {' | '.join(page_errors)}")
            except Exception as exc:  # pragma: no cover - failure path for CI diagnostics
                failures.append(f"{path}: {type(exc).__name__}: {exc}")

        browser.close()

    if failures:
        raise SystemExit("Browser smoke test failures:\n- " + "\n- ".join(failures))

    print(f"Browser smoke PASS: {len(PAGES)} public pages served and initialized without page errors.")


if __name__ == "__main__":
    main()
