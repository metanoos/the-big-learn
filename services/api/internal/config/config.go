// Package config loads runtime configuration from the environment and .env.
//
// All knobs are env-driven so the same binary runs locally (docker-compose
// Postgres on :5433), on a VPS (Postgres in the same compose), or anywhere
// else — no compile-time choices.
package config

import (
	"fmt"
	"log"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"thebiglearn/api/internal/storage"
)

// Config is the resolved runtime configuration.
type Config struct {
	// Server
	HTTPAddr string // ":8080"

	// Postgres
	DatabaseURL string // "postgres://tbl:tbl_dev@localhost:5433/thebiglearn?sslmode=disable"

	// Content root (the-big-learn/content)
	ContentRoot string

	// Auth
	JWTSecret       string
	SessionCookieName string

	// GLM / z.ai (for the posit-feedback loop)
	GLMAPIKey  string
	GLMBaseURL string // Anthropic-compatible endpoint
	GLMModel   string

	// Trust/safety
	FeedbackHourlyPerUser int // LLM feedback rate limit (legacy field, kept for logs)
	RateLimits            map[string]int

	// Email verification
	AppURL    string // public base URL for verification links
	SMTPHost  string
	SMTPPort  int
	SMTPUser  string
	SMTPPass  string
	SMTPFrom  string
}

// Load reads env vars, falling back to defaults appropriate for local dev.
// Exits the process if a required value (DatabaseURL) is missing.
func Load() Config {
	loadDotEnv() // best-effort, doesn't override existing env

	c := Config{
		HTTPAddr:              env("HTTP_ADDR", ":8080"),
		DatabaseURL:           env("DATABASE_URL", "postgres://tbl:tbl_dev@localhost:5433/thebiglearn?sslmode=disable"),
		ContentRoot:           env("CONTENT_ROOT", defaultContentRoot()),
		JWTSecret:             env("JWT_SECRET", ""),
		SessionCookieName:     env("SESSION_COOKIE_NAME", "tbl_session"),
		GLMAPIKey:             env("GLM_API_KEY", ""),
		GLMBaseURL:            env("GLM_BASE_URL", "https://api.z.ai/api/anthropic"),
		GLMModel:              env("GLM_MODEL", "glm-4.6"),
		FeedbackHourlyPerUser: envInt("FEEDBACK_HOURLY_PER_USER", 20),
	}
	// Rate limits: start from defaults, allow env override per action.
	c.RateLimits = make(map[string]int, len(storage.DefaultLimits))
	for k, v := range storage.DefaultLimits {
		c.RateLimits[k] = v
	}
	c.RateLimits[storage.ActionFeedback] = envInt("RATE_LIMIT_FEEDBACK_HOURLY", c.FeedbackHourlyPerUser)
	c.RateLimits[storage.ActionPublishTrans] = envInt("RATE_LIMIT_PUBLISH_HOURLY", storage.DefaultLimits[storage.ActionPublishTrans])
	c.RateLimits[storage.ActionComment] = envInt("RATE_LIMIT_COMMENT_HOURLY", storage.DefaultLimits[storage.ActionComment])
	c.RateLimits[storage.ActionRegister] = envInt("RATE_LIMIT_REGISTER_HOURLY", storage.DefaultLimits[storage.ActionRegister])

	// Email verification. Empty SMTP_HOST -> dev mode (link logged to console).
	c.AppURL = env("APP_URL", "http://localhost:3000")
	c.SMTPHost = env("SMTP_HOST", "")
	c.SMTPPort = envInt("SMTP_PORT", 587)
	c.SMTPUser = env("SMTP_USER", "")
	c.SMTPPass = env("SMTP_PASS", "")
	c.SMTPFrom = env("SMTP_FROM", "The Big Learn <noreply@thebiglearn.app>")

	if c.JWTSecret == "" {
		// Local-dev default: NOT for production. Logged loudly.
		c.JWTSecret = "dev-insecure-secret-change-me"
		log.Println("config: WARNING using insecure default JWT_SECRET (local dev only)")
	}
	if c.GLMAPIKey == "" {
		log.Println("config: GLM_API_KEY not set; posit-feedback endpoint will return 503")
	}

	// Sanity-check the DSN parses.
	if _, err := url.Parse(c.DatabaseURL); err != nil {
		log.Fatalf("config: invalid DATABASE_URL: %v", err)
	}
	if _, err := os.Stat(c.ContentRoot); err != nil {
		log.Fatalf("config: CONTENT_ROOT not found: %v", err)
	}
	return c
}

// defaultContentRoot resolves the content dir relative to the binary's repo,
// so `go run ./cmd/server` from services/api Just Works without env config.
func defaultContentRoot() string {
	wd, err := os.Getwd()
	if err != nil {
		return "content"
	}
	// Prefer the first existing candidate so the right content loads whether
	// the binary runs from services/api (../../content) or the repo root
	// (./content).
	for _, candidate := range []string{
		filepath.Join(wd, "..", "..", "content"),
		filepath.Join(wd, "content"),
	} {
		if info, err := os.Stat(candidate); err == nil && info.IsDir() {
			return candidate
		}
	}
	return "content" // relative fallback; Load() existence check catches a miss
}

func env(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
		log.Printf("config: %s=%q is not an int, using default %d", key, v, fallback)
	}
	return fallback
}

// loadDotEnv reads .env if present. Does NOT override vars already in the
// environment (matches da-xue's convention).
func loadDotEnv() {
	paths := []string{".env", "../../.env"}
	for _, p := range paths {
		b, err := os.ReadFile(p)
		if err != nil {
			continue
		}
		for _, line := range strings.Split(string(b), "\n") {
			line = strings.TrimSpace(line)
			if line == "" || strings.HasPrefix(line, "#") {
				continue
			}
			k, v, ok := strings.Cut(line, "=")
			if !ok {
				continue
			}
			k = strings.TrimSpace(k)
			v = strings.Trim(strings.TrimSpace(v), `"'`)
			if _, exists := os.LookupEnv(k); !exists {
				_ = os.Setenv(k, v)
			}
		}
		return // first found .env wins
	}
}

// String is a debug helper.
func (c Config) String() string {
	keyRedacted := "(set)"
	if c.GLMAPIKey == "" {
		keyRedacted = "(empty)"
	}
	return fmt.Sprintf("config{http:%s db:%s content:%s glm:%s/%s key:%s rateLimit:%d/h}",
		c.HTTPAddr, maskDSN(c.DatabaseURL), c.ContentRoot, c.GLMBaseURL, c.GLMModel,
		keyRedacted, c.FeedbackHourlyPerUser)
}

func maskDSN(dsn string) string {
	u, err := url.Parse(dsn)
	if err != nil {
		return "(invalid)"
	}
	if u.User != nil {
		u.User = url.User(u.User.Username()) // drop password
	}
	return u.String()
}
