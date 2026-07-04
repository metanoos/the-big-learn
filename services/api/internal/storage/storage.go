// Package storage is the Postgres access layer for user-generated content.
//
// Canonical content (Chinese text + seeded translations) lives in JSON files
// served by the content package; this package holds ONLY user data: users,
// lines (a light registry), translations, votes, comments, drafts, progress.
package storage

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

// DB is the shared connection pool wrapper.
type DB struct {
	Pool *pgxpool.Pool
}

// Open creates a pool against the given DSN.
func Open(ctx context.Context, dsn string) (*DB, error) {
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, fmt.Errorf("storage: open pool: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("storage: ping: %w", err)
	}
	return &DB{Pool: pool}, nil
}

// Close releases the pool.
func (db *DB) Close() { db.Pool.Close() }

// ErrNotFound is returned by getters when a row is absent.
var ErrNotFound = errors.New("not found")

// IsUniqueViolation reports whether err is a Postgres unique-constraint failure.
func IsUniqueViolation(err error) bool {
	var pgErr *pgconn.PgError
	return errors.As(err, &pgErr) && pgErr.Code == "23505"
}

// ---------------------------------------------------------------------------
// users
// ---------------------------------------------------------------------------

// User is the authenticated principal.
type User struct {
	ID           uuid.UUID
	Username     string
	Email        string
	PasswordHash string
	Role         string
	CreatedAt    time.Time
}

// CreateUser inserts a new user. Returns ErrTaken on username/email collision.
var ErrTaken = errors.New("username or email already taken")

func (db *DB) CreateUser(ctx context.Context, username, email, passwordHash string) (User, error) {
	const q = `
		INSERT INTO users (username, email, password_hash)
		VALUES ($1, $2, $3)
		RETURNING id, username, email, password_hash, role, created_at`
	var u User
	err := db.Pool.QueryRow(ctx, q, username, email, passwordHash).
		Scan(&u.ID, &u.Username, &u.Email, &u.PasswordHash, &u.Role, &u.CreatedAt)
	if IsUniqueViolation(err) {
		return User{}, ErrTaken
	}
	if err != nil {
		return User{}, fmt.Errorf("storage: create user: %w", err)
	}
	return u, nil
}

// UserByEmail looks up a user for login.
func (db *DB) UserByEmail(ctx context.Context, email string) (User, error) {
	const q = `
		SELECT id, username, email, password_hash, role, created_at
		FROM users WHERE email = $1`
	var u User
	err := db.Pool.QueryRow(ctx, q, email).
		Scan(&u.ID, &u.Username, &u.Email, &u.PasswordHash, &u.Role, &u.CreatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return User{}, ErrNotFound
	}
	if err != nil {
		return User{}, fmt.Errorf("storage: user by email: %w", err)
	}
	return u, nil
}

// UserByID for session resolution.
func (db *DB) UserByID(ctx context.Context, id uuid.UUID) (User, error) {
	const q = `
		SELECT id, username, email, password_hash, role, created_at
		FROM users WHERE id = $1`
	var u User
	err := db.Pool.QueryRow(ctx, q, id).
		Scan(&u.ID, &u.Username, &u.Email, &u.PasswordHash, &u.Role, &u.CreatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return User{}, ErrNotFound
	}
	if err != nil {
		return User{}, fmt.Errorf("storage: user by id: %w", err)
	}
	return u, nil
}

// ---------------------------------------------------------------------------
// lines (lazy registry)
// ---------------------------------------------------------------------------

// EnsureLine lazily creates a lines row for (book, chapter, line) and returns
// its id. Idempotent. Used whenever UGC first engages a canonical line.
func (db *DB) EnsureLine(ctx context.Context, book string, chapterNum, lineNum int) (int64, error) {
	const q = `
		INSERT INTO lines (book, chapter_num, line_num)
		VALUES ($1, $2, $3)
		ON CONFLICT (book, chapter_num, line_num) DO UPDATE SET book = EXCLUDED.book
		RETURNING id`
	var id int64
	err := db.Pool.QueryRow(ctx, q, book, chapterNum, lineNum).Scan(&id)
	if err != nil {
		return 0, fmt.Errorf("storage: ensure line: %w", err)
	}
	return id, nil
}

