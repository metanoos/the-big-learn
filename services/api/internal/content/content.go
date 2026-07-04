// Package content serves the canonical, read-only JSON content from disk.
//
// The content/ tree is the source of truth for Chinese text + seeded
// translations; it is NOT mirrored into Postgres. This package loads and
// caches book catalogs, chapter payloads, and the character index.
package content

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
)

// Service reads canonical content from a content root.
type Service struct {
	root       string
	mu         sync.RWMutex
	chapterLRU map[string]*Chapter // key: book/chapter-NNN
	lineTotals map[string]int      // lazy; cached after first LineTotals() call
}

// New constructs a Service rooted at root (the-big-learn/content).
func New(root string) *Service {
	return &Service{root: root, chapterLRU: make(map[string]*Chapter)}
}

// Book is a catalog-level entry.
type Book struct {
	Slug         string `json:"slug"`
	Title        string `json:"title"`
	ChapterCount int    `json:"chapter_count"`
	// SourceTitle / PedagogyNote are passed through from catalog.json when present.
	SourceTitle  string `json:"source_title,omitempty"`
	PedagogyNote string `json:"pedagogy_note,omitempty"`
	V1           bool   `json:"v1"`
}

// Books returns the curriculum, sorted in a sensible pedagogical order with
// v1 books first.
func (s *Service) Books() ([]Book, error) {
	entries, err := os.ReadDir(filepath.Join(s.root, "books"))
	if err != nil {
		return nil, fmt.Errorf("content: list books: %w", err)
	}
	v1 := map[string]bool{"da-xue": true, "zhong-yong": true, "lunyu": true, "mengzi": true, "daodejing": true}
	order := map[string]int{
		"da-xue": 0, "zhong-yong": 1, "lunyu": 2, "mengzi": 3, "daodejing": 4,
		"sunzi-bingfa": 5, "san-zi-jing": 6, "qian-zi-wen": 7,
		"sanguo-yanyi": 8, "chengyu-catalog": 9,
	}
	// Clean display names. The catalog.json `title` field holds the source
	// document title (e.g. "四書章句集注 : 大學章句"), which is provenance —
	// exposed separately as SourceTitle. Title is the human-facing book name.
	displayName := map[string]string{
		"da-xue":          "Da Xue 大學",
		"zhong-yong":      "Zhong Yong 中庸",
		"lunyu":           "Lunyu 論語",
		"mengzi":          "Mengzi 孟子",
		"daodejing":       "Daodejing 道德經",
		"sunzi-bingfa":    "Sunzi Bingfa 孫子兵法",
		"san-zi-jing":     "San Zi Jing 三字經",
		"qian-zi-wen":     "Qian Zi Wen 千字文",
		"sanguo-yanyi":    "Sanguo Yanyi 三國演義",
		"chengyu-catalog": "Chengyu Catalog 成語目錄",
	}
	var books []Book
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		slug := e.Name()
		cat, err := s.loadCatalog(slug)
		if err != nil {
			return nil, err
		}
		b := Book{
			Slug:         slug,
			Title:        firstNonEmpty(displayName[slug], stringFrom(cat["title"]), slug),
			ChapterCount: intFrom(cat["chapter_count"]),
			SourceTitle:  stringFrom(cat["source_title"]),
			PedagogyNote: stringFrom(cat["pedagogy_note"]),
			V1:           v1[slug],
		}
		books = append(books, b)
	}
	sort.SliceStable(books, func(i, j int) bool {
		return order[books[i].Slug] < order[books[j].Slug]
	})
	return books, nil
}

// Chapter is a loaded chapter payload (shape matches the JSON files).
type Chapter struct {
	Chapter struct {
		ID              string       `json:"id"`
		Order           int          `json:"order"`
		Title           string       `json:"title"`
		Summary         string       `json:"summary"`
		Text            string       `json:"text"`
		CharacterCount  int          `json:"character_count"`
		ReadingUnitCount int         `json:"reading_unit_count"`
		ReadingUnits    []ReadingUnit `json:"reading_units"`
	} `json:"chapter"`
	Provider      string `json:"provider"`
	SourceTitle   string `json:"source_title"`
	SourceURL     string `json:"source_url"`
	SchemaVersion int    `json:"schema_version"`
}

