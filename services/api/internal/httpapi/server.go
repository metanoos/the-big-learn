// Package httpapi exposes the file-backed content service over HTTP.
//
// Routing is deliberately stdlib (net/http ServeMux, Go 1.22+ method patterns)
// to avoid a framework dependency. JSON in/out. CORS is opt-in for one
// explicitly configured browser origin.
//
// There are no accounts. The server exposes:
//   - read-only content (books, chapters, character breakdown + batch pinyin).
//
// All reader state (reading progress, bookmarks, and the character review
// pile) lives in the browser's localStorage; the server keeps no database.
package httpapi

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strings"

	"thebiglearn/api/internal/content"
)

// Server holds all dependencies.
type Server struct {
	content       *content.Service
	mux           *http.ServeMux
	allowedOrigin string
}

// New constructs the server and registers routes.
func New(cs *content.Service, allowedOrigin string) *Server {
	s := &Server{content: cs, allowedOrigin: strings.TrimSpace(allowedOrigin)}
	mux := http.NewServeMux()
	s.mux = mux

	mux.HandleFunc("GET /api/v1/health", s.handleHealth)
	mux.HandleFunc("GET /api/v1/books", s.handleBooks)
	mux.HandleFunc("GET /api/v1/books/{book}/chapters/{chapter}", s.handleChapter)

	// Character lookup: popover breakdown + batch pinyin for the reader.
	mux.HandleFunc("GET /api/v1/characters/{char}", s.handleCharacter)
	mux.HandleFunc("POST /api/v1/characters/batch", s.handleCharacterBatch)

	return s
}

// ServeHTTP implements http.Handler.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
	// The Next app normally reaches the API through a same-origin rewrite, so
	// CORS is unnecessary. Set CORS_ALLOWED_ORIGIN only for a browser frontend
	// hosted on a different origin; never reflect arbitrary origins.
	if origin := r.Header.Get("Origin"); s.allowedOrigin != "" && origin == s.allowedOrigin {
		w.Header().Set("Access-Control-Allow-Origin", origin)
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		w.Header().Set("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
		w.Header().Set("Vary", "Origin")
	}
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
	resp := chapterSimplified(ch, s.content)

	writeJSON(w, http.StatusOK, map[string]any{
		"chapter":        resp.Chapter,
		"provider":       resp.Provider,
		"source_title":   resp.SourceTitle,
		"source_url":     resp.SourceURL,
		"schema_version": resp.SchemaVersion,
	})
}

// chapterSimplified returns a shallow copy of ch with each reading unit's
// Chinese text and the chapter title/summary converted to simplified. The
// cached payload stays traditional (the source of truth on disk); only the
// response is simplified. We avoid a full deep copy by cloning just the slice
// + the fields we mutate.
func chapterSimplified(ch *content.Chapter, cs *content.Service) *content.Chapter {
	if ch == nil {
		return nil
	}
	out := *ch           // shallow copy of the wrapper
	inner := out.Chapter // value copy of the nested struct
	inner.Title = cs.Simplify(inner.Title)
	inner.Summary = cs.Simplify(inner.Summary)
	inner.ReadingUnits = append([]content.ReadingUnit(nil), ch.Chapter.ReadingUnits...)
	for i := range inner.ReadingUnits {
		inner.ReadingUnits[i].Text = cs.Simplify(inner.ReadingUnits[i].Text)
	}
	out.Chapter = inner
	return &out
}

// ---------------------------------------------------------------------------
// characters (popover breakdown + batch pinyin)
// ---------------------------------------------------------------------------

// charDetailsResponse is the shape the popover consumes. We project the index
// entry into a flat, stable contract rather than dumping the whole entry, so
// the frontend doesn't couple to the index's internal nesting.
type charDetailsResponse struct {
	Character     string         `json:"character"`   // simplified form (the index headword)
	Traditional   string         `json:"traditional"` // traditional form, shown as the popover headline
	Pinyin        []string       `json:"pinyin"`
	English       []string       `json:"english"`
	Decomposition *decomposition `json:"decomposition,omitempty"`
	Phrases       *phrases       `json:"phrases,omitempty"`
}

