// Reports + moderation actions.
package storage

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
)

// Report is a flag submitted by a user for moderator review.
type Report struct {
	ID         uuid.UUID  `json:"id"`
	ReporterID *uuid.UUID `json:"reporter_id,omitempty"`
	TargetType string     `json:"target_type"`
	TargetID   uuid.UUID  `json:"target_id"`
	Reason     string     `json:"reason"`
	Status     string     `json:"status"`
	CreatedAt  time.Time  `json:"created_at"`
	ResolvedBy *uuid.UUID `json:"resolved_by,omitempty"`
	ResolvedAt *time.Time `json:"resolved_at,omitempty"`
}

// CreateReport inserts a report.
func (db *DB) CreateReport(ctx context.Context, reporterID uuid.UUID, targetType, reason string, targetID uuid.UUID) (Report, error) {
	q := `
		INSERT INTO reports (reporter_id, target_type, target_id, reason)
		VALUES ($1, $2, $3, $4)
		RETURNING id, reporter_id, target_type, target_id, reason, status, created_at`
	var r Report
	var repID *uuid.UUID
	if reporterID != uuid.Nil {
		repID = &reporterID
	}
	err := db.Pool.QueryRow(ctx, q, repID, targetType, targetID, reason).
		Scan(&r.ID, &r.ReporterID, &r.TargetType, &r.TargetID, &r.Reason, &r.Status, &r.CreatedAt)
	if err != nil {
		return Report{}, fmt.Errorf("storage: create report: %w", err)
	}
	return r, nil
}

// OpenReports lists reports awaiting moderation, newest first.
func (db *DB) OpenReports(ctx context.Context, limit int) ([]Report, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	q := `
		SELECT id, reporter_id, target_type, target_id, reason, status, created_at, resolved_by, resolved_at
		FROM reports
		WHERE status = 'open'
		ORDER BY created_at DESC
		LIMIT $1`
	rows, err := db.Pool.Query(ctx, q, limit)
	if err != nil {
		return nil, fmt.Errorf("storage: list reports: %w", err)
	}
	defer rows.Close()
	var out []Report
	for rows.Next() {
		var r Report
		if err := rows.Scan(&r.ID, &r.ReporterID, &r.TargetType, &r.TargetID,
			&r.Reason, &r.Status, &r.CreatedAt, &r.ResolvedBy, &r.ResolvedAt); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// ResolveReport marks a report resolved/dismissed and hides the target content.
func (db *DB) ResolveReport(ctx context.Context, reportID, modID uuid.UUID, dismiss bool) error {
	status := "resolved"
	if dismiss {
		status = "dismissed"
	}
	tx, err := db.Pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("storage: resolve report (begin): %w", err)
	}
	defer tx.Rollback(ctx)

	// fetch the report to know its target
	var targetType string
	var targetID uuid.UUID
	err = tx.QueryRow(ctx, `SELECT target_type, target_id FROM reports WHERE id = $1 AND status = 'open'`,
		reportID).Scan(&targetType, &targetID)
	if err != nil {
		return fmt.Errorf("storage: resolve report (fetch): %w", err)
	}

	// hide the target if not dismissed
	if !dismiss {
		switch targetType {
		case "translation":
			_, err = tx.Exec(ctx, `UPDATE translations SET status='removed_by_mod', deleted_at=now() WHERE id=$1`, targetID)
		case "comment":
			_, err = tx.Exec(ctx, `UPDATE comments SET deleted_at=now() WHERE id=$1`, targetID)
		}
		if err != nil {
			return fmt.Errorf("storage: resolve report (hide): %w", err)
		}
	}

	_, err = tx.Exec(ctx,
		`UPDATE reports SET status=$1, resolved_by=$2, resolved_at=now() WHERE id=$3`,
		status, modID, reportID)
	if err != nil {
		return fmt.Errorf("storage: resolve report (mark): %w", err)
	}
	return tx.Commit(ctx)
}