// ---------------------------------------------------------------------------
// translations
// ---------------------------------------------------------------------------

// Translation is a user-submitted translation of a line.
type Translation struct {
	ID          uuid.UUID  `json:"id"`
	LineID      int64      `json:"line_id"`
	UserID      uuid.UUID  `json:"user_id"`
	Username    string     `json:"username"` // joined for display
	Body        string     `json:"body"`
	Status      string     `json:"status"`
	Note        *string    `json:"note"` // nullable in DB
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	PublishedAt *time.Time `json:"published_at"`
	VoteScore   int        `json:"vote_score"` // aggregated
	MyVote      int        `json:"my_vote"`    // -1/0/1 from the viewer's perspective
}

// PublishTranslation creates a published translation, replacing any prior
// published one by the same user for the same line (the partial unique index
// enforces one-published-per-user-per-line).
func (db *DB) PublishTranslation(ctx context.Context, lineID int64, userID uuid.UUID, body string, note *string) (Translation, error) {
	const q = `
		WITH cleared AS (
			UPDATE translations
			   SET status = 'hidden_by_user', updated_at = now()
			 WHERE line_id = $1 AND user_id = $2 AND status = 'published'
		 RETURNING id)
		INSERT INTO translations (line_id, user_id, body, note, status, published_at)
		VALUES ($1, $2, $3, $4, 'published', now())
		RETURNING id, line_id, user_id, body, status, note, created_at, updated_at, published_at`
	var t Translation
	err := db.Pool.QueryRow(ctx, q, lineID, userID, body, nullIfEmpty(note)).
		Scan(&t.ID, &t.LineID, &t.UserID, &t.Body, &t.Status, &t.Note, &t.CreatedAt, &t.UpdatedAt, &t.PublishedAt)
	if err != nil {
		return Translation{}, fmt.Errorf("storage: publish translation: %w", err)
	}
	return t, nil
}

// SaveDraftTranslation stores a draft (no publishing). Drafts are unlimited.
func (db *DB) SaveDraftTranslation(ctx context.Context, lineID int64, userID uuid.UUID, body string, note *string) (Translation, error) {
	const q = `
		INSERT INTO translations (line_id, user_id, body, note, status)
		VALUES ($1, $2, $3, $4, 'draft')
		RETURNING id, line_id, user_id, body, status, note, created_at, updated_at, published_at`
	var t Translation
	err := db.Pool.QueryRow(ctx, q, lineID, userID, body, nullIfEmpty(note)).
		Scan(&t.ID, &t.LineID, &t.UserID, &t.Body, &t.Status, &t.Note, &t.CreatedAt, &t.UpdatedAt, &t.PublishedAt)
	if err != nil {
		return Translation{}, fmt.Errorf("storage: save draft: %w", err)
	}
	return t, nil
}

// nullIfEmpty returns nil for an empty/nil string so the column stays NULL.
func nullIfEmpty(s *string) *string {
	if s == nil || *s == "" {
		return nil
	}
	return s
}

