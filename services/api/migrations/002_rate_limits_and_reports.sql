-- 002: rate limits (persisted, fixed-window-per-hour) + reports handling.
--
-- rate_limits: one row per (key, action, hour_window). key is a user UUID
-- (or IP string for registration). Atomic upsert-increment enforces the cap.
-- Old hour_windows are pruned by a janitor job (or just accumulate; rows are
-- tiny and hourly).

CREATE TABLE IF NOT EXISTS rate_limits (
    key          text NOT NULL,        -- user UUID or IP
    action       text NOT NULL,
    hour_window  timestamptz NOT NULL, -- date_trunc('hour', now())
    count        int  NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (key, action, hour_window)
);

-- prune anything older than 2 hours (cheap janitor; called by the API on
-- health checks or a cron). Kept as a function so it's callable ad hoc.
CREATE OR REPLACE FUNCTION prune_rate_limits(retain_hours int DEFAULT 2)
RETURNS int LANGUAGE sql AS $$
    WITH deleted AS (
        DELETE FROM rate_limits
         WHERE hour_window < date_trunc('hour', now()) - (retain_hours || ' hours')::interval
        RETURNING 1
    )
    SELECT count(*) FROM deleted;
$$;

-- reports table is created in 001; here we just ensure a moderator action
-- column exists for tracking resolutions. (Add if missing — idempotent.)
ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolved_by uuid REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolved_at timestamptz;

-- Hide a translation (moderator action). Sets status + deleted_at.
CREATE OR REPLACE FUNCTION hide_translation(p_id uuid, p_mod uuid)
RETURNS void LANGUAGE sql AS $$
    UPDATE translations
       SET status = 'removed_by_mod', deleted_at = now()
     WHERE id = p_id;
$$;

-- Hide a comment (moderator action).
CREATE OR REPLACE FUNCTION hide_comment(p_id uuid, p_mod uuid)
RETURNS void LANGUAGE sql AS $$
    UPDATE comments SET deleted_at = now() WHERE id = p_id;
$$;
