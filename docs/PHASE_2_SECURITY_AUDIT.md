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

### CI status
The latest Phase 2 head commit `058d2b00000f234e6a1411667d3559e57492e666` completed CI successfully as run **#179** (`34401765702`). The job passed the frontend file checks, JavaScript/Python validation, Phase 1 regression tests, checkout API integration, HTTP security regression, Admin/CSP resource wiring, browser smoke tests and committed-secret guard.

This is a code/CI gate only; it does not prove that production HTTPS, Stripe, SMTP, backups or the real customer flow work on an external deployment.

## Open implementation gates

1. **CSP hardening** — remove `unsafe-inline` from `script-src`. The frontend currently contains dynamic inline style mutations, so this must be refactored without breaking the visual effects. The current CSP is therefore a baseline, not the final strict policy.
2. **Admin authentication model** — decide between retaining bearer tokens with stronger XSS defenses or moving to an HttpOnly/Secure/SameSite cookie session plus an explicit CSRF mechanism.
3. **Session lifecycle** — verify expiry cleanup, logout invalidation, authorization boundaries and production secret requirements under browser testing. The current 12-hour session is functional but is not yet the final production session model.
4. **Order-status privacy** — `/api/orders/status?id=...` is currently unauthenticated and exposes order/payment/shipping state. The order identifier is generated as `KC-YYYYMMDD-` plus only 3 random bytes (`secrets.token_hex(3)`). Before production, replace this with a dedicated high-entropy status token or an authenticated/unguessable customer status credential, and add an automated regression test proving that possession of a predictable order ID is insufficient to enumerate order state.
5. **API validation** — systematically test malformed JSON, missing/incorrect content types, oversized payloads, invalid IDs, invalid quantities, path traversal strings, and unexpected fields.
6. **Error surfaces** — ensure production responses do not expose exception details or internal paths; server logs must not become a substitute for safe API responses. Webhook and email exception logging still needs a production review.
7. **CORS/origin policy** — verify that the deployment does not accidentally become a cross-origin authenticated API.
8. **HTTPS/staging** — deploy the exact branch to a disposable HTTPS environment with persistent SQLite storage/backup strategy and a rollback point.
9. **Stripe test flow** — verify checkout creation, signed webhook delivery, duplicate webhook idempotency, expiry/cancellation stock release, and paid-order stock decrement.
10. **E2E** — verify Home → Shop → Product → Bag → Checkout/confirmation on desktop and mobile. CI currently verifies the public pages and Shop → Cart only; it intentionally stops before a real payment flow.
11. **Performance/accessibility/SEO** — complete Lighthouse-style checks, reduced-motion behavior, keyboard navigation, metadata, canonical URLs and image loading.

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