// PublishedTranslationsForLine returns all published translations for a line,
// vote-score-desc. (Viewer-specific myVote is resolved in a second pass when
// needed; keeping the query single-purpose avoids a tangled join.)
func (db *DB) PublishedTranslationsForLine(ctx context.Context, lineID int64) ([]Translation, error) {
	const q = `
		SELECT t.id, t.line_id, t.user_id, u.username, t.body, t.status,
		       t.note, t.created_at, t.updated_at, t.published_at,
		       COALESCE(v.score, 0)
		FROM translations t
		JOIN users u ON u.id = t.user_id
		LEFT JOIN (
			SELECT target_id, SUM(value) AS score
			FROM votes WHERE target_type = 'translation'
			GROUP BY target_id
		) v ON v.target_id = t.id
		WHERE t.line_id = $1 AND t.status = 'published' AND t.deleted_at IS NULL
		ORDER BY v.score DESC NULLS LAST, t.published_at DESC`
	rows, err := db.Pool.Query(ctx, q, lineID)
	if err != nil {
		return nil, fmt.Errorf("storage: list translations: %w", err)
	}
	defer rows.Close()

	var out []Translation
	for rows.Next() {
		var t Translation
		if err := rows.Scan(&t.ID, &t.LineID, &t.UserID, &t.Username, &t.Body, &t.Status,
			&t.Note, &t.CreatedAt, &t.UpdatedAt, &t.PublishedAt, &t.VoteScore); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

// MyVote returns the viewer's vote value on a target, or 0 if none.
func (db *DB) MyVote(ctx context.Context, userID uuid.UUID, target string, targetID uuid.UUID) (int, error) {
	const q = `SELECT value FROM votes WHERE user_id = $1 AND target_type = $2 AND target_id = $3`
	var v int
	err := db.Pool.QueryRow(ctx, q, userID, target, targetID).Scan(&v)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, nil
	}
	if err != nil {
		return 0, fmt.Errorf("storage: my vote: %w", err)
	}
	return v, nil
}

// ---------------------------------------------------------------------------
// votes
// ---------------------------------------------------------------------------

// SetVote upserts a vote. value must be -1 or +1. Enforces one-vote-per-target
// via the PRIMARY KEY (user_id, target_type, target_id).
func (db *DB) SetVote(ctx context.Context, userID uuid.UUID, target string, targetID uuid.UUID, value int) error {
	const q = `
		INSERT INTO votes (user_id, target_type, target_id, value)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (user_id, target_type, target_id) DO UPDATE SET value = EXCLUDED.value`
	_, err := db.Pool.Exec(ctx, q, userID, target, targetID, value)
	if err != nil {
		return fmt.Errorf("storage: set vote: %w", err)
	}
	return nil
}

// RemoveVote deletes a vote (toggle off).
func (db *DB) RemoveVote(ctx context.Context, userID uuid.UUID, target string, targetID uuid.UUID) error {
	const q = `DELETE FROM votes WHERE user_id = $1 AND target_type = $2 AND target_id = $3`
	_, err := db.Pool.Exec(ctx, q, userID, target, targetID)
	if err != nil {
		return fmt.Errorf("storage: remove vote: %w", err)
	}
	return nil
}

// ---------------------------------------------------------------------------
// comments
// ---------------------------------------------------------------------------

// Comment is a line-anchored remark, optionally on a translation.
type Comment struct {
	ID         uuid.UUID  `json:"id"`
	LineID     int64      `json:"line_id"`
	UserID     uuid.UUID  `json:"user_id"`
	Username   string     `json:"username"`
	ParentID   *uuid.UUID `json:"parent_id,omitempty"`
	RefTransID *uuid.UUID `json:"referenced_translation_id,omitempty"`
	Body       string     `json:"body"`
	CreatedAt  time.Time  `json:"created_at"`
}

// CreateComment inserts a comment.
func (db *DB) CreateComment(ctx context.Context, lineID int64, userID uuid.UUID, parentID, refTransID *uuid.UUID, body string) (Comment, error) {
	q := `
		INSERT INTO comments (line_id, user_id, parent_comment_id, referenced_translation_id, body)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, line_id, user_id, parent_comment_id, referenced_translation_id, body, created_at`
	var c Comment
	err := db.Pool.QueryRow(ctx, q, lineID, userID, parentID, refTransID, body).
		Scan(&c.ID, &c.LineID, &c.UserID, &c.ParentID, &c.RefTransID, &c.Body, &c.CreatedAt)
	if err != nil {
		return Comment{}, fmt.Errorf("storage: create comment: %w", err)
	}
	return c, nil
}

// CommentsForLine lists a line's comments, oldest-first.
func (db *DB) CommentsForLine(ctx context.Context, lineID int64) ([]Comment, error) {
	q := `
		SELECT c.id, c.line_id, c.user_id, u.username, c.parent_comment_id,
		       c.referenced_translation_id, c.body, c.created_at
		FROM comments c
		JOIN users u ON u.id = c.user_id
		WHERE c.line_id = $1 AND c.deleted_at IS NULL
		ORDER BY c.created_at`
	rows, err := db.Pool.Query(ctx, q, lineID)
	if err != nil {
		return nil, fmt.Errorf("storage: list comments: %w", err)
	}
	defer rows.Close()
	var out []Comment
	for rows.Next() {
		var c Comment
		if err := rows.Scan(&c.ID, &c.LineID, &c.UserID, &c.Username, &c.ParentID,
			&c.RefTransID, &c.Body, &c.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, rows.Err()
}

// ---------------------------------------------------------------------------
// translation_drafts (posit + LLM feedback)
// ---------------------------------------------------------------------------

// Draft is a user's private translation attempt with LLM feedback.
type Draft struct {
	ID        uuid.UUID `json:"id"`
	LineID    int64     `json:"line_id"`
	UserID    uuid.UUID `json:"user_id"`
	Body      string    `json:"body"`
	Feedback  []byte    `json:"feedback,omitempty"` // raw jsonb
	Model     string    `json:"model,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

// SaveDraft persists a draft + its LLM feedback.
func (db *DB) SaveDraft(ctx context.Context, lineID int64, userID uuid.UUID, body string, feedback []byte, model string) (Draft, error) {
	q := `
		INSERT INTO translation_drafts (line_id, user_id, body, feedback, model)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, line_id, user_id, body, feedback, model, created_at`
	var d Draft
	err := db.Pool.QueryRow(ctx, q, lineID, userID, body, feedback, modelString(model)).
		Scan(&d.ID, &d.LineID, &d.UserID, &d.Body, &d.Feedback, &d.Model, &d.CreatedAt)
	if err != nil {
		return Draft{}, fmt.Errorf("storage: save draft: %w", err)
	}
	return d, nil
}

func modelString(s string) any {
	if s == "" {
		return nil
	}
	return s
}

// DraftsByUser lists a user's drafts (most recent first), for the dashboard.
func (db *DB) DraftsByUser(ctx context.Context, userID uuid.UUID, limit int) ([]Draft, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	q := `
		SELECT d.id, d.line_id, d.user_id, d.body, d.feedback, d.model, d.created_at
		FROM translation_drafts d
		WHERE d.user_id = $1
		ORDER BY d.created_at DESC
		LIMIT $2`
	rows, err := db.Pool.Query(ctx, q, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("storage: drafts by user: %w", err)
	}
	defer rows.Close()
	var out []Draft
	for rows.Next() {
		var d Draft
		if err := rows.Scan(&d.ID, &d.LineID, &d.UserID, &d.Body, &d.Feedback, &d.Model, &d.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, d)
	}
	return out, rows.Err()
}

// ---------------------------------------------------------------------------
// reading_progress (dashboard)
// ---------------------------------------------------------------------------

// ProgressSummary is the per-book counts that drive the dashboard.
type ProgressSummary struct {
	Book         string
	TotalLines   int
	Read         int
	Translated   int
	Voted        int
	Commented    int
}

// MarkRead marks a line as read by the user (idempotent).
func (db *DB) MarkRead(ctx context.Context, userID uuid.UUID, lineID int64) error {
	const q = `
		INSERT INTO reading_progress (user_id, line_id, read_at, updated_at)
		VALUES ($1, $2, now(), now())
		ON CONFLICT (user_id, line_id) DO UPDATE SET read_at = now(), updated_at = now()`
	_, err := db.Pool.Exec(ctx, q, userID, lineID)
	if err != nil {
		return fmt.Errorf("storage: mark read: %w", err)
	}
	return nil
}

// TouchProgress sets a timestamp column when UGC happens. Called as a side
// effect of publish/vote/comment so the dashboard stays current.
func (db *DB) TouchProgress(ctx context.Context, userID uuid.UUID, lineID int64, col string) error {
	// col is one of translated_at / voted_at / commented_at — validated here.
	switch col {
	case "translated_at", "voted_at", "commented_at":
	default:
		return fmt.Errorf("storage: invalid progress column %q", col)
	}
	q := `
		INSERT INTO reading_progress (user_id, line_id, ` + col + `, updated_at)
		VALUES ($1, $2, now(), now())
		ON CONFLICT (user_id, line_id) DO UPDATE SET ` + col + ` = now(), updated_at = now()`
	_, err := db.Pool.Exec(ctx, q, userID, lineID)
	if err != nil {
		return fmt.Errorf("storage: touch progress: %w", err)
	}
	return nil
}