type decomposition struct {
	Expression string   `json:"expression"` // e.g. "六 + 井 + 一 + 𧘇"
	Parts      []string `json:"parts"`
}

type phrases struct {
	Classical []string  `json:"classical"` // from index.explosion.synthesis.phraseUse
	Chengyu   []chengyu `json:"chengyu"`   // idioms containing this char
}

type chengyu struct {
	Text   string `json:"text"`
	Pinyin string `json:"pinyin"`
	Gloss  string `json:"gloss"`
}

func (s *Server) handleCharacter(w http.ResponseWriter, r *http.Request) {
	raw := r.PathValue("char")
	runes := []rune(raw)
	if len(runes) == 0 {
		errJSON(w, http.StatusBadRequest, "empty character")
		return
	}
	// Path may carry more than one rune if the client encoded a phrase; we only
	// resolve the first. Keeps the route a single-segment match.
	entry, refs, ok := s.content.Character(runes[0])
	if !ok {
		errJSON(w, http.StatusNotFound, "character not in index")
		return
	}

	resp := charDetailsResponse{
		Character:   entry.Character,
		Traditional: entry.Traditional,
		Pinyin:      entry.Pinyin,
		English:     entry.English,
	}
	if entry.Explosion != nil {
		if entry.Explosion.Analysis != nil && (entry.Explosion.Analysis.Expression != "" || len(entry.Explosion.Analysis.Parts) > 0) {
			resp.Decomposition = &decomposition{
				Expression: entry.Explosion.Analysis.Expression,
				Parts:      entry.Explosion.Analysis.Parts,
			}
		}
		// Classical phrases are stored traditional; the reading UI is simplified,
		// so convert them to match what the reader sees everywhere else.
		var classical []string
		if entry.Explosion.Synthesis != nil {
			classical = entry.Explosion.Synthesis.PhraseUse
		}
		if len(classical) > 0 {
			converted := make([]string, len(classical))
			for i, p := range classical {
				converted[i] = s.content.Simplify(p)
			}
			classical = converted
		}
		// Always include phrases (even if empty) so the popover can render the
		// section consistently; only chengyu is non-trivial in practice.
		var cy []chengyu
		for _, r := range refs {
			cy = append(cy, chengyu{Text: r.Text, Pinyin: r.Pinyin, Gloss: r.Gloss})
		}
		if len(classical) > 0 || len(cy) > 0 {
			resp.Phrases = &phrases{Classical: classical, Chengyu: cy}
		}
	}
	writeJSON(w, http.StatusOK, resp)
}

// handleCharacterBatch returns pinyin for a list of characters in one shot.
// Body: {"chars": ["大","学",...]}. Response: {"大":{"pinyin":"dà","has_entry":true}, ...}.
// Used by the reader to render pinyin above every line without N round-trips.
func (s *Server) handleCharacterBatch(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 128<<10)
	var req struct {
		Chars []string `json:"chars"`
	}
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&req); err != nil {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		errJSON(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if len(req.Chars) > 2000 {
		errJSON(w, http.StatusBadRequest, "too many chars (max 2000)")
		return
	}
	// Dedup while preserving only the unique runes the index needs to consult.
	seen := map[rune]bool{}
	var runes []rune
	for _, c := range req.Chars {
		for _, r := range []rune(c) {
			if !seen[r] {
				seen[r] = true
				runes = append(runes, r)
			}
		}
	}
	pinyin := s.content.CharacterBatch(runes)
	type entry struct {
		Pinyin   *string `json:"pinyin"` // null when the char isn't indexed
		HasEntry bool    `json:"has_entry"`
	}
	out := make(map[string]entry, len(seen))
	for r := range seen {
		key := string(r)
		p := pinyin[key]
		out[key] = entry{Pinyin: p, HasEntry: p != nil}
	}
	writeJSON(w, http.StatusOK, out)
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
