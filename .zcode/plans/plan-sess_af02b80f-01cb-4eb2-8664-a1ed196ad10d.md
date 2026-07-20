Add basic telemetry: unique-visitor + page-view counts per book/chapter, shown on a gated /admin page.

DECISIONS (confirmed with user):
- Visitor identity = reuse existing tbl:client-uuid (same per-browser honesty likes already use; clearing localStorage = new visitor, accepted trade-off).
- Admin gate = single ADMIN_TOKEN env secret sent as Bearer header.

BACKEND (Go):
1. services/api/migrations/002_telemetry.sql (new): append-only `page_views` table (client_uuid, book, chapter_num NULLable, viewed_at) + indexes on (book, chapter_num) and viewed_at. Matches 001_init.sql style; auto-runs on fresh Postgres init, applied once manually to existing dev DBs.
2. services/api/internal/storage/pageviews.go (new): RecordPageView(ctx, clientUUID, book, chapterNum *int) + Stats(ctx) returning totals + per-book + per-chapter aggregates.
3. services/api/internal/httpapi/server.go: POST /api/v1/pageviews (anonymous, 204) + GET /api/v1/stats (admin-gated via requireAdmin helper using crypto/subtle.ConstantTimeCompare; empty ADMIN_TOKEN = endpoint disabled/404).
4. services/api/internal/config/config.go: add AdminToken field from ADMIN_TOKEN env (default empty).

FRONTEND (Next.js):
5. apps/web/src/lib/api.ts: trackPageView(book, chapter?) fire-and-forget fetch with keepalive + getStats(adminToken) with Bearer header + types.
6. apps/web/src/components/ViewTracker.tsx (new, use client): fires beacon in useEffect; 5s same-key guard prevents React Strict Mode dev double-count.
7. apps/web/src/app/books/[book]/page.tsx + [chapter]/page.tsx: mount <ViewTracker> only on success path (not 404/placeholder).
8. apps/web/src/app/admin/page.tsx (new, unlisted): token prompt (sessionStorage) → totals + per-book table with expandable per-chapter rows, matching stone/dark theme.

DOCS:
9. .env.example: add ADMIN_TOKEN with comment.
10. README.md: update the now-untrue "nothing about who read what" line to honest framing (aggregate views recorded per-browser-UUID, like likes already are).

OUT OF SCOPE (noted, easy later): homepage views, time-windowed stats, migrations runner.

VERIFY: go build + go test in services/api; npm run build in apps/web; manual chapter-load + /admin check.