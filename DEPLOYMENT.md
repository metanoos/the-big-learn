# Deployment

The Big Learn is two stateless processes plus the versioned `content/` tree.
There is no database, migration step, worker, or object store.

## Runtime contract

| Process | Runtime | Command | Health |
| --- | --- | --- | --- |
| Web | Node.js 20.9+ | `cd apps/web && npm ci && npm run build && npm start` | `GET /` |
| API | Go 1.25+ | `cd services/api && go build -o bin/server ./cmd/server && ./bin/server` | `GET /api/v1/health` |

Ship `content/` with the API release or mount the exact same version read-only.
The API caches parsed files in memory and never writes to that directory.

Only the web process needs to be public. It proxies `/api/*` to the Go process,
which keeps browser requests same-origin and avoids a separate public API host.

## Environment

Web process:

```dotenv
API_BASE_URL=http://api-internal:8180
NEXT_PUBLIC_SITE_URL=https://reader.example.com
NEXT_PUBLIC_SUPPORT_URL=https://processor.example.com/membership
NEXT_PUBLIC_SUPPORT_URL_ONE_TIME=https://processor.example.com/gift
```

Set the web variables for both the build and runtime environments. Next.js
resolves the API rewrite and embeds `NEXT_PUBLIC_*` values during `npm run build`,
so changing them afterward requires a rebuild.

API process:

```dotenv
HTTP_ADDR=:8180
CONTENT_ROOT=/app/content
```

`CORS_ALLOWED_ORIGIN` should normally remain unset because the Next rewrite is
same-origin. Set it to one exact origin only if a browser must call the Go API
directly from a different host.

The support variables are optional; without them the Support page renders
disabled placeholders rather than dead links. `NEXT_PUBLIC_SITE_URL` is not
optional in production because it controls canonical URLs, the sitemap, and
social metadata.

## Release checks

Run these against the exact release revision:

```bash
cd apps/web
npm ci
npm test
npm audit --audit-level=high
npm run build
npm run test:e2e

cd ../../services/api
go test ./...

cd ../..
python3 tools/validate_content.py
python3 tools/validate_sanguo.py --show-outliers 0
```

After starting both processes, verify:

```bash
curl --fail http://api-internal:8180/api/v1/health
curl --fail https://reader.example.com/
curl --fail https://reader.example.com/api/v1/books
curl --fail https://reader.example.com/robots.txt
curl --fail https://reader.example.com/sitemap.xml
```

Also open a chapter, expand a character with the keyboard, save a line, and
confirm its Chinese and translation appear on `/dashboard`.

## Persistence and rollback

Reader progress is browser-local. The Review page provides JSON backup/restore;
there is no server backup job. Content rollback is therefore an application
rollback: redeploy the previous API binary together with its matching `content/`
tree, then roll back the web process if its API contract changed.

Keep the Go API private, terminate TLS at the platform or reverse proxy, and
run at least one instance of each process. Both are horizontally replicable
because neither stores user state.