// ReadingUnit is one line (the atomic content unit).
type ReadingUnit struct {
	ID          string                 `json:"id"`
	Order       int                    `json:"order"`
	Text        string                 `json:"text"`
	Pinyin      string                 `json:"pinyin,omitempty"`
	PinyinSource string                `json:"pinyin_source,omitempty"`
	CharacterCount int                 `json:"character_count"`
	CanonicalTranslations []CanonicalTranslation `json:"canonical_translations"`
}

// CanonicalTranslation is a seeded (public-domain) translation of a line.
type CanonicalTranslation struct {
	Translator string `json:"translator"`
	Year       int    `json:"year,omitempty"`
	License    string `json:"license"`
	SourceURL  string `json:"source_url"`
	Text       string `json:"text"`
}

// Chapter loads one chapter, with a simple in-memory cache.
func (s *Service) Chapter(book, chapterID string) (*Chapter, error) {
	key := book + "/" + chapterID
	s.mu.RLock()
	if c, ok := s.chapterLRU[key]; ok {
		s.mu.RUnlock()
		return c, nil
	}
	s.mu.RUnlock()

	path := filepath.Join(s.root, "books", book, "chapters", chapterID+".json")
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("content: read chapter: %w", err)
	}
	var ch Chapter
	if err := json.Unmarshal(data, &ch); err != nil {
		return nil, fmt.Errorf("content: parse chapter %s: %w", path, err)
	}

	s.mu.Lock()
	s.chapterLRU[key] = &ch
	s.mu.Unlock()
	return &ch, nil
}

// ErrNotFound is returned for missing books/chapters.
var ErrNotFound = fmt.Errorf("content: not found")

// LineTotals returns the canonical reading-unit count for every book. Used by
// the dashboard to compute "% read". Cached after first call.
func (s *Service) LineTotals() (map[string]int, error) {
	s.mu.RLock()
	if s.lineTotals != nil {
		out := make(map[string]int, len(s.lineTotals))
		for k, v := range s.lineTotals {
			out[k] = v
		}
		s.mu.RUnlock()
		return out, nil
	}
	s.mu.RUnlock()

	entries, err := os.ReadDir(filepath.Join(s.root, "books"))
	if err != nil {
		return nil, fmt.Errorf("content: line totals: %w", err)
	}
	totals := make(map[string]int)
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		book := e.Name()
		chDir := filepath.Join(s.root, "books", book, "chapters")
		files, err := os.ReadDir(chDir)
		if err != nil {
			continue
		}
		total := 0
		for _, f := range files {
			if f.IsDir() {
				continue
			}
			ch, err := s.Chapter(book, f.Name()[:len(f.Name())-len(".json")])
			if err != nil {
				continue
			}
			total += len(ch.Chapter.ReadingUnits)
		}
		totals[book] = total
	}
	s.mu.Lock()
	s.lineTotals = totals
	s.mu.Unlock()
	return totals, nil
}

// --- helpers for loosely-typed catalog.json --------------------------------

func (s *Service) loadCatalog(book string) (map[string]any, error) {
	path := filepath.Join(s.root, "books", book, "catalog.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("content: read catalog for %s: %w", book, err)
	}
	var m map[string]any
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, fmt.Errorf("content: parse catalog %s: %w", book, err)
	}
	return m, nil
}

func firstNonEmpty(s ...string) string {
	for _, v := range s {
		if v != "" {
			return v
		}
	}
	return ""
}

func intFrom(v any) int {
	if n, ok := v.(float64); ok {
		return int(n)
	}
	return 0
}

func stringFrom(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}
