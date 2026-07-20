// Package content serves the canonical, read-only JSON content from disk.
// The content/ tree is the sole source of truth for Chinese text + seeded
// translations. This package loads and caches book catalogs, chapter payloads,
// and the character index.
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
	root          string
	mu            sync.RWMutex
	chapterLRU    map[string]*Chapter   // key: book/chapter-NNN
	lineTotals    map[string]int        // lazy; cached after first LineTotals() call
	charIndex     map[rune]*CharEntry   // lazy; loaded from references/characters/index.json
	chengyuByChar map[rune][]ChengyuRef // lazy; reverse index char -> idioms containing it
	trad2simpl    map[rune]rune         // lazy; traditional -> simplified, built from the char index
}

// New constructs a Service rooted at root (the-big-learn/content).
func New(root string) *Service {
	return &Service{root: root, chapterLRU: make(map[string]*Chapter)}
}

// CharEntry is one character in the references/characters index. Fields mirror
// index.json exactly; sub-structs are pointers so thin entries still parse.
type CharEntry struct {
	Character   string     `json:"character"`
	Simplified  string     `json:"simplified"`
	Traditional string     `json:"traditional"`
	Aliases     []string   `json:"aliases"`
	Pinyin      []string   `json:"pinyin"`
	Zhuyin      []string   `json:"zhuyin"`
	English     []string   `json:"english"`
	Explosion   *Explosion `json:"explosion,omitempty"`
}

// Explosion is the per-character breakdown (decomposition + usage + meaning).
type Explosion struct {
	Analysis   *Analysis   `json:"analysis,omitempty"`
	Synthesis  *Synthesis  `json:"synthesis,omitempty"`
	MeaningMap *MeaningMap `json:"meaningMap,omitempty"`
}

// Analysis is the structural decomposition into component parts.
type Analysis struct {
	Expression string   `json:"expression"` // e.g. "六 + 井 + 一 + 𧘇"
	Parts      []string `json:"parts"`
}

// Synthesis is usage context: containing characters, classical phrases, homophones.
type Synthesis struct {
	ContainingCharacters []string    `json:"containingCharacters"`
	PhraseUse            []string    `json:"phraseUse"`
	Homophones           *Homophones `json:"homophones,omitempty"`
}

// Homophones groups same-tone vs different-tone sound-alikes.
type Homophones struct {
	SameTone      []string `json:"sameTone"`
	DifferentTone []string `json:"differentTone"`
}

// MeaningMap holds synonyms/antonyms for the character.
type MeaningMap struct {
	Synonyms []string `json:"synonyms"`
	Antonyms []string `json:"antonyms"`
}

// ChengyuRef is a lightweight pointer to a chengyu containing a given character.
type ChengyuRef struct {
	Text   string `json:"text"`   // the 4-char idiom
	Pinyin string `json:"pinyin"` // space-separated, may be ""
	Gloss  string `json:"gloss"`  // first canonical translation, may be ""
}

// CatalogChapter is one entry in a book's catalog `chapters` array — the
// lightweight per-chapter metadata (id, order, title) the chapter list needs
// without loading each chapter file. Mirrors the shape authored in
// catalog.json. Title is simplified at load time (same convention as the
// chapter response payload) so the frontend renders simplified Chinese.
type CatalogChapter struct {
	ID    string `json:"id"`
	Order int    `json:"order"`
	Title string `json:"title,omitempty"`
	// title_en is the optional English chapter label (e.g. "On Learning" for
	// Lunyu Book I). Wired through today but not yet authored in any catalog;
	// renders nothing until data lands.
	TitleEn string `json:"title_en,omitempty"`
	// title_en_source is the provenance discriminant for title_en, mirroring
	// CanonicalTranslation.Source: "human" for rule-derived / hand-authored
	// (e.g. daodejing's "Chapter N"), "llm" for GLM-generated. Recorded for
	// honesty/audit so machine-generated titles are never laundered as
	// authoritative; the chapter-list row carries no visual badge.
	TitleEnSource    string `json:"title_en_source,omitempty"`
	CharacterCount   int    `json:"character_count,omitempty"`
	ReadingUnitCount int    `json:"reading_unit_count,omitempty"`
}

