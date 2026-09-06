# Security Policy

## Supported version

Security updates are made on the default branch. Older commits and unofficial builds are not supported.

## Report a vulnerability

Please do not disclose vulnerabilities in a public issue. Check the repository's [Security page](https://github.com/NotADevIAmaMeatPopsicle/DTAT-OCR/security) for a private reporting option. If it is unavailable, open a minimal issue asking the maintainer for a private contact channel without including vulnerability details. A private report should include reproduction steps, affected endpoints or files, impact, and any suggested mitigation.

## Deployment expectations

- Set `DTAT_PASSWORD` to a unique value of at least 12 characters. The service refuses to start without a non-default password.
- Put internet-facing deployments behind TLS and rate limiting. HTTP Basic credentials are not confidential over plain HTTP.
- `/health` is public by design. Processing endpoints, stored results, settings, templates, and API documentation require authentication.
- Azure-compatible endpoints require `DTAT_AZURE_COMPAT_KEY`; when it is unset, they use `DTAT_PASSWORD`.
- Cloud OCR is disabled by default. Prefer workload identities or IAM roles over long-lived provider access keys.
- The supplied containers run as an unprivileged user. Also configure CPU, memory, request-size, and execution-time limits in the deployment platform.

## Document data

DTAT OCR handles untrusted documents through third-party parsers. Isolate the service and keep its dependencies current.

By default, the database stores both original upload bytes and extracted content. Treat the database and backups as sensitive, restrict access, encrypt them where appropriate, and define a retention/deletion policy. Set `STORE_ORIGINAL_FILE=false` only when queued processing is not required or another durable source is available.

Temporary processing files are removed after each operation. Abrupt process or host termination can still leave operating-system temporary files, so deployments should periodically clean their isolated temporary directory.

## Secrets and logs

Use environment variables or the deployment platform's secret manager. Never commit `.env` files, cloud keys, database credentials, production documents, or exported databases. Database URLs are redacted in service startup logs; review downstream proxy and platform logs for request data before production use.

## Known hardening boundaries

- The browser UI currently loads CSS and JavaScript from public CDNs.
- The application does not include a rate limiter or malware scanner.
- Provider and parser behavior depends on third-party services and packages.

These boundaries are documented so operators can place the service behind appropriate network and runtime controls.
