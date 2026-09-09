# Phase 2 — Security & Deployment Hardening

## Entry state

Phase 1 code gate is green on the parent commit. This phase must not be treated as a production approval until staging/external verification is complete.

## Work order

1. **CSP hardening**
   - inventory every inline script/style requirement across public pages
   - remove `unsafe-inline` from `script-src`
   - reduce/remove `unsafe-inline` from `style-src` where practical
   - preserve Stripe checkout compatibility
   - add regression checks so CSP cannot silently loosen again

2. **Admin authentication/session review**
   - review token lifecycle, expiry, logout and storage
   - verify authorization on every admin mutation/read
   - evaluate CSRF exposure and add protection where browser credentials make it relevant
   - verify brute-force/rate-limit behavior and production secret requirements

3. **Production HTTP security**
   - verify HSTS behavior behind a real HTTPS reverse proxy
   - review X-Frame-Options/frame-ancestors compatibility
   - verify Referrer-Policy, Permissions-Policy and MIME sniffing protection
   - review cache-control for public/private/admin responses

4. **API hardening**
   - verify malformed JSON, oversized payloads, invalid IDs, quantities and path traversal
   - verify error responses never expose secrets, database paths or provider credentials
   - review CORS and origin assumptions for the real frontend host

5. **Deployment readiness**
   - stage frontend and backend with HTTPS
   - configure environment variables from `.env.example`
   - configure database persistence/backup strategy
   - configure Stripe test-mode webhook endpoint and secret
   - verify health/readiness endpoints and startup behavior
   - document rollback procedure

6. **Real-flow verification**
   - HOME → SHOP → PRODUCT → BAG → CHECKOUT → confirmation
   - stock 0 / stock 1 / concurrent last-unit checkout
   - Stripe test payment + webhook + idempotent replay
   - cancelled/expired checkout releases reservation
   - Admin login/session/logout and protected operations
   - mobile and desktop smoke checks

## Exit criteria

Phase 2 is complete only when automated tests are green **and** the real staged application flow has been exercised. `READY FOR PRODUCTION` must not be declared from static/code analysis alone.
