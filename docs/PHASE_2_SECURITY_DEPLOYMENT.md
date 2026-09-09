# Phase 2 — Security & Deployment Hardening

Phase 1 code gate is green. Phase 2 starts from the verified `development` head and focuses on the remaining production blockers.

## Execution order

1. Strict CSP hardening: inventory inline behavior, remove `unsafe-inline` from `script-src`, then reduce `style-src` safely.
2. Admin authentication/session and CSRF review: lifecycle, expiry, logout, authorization, browser storage, rate limiting and production secret requirements.
3. HTTP security: HSTS behind HTTPS, frame protection, Referrer-Policy, Permissions-Policy, MIME protection and cache policy.
4. API hardening: malformed JSON, payload limits, IDs, quantities, path traversal, CORS/origin assumptions and safe error surfaces.
5. Staging deployment: HTTPS frontend/backend, environment configuration, persistent database/backup strategy, health checks and rollback.
6. Stripe test-mode verification: Checkout Session, signed webhook, payment finalization, idempotent replay and expiry/cancellation release.
7. Real application flow: HOME → SHOP → PRODUCT → BAG → CHECKOUT → confirmation, including mobile and desktop.
8. Performance/accessibility/SEO final pass, including Matrix lifecycle and reduced-motion behavior.

## Audit baseline — 2026-09-09

- **2.1 CSP:** not yet complete. The backend CSP still allows inline scripts; the frontend also relies on runtime style mutations. The refactor must be coordinated rather than removing the directive blindly.
- **2.2 Admin session/CSRF:** baseline mechanisms exist (random bearer session, server-side TTL, login rate limit and explicit admin authorization), but browser token storage and the final CSRF/XSS model remain open.
- **2.3 HTTP headers:** baseline headers are already implemented and need HTTPS/staging verification.
- **2.4 API hardening:** body/upload limits, MIME/signature validation and path containment are present; malformed-input and safe-error testing remains open.
- **2.5–2.8:** require real staging/external verification and are not considered complete from source inspection.

## Functional progress — 2026-09-09

- Extended the automated browser smoke test to verify the public **SHOP → CART** path.
- The test now confirms product cards and the Add to cart control render, the cart counter changes after adding an item, the cart page initializes, and the order form contains the expected customer fields and submit control.
- The test intentionally stops before creating an order because CI has no sellable production inventory and no payment provider configured. Real checkout/payment verification remains a staging task.

Detailed findings are recorded in `docs/PHASE_2_SECURITY_AUDIT.md`.

## Exit rule

Do not label the project `READY FOR PRODUCTION` from code analysis alone. Automated tests must be green and the real staged application flow must be exercised successfully, including HTTPS and Stripe test-mode webhook verification.
