# Management API authentication

All management `/api/` requests now require a valid `Authorization: Bearer <JWT>` header, except the login POST and CORS preflight requests. Preflight responses are generated before route handlers, so an unauthenticated OPTIONS request cannot perform a download or mutation. Missing, expired, malformed, unsupported-role, or incomplete tokens return HTTP 401. Authenticated requests outside their permissions return HTTP 403. If ownership cannot be verified because storage is unavailable, requests fail closed.

## Roles and resource scope

- Administrators can use management APIs, including global user management, tenant configuration, conversations, and embedding credentials/configuration.
- Team owners can use their own team, uploaded files, tenant knowledgebases and documents. Detail, download, batch and mutation requests are checked as well as lists. All IDs in a batch must belong to the permitted scope.
- Team owners cannot create other management owners or modify existing owner memberships. Global user selectors and global configuration controls are administrator-only in the management UI.
- Owner knowledgebase creation derives ownership from the authenticated token and uses an embedding model configured for that tenant; it never selects the global fallback. Configure the tenant's embedding model before creating or parsing a knowledgebase. Legacy knowledgebases that relied on the global model must configure the matching model and credentials for their actual tenant. Knowledgebases previously indexed under the creator ID may need to be parsed again if the creator and tenant IDs differ; this change does not migrate existing search indexes.
- File uploads and chunked uploads retain authenticated ownership and isolated storage. Clients must send the Bearer header for uploads, downloads, conversation requests and document additions, including requests made outside the shared HTTP client.

The JWT signing key and administrator password must be explicitly configured. See [credential setup and migration](jwt-secret.md). Deploy the updated backend and frontend together, then sign in again after replacing the old signing key. Restart any in-progress chunked uploads after upgrading: legacy upload state is intentionally not accepted by the new per-user upload namespace. A source merge alone does not update running containers or published images.

JWTs remain stateless and expire after one hour. Resource ownership is checked against current database records, but a role change or user removal does not revoke an already-issued token before expiry. Rotating the signing key invalidates all management tokens; coordinate such a rotation across every backend replica.

## Regression tests

From the repository root, install the lightweight test dependencies and run:

```bash
python -m pip install Flask==3.0.3 flask-cors==5.0.0 PyJWT==2.10.1 python-dotenv==1.0.1
python -m unittest discover -s management/server/tests -v
```

Backend tests use real application/authentication/query code with mocked database and infrastructure dependencies. They do not replace integration testing against the deployment's MySQL, Redis, object store and model services. Frontend tests and production build run from `management/web` with `pnpm exec vitest run` and `pnpm build`.
