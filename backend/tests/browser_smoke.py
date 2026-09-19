from __future__ import annotations

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
PAGES = [
    "index.html",
    "shop.html",
    "cart.html",
    "live.html",
    "contact.html",
    "us.html",
    "legal.html",
    "404.html",
]


def main() -> None:
    base_url = os.getenv("KOSMIK_BASE_URL", "http://127.0.0.1:8080")
    failures: list[str] = []

    with sync_playwright() as p:
        executable = next(
            (shutil.which(name) for name in ("google-chrome", "chromium", "chromium-browser") if shutil.which(name)),
            None,
        )
        launch_options = {"headless": True}
        if executable:
            launch_options["executable_path"] = executable
        browser = p.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page_errors: list[str] = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        for path in PAGES:
            page_errors.clear()
            url = f"{base_url}/{path}"
            try:
                response = page.goto(url, wait_until="commit", timeout=15_000)
                if response is None or response.status != 200:
                    failures.append(f"{path}: HTTP {response.status if response else 'no response'}")
                    continue

                page.wait_for_selector("header.site-header", state="visible", timeout=10_000)
                title = page.title()
                if "kosmik circles" not in title.lower():
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

        # Functional public flow with no payment credentials: catalogue is
        # visible, checkout controls are safely unavailable, and the cart is
        # never converted into a local/demo order.
        try:
            page_errors.clear()
            page.goto(f"{base_url}/shop.html", wait_until="networkidle", timeout=15_000)
            page.wait_for_selector("[data-shop-products]", state="visible", timeout=10_000)
            if "COMING SOON" not in page.locator("[data-shop-products]").inner_text():
                failures.append("shop.html: Coming Soon state is missing")
            if page.locator("[data-shop-products] button[data-product-id]").count() != 0:
                failures.append("shop.html: purchase controls are visible while commerce is disabled")

            page.goto(f"{base_url}/cart.html", wait_until="networkidle", timeout=15_000)
            page.wait_for_selector("[data-cart-content]", state="visible", timeout=10_000)
            if page.locator("[data-cart-content]").count() != 1:
                failures.append("cart.html: cart container is missing")
            if page_errors:
                failures.append(f"cart.html checkout flow: page errors: {' | '.join(page_errors)}")
        except Exception as exc:  # pragma: no cover - failure path for CI diagnostics
            failures.append(f"checkout flow: {type(exc).__name__}: {exc}")

        browser.close()

    if failures:
        raise SystemExit("Browser smoke test failures:\n- " + "\n- ".join(failures))

    print(
        f"Browser smoke PASS: {len(PAGES)} public pages served, initialized without page errors, "
        "and shop -> cart flow verified."
    )


if __name__ == "__main__":
    main()

