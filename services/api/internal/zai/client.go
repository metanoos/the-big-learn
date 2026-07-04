// Package zai is a thin client for the GLM/z.ai Anthropic-compatible Messages
// API. Ported from da-xue/services/api/internal/zai (same surface, new module
// path) so the posit-feedback endpoint reuses the proven integration.
package zai

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"
)

// ErrNotConfigured is returned when no API key is set.
var ErrNotConfigured = errors.New("zai: missing GLM_API_KEY")

// Message is one chat message.
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ResponseFormat requests structured output.
type ResponseFormat struct {
	Type string `json:"type"` // "json_object" | "text"
}

// ChatCompletionRequest mirrors the fields we use.
type ChatCompletionRequest struct {
	Model          string          `json:"model"`
	Messages       []Message       `json:"messages"`
	Temperature    float64         `json:"temperature,omitempty"`
	MaxTokens      int             `json:"max_tokens,omitempty"`
	ResponseFormat *ResponseFormat `json:"response_format,omitempty"`
}

// ChatCompletionResponse is the trimmed response shape.
type ChatCompletionResponse struct {
	Content string `json:"-"` // populated from the API body
	raw     string
}

// FirstMessageContent returns the assistant message text.
func (r ChatCompletionResponse) FirstMessageContent() string { return r.Content }

// Client talks to the Anthropic-compatible endpoint.
type Client struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client

	// Serialize calls so we don't hammer the API during a backfill; for the
	// feedback endpoint (one call per user action) this is a non-issue, but
	// the serialization also bounds concurrency cheaply.
	mu chan struct{}
}

// NewClient returns a client. apiKey empty -> ErrNotConfigured on call.
func NewClient(apiKey, baseURL string, httpClient *http.Client) *Client {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 60 * time.Second}
	}
	// Bounded concurrency (8 in flight). Feedback calls are rare; this mostly
	// exists to mirror da-xue's discipline.
	return &Client{
		apiKey:     strings.TrimSpace(apiKey),
		baseURL:    strings.TrimRight(strings.TrimSpace(baseURL), "/"),
		httpClient: httpClient,
		mu:         make(chan struct{}, 8),
	}
}

// Configured reports whether the client can make calls.
func (c *Client) Configured() bool { return c != nil && c.apiKey != "" }

// ChatCompletion performs one Messages-API call.
func (c *Client) ChatCompletion(ctx context.Context, req ChatCompletionRequest) (ChatCompletionResponse, error) {
	if !c.Configured() {
		return ChatCompletionResponse{}, ErrNotConfigured
	}
	if req.Model == "" {
		return ChatCompletionResponse{}, errors.New("zai: missing model")
	}

	select {
	case c.mu <- struct{}{}:
	case <-ctx.Done():
		return ChatCompletionResponse{}, ctx.Err()
	}
	defer func() { <-c.mu }()

	body, err := buildAnthropicRequest(req)
	if err != nil {
		return ChatCompletionResponse{}, fmt.Errorf("zai: build request: %w", err)
	}

	url := c.baseURL + "/v1/messages"
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return ChatCompletionResponse{}, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("x-api-key", c.apiKey)
	httpReq.Header.Set("anthropic-version", "2023-06-01")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return ChatCompletionResponse{}, fmt.Errorf("zai: request: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return ChatCompletionResponse{}, fmt.Errorf("zai: read body: %w", err)
	}
	if resp.StatusCode >= 400 {
		return ChatCompletionResponse{}, fmt.Errorf("zai: HTTP %d: %s", resp.StatusCode, snippet(string(raw)))
	}

	content, err := extractAssistantContent(raw)
	if err != nil {
		return ChatCompletionResponse{}, fmt.Errorf("zai: decode: %w", err)
	}
	return ChatCompletionResponse{Content: content}, nil
}

func snippet(s string) string {
	if len(s) > 300 {
		return s[:300] + "..."
	}
	return s
}

// --- request/response shaping ---------------------------------------------

func buildAnthropicRequest(req ChatCompletionRequest) ([]byte, error) {
	// Anthropic Messages API splits system from the messages list.
	var system string
	var msgs []Message
	for _, m := range req.Messages {
		if m.Role == "system" {
			system = m.Content
			continue
		}
		msgs = append(msgs, m)
	}
	if system == "" {
		system = "You are a helpful assistant."
	}

	payload := map[string]any{
		"model":      req.Model,
		"max_tokens": maxOr(req.MaxTokens, 2048),
		"system":     system,
		"messages":   msgs,
	}
	if req.Temperature > 0 {
		payload["temperature"] = req.Temperature
	}
	if req.ResponseFormat != nil {
		payload["response_format"] = req.ResponseFormat
	}
	return json.Marshal(payload)
}

func maxOr(v, fallback int) int {
	if v > 0 {
		return v
	}
	return fallback
}

// extractAssistantContent pulls the text out of the Anthropic content blocks.
func extractAssistantContent(raw []byte) (string, error) {
	var resp struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
	}
	if err := json.Unmarshal(raw, &resp); err != nil {
		return "", err
	}
	var sb strings.Builder
	for _, b := range resp.Content {
		if b.Type == "text" {
			sb.WriteString(b.Text)
		}
	}
	return sb.String(), nil
}

// once guards compile-time that sync is used.
var _ = sync.Once{}
