// Package feedback implements the posit-feedback loop: a user submits a draft
// English translation of a Classical Chinese line, and the GLM model returns
// structured feedback. This is the product's wedge feature.
//
// Discipline (the lesson from the chengyu MT corruption): the prompt is
// governed by a project glossary for key philosophical terms so the model's
// feedback is consistent and doesn't free-translate 仁/道/德/etc. Temperature
// is low (0.2). Output is a JSON object we validate.
package feedback

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"thebiglearn/api/internal/zai"
)

// Posit is the input: the user's attempt + the source line context.
type Posit struct {
	SourceLine  string   // Chinese text
	Pinyin      string   // if available
	Canonical   []string // seeded translations, for comparison
	UserAttempt string   // the user's draft English
}

// Result is the structured feedback returned to the user.
type Result struct {
	CharsCorrect    string   `json:"chars_correct"`     // "all / most / some / few"
	Grammar         string   `json:"grammar"`           // short note
	KeyTerms        []TermNote `json:"key_terms"`
	Suggested       string   `json:"suggested"`         // a model-suggested rendering (for comparison only)
	Encouragement   string   `json:"encouragement"`     // a single sentence
}

// TermNote is feedback on a specific philosophical term's handling.
type TermNote struct {
	Term     string `json:"term"`      // 仁, 道, etc.
	UserDid  string `json:"user_did"`  // how the user rendered it
	Comment  string `json:"comment"`   // one-line guidance
}

// GlossaryEntry pins how we want the model to treat key terms.
type GlossaryEntry struct {
	Term    string
	ROM     string // preferred romanization: ren
	Gloss   string // preferred gloss: "humaneness" / "goodness"
}

// ProjectGlossary governs key philosophical terms. The model is instructed to
// flag when a user's rendering diverges from these, not to silently accept
// loose translations. This is the guard against the "profit"-style distortion
// that Legge's Mengzi suffers from.
var ProjectGlossary = []GlossaryEntry{
	{Term: "仁", ROM: "rén", Gloss: "humaneness / benevolence (Confucius's central virtue)"},
	{Term: "義", ROM: "yì", Gloss: "rightness / righteousness"},
	{Term: "禮", ROM: "lǐ", Gloss: "ritual propriety / rites"},
	{Term: "智", ROM: "zhì", Gloss: "wisdom"},
	{Term: "信", ROM: "xìn", Gloss: "trustworthiness / good faith"},
	{Term: "道", ROM: "dào", Gloss: "the Way (path, method, ultimate reality)"},
	{Term: "德", ROM: "dé", Gloss: "virtue / power (moral force)"},
	{Term: "君子", ROM: "jūnzǐ", Gloss: "the gentleman / noble person (exemplary moral agent)"},
	{Term: "天", ROM: "tiān", Gloss: "Heaven (cosmic-moral order)"},
	{Term: "性", ROM: "xìng", Gloss: "nature (innate endowment)"},
}

// Service wraps the z.ai client.
type Service struct {
	client *zai.Client
	model  string
}

// New constructs a feedback service. Returns nil-safe behavior if client nil.
func New(client *zai.Client, model string) *Service {
	return &Service{client: client, model: strings.TrimSpace(model)}
}

// ErrNotConfigured is returned when no GLM key is configured.
var ErrNotConfigured = errors.New("feedback: GLM not configured (set GLM_API_KEY)")

// Evaluate sends a posit to the model and returns structured feedback.
func (s *Service) Evaluate(ctx context.Context, p Posit) (Result, error) {
	if s.client == nil || !s.client.Configured() {
		return Result{}, ErrNotConfigured
	}
	if strings.TrimSpace(p.UserAttempt) == "" {
		return Result{}, errors.New("feedback: empty user attempt")
	}

	resp, err := s.client.ChatCompletion(ctx, zai.ChatCompletionRequest{
		Model: s.model,
		Messages: []zai.Message{
			{Role: "system", Content: systemPrompt()},
			{Role: "user", Content: buildUserPrompt(p)},
		},
		Temperature: 0.2,
		ResponseFormat: &zai.ResponseFormat{Type: "json_object"},
	})
	if err != nil {
		return Result{}, fmt.Errorf("feedback: llm call: %w", err)
	}

	raw := extractJSONObject(resp.FirstMessageContent())
	if raw == "" {
		return Result{}, errors.New("feedback: empty model response")
	}

	var r Result
	if err := json.Unmarshal([]byte(raw), &r); err != nil {
		return Result{}, fmt.Errorf("feedback: decode: %w (raw: %s)", err, snippet(raw))
	}
	return r, nil
}

func systemPrompt() string {
	var b strings.Builder
	b.WriteString("You are a tutor giving private feedback on a learner's English translation ")
	b.WriteString("of a Classical Chinese line. Be specific, honest, and kind. ")
	b.WriteString("Evaluate character-by-character accuracy, grammar, and how the learner ")
	b.WriteString("handled key philosophical terms. ")
	b.WriteString("Return STRICT JSON only (no markdown fences) with these keys: ")
	b.WriteString(`"chars_correct" (one of: all|most|some|few), `)
	b.WriteString(`"grammar" (one short sentence), `)
	b.WriteString(`"key_terms" (array of {term, user_did, comment} for any of the glossary terms present), `)
	b.WriteString(`"suggested" (your own rendering, for comparison — frame as one option not THE answer), `)
	b.WriteString(`"encouragement" (one sentence).`)

	b.WriteString("\n\nProject glossary (flag when the learner's rendering diverges; do not punish considered choices):\n")
	for _, g := range ProjectGlossary {
		fmt.Fprintf(&b, "- %s (%s): %s\n", g.Term, g.ROM, g.Gloss)
	}
	return b.String()
}

func buildUserPrompt(p Posit) string {
	var b strings.Builder
	b.WriteString("Source line (Classical Chinese):\n")
	b.WriteString(p.SourceLine)
	b.WriteString("\n")
	if p.Pinyin != "" {
		b.WriteString("Pinyin: " + p.Pinyin + "\n")
	}
	if len(p.Canonical) > 0 {
		b.WriteString("Canonical reference translation(s) (Legge, public domain — for comparison only):\n")
		for _, c := range p.Canonical {
			b.WriteString("  - " + c + "\n")
		}
	}
	b.WriteString("\nLearner's attempted translation:\n")
	b.WriteString(p.UserAttempt)
	b.WriteString("\n\nReturn the JSON feedback object now.")
	return b.String()
}

func extractJSONObject(raw string) string {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return ""
	}
	if strings.HasPrefix(trimmed, "```") {
		trimmed = strings.TrimPrefix(trimmed, "```json")
		trimmed = strings.TrimPrefix(trimmed, "```JSON")
		trimmed = strings.TrimPrefix(trimmed, "```")
		trimmed = strings.TrimSuffix(trimmed, "```")
		trimmed = strings.TrimSpace(trimmed)
	}
	start := strings.Index(trimmed, "{")
	end := strings.LastIndex(trimmed, "}")
	if start >= 0 && end >= start {
		return trimmed[start : end+1]
	}
	return trimmed
}

func snippet(s string) string {
	if len(s) > 200 {
		return s[:200] + "..."
	}
	return s
}