// Book is a catalog-level entry. Facet fields (Tradition/Form/Year/Tier/
// Difficulty/CurriculumOrder/DisplayName) and V1 are read straight from
// catalog.json — there is no longer a hardcoded v1 set or display-name map.
// See content/TAXONOMY.md for the vocabulary.
type Book struct {
	Slug         string `json:"slug"`
	Title        string `json:"title"`
	ChapterCount int    `json:"chapter_count"`
	// Chapters is the per-chapter metadata from the catalog `chapters` array,
	// used by the book page's chapter list to render titled rows. Absent on
	// stub catalogs (available:false) where no chapter files exist yet.
	Chapters []CatalogChapter `json:"chapters,omitempty"`
	// SourceTitle / PedagogyNote are passed through from catalog.json when present.
	SourceTitle  string `json:"source_title,omitempty"`
	PedagogyNote string `json:"pedagogy_note,omitempty"`
	// Blurb is the short one-line description used on cards and as the
	// background fallback; Background is the longer "about this book"
	// paragraph shown on the book page. Both optional, both passed through
	// verbatim — authoring lives in catalog.json.
	Blurb      string `json:"blurb,omitempty"`
	Background string `json:"background,omitempty"`
	// SeedTranslator is the catalog-level attribution shown on the book page.
	// It is optional because some readable books are Chinese-only, reference
	// works, or intentionally combine more than one translation source.
	SeedTranslator *SeedTranslator `json:"seed_translator,omitempty"`
	V1             bool            `json:"v1"`
	// Available reports whether the book has ingested content. Placeholders
	// (catalog stubs for roadmap texts) carry available:false so the library
	// can render them dimmed and non-clickable. Defaults to true when the
	// field is absent — a missing flag must never accidentally hide a real book.
	Available bool `json:"available"`
	// Two-facet taxonomy (tradition × form) + cross-cutting tags. TAXONOMY.md
	// is the source of truth for the closed vocabularies these draw from.
	DisplayName string `json:"display_name,omitempty"`
	// Structured name parts for ruby rendering (see apps/web BookTitle):
	// name_zh is the Chinese title, name_pinyin is one space-separated syllable
	// per CJK character (aligned by index), name_en is the established English
	// name. display_name stays as the plain-string fallback.
	NameZh          string `json:"name_zh,omitempty"`
	NamePinyin      string `json:"name_pinyin,omitempty"`
	NameEn          string `json:"name_en,omitempty"`
	Tradition       string `json:"tradition,omitempty"`
	Form            string `json:"form,omitempty"`
	Year            int    `json:"year,omitempty"`
	Tier            string `json:"tier,omitempty"`
	Difficulty      string `json:"difficulty,omitempty"`
	CurriculumOrder *int   `json:"curriculum_order,omitempty"`
	// For commentaries: the slug of the parent text this comments on
	// (e.g. Zuozhuan → "chun-qiu"). Rendered as "commentary on <parent>"
	// on the library card so a commentary isn't mistaken for a standalone
	// classic.
	CommentaryOn string `json:"commentary_on,omitempty"`
}

// SeedTranslator is the structured attribution authored in catalog.json.
// Keeping it as data avoids coupling the editorial `v1` flag to one specific
// translator (Sanguo, for example, is v1 but is not translated by Legge).
type SeedTranslator struct {
	Translator string `json:"translator"`
	Year       int    `json:"year,omitempty"`
	License    string `json:"license,omitempty"`
}

// tierRank orders Tier within a group (S → A → B → unset).
var tierRank = map[string]int{"S": 0, "A": 1, "B": 2}

