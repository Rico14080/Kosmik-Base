# Kosmik Circles — Production Readiness

Updated: 2026-09-09
Branch: `development`

## Current gate

**NOT READY FOR PRODUCTION**

This status is intentional. The repository is not promoted to `main` until the production inventory contract is enforced by the backend and the full validation suite is green.

## Verified in GitHub CI

- Frontend file inventory: PASS
- JavaScript syntax checks: PASS
- Python compilation: PASS
- Existing Phase 1 checkout regression suite: PASS
- Admin external-resource/CSP wiring check: PASS
- Local browser smoke suite served by the backend: PASS
- Repository secret/database guard: PASS
- New production inventory guard: FAIL (expected blocker; stock `0` is currently accepted by `reserve_order_stock`)

## Production blockers

### 1. Inventory semantics

The backend currently treats `stock=0` as effectively unlimited in `reserve_order_stock`: availability checks and reservation updates are conditional on `stock > 0`. This violates the production contract that stock `0` means unavailable.

The production guard test reproduces this exact failure in CI. Do not weaken or remove the test; fix the backend semantics instead.

### 2. Invalid quantities

The checkout endpoint currently normalizes malformed/non-positive quantities to `1`. Production behaviour should reject zero and negative quantities server-side rather than silently changing the customer's requested order.

The production inventory test also covers this contract.

### 3. Real payment verification

Stripe Checkout/webhook behaviour still requires a real Stripe test-mode configuration and HTTPS staging endpoint. The repository alone cannot verify external provider credentials.

### 4. Production Admin session strategy

The current Admin flow uses a bearer token stored client-side. Before production, evaluate migration to secure cookie-based sessions (`Secure`, `HttpOnly`, `SameSite`) with an explicit CSRF strategy.

### 5. CSP tightening

The backend CSP still contains `unsafe-inline` for compatibility. The current Admin HTML has been moved to external scripts/styles, but the public runtime still uses dynamic inline styles. A stricter CSP needs a coordinated frontend refactor rather than a header-only change.

### 6. Matrix lifecycle/performance

The Matrix canvas currently runs a continuous animation frame loop. The visibility guard hides the canvas but does not yet stop the rendering loop. This requires a coordinated change to the Matrix lifecycle code and real browser performance verification.

## Restore point

A pre-production audit restore branch was created before this work:

`backup/pre-production-audit-20260909`

It points to the `development` baseline used for the audit.

## Definition of done

This file should only be changed to `READY FOR PRODUCTION` after:

- inventory guard passes;
- non-positive quantities are rejected;
- concurrent last-unit checkout passes;
- payment/webhook flow is verified in Stripe test mode on staging;
- Admin authentication/session/CSRF review is complete;
- CSP is as strict as the implementation safely permits;
- Matrix lifecycle is verified on desktop and mobile;
- full CI is green;
- deployment/staging smoke tests pass;
- external configuration dependencies are documented.
