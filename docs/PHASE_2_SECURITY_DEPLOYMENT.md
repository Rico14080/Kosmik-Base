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

## Exit rule

Do not label the project `READY FOR PRODUCTION` from code analysis alone. Automated tests must be green and the real staged application flow must be exercised successfully.