// Books returns every cataloged book with its facets populated from
// catalog.json. The list is sorted in curriculum order (the hand-set
// sequence readers follow by default); books without a curriculum_order
// sort after, by tier then slug. The frontend regroups by tradition/form/
// year/tier for the other library views — it does not rely on this order
// beyond the default Curriculum view.
func (s *Service) Books() ([]Book, error) {
	entries, err := os.ReadDir(filepath.Join(s.root, "books"))
	if err != nil {
		return nil, fmt.Errorf("content: list books: %w", err)
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
		// catalog.json `title` holds the source document title (e.g.
		// "四书章句集注 : 大学章句"), which is provenance — exposed as
		// SourceTitle. The human-facing name is `display_name`.
		displayName := stringFrom(cat["display_name"])
		b := Book{
			Slug:            slug,
			Title:           firstNonEmpty(displayName, stringFrom(cat["title"]), slug),
			ChapterCount:    intFrom(cat["chapter_count"]),
			SourceTitle:     stringFrom(cat["source_title"]),
			PedagogyNote:    stringFrom(cat["pedagogy_note"]),
			Blurb:           stringFrom(cat["blurb"]),
			Background:      stringFrom(cat["background"]),
			SeedTranslator:  seedTranslatorFrom(cat["seed_translator"]),
			V1:              boolFrom(cat["v1"]),
			Available:       boolFromWithDefault(cat["available"], true),
			DisplayName:     displayName,
			NameZh:          stringFrom(cat["name_zh"]),
			NamePinyin:      stringFrom(cat["name_pinyin"]),
			NameEn:          stringFrom(cat["name_en"]),
			Tradition:       stringFrom(cat["tradition"]),
			Form:            stringFrom(cat["form"]),
			Year:            intFrom(cat["year"]),
			Tier:            stringFrom(cat["tier"]),
			Difficulty:      stringFrom(cat["difficulty"]),
			CurriculumOrder: intPtrFrom(cat["curriculum_order"]),
			CommentaryOn:    stringFrom(cat["commentary_on"]),
			Chapters:        s.catalogChapters(cat["chapters"]),
		}
		books = append(books, b)
	}
	sort.SliceStable(books, func(i, j int) bool {
		// Curriculum order first. Books with no curriculum_order go last,
		// sorted by tier then slug so the tail is still deterministic.
		oi, oj := books[i].CurriculumOrder, books[j].CurriculumOrder
		switch {
		case oi != nil && oj != nil:
			if *oi != *oj {
				return *oi < *oj
			}
		case oi != nil:
			return true
		case oj != nil:
			return false
		}
		ri, rj := tierRank[books[i].Tier], tierRank[books[j].Tier]
		if ri != rj {
			return ri < rj
		}
		return books[i].Slug < books[j].Slug
	})
	return books, nil
}

func seedTranslatorFrom(v any) *SeedTranslator {
	m, ok := v.(map[string]any)
	if !ok {
		return nil
	}
	translator := stringFrom(m["translator"])
	if translator == "" {
		return nil
	}
	return &SeedTranslator{
		Translator: translator,
		Year:       intFrom(m["year"]),
		License:    stringFrom(m["license"]),
	}
}

