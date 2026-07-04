// Rate limiting, persisted in Postgres so limits survive restarts.
//
// We use a fixed-window-per-hour counter per (user_id, action). Simple and
// adequate for v1 — no Redis dependency, no sliding-window complexity. The
// window resets each hour (keyed on date_trunc('hour')).
//
// Actions and their default limits live in DefaultLimits; overridable via env
// (RATE_LIMIT_FEEDBACK_HOURLY etc.) in config.
package storage

import (
	"context"
	"fmt"
	"time"
)

// RateLimit actions.
const (
	ActionFeedback      = "feedback"
	ActionPublishTrans  = "publish_translation"
	ActionSaveDraft     = "save_draft"
	ActionComment       = "comment"
	ActionRegister      = "register" // keyed on IP, not user_id
)

// DefaultLimits is the per-hour cap for each action.
var DefaultLimits = map[string]int{
	ActionFeedback:     20,
	ActionPublishTrans: 30,
	ActionSaveDraft:    60,
	ActionComment:      30,
	ActionRegister:     5,
}

// ErrRateLimited is returned when an action would exceed its hourly cap.
type ErrRateLimited struct {
	Action      string
	Limit       int
	WindowReset time.Time
}

func (e ErrRateLimited) Error() string {
	return fmt.Sprintf("rate limited: %s (max %d/h, resets at %s)",
		e.Action, e.Limit, e.WindowReset.Format(time.Kitchen))
}

// CheckAndIncrement atomically checks the current count for (key, action, hour)
// and increments it if under the limit. Returns ErrRateLimited if over.
//
// key is usually the user UUID (or an IP for registration). We use one row per
// (key, action, hour_window); the upsert-increment is atomic.
func (db *DB) CheckAndIncrement(ctx context.Context, key, action string, limit int) error {
	const q = `
		WITH bump AS (
			INSERT INTO rate_limits (key, action, hour_window, count, updated_at)
			VALUES ($1, $2, date_trunc('hour', now()), 1, now())
			ON CONFLICT (key, action, hour_window)
			DO UPDATE SET count = rate_limits.count + 1, updated_at = now()
			RETURNING count
		)
		SELECT count FROM bump`
	var newCount int
	err := db.Pool.QueryRow(ctx, q, key, action).Scan(&newCount)
	if err != nil {
		return fmt.Errorf("storage: rate limit check: %w", err)
	}
	if newCount > limit {
		// compute window reset (top of next hour)
		now := time.Now()
		reset := now.Truncate(time.Hour).Add(time.Hour)
		return ErrRateLimited{Action: action, Limit: limit, WindowReset: reset}
	}
	return nil
}
