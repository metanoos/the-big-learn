// Package httpapi wires the storage/content/feedback/auth into HTTP handlers.
//
// Routing is deliberately stdlib (net/http ServeMux, Go 1.22+ method patterns)
// to avoid a framework dependency. JSON in/out. CORS open in dev.
//
// Auth model: most read endpoints are anonymous; write endpoints require a
// valid session token (cookie or Authorization: Bearer).
package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"

	"thebiglearn/api/internal/auth"
	"thebiglearn/api/internal/config"
	"thebiglearn/api/internal/content"
	"thebiglearn/api/internal/feedback"
	"thebiglearn/api/internal/storage"
)

// Server holds all dependencies.
type Server struct {
	cfg      config.Config
	db       *storage.DB
	content  *content.Service
	feedback *feedback.Service
	mux      *http.ServeMux
}

// New constructs the server and registers routes.
func New(cfg config.Config, db *storage.DB, cs *content.Service, fs *feedback.Service) *Server {
	s := &Server{cfg: cfg, db: db, content: cs, feedback: fs}
	mux := http.NewServeMux()
	s.mux = mux

	mux.HandleFunc("GET /api/v1/health", s.handleHealth)
	mux.HandleFunc("GET /api/v1/books", s.handleBooks)
	mux.HandleFunc("GET /api/v1/books/{book}/chapters/{chapter}", s.handleChapter)

	mux.HandleFunc("POST /api/v1/auth/register", s.handleRegister)
	mux.HandleFunc("POST /api/v1/auth/login", s.handleLogin)
	mux.HandleFunc("POST /api/v1/auth/logout", s.handleLogout)
	mux.HandleFunc("GET /api/v1/me", s.requireAuth(s.handleMe))

	mux.HandleFunc("GET /api/v1/lines/{book}/{chapter}/{line}", s.handleLineBundle)
	mux.HandleFunc("POST /api/v1/lines/{book}/{chapter}/{line}/translations", s.requireAuth(s.handlePublishTranslation))
	mux.HandleFunc("POST /api/v1/lines/{book}/{chapter}/{line}/drafts", s.requireAuth(s.handleSaveDraft))
	mux.HandleFunc("GET /api/v1/lines/{book}/{chapter}/{line}/comments", s.handleListComments)
	mux.HandleFunc("POST /api/v1/lines/{book}/{chapter}/{line}/comments", s.requireAuth(s.handleCreateComment))
	mux.HandleFunc("POST /api/v1/lines/{book}/{chapter}/{line}/feedback", s.requireAuth(s.handleFeedback))
	mux.HandleFunc("POST /api/v1/lines/{book}/{chapter}/{line}/read", s.requireAuth(s.handleMarkRead))

	mux.HandleFunc("POST /api/v1/votes", s.requireAuth(s.handleVote))
	mux.HandleFunc("DELETE /api/v1/votes/{targetType}/{targetID}", s.requireAuth(s.handleRemoveVote))

	// Trust/safety (Phase 5): report submission + moderation queue.
	mux.HandleFunc("POST /api/v1/reports", s.requireAuth(s.handleReport))
	mux.HandleFunc("GET /api/v1/admin/reports", s.requireMod(s.handleListReports))
	mux.HandleFunc("POST /api/v1/admin/reports/{id}/resolve", s.requireMod(s.handleResolveReport))

	return s
}

// requireMod wraps a handler requiring moderator or admin role.
func (s *Server) requireMod(h http.HandlerFunc) http.HandlerFunc {
	wrapped := s.requireAuth(func(w http.ResponseWriter, r *http.Request) {
		sess, _ := sessionFrom(r.Context())
		if sess.Role != "moderator" && sess.Role != "admin" {
			errJSON(w, http.StatusForbidden, "moderator role required")
			return
		}
		h(w, r)
	})
	return wrapped
}

// rateLimitKey returns the per-user key for rate limiting (their UUID).
func rateLimitKey(sess auth.Session) string {
	return sess.UserID.String()
}

// rateLimit checks + increments the counter; writes a 429 on limit.
func (s *Server) rateLimit(w http.ResponseWriter, r *http.Request, sess auth.Session, action string) bool {
	limit := s.cfg.RateLimits[action]
	if limit <= 0 {
		return true // unlimited
	}
	if err := s.db.CheckAndIncrement(r.Context(), rateLimitKey(sess), action, limit); err != nil {
		var rl storage.ErrRateLimited
		if errors.As(err, &rl) {
			w.Header().Set("Retry-After", "3600")
			errJSON(w, http.StatusTooManyRequests, rl.Error())
			return false
		}
		log.Printf("rate limit check failed: %v", err)
		// fail-open on infra error (don't block legit users because the DB hiccupped)
		return true
	}
	return true
}