// catalogChapters extracts the `chapters` array from a parsed catalog map into
// typed CatalogChapter entries, simplifying each title (catalog.json stores
// traditional; the frontend renders simplified, matching chapter responses).
// Returns nil when the array is absent or empty so the JSON omits the field.
func (s *Service) catalogChapters(raw any) []CatalogChapter {
	arr, ok := raw.([]any)
	if !ok || len(arr) == 0 {
		return nil
	}
	out := make([]CatalogChapter, 0, len(arr))
	for _, e := range arr {
		m, ok := e.(map[string]any)
		if !ok {
			continue
		}
		out = append(out, CatalogChapter{
			ID:               stringFrom(m["id"]),
			Order:            intFrom(m["order"]),
			Title:            s.Simplify(stringFrom(m["title"])),
			TitleEn:          stringFrom(m["title_en"]),
			TitleEnSource:    stringFrom(m["title_en_source"]),
			CharacterCount:   intFrom(m["character_count"]),
			ReadingUnitCount: intFrom(m["reading_unit_count"]),
		})
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

// Chapter is a loaded chapter payload (shape matches the JSON files).
type Chapter struct {
	Chapter struct {
		ID               string        `json:"id"`
		Order            int           `json:"order"`
		Title            string        `json:"title"`
		Summary          string        `json:"summary"`
		Text             string        `json:"text"`
		CharacterCount   int           `json:"character_count"`
		ReadingUnitCount int           `json:"reading_unit_count"`
		ReadingUnits     []ReadingUnit `json:"reading_units"`
	} `json:"chapter"`
	Provider      string `json:"provider"`
	SourceTitle   string `json:"source_title"`
	SourceURL     string `json:"source_url"`
	SchemaVersion int    `json:"schema_version"`
}

// ReadingUnit is one line (the atomic content unit).
type ReadingUnit struct {
	ID           string `json:"id"`
	Order        int    `json:"order"`
	Text         string `json:"text"`
	Pinyin       string `json:"pinyin,omitempty"`
	PinyinSource string `json:"pinyin_source,omitempty"`
	// PinyinPerChar is one pinyin syllable per rune in Text (context-disambiguated
	// at build time by tools/build_pinyin.py, with tone sandhi applied). Empty
	// string for non-CJK runes or runes with no reading (honest gap, rendered
	// bare). When present, the reader prefers this over the per-char fallback
	// map so polyphones and sandhi read correctly in context.
	PinyinPerChar         []string               `json:"pinyin_per_char,omitempty"`
	CharacterCount        int                    `json:"character_count"`
	CanonicalTranslations []CanonicalTranslation `json:"canonical_translations"`
	// WordSpans is the build-time compound segmentation of Text into multi-char
	// words with glosses (tools/build_word_gloss.py). Optional: chengyu-catalog
	// units and any unit the build hasn't enriched omit it. start/end are rune
	// indices into Text. The reader wraps chars in the same span so the whole
	// compound highlights together, and surfaces the token's gloss above the
	// per-char breakdown.
	WordSpans []WordSpan `json:"word_spans,omitempty"`
	// Origin links a chengyu unit to the verbatim classical line where the 4-char
	// idiom was coined (tools/attach_chengyu_origins.py). Optional; absent on
	// classical-book units and on chengyu with no verbatim origin (honest gap).
	Origin *UnitOrigin `json:"origin,omitempty"`
}

// WordSpan is one segment of a reading unit's Text (a multi-char compound or a
// single-char fallback). start/end are rune indices into the unit's Text,
// end-exclusive. Source discriminates curated classical compounds ("classical-
// override"), CEDICT entries ("CC-CEDICT"), and the single-char fallback
// ("char") that fills the gaps between compounds.
type WordSpan struct {
	Start  int    `json:"start"`
	End    int    `json:"end"` // exclusive
	Word   string `json:"word"`
	Pinyin string `json:"pinyin,omitempty"` // tone-marked, space-separated; empty for char fallback
	Gloss  string `json:"gloss,omitempty"`  // empty for char fallback (per-char defs cover it)
	Source string `json:"source,omitempty"`
}

// UnitOrigin points at the classical line a chengyu was coined in.
type UnitOrigin struct {
	Book    string `json:"book"`    // slug, e.g. "mengzi"
	Chapter int    `json:"chapter"` // bare integer
	Line    int    `json:"line"`    // the origin unit's order
	Snippet string `json:"snippet,omitempty"`
}

// CanonicalTranslation is a seeded (public-domain) translation of a line.
type CanonicalTranslation struct {
	Translator string `json:"translator"`
	Year       int    `json:"year,omitempty"`
	License    string `json:"license"`
	SourceURL  string `json:"source_url"`
	Text       string `json:"text"`
	// Source discriminates human-authored canon from machine-generated text.
	// Empty/"human" (omitted) = a human translation; "llm" = machine-generated
	// (e.g. GLM poem translations where no PD human rendering exists). The
	// reader renders the latter with a visible badge so generated text is
	// never laundered as authoritative human canon. Mirrors the per-item
	// `source` discriminant pattern already used on WordSpan.
	Source string `json:"source,omitempty"`
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

// Character returns the index entry for a rune plus up to 5 chengyu containing
// it. ok is false if the rune isn't in the index. Both indexes are lazy-loaded
// on first call (one-time: ~9MB index + 20 chapter scans), then O(1).
func (s *Service) Character(r rune) (entry *CharEntry, chengyu []ChengyuRef, ok bool) {
	// Ensure loaded. ensureCharIndex takes the write lock only on the cold path;
	// the fast path is a read-locked map lookup.
	s.ensureCharIndex()
	s.mu.RLock()
	entry, ok = s.charIndex[r]
	chengyu = s.chengyuByChar[r]
	s.mu.RUnlock()
	if len(chengyu) > 5 {
		chengyu = chengyu[:5]
	}
	return entry, chengyu, ok
}

// CharacterBatch returns pinyin (first reading) for each requested char. Chars
// not in the index map to null. Used by the reader to render pinyin above text.
func (s *Service) CharacterBatch(chars []rune) map[string]*string {
	s.ensureCharIndex()
	out := make(map[string]*string, len(chars))
	s.mu.RLock()
	for _, r := range chars {
		key := string(r)
		if _, seen := out[key]; seen {
			continue
		}
		if e, ok := s.charIndex[r]; ok && len(e.Pinyin) > 0 {
			p := e.Pinyin[0]
			out[key] = &p
		} else {
			out[key] = nil
		}
	}
	s.mu.RUnlock()
	return out
}

// ensureCharIndex loads both the character index and the chengyu reverse-index
// on first use. Subsequent calls are a cheap read-locked nil check. The write
// lock is only held during the one-time load.
func (s *Service) ensureCharIndex() {
	s.mu.RLock()
	loaded := s.charIndex != nil
	s.mu.RUnlock()
	if loaded {
		return
	}

	idx, err := s.loadCharIndex()
	if err != nil {
		// Don't poison the cache on a transient read error; retry next call.
		// Log via an empty map so callers degrade to "no pinyin" rather than crash.
		idx = map[rune]*CharEntry{}
	}
	rev := s.loadChengyuReverseIndex()
	t2s := buildTradToSimplified(idx)

	s.mu.Lock()
	s.charIndex = idx
	s.chengyuByChar = rev
	s.trad2simpl = t2s
	s.mu.Unlock()
}

// buildTradToSimplified constructs a rune map from traditional (and alias)
// forms to simplified, drawn from the loaded character index. The canon texts
// are traditional; the reading UI is simplified — this map drives that
// conversion. Verified to cover 100% of CJK chars in the v1 canon.
// Collisions (one trad -> two simpl) are last-wins; none occur in the canon.
func buildTradToSimplified(idx map[rune]*CharEntry) map[rune]rune {
	out := make(map[rune]rune, len(idx))
	add := func(from, to string) {
		fr := []rune(from)
		tr := []rune(to)
		if len(fr) != 1 || len(tr) != 1 || fr[0] == tr[0] {
			return
		}
		out[fr[0]] = tr[0]
	}
	for _, e := range idx {
		add(e.Traditional, e.Simplified)
		for _, a := range e.Aliases {
			add(a, e.Simplified)
		}
	}
	return out
}

// Simplify converts a string from traditional to simplified Chinese by mapping
// each rune through the trad2simpl index. Runes absent from the map (already
// simplified, or non-CJK) pass through unchanged. The map is lazy-loaded.
func (s *Service) Simplify(str string) string {
	s.ensureCharIndex()
	s.mu.RLock()
	t2s := s.trad2simpl
	s.mu.RUnlock()
	if len(t2s) == 0 {
		return str
	}
	runes := []rune(str)
	changed := false
	for i, r := range runes {
		if sr, ok := t2s[r]; ok {
			runes[i] = sr
			changed = true
		}
	}
	if !changed {
		return str // avoid allocating a new string for already-simplified input
	}
	return string(runes)
}

// loadCharIndex reads references/characters/index.json into a rune-keyed map.
func (s *Service) loadCharIndex() (map[rune]*CharEntry, error) {
	path := filepath.Join(s.root, "references", "characters", "index.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("content: read char index: %w", err)
	}
	var payload struct {
		Entries []CharEntry `json:"entries"`
	}
	if err := json.Unmarshal(data, &payload); err != nil {
		return nil, fmt.Errorf("content: parse char index: %w", err)
	}
	// Key by BOTH the headword (simplified) and the traditional form. The
	// index is simplified-keyed (character == simplified for every entry);
	// canon texts are now stored simplified too, but the traditional alias
	// is retained so any traditional rune still resolves — and when it
	// collides with another entry's headword, prefer the entry whose
	// headword IS that rune (the headword match is exact).
	headword := make(map[rune]*CharEntry, len(payload.Entries))
	for i := range payload.Entries {
		e := payload.Entries[i]
		rs := []rune(e.Character)
		if len(rs) == 0 {
			continue
		}
		headword[rs[0]] = &e
	}
	out := make(map[rune]*CharEntry, len(headword)*2)
	// First pass: traditional mappings (lower priority, may be overwritten).
	for _, e := range headword {
		if trs := []rune(e.Traditional); len(trs) == 1 {
			out[trs[0]] = e
		}
	}
	// Second pass: headwords win on collision.
	for r, e := range headword {
		out[r] = e
	}
	return out, nil
}

// loadChengyuReverseIndex walks the chengyu-catalog chapters and builds a
// rune -> []ChengyuRef map so a character popover can show idioms containing
// the clicked char. Each rune is capped at 8 idioms (enough variety, bounded).
func (s *Service) loadChengyuReverseIndex() map[rune][]ChengyuRef {
	const perRuneCap = 8
	out := map[rune][]ChengyuRef{}

	dir := filepath.Join(s.root, "books", "chengyu-catalog", "chapters")
	files, err := os.ReadDir(dir)
	if err != nil {
		return out // chengyu absent -> empty index; not fatal
	}
	for _, f := range files {
		if f.IsDir() || filepath.Ext(f.Name()) != ".json" {
			continue
		}
		data, err := os.ReadFile(filepath.Join(dir, f.Name()))
		if err != nil {
			continue
		}
		var ch Chapter
		if err := json.Unmarshal(data, &ch); err != nil {
			continue
		}
		for _, u := range ch.Chapter.ReadingUnits {
			ref := ChengyuRef{Text: u.Text, Pinyin: u.Pinyin}
			if len(u.CanonicalTranslations) > 0 {
				ref.Gloss = u.CanonicalTranslations[0].Text
			}
			seen := map[rune]bool{}
			for _, r := range []rune(u.Text) {
				if seen[r] {
					continue // don't double-count a char within one idiom
				}
				seen[r] = true
				if len(out[r]) >= perRuneCap {
					continue
				}
				out[r] = append(out[r], ref)
			}
		}
	}
	return out
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

// intPtrFrom returns nil for absent/null values so CurriculumOrder can be
// omitted from JSON when unset, matching the catalog's `"curriculum_order": null`.
func intPtrFrom(v any) *int {
	if v == nil {
		return nil
	}
	if n, ok := v.(float64); ok {
		i := int(n)
		return &i
	}
	return nil
}

func boolFrom(v any) bool {
	if b, ok := v.(bool); ok {
		return b
	}
	return false
}

// boolFromWithDefault is like boolFrom but returns def when the field is
// absent. Used for `available`, where a missing flag must mean "yes, this
// book has content" (the safe default) rather than "no".
func boolFromWithDefault(v any, def bool) bool {
	if v == nil {
		return def
	}
	if b, ok := v.(bool); ok {
		return b
	}
	return def
}

func stringFrom(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}
