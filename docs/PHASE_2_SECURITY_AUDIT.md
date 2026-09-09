# Phase 2 — Security Audit Findings

Date: 2026-09-09
Branch: `phase-2-security-deployment-v2`

This document records the implementation audit before the production deployment gate. It is intentionally conservative: a security control is not marked complete only because the code appears to contain a related mechanism.

## Current verified controls

### HTTP security headers
The backend already emits:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` disabling camera, microphone and geolocation
- CSP with `base-uri`, `object-src`, `frame-ancestors`, restricted image/font/connect/form sources
- HSTS when the request is observed as HTTPS through `X-Forwarded-Proto`

These controls still require validation behind the real HTTPS reverse proxy/CDN. They are not a substitute for the staging deployment check.

### Automated HTTP security regression coverage
`backend/tests/security_http_regression_test.py` now exercises the live HTTP handler against a temporary SQLite database. It verifies the baseline security headers, blocks direct access to protected backend files, requires authentication on representative Admin endpoints, rejects malformed JSON, and rejects unsigned Stripe webhook requests. The test is part of CI.

### Admin session
The current backend uses random bearer session tokens, stores only a token hash in the session table, applies a 12-hour TTL, and rate-limits login attempts. Admin endpoints check the authenticated session before performing privileged operations.

The browser currently keeps the bearer token in `sessionStorage`. This reduces persistence compared with `localStorage`, but it still means an XSS vulnerability can expose the admin credential. This remains an explicit Phase 2 hardening decision.

### Request/body limits
The backend has explicit body limits for JSON requests, image uploads and gallery media uploads. Uploaded files are checked against an allow-list and their magic bytes are validated before being stored.

### Path traversal
Upload and media access use constrained filename validation and resolved-path containment checks before filesystem operations.

### Stripe webhook
The Stripe webhook verifier checks the timestamp tolerance and compares the HMAC-SHA256 signature with `hmac.compare_digest`. Production verification still requires a real Stripe test-mode webhook against HTTPS staging.

### Checkout pricing/inventory
The HTTP checkout integration test verifies that the server reconstructs the order total from the database rather than trusting the client-provided price, and that an excessive quantity is rejected when stock is insufficient. The same test verifies that a non-paid checkout releases its reservation.

## Open implementation gates

1. **CSP hardening** — remove `unsafe-inline` from `script-src`. The frontend currently contains dynamic inline style mutations, so this must be refactored without breaking the visual effects.
2. **Admin authentication model** — decide between retaining bearer tokens with stronger XSS defenses or moving to an HttpOnly/Secure/SameSite cookie session plus an explicit CSRF mechanism.
3. **Session lifecycle** — add/verify explicit expiry cleanup, logout invalidation, authorization boundaries and production secret requirements.
4. **Order-status privacy** — `/api/orders/status?id=...` is currently unauthenticated and exposes order/payment/shipping state. The order identifier also uses only a short random suffix. Before production, replace this with a high-entropy status token or require an authenticated/unguessable customer status credential, and add an automated regression test proving that possession of a predictable order ID is insufficient to enumerate order state.
5. **API validation** — systematically test malformed JSON, missing/incorrect content types, oversized payloads, invalid IDs, invalid quantities, path traversal strings, and unexpected fields.
6. **Error surfaces** — ensure production responses do not expose exception details or internal paths; server logs must not become a substitute for safe API responses.
7. **CORS/origin policy** — verify that the deployment does not accidentally become a cross-origin authenticated API.
8. **HTTPS/staging** — deploy the exact branch to a disposable HTTPS environment with persistent SQLite storage/backup strategy and a rollback point.
9. **Stripe test flow** — verify checkout creation, signed webhook delivery, duplicate webhook idempotency, expiry/cancellation stock release, and paid-order stock decrement.
10. **E2E** — verify Home → Shop → Product → Bag → Checkout/confirmation on desktop and mobile.
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