// ServeHTTP implements http.Handler.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// CORS: open in dev. Tighten via env in production.
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type")
	w.Header().Set("Access-Control-Allow-Methods", "GET,POST,DELETE,PUT,PATCH,OPTIONS")
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return
	}
	s.mux.ServeHTTP(w, r)
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(v)
}

func errJSON(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

type ctxKey string

const sessionCtxKey ctxKey = "session"

// requireAuth wraps a handler, requiring a valid session token.
func (s *Server) requireAuth(h http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		tok := tokenFromRequest(r, s.cfg.SessionCookieName)
		if tok == "" {
			errJSON(w, http.StatusUnauthorized, "authentication required")
			return
		}
		sess, err := auth.ParseToken(s.cfg.JWTSecret, tok)
		if err != nil {
			errJSON(w, http.StatusUnauthorized, "invalid or expired session")
			return
		}
		ctx := context.WithValue(r.Context(), sessionCtxKey, sess)
		h(w, r.WithContext(ctx))
	}
}

func sessionFrom(ctx context.Context) (auth.Session, bool) {
	s, ok := ctx.Value(sessionCtxKey).(auth.Session)
	return s, ok
}

func tokenFromRequest(r *http.Request, cookieName string) string {
	if c, err := r.Cookie(cookieName); err == nil && c.Value != "" {
		return c.Value
	}
	if h := r.Header.Get("Authorization"); strings.HasPrefix(h, "Bearer ") {
		return strings.TrimPrefix(h, "Bearer ")
	}
	return ""
}

// ---------------------------------------------------------------------------
// health + content
// ---------------------------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "service": "the-big-learn"})
}

func (s *Server) handleBooks(w http.ResponseWriter, r *http.Request) {
	books, err := s.content.Books()
	if err != nil {
		log.Printf("books: %v", err)
		errJSON(w, http.StatusInternalServerError, "failed to load books")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"books": books})
}

func (s *Server) handleChapter(w http.ResponseWriter, r *http.Request) {
	book := r.PathValue("book")
	// Accept either a numeric chapter order (1, 2, ...) or the full file ID
	// (chapter-001). Normalize to the file ID so both styles work.
	chapter := normalizeChapterID(r.PathValue("chapter"))
	ch, err := s.content.Chapter(book, chapter)
	if err != nil {
		if errors.Is(err, content.ErrNotFound) {
			errJSON(w, http.StatusNotFound, "chapter not found")
			return
		}
		log.Printf("chapter %s/%s: %v", book, chapter, err)
		errJSON(w, http.StatusInternalServerError, "failed to load chapter")
		return
	}
	writeJSON(w, http.StatusOK, ch)
}

// ---------------------------------------------------------------------------
// auth
// ---------------------------------------------------------------------------

type registerRequest struct {
	Username string `json:"username"`
	Email    string `json:"email"`
	Password string `json:"password"`
}

func (s *Server) handleRegister(w http.ResponseWriter, r *http.Request) {
	var req registerRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	req.Username = strings.TrimSpace(req.Username)
	req.Email = strings.TrimSpace(strings.ToLower(req.Email))
	if len(req.Username) < 2 || len(req.Username) > 32 {
		errJSON(w, http.StatusBadRequest, "username must be 2–32 chars")
		return
	}
	if !strings.Contains(req.Email, "@") {
		errJSON(w, http.StatusBadRequest, "invalid email")
		return
	}
	if len(req.Password) < 8 {
		errJSON(w, http.StatusBadRequest, "password must be at least 8 chars")
		return
	}
	// Rate limit by IP (no user yet). Defends against bot account creation.
	ip := clientIP(r)
	limit := s.cfg.RateLimits[storage.ActionRegister]
	if limit > 0 {
		if err := s.db.CheckAndIncrement(r.Context(), "ip:"+ip, storage.ActionRegister, limit); err != nil {
			var rl storage.ErrRateLimited
			if errors.As(err, &rl) {
				w.Header().Set("Retry-After", "3600")
				errJSON(w, http.StatusTooManyRequests, "too many registrations from this address, try again later")
				return
			}
		}
	}
	hash, err := auth.HashPassword(req.Password)
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "hash failed")
		return
	}
	u, err := s.db.CreateUser(r.Context(), req.Username, req.Email, hash)
	if errors.Is(err, storage.ErrTaken) {
		errJSON(w, http.StatusConflict, "username or email already taken")
		return
	}
	if err != nil {
		log.Printf("register: %v", err)
		errJSON(w, http.StatusInternalServerError, "create failed")
		return
	}
	s.issueSession(w, u)
	writeJSON(w, http.StatusCreated, publicUser(u))
}

type loginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

func (s *Server) handleLogin(w http.ResponseWriter, r *http.Request) {
	var req loginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	u, err := s.db.UserByEmail(r.Context(), strings.TrimSpace(strings.ToLower(req.Email)))
	if errors.Is(err, storage.ErrNotFound) {
		errJSON(w, http.StatusUnauthorized, "invalid credentials")
		return
	}
	if err != nil {
		log.Printf("login lookup: %v", err)
		errJSON(w, http.StatusInternalServerError, "lookup failed")
		return
	}
	if !auth.VerifyPassword(u.PasswordHash, req.Password) {
		errJSON(w, http.StatusUnauthorized, "invalid credentials")
		return
	}
	s.issueSession(w, u)
	writeJSON(w, http.StatusOK, publicUser(u))
}

func (s *Server) handleLogout(w http.ResponseWriter, r *http.Request) {
	http.SetCookie(w, &http.Cookie{
		Name: s.cfg.SessionCookieName, Value: "", Path: "/",
		Expires: time.Unix(0, 0), HttpOnly: true, SameSite: http.SameSiteLaxMode,
	})
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (s *Server) handleMe(w http.ResponseWriter, r *http.Request) {
	sess, _ := sessionFrom(r.Context())
	u, err := s.db.UserByID(r.Context(), sess.UserID)
	if errors.Is(err, storage.ErrNotFound) {
		errJSON(w, http.StatusUnauthorized, "user not found")
		return
	}
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "lookup failed")
		return
	}
	writeJSON(w, http.StatusOK, publicUser(u))
}

func (s *Server) issueSession(w http.ResponseWriter, u storage.User) {
	tok, err := auth.IssueToken(s.cfg.JWTSecret, auth.Session{
		UserID: u.ID, Role: u.Role, IssuedAt: time.Now(),
	})
	if err != nil {
		log.Printf("issue token: %v", err)
		return
	}
	http.SetCookie(w, &http.Cookie{
		Name: s.cfg.SessionCookieName, Value: tok, Path: "/",
		MaxAge: 60 * 60 * 24 * 30, // 30d
		HttpOnly: true, SameSite: http.SameSiteLaxMode,
	})
}

type publicUserT struct {
	ID       uuid.UUID `json:"id"`
	Username string    `json:"username"`
	Role     string    `json:"role"`
}

func publicUser(u storage.User) publicUserT {
	return publicUserT{ID: u.ID, Username: u.Username, Role: u.Role}
}

// ---------------------------------------------------------------------------
// line bundle (canonical content + UGC for one line, in one round-trip)
// ---------------------------------------------------------------------------

// handleLineBundle returns everything needed to render a line: the canonical
// reading unit, its seeded translations, the published user translations
// (vote-sorted), and the comments. This is the core read endpoint for the
// reader UI.
func (s *Server) handleLineBundle(w http.ResponseWriter, r *http.Request) {
	book := r.PathValue("book")
	chapterNum := atoiOr(r.PathValue("chapter"), 0)
	lineNum := atoiOr(r.PathValue("line"), 0)

	ch, err := s.content.Chapter(book, chapterID(chapterNum))
	if err != nil {
		if errors.Is(err, content.ErrNotFound) {
			errJSON(w, http.StatusNotFound, "chapter not found")
			return
		}
		errJSON(w, http.StatusInternalServerError, "load failed")
		return
	}
	var unit *content.ReadingUnit
	for i := range ch.Chapter.ReadingUnits {
		if ch.Chapter.ReadingUnits[i].Order == lineNum {
			unit = &ch.Chapter.ReadingUnits[i]
			break
		}
	}
	if unit == nil {
		errJSON(w, http.StatusNotFound, "line not found")
		return
	}

	resp := map[string]any{
		"book":         book,
		"chapter":      chapterNum,
		"line":         lineNum,
		"unit":         unit,
		"translations": []any{}, // default empty
		"comments":     []any{},
	}

	// UGC only if any exists. EnsureLine lazily; if no rows, skip the query.
	lineID, err := s.db.EnsureLine(r.Context(), book, chapterNum, lineNum)
	if err != nil {
		// non-fatal: return canonical content without UGC
		writeJSON(w, http.StatusOK, resp)
		return
	}
	trans, _ := s.db.PublishedTranslationsForLine(r.Context(), lineID)
	resp["translations"] = trans
	comments, _ := s.db.CommentsForLine(r.Context(), lineID)
	resp["comments"] = comments

	writeJSON(w, http.StatusOK, resp)
}

