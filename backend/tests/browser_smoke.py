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

        # Functional public flow: shop -> cart. This intentionally stops
        # before creating an order because the CI database has no sellable
        # production inventory or payment provider configured.
        try:
            page_errors.clear()
            page.goto(f"{base_url}/shop.html", wait_until="networkidle", timeout=15_000)
            page.wait_for_selector("[data-shop-products] .add-to-cart", state="visible", timeout=10_000)
            first_product = page.locator("[data-shop-products] .product").first
            if first_product.count() != 1:
                failures.append("shop.html: product cards are missing")
            add_button = first_product.locator(".add-to-cart")
            if add_button.count() != 1:
                failures.append("shop.html: add-to-cart control is missing")
            else:
                add_button.click()
                page.wait_for_function(
                    """() => {
                        try {
                            const cart = JSON.parse(localStorage.getItem('kosmik-circles-cart') || '[]');
                            return Array.isArray(cart) && cart.length === 1 && Number(cart[0].quantity) === 1;
                        } catch (_) { return false; }
                    }""",
                    timeout=5_000,
                )
                count = page.locator("[data-cart-count]").first
                if count.count() != 1 or count.inner_text().strip() != "1":
                    failures.append("shop.html: cart counter did not update after adding an item")

            page.goto(f"{base_url}/cart.html", wait_until="networkidle", timeout=15_000)
            page.wait_for_selector("[data-cart-content]", state="visible", timeout=10_000)
            if page.locator("[data-order-form]").count() != 1:
                failures.append("cart.html: order form is missing")
            else:
                for field in ("email", "name", "phone", "address", "city", "postcode", "country"):
                    if page.locator(f"[data-order-form] [name='{field}']").count() != 1:
                        failures.append(f"cart.html: order field {field!r} is missing")
                if page.locator("[data-order-form] button[type='submit']").count() != 1:
                    failures.append("cart.html: order submit button is missing")
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
