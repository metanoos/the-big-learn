-- The Big Learn — initial schema.
-- Run automatically by the postgres container on first init
-- (mounted at /docker-entrypoint-initdb.d).
--
-- Design notes:
--   - Canonical content (Chinese text + seeded translations) lives in JSON
--     files under content/, NOT in this DB. The DB is only for user-generated
--     content (UGC) + per-user state. This keeps the canonical layer
--     version-controlled, read-only in prod, and trivially re-importable.
--   - The line locator (book, chapter, line) is a composite natural key. We
--     do NOT mirror the full canonical record into a lines table — that would
--     duplicate content/ and create a sync problem. References are (book,
--     chapter_num, line_num).
--   - All UGC is soft-deletable (deleted_at) for moderation without
--     referential destruction.
--   - Votes are unique per (user, target) so one-person-one-vote holds.

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- for gen_random_uuid()

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username        text NOT NULL UNIQUE,                       -- display handle
    email           text NOT NULL UNIQUE,
    password_hash   text NOT NULL,                              -- bcrypt/argon2
    role            text NOT NULL DEFAULT 'user'
                    CHECK (role IN ('user','moderator','admin')),
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_seen_at    timestamptz
);

-- ---------------------------------------------------------------------------
-- line locators
-- A lightweight registry of every line users have engaged with. Populated
-- lazily (on first reference) so we don't have to mirror all ~14k canonical
-- lines into the DB up front. book/chapter/line correspond to the JSON files.
-- ---------------------------------------------------------------------------
CREATE TABLE lines (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    book            text NOT NULL,         -- 'lunyu','mengzi','chengyu-catalog',...
    chapter_num     int  NOT NULL,         -- 1-based chapter order in catalog
    line_num        int  NOT NULL,         -- 1-based line order in chapter
    first_engaged_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (book, chapter_num, line_num)
);
CREATE INDEX lines_book_chapter_idx ON lines (book, chapter_num);

-- ---------------------------------------------------------------------------
-- translations
-- User-submitted translations of a line. One user may have at most one
-- PUBLISHED translation per line (drafts are unlimited). Canonical seeded
-- translations are NOT stored here — they live in content/ JSON.
-- ---------------------------------------------------------------------------
CREATE TABLE translations (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id         bigint NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    user_id         uuid  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body            text NOT NULL,                              -- the English text
    status          text NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','published','hidden_by_user','removed_by_mod')),
    note            text,                                       -- optional author note
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    published_at    timestamptz,
    deleted_at      timestamptz
);
-- At most one published translation per (user, line). Partial uniqueness
-- can't be an inline table constraint; must be a separate partial index.
CREATE UNIQUE INDEX translations_one_published_per_user_line_idx
    ON translations (line_id, user_id) WHERE (status = 'published');
CREATE INDEX translations_line_status_idx
    ON translations (line_id, status, deleted_at);
CREATE INDEX translations_user_idx ON translations (user_id);

-- ---------------------------------------------------------------------------
-- votes
-- One vote per user per target. target_type lets us extend voting beyond
-- translations (e.g. comments) without a second table.
-- ---------------------------------------------------------------------------
CREATE TABLE votes (
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type     text  NOT NULL CHECK (target_type IN ('translation','comment')),
    target_id       uuid  NOT NULL,
    value           smallint NOT NULL CHECK (value IN (-1, 1)),
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, target_type, target_id)
);
CREATE INDEX votes_target_idx ON votes (target_type, target_id);

-- ---------------------------------------------------------------------------
-- comments
-- Threaded comments anchored to a line. May optionally reference a specific
-- translation_id (the "comment on a translation" case). parent_comment_id
-- enables one level of threading; deeper nesting is discouraged in UI.
-- ---------------------------------------------------------------------------
CREATE TABLE comments (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id             bigint NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    user_id             uuid  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id   uuid REFERENCES comments(id) ON DELETE CASCADE,
    referenced_translation_id uuid,   -- not FK'd: translations can be removed
    body                text NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    deleted_at          timestamptz
);
CREATE INDEX comments_line_idx ON comments (line_id, created_at);
CREATE INDEX comments_parent_idx ON comments (parent_comment_id);

-- ---------------------------------------------------------------------------
-- translation_drafts (the posit-feedback loop)
-- A user's private draft of a line translation + the LLM feedback they got.
-- These are NOT public; publishing promotes a draft to translations.
-- Keeps the feedback history so a user can revisit prior attempts.
-- ---------------------------------------------------------------------------
CREATE TABLE translation_drafts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id         bigint NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    user_id         uuid  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body            text NOT NULL,                  -- the user's posit
    feedback        jsonb NOT NULL DEFAULT '{}'::jsonb,  -- LLM feedback payload
    model           text,                           -- which GLM model produced it
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX drafts_user_line_idx ON translation_drafts (user_id, line_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- reading_progress
-- Per-user, per-line engagement flags. Drives the dashboard "what have I
-- read / translated / voted / commented on" overview. Updated as a side
-- effect of UGC actions + an explicit "I read this" signal.
-- ---------------------------------------------------------------------------
CREATE TABLE reading_progress (
    user_id         uuid   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    line_id         bigint NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    read_at         timestamptz,
    translated_at   timestamptz,
    voted_at        timestamptz,
    commented_at    timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, line_id)
);

-- updated_at trigger for translations / comments
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER translations_touch BEFORE UPDATE ON translations
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER comments_touch BEFORE UPDATE ON comments
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER reading_progress_touch BEFORE UPDATE ON reading_progress
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ---------------------------------------------------------------------------
-- reports (moderation queue)
-- Lightweight flag for moderators. Used by the trust/safety minimum (Phase 5).
-- ---------------------------------------------------------------------------
CREATE TABLE reports (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id     uuid REFERENCES users(id) ON DELETE SET NULL,
    target_type     text NOT NULL CHECK (target_type IN ('translation','comment','user')),
    target_id       uuid NOT NULL,
    reason          text NOT NULL,
    status          text NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','resolved','dismissed')),
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX reports_status_idx ON reports (status, created_at);