// ---------------------------------------------------------------------------
// translations + drafts
// ---------------------------------------------------------------------------

type publishTranslationRequest struct {
	Body string `json:"body"`
	Note string `json:"note"`
}

func (s *Server) handlePublishTranslation(w http.ResponseWriter, r *http.Request) {
	var req publishTranslationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if strings.TrimSpace(req.Body) == "" {
		errJSON(w, http.StatusBadRequest, "body is required")
		return
	}
	sess, _ := sessionFrom(r.Context())
	if !s.rateLimit(w, r, sess, storage.ActionPublishTrans) {
		return
	}
	lineID, err := s.db.EnsureLine(r.Context(), r.PathValue("book"),
		atoiOr(r.PathValue("chapter"), 0), atoiOr(r.PathValue("line"), 0))
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "ensure line failed")
		return
	}
	t, err := s.db.PublishTranslation(r.Context(), lineID, sess.UserID, req.Body, stringPtr(req.Note))
	if err != nil {
		log.Printf("publish translation: %v", err)
		errJSON(w, http.StatusInternalServerError, "publish failed")
		return
	}
	_ = s.db.TouchProgress(r.Context(), sess.UserID, lineID, "translated_at")
	writeJSON(w, http.StatusCreated, t)
}

type saveDraftRequest struct {
	Body string `json:"body"`
	Note string `json:"note"`
}

func (s *Server) handleSaveDraft(w http.ResponseWriter, r *http.Request) {
	var req saveDraftRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if strings.TrimSpace(req.Body) == "" {
		errJSON(w, http.StatusBadRequest, "body is required")
		return
	}
	sess, _ := sessionFrom(r.Context())
	lineID, err := s.db.EnsureLine(r.Context(), r.PathValue("book"),
		atoiOr(r.PathValue("chapter"), 0), atoiOr(r.PathValue("line"), 0))
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "ensure line failed")
		return
	}
	t, err := s.db.SaveDraftTranslation(r.Context(), lineID, sess.UserID, req.Body, stringPtr(req.Note))
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "save failed")
		return
	}
	writeJSON(w, http.StatusCreated, t)
}

// stringPtr returns &s; used for optional note fields that map to nullable cols.
func stringPtr(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}

// ---------------------------------------------------------------------------
// comments
// ---------------------------------------------------------------------------

func (s *Server) handleListComments(w http.ResponseWriter, r *http.Request) {
	lineID, err := s.db.EnsureLine(r.Context(), r.PathValue("book"),
		atoiOr(r.PathValue("chapter"), 0), atoiOr(r.PathValue("line"), 0))
	if err != nil {
		writeJSON(w, http.StatusOK, []any{})
		return
	}
	cs, err := s.db.CommentsForLine(r.Context(), lineID)
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "list comments failed")
		return
	}
	if cs == nil {
		cs = []storage.Comment{}
	}
	writeJSON(w, http.StatusOK, cs)
}

type createCommentRequest struct {
	Body        string `json:"body"`
	ParentID    string `json:"parent_id"`
	Translation string `json:"translation_id"`
}

func (s *Server) handleCreateComment(w http.ResponseWriter, r *http.Request) {
	var req createCommentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if strings.TrimSpace(req.Body) == "" {
		errJSON(w, http.StatusBadRequest, "body is required")
		return
	}
	sess, _ := sessionFrom(r.Context())
	if !s.rateLimit(w, r, sess, storage.ActionComment) {
		return
	}
	lineID, err := s.db.EnsureLine(r.Context(), r.PathValue("book"),
		atoiOr(r.PathValue("chapter"), 0), atoiOr(r.PathValue("line"), 0))
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "ensure line failed")
		return
	}
	var parentID, refTrans *uuid.UUID
	if id, err := uuid.Parse(req.ParentID); err == nil {
		parentID = &id
	}
	if id, err := uuid.Parse(req.Translation); err == nil {
		refTrans = &id
	}
	c, err := s.db.CreateComment(r.Context(), lineID, sess.UserID, parentID, refTrans, req.Body)
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "create comment failed")
		return
	}
	_ = s.db.TouchProgress(r.Context(), sess.UserID, lineID, "commented_at")
	writeJSON(w, http.StatusCreated, c)
}

