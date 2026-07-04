// Dashboard progress aggregation.
package storage

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
)

// BookProgress is the per-book summary shown on the dashboard.
type BookProgress struct {
	Book        string `json:"book"`
	Title       string `json:"title"`
	V1          bool   `json:"v1"`
	TotalLines  int    `json:"total_lines"`  // canonical line count for the book
	Read        int    `json:"read"`         // lines this user marked read
	Translated  int    `json:"translated"`   // lines with a published translation by this user
	Voted       int    `json:"voted"`        // lines this user voted on
	Commented   int    `json:"commented"`    // lines this user commented on
}

// UserActivity is recent UGC by the user (for the dashboard feed).
type UserActivity struct {
	Type    string    `json:"type"` // "translation" | "comment" | "draft"
	Book    string    `json:"book"`
	Chapter int       `json:"chapter"`
	Line    int       `json:"line"`
	Snippet string    `json:"snippet"` // first ~80 chars
	At      time.Time `json:"at"`
}

// UserProgress returns per-book progress for a user. TotalLines comes from
// the canonical content (passed in as a map so storage stays content-agnostic).
func (db *DB) UserProgress(ctx context.Context, userID uuid.UUID, totals map[string]int, titles map[string]string, v1Books map[string]bool) ([]BookProgress, error) {
	q := `
		SELECT book,
		       COUNT(*) FILTER (WHERE read_at IS NOT NULL)       AS read,
		       COUNT(*) FILTER (WHERE translated_at IS NOT NULL) AS translated,
		       COUNT(*) FILTER (WHERE voted_at IS NOT NULL)      AS voted,
		       COUNT(*) FILTER (WHERE commented_at IS NOT NULL)  AS commented
		FROM reading_progress rp
		JOIN lines l ON l.id = rp.line_id
		WHERE rp.user_id = $1
		GROUP BY book`
	rows, err := db.Pool.Query(ctx, q, userID)
	if err != nil {
		return nil, fmt.Errorf("storage: user progress: %w", err)
	}
	defer rows.Close()

	byBook := map[string]BookProgress{}
	for rows.Next() {
		var book string
		var read, translated, voted, commented int
		if err := rows.Scan(&book, &read, &translated, &voted, &commented); err != nil {
			return nil, err
		}
		byBook[book] = BookProgress{
			Book:       book,
			Read:       read,
			Translated: translated,
			Voted:      voted,
			Commented:  commented,
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	// Merge with all canonical books (so untouched books show 0/N).
	out := make([]BookProgress, 0, len(totals))
	for book, total := range totals {
		bp := byBook[book] // zero-value if absent
		bp.Book = book
		bp.TotalLines = total
		if t, ok := titles[book]; ok {
			bp.Title = t
		}
		bp.V1 = v1Books[book]
		out = append(out, bp)
	}
	return out, nil
}

// RecentActivity returns the user's most recent translations, comments, and
// drafts (unioned), newest first. Used as a dashboard feed.
func (db *DB) RecentActivity(ctx context.Context, userID uuid.UUID, limit int) ([]UserActivity, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}
	q := `
		( SELECT 'translation' AS type, l.book, l.chapter_num, l.line_num,
		         LEFT(t.body, 80) AS snippet, t.created_at AS at
		    FROM translations t JOIN lines l ON l.id = t.line_id
		   WHERE t.user_id = $1 AND t.status = 'published' AND t.deleted_at IS NULL )
		UNION ALL
		( SELECT 'comment' AS type, l.book, l.chapter_num, l.line_num,
		         LEFT(c.body, 80), c.created_at
		    FROM comments c JOIN lines l ON l.id = c.line_id
		   WHERE c.user_id = $1 AND c.deleted_at IS NULL )
		UNION ALL
		( SELECT 'draft' AS type, l.book, l.chapter_num, l.line_num,
		         LEFT(d.body, 80), d.created_at
		    FROM translation_drafts d JOIN lines l ON l.id = d.line_id
		   WHERE d.user_id = $1 )
		ORDER BY at DESC
		LIMIT $2`
	rows, err := db.Pool.Query(ctx, q, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("storage: recent activity: %w", err)
	}
	defer rows.Close()
	var out []UserActivity
	for rows.Next() {
		var a UserActivity
		if err := rows.Scan(&a.Type, &a.Book, &a.Chapter, &a.Line, &a.Snippet, &a.At); err != nil {
			return nil, err
		}
		out = append(out, a)
	}
	return out, rows.Err()
}
