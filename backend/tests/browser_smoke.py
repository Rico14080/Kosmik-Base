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

        # Commerce-off contract: the Shop is an informational showcase only.
        try:
            page_errors.clear()
            page.goto(f"{base_url}/shop.html", wait_until="networkidle", timeout=15_000)
            page.wait_for_selector("[data-shop-products]", state="visible", timeout=10_000)
            cards = page.locator(".shop-showcase-card")
            if cards.count() < 1:
                failures.append("shop.html: showcase items are missing")
            if cards.locator("img").count() < 1 or cards.locator("h2").count() != cards.count() or cards.locator(".shop-showcase-copy p").count() != cards.count():
                failures.append("shop.html: image/title/description structure is incomplete")
            if cards.locator("img[alt='']").count():
                failures.append("shop.html: showcase image ALT fallback is missing")
            purchase_selectors = "[data-shop-products] a, [data-shop-products] button, [data-shop-products] input, [data-shop-products] select, header a[href*='cart'], footer a[href*='cart']"
            if page.locator(purchase_selectors).count():
                failures.append("shop.html: interactive purchase path exists while commerce is disabled")
            shop_text = page.locator("body").inner_text().lower()
            for forbidden in ("add to cart", "buy now", "checkout", "stripe", "shipping", "quantity", "sold out", "€"):
                if forbidden in shop_text:
                    failures.append(f"shop.html: purchase text is exposed: {forbidden}")
            for width in (1024, 768, 390):
                page.set_viewport_size({"width": width, "height": 900})
                if page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"):
                    failures.append(f"shop.html: horizontal overflow at {width}px")

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
        "and commerce-off Shop showcase verified."
    )


if __name__ == "__main__":
    main()