// ---------------------------------------------------------------------------
// feedback (the wedge)
// ---------------------------------------------------------------------------

type feedbackRequest struct {
	Attempt string `json:"attempt"`
}

func (s *Server) handleFeedback(w http.ResponseWriter, r *http.Request) {
	var req feedbackRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if strings.TrimSpace(req.Attempt) == "" {
		errJSON(w, http.StatusBadRequest, "attempt is required")
		return
	}
	// Rate limit: this is the LLM-spend surface. Cap per user per hour.
	sess, _ := sessionFrom(r.Context())
	if !s.rateLimit(w, r, sess, storage.ActionFeedback) {
		return
	}

	// Load the canonical line to give the model context.
	book := r.PathValue("book")
	chapterNum := atoiOr(r.PathValue("chapter"), 0)
	lineNum := atoiOr(r.PathValue("line"), 0)
	ch, err := s.content.Chapter(book, chapterID(chapterNum))
	if err != nil {
		errJSON(w, http.StatusNotFound, "chapter not found")
		return
	}
	var unit *content.ReadingUnit
	for i := range ch.Chapter.ReadingUnits {
		if ch.Chapter.ReadingUnits[i].Order == lineNum {
			unit = &ch.Chapter.ReadingUnits[i]
			break
		}
	}
	if unit == nil {
		errJSON(w, http.StatusNotFound, "line not found")
		return
	}

	canon := make([]string, 0, len(unit.CanonicalTranslations))
	for _, c := range unit.CanonicalTranslations {
		canon = append(canon, c.Text)
	}

	result, err := s.feedback.Evaluate(r.Context(), feedback.Posit{
		SourceLine:  unit.Text,
		Pinyin:      unit.Pinyin,
		Canonical:   canon,
		UserAttempt: req.Attempt,
	})
	if errors.Is(err, feedback.ErrNotConfigured) {
		errJSON(w, http.StatusServiceUnavailable, "LLM feedback not configured")
		return
	}
	if err != nil {
		log.Printf("feedback: %v", err)
		errJSON(w, http.StatusInternalServerError, "feedback failed")
		return
	}

	// Persist the draft + feedback so the user can revisit prior attempts.
	lineID, _ := s.db.EnsureLine(r.Context(), book, chapterNum, lineNum)
	if lineID > 0 {
		fbJSON, _ := json.Marshal(result)
		_, _ = s.db.SaveDraft(r.Context(), lineID, sess.UserID, req.Attempt, fbJSON, s.cfg.GLMModel)
	}

	writeJSON(w, http.StatusOK, result)
}

// ---------------------------------------------------------------------------
// votes + read
// ---------------------------------------------------------------------------

type voteRequest struct {
	TargetType string `json:"target_type"` // "translation" | "comment"
	TargetID   string `json:"target_id"`
	Value      int    `json:"value"` // -1 | 1
}

