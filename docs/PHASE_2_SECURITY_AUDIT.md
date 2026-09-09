# Phase 2 — Security Audit Findings

Date: 2026-09-09
Branch: `phase-2-security-deployment-v2`

This document records the implementation audit before the production deployment gate. It is intentionally conservative: a security control is not marked complete only because the code appears to contain a related mechanism.

## Current verified controls

### HTTP security headers
The backend emits:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` disabling camera, microphone and geolocation
- CSP with `base-uri`, `object-src`, `frame-ancestors`, restricted image/font/connect/form sources
- HSTS when the request is observed as HTTPS through `X-Forwarded-Proto`

These controls still require validation behind the real HTTPS reverse proxy/CDN. They are not a substitute for the staging deployment check.

### Automated HTTP security regression coverage
`backend/tests/security_http_regression_test.py` exercises the live HTTP handler against a temporary SQLite database. It verifies the baseline security headers, blocks direct access to protected backend files, requires authentication on representative Admin endpoints, rejects malformed JSON, and rejects unsigned Stripe webhook requests. The test is part of CI.

### Admin authentication/session baseline
The current backend uses cryptographically random bearer session tokens, stores the token value in the `sessions` table, applies a 12-hour TTL, rate-limits login attempts, and invalidates the token on logout. Admin endpoints check the authenticated session before privileged operations.

The browser currently keeps the bearer token in `sessionStorage`. This reduces persistence compared with `localStorage`, but it still means an XSS vulnerability can expose the admin credential. Moving to an HttpOnly/Secure/SameSite cookie session with an explicit CSRF mechanism remains an open Phase 2 decision.

### Request/body limits
The backend has explicit body limits for JSON requests, image uploads and gallery media uploads. Uploaded files are checked against an allow-list and their magic bytes are validated before being stored.

### Path traversal
Upload and media access use constrained filename validation and resolved-path containment checks before filesystem operations.

### Stripe webhook
The Stripe webhook verifier checks the timestamp tolerance and compares the HMAC-SHA256 signature with `hmac.compare_digest`. Production verification still requires a real Stripe test-mode webhook against HTTPS staging.

### Checkout pricing/inventory
The HTTP checkout integration test verifies that the server reconstructs the order total from the database rather than trusting the client-provided price, and that an excessive quantity is rejected when stock is insufficient. The same test verifies that a non-paid checkout releases its reservation.

### Order-status privacy
Public order status is now protected by a dedicated high-entropy `status_token`. The token is generated with `secrets.token_urlsafe(32)`, persisted with the order, returned to the browser only at checkout creation, and required together with the order ID for `/api/orders/status`. Existing databases are migrated by adding the column and backfilling tokens for legacy orders. The Stripe success URL continues to contain only the order ID; the status token is kept out of URLs.

The checkout integration test verifies all three access cases: order ID alone is rejected, an incorrect token is rejected, and the correct token returns the order state.

### CI status
The last previously verified Phase 2 head `dc9806db878a501087d3b0590432cbd6b0d9ffd5` completed CI successfully as run **#180** (`34402001538`). The current branch has additional order-status hardening commits; CI for the new head must be rechecked before merging.

This is a code/CI gate only; it does not prove that production HTTPS, Stripe, SMTP, backups or the real customer flow work on an external deployment.

## Open implementation gates

1. **Admin authentication model** — decide between retaining bearer tokens with stronger XSS defenses or moving to an HttpOnly/Secure/SameSite cookie session plus an explicit CSRF mechanism.
2. **Session lifecycle** — verify expiry cleanup, logout invalidation, authorization boundaries and production secret requirements under browser testing. The current 12-hour session is functional but is not yet the final production session model.
3. **CSP hardening** — remove `unsafe-inline` from `script-src`. The frontend currently contains dynamic inline style mutations, so this must be refactored without breaking the visual effects. The current CSP is therefore a baseline, not the final strict policy.
4. **API validation** — systematically test malformed JSON, missing/incorrect content types, oversized payloads, invalid IDs, invalid quantities, path traversal strings, and unexpected fields.
5. **Error surfaces** — ensure production responses do not expose exception details or internal paths; server logs must not become a substitute for safe API responses. Webhook and email exception logging still needs a production review.
6. **CORS/origin policy** — verify that the deployment does not accidentally become a cross-origin authenticated API.
7. **HTTPS/staging** — deploy the exact branch to a disposable HTTPS environment with persistent SQLite storage/backup strategy and a rollback point.
8. **Stripe test flow** — verify checkout creation, signed webhook delivery, duplicate webhook idempotency, expiry/cancellation stock release, and paid-order stock decrement.
9. **E2E** — verify Home → Shop → Product → Bag → Checkout/confirmation on desktop and mobile. CI currently verifies the public pages and Shop → Cart only; it intentionally stops before a real payment flow.
10. **Performance/accessibility/SEO** — complete Lighthouse-style checks, reduced-motion behavior, keyboard navigation, metadata, canonical URLs and image loading.

## Immediate execution order

The remaining work should be executed in this order because each step reduces risk for the next one:

1. **Harden the Admin session model** and test login/logout/expiry/authorization boundaries.
2. **Complete CSP hardening** after the authentication surface is stable, including the dynamic-style refactor required by the current frontend.
3. **Expand API/error/CORS regression coverage** so malformed and hostile requests are covered before staging.
4. **Deploy a disposable HTTPS staging environment**, configure secrets and persistent storage, and establish backup/restore plus rollback.
5. **Run the real Stripe test-mode flow**, including signed webhook, replay/idempotency, cancellation/expiry and stock transitions.
6. **Run the full customer E2E flow** on desktop and mobile, then finish accessibility, performance and SEO checks.

## Production rule

Do **not** label the project `READY FOR PRODUCTION` from source inspection alone. The final gate requires:

- CI green
- HTTPS staging deployment
- real browser flow
- Stripe test-mode webhook verification
- authentication/session verification
- backup/restore check
- rollback plan

Only after those checks pass should the production deployment be considered ready.
