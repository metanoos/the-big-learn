// Email verification tokens.
package storage

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
)

// ErrVerifyTokenInvalid is returned by ConsumeVerifyToken for bad/expired tokens.
var ErrVerifyTokenInvalid = errors.New("invalid or expired verification token")

// ErrVerifyThrottle is returned when a resend is requested too soon.
var ErrVerifyThrottle = errors.New("verification email sent recently; wait before resending")

// CreateVerifyToken issues a fresh token for a user. Returns the raw token
// (to send to the user) — only its hash is stored. Throttles resends to one
// per 2 minutes.
func (db *DB) CreateVerifyToken(ctx context.Context, userID uuid.UUID) (string, error) {
	// throttle: don't allow hammering resend
	var lastSent *time.Time
	err := db.Pool.QueryRow(ctx,
		`SELECT verify_token_sent_at FROM users WHERE id = $1`, userID).Scan(&lastSent)
	if err != nil {
		return "", fmt.Errorf("storage: verify throttle check: %w", err)
	}
	if lastSent != nil && time.Since(*lastSent) < 2*time.Minute {
		return "", ErrVerifyThrottle
	}

	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	token := hex.EncodeToString(raw)
	hash := hashToken(token)

	// store the hash on the user (current outstanding token) + a row for audit
	if _, err := db.Pool.Exec(ctx,
		`UPDATE users SET verify_token_hash = $2, verify_token_sent_at = now() WHERE id = $1`,
		userID, hash); err != nil {
		return "", fmt.Errorf("storage: set verify token: %w", err)
	}
	_, err = db.Pool.Exec(ctx,
		`INSERT INTO email_verifications (user_id, token_hash) VALUES ($1, $2)`,
		userID, hash)
	if err != nil {
		return "", fmt.Errorf("storage: insert verification row: %w", err)
	}
	return token, nil
}

// ConsumeVerifyToken validates a token, marks the user email_verified, and
// consumes the token. Returns the user id on success.
func (db *DB) ConsumeVerifyToken(ctx context.Context, token string) (uuid.UUID, error) {
	hash := hashToken(token)
	tx, err := db.Pool.Begin(ctx)
	if err != nil {
		return uuid.Nil, fmt.Errorf("storage: consume verify (begin): %w", err)
	}
	defer tx.Rollback(ctx)

	var userID uuid.UUID
	var sentAt time.Time
	err = tx.QueryRow(ctx,
		`SELECT id, verify_token_sent_at FROM users WHERE verify_token_hash = $1`,
		hash).Scan(&userID, &sentAt)
	if err != nil {
		return uuid.Nil, ErrVerifyTokenInvalid // not found == invalid
	}
	if time.Since(sentAt) > 24*time.Hour {
		return uuid.Nil, ErrVerifyTokenInvalid // expired
	}

	if _, err := tx.Exec(ctx,
		`UPDATE users SET email_verified = true, verify_token_hash = NULL WHERE id = $1`,
		userID); err != nil {
		return uuid.Nil, fmt.Errorf("storage: consume verify (mark): %w", err)
	}
	if _, err := tx.Exec(ctx,
		`UPDATE email_verifications SET consumed_at = now()
		  WHERE user_id = $1 AND token_hash = $2`, userID, hash); err != nil {
		return uuid.Nil, fmt.Errorf("storage: consume verify (audit): %w", err)
	}
	return userID, tx.Commit(ctx)
}

func hashToken(token string) string {
	h := sha256.Sum256([]byte(token))
	return hex.EncodeToString(h[:])
}
