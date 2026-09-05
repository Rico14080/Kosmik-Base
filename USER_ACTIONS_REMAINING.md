# Remaining owner actions before public launch

These are the actions that require the owner's accounts, identity or provider access. They are deliberately not fabricated in code.

1. Choose and register the final domain.
2. Choose a host/server capable of running Python and SQLite (or migrate the DB to a managed DB later).
3. Create the business/payment account (Stripe or another chosen provider).
4. Set the final HTTPS `PUBLIC_BASE_URL`.
5. Add Stripe secret and webhook signing secret to the server environment.
6. Create/configure a transactional email mailbox/provider and set SMTP variables.
7. Supply real business/legal information and finalize Privacy, Cookie, Terms, Sales, Shipping and Returns pages.
8. Confirm product prices, stock policy, shipping countries/costs and real event/ticket URLs.
9. Perform the final production test pass after deployment.
10. Point DNS to the server and enable HTTPS.

Never send passwords or private account credentials in chat. Use the provider's secure secret/environment configuration.