func (s *Server) handleVote(w http.ResponseWriter, r *http.Request) {
	var req voteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.TargetType != "translation" && req.TargetType != "comment" {
		errJSON(w, http.StatusBadRequest, "invalid target_type")
		return
	}
	id, err := uuid.Parse(req.TargetID)
	if err != nil {
		errJSON(w, http.StatusBadRequest, "invalid target_id")
		return
	}
	if req.Value != 1 && req.Value != -1 {
		errJSON(w, http.StatusBadRequest, "value must be 1 or -1")
		return
	}
	sess, _ := sessionFrom(r.Context())
	if err := s.db.SetVote(r.Context(), sess.UserID, req.TargetType, id, req.Value); err != nil {
		errJSON(w, http.StatusInternalServerError, "vote failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (s *Server) handleRemoveVote(w http.ResponseWriter, r *http.Request) {
	sess, _ := sessionFrom(r.Context())
	targetType := r.PathValue("targetType")
	id, err := uuid.Parse(r.PathValue("targetID"))
	if err != nil {
		errJSON(w, http.StatusBadRequest, "invalid target_id")
		return
	}
	if err := s.db.RemoveVote(r.Context(), sess.UserID, targetType, id); err != nil {
		errJSON(w, http.StatusInternalServerError, "remove vote failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (s *Server) handleMarkRead(w http.ResponseWriter, r *http.Request) {
	sess, _ := sessionFrom(r.Context())
	lineID, err := s.db.EnsureLine(r.Context(), r.PathValue("book"),
		atoiOr(r.PathValue("chapter"), 0), atoiOr(r.PathValue("line"), 0))
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "ensure line failed")
		return
	}
	if err := s.db.MarkRead(r.Context(), sess.UserID, lineID); err != nil {
		errJSON(w, http.StatusInternalServerError, "mark read failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

// ---------------------------------------------------------------------------
// reports + moderation (Phase 5)
// ---------------------------------------------------------------------------

type reportRequest struct {
	TargetType string `json:"target_type"`
	TargetID   string `json:"target_id"`
	Reason     string `json:"reason"`
}

func (s *Server) handleReport(w http.ResponseWriter, r *http.Request) {
	var req reportRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.TargetType != "translation" && req.TargetType != "comment" && req.TargetType != "user" {
		errJSON(w, http.StatusBadRequest, "invalid target_type")
		return
	}
	id, err := uuid.Parse(req.TargetID)
	if err != nil {
		errJSON(w, http.StatusBadRequest, "invalid target_id")
		return
	}
	if len(req.Reason) < 3 || len(req.Reason) > 1000 {
		errJSON(w, http.StatusBadRequest, "reason must be 3–1000 chars")
		return
	}
	sess, _ := sessionFrom(r.Context())
	rep, err := s.db.CreateReport(r.Context(), sess.UserID, req.TargetType, req.Reason, id)
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "report failed")
		return
	}
	writeJSON(w, http.StatusCreated, rep)
}

func (s *Server) handleListReports(w http.ResponseWriter, r *http.Request) {
	reports, err := s.db.OpenReports(r.Context(), 50)
	if err != nil {
		errJSON(w, http.StatusInternalServerError, "list failed")
		return
	}
	if reports == nil {
		reports = []storage.Report{}
	}
	writeJSON(w, http.StatusOK, reports)
}

func (s *Server) handleResolveReport(w http.ResponseWriter, r *http.Request) {
	id, err := uuid.Parse(r.PathValue("id"))
	if err != nil {
		errJSON(w, http.StatusBadRequest, "invalid report id")
		return
	}
	dismiss := r.URL.Query().Get("dismiss") == "1"
	sess, _ := sessionFrom(r.Context())
	if err := s.db.ResolveReport(r.Context(), id, sess.UserID, dismiss); err != nil {
		log.Printf("resolve report: %v", err)
		errJSON(w, http.StatusInternalServerError, "resolve failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

// --- util ------------------------------------------------------------------

func chapterID(n int) string {
	if n <= 0 {
		return "chapter-001"
	}
	return "chapter-" + pad3(n)
}

// normalizeChapterID accepts either a numeric chapter (1, 2, ...) or a full
// file ID (chapter-001) and returns the file ID. Numeric is the friendlier
// URL form for the frontend.
func normalizeChapterID(s string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return "chapter-001"
	}
	// already a full id
	if strings.HasPrefix(s, "chapter-") {
		return s
	}
	// numeric -> file id
	if n := atoiOr(s, 0); n > 0 {
		return chapterID(n)
	}
	return s
}

func pad3(n int) string {
	if n < 10 {
		return "00" + itoa(n)
	}
	if n < 100 {
		return "0" + itoa(n)
	}
	return itoa(n)
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var b [20]byte
	i := len(b)
	for n > 0 {
		i--
		b[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		b[i] = '-'
	}
	return string(b[i:])
}

func atoiOr(s string, def int) int {
	n := 0
	any := false
	for _, c := range s {
		if c < '0' || c > '9' {
			return def
		}
		n = n*10 + int(c-'0')
		any = true
	}
	if !any {
		return def
	}
	return n
}

// clientIP extracts the caller's IP, honoring X-Forwarded-For (first hop) for
// reverse-proxy deploys (Caddy/nginx on the VPS). Falls back to RemoteAddr.
func clientIP(r *http.Request) string {
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		if i := strings.Index(xff, ","); i > 0 {
			return strings.TrimSpace(xff[:i])
		}
		return strings.TrimSpace(xff)
	}
	if i := strings.LastIndex(r.RemoteAddr, ":"); i > 0 {
		return r.RemoteAddr[:i]
	}
	return r.RemoteAddr
}
