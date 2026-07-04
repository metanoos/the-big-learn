-- 003: email verification.
--
-- Design: a new account is created in 'pending' state with a verification
-- token. The token is a random secret stored hashed (so a DB leak can't
-- validate accounts). Public-post endpoints (publish/comment) check
-- email_verified; reading + private posit feedback work unverified so a new
-- signup isn't dead on arrival (a deliberate choice — see inline note).

ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified  boolean NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_token_hash text;   -- set when a verify email is outstanding
ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_token_sent_at timestamptz;

CREATE TABLE IF NOT EXISTS email_verifications (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   text NOT NULL,                  -- SHA-256 of the secret
    consumed_at  timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS email_verifications_user_idx ON email_verifications (user_id, created_at DESC);

-- Janitor: purge unconsumed tokens older than 24h (callable ad hoc).
CREATE OR REPLACE FUNCTION prune_email_verifications(max_age_hours int DEFAULT 24)
RETURNS int LANGUAGE sql AS $$
    WITH deleted AS (
        DELETE FROM email_verifications
         WHERE consumed_at IS NULL
           AND created_at < now() - (max_age_hours || ' hours')::interval
        RETURNING 1
    )
    SELECT count(*) FROM deleted;
$$;
