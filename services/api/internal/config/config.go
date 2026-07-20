// Package config loads runtime configuration from the environment and .env.
//
// All knobs are env-driven so the same binary runs locally, on a VPS, or
// anywhere else without compile-time choices.
//
// There are no accounts or server-side reader state; the server is a thin
// read-through layer over content/.
package config

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
)

// Config is the resolved runtime configuration.
type Config struct {
	// Server
	HTTPAddr      string // ":8180"
	AllowedOrigin string // optional browser origin allowed to call the API directly

	// Content root (the-big-learn/content)
	ContentRoot string
}

// Load reads env vars, falling back to defaults appropriate for local dev.
func Load() Config {
	loadDotEnv() // best-effort, doesn't override existing env

	c := Config{
		HTTPAddr:      env("HTTP_ADDR", ":8180"),
		AllowedOrigin: env("CORS_ALLOWED_ORIGIN", ""),
		ContentRoot:   env("CONTENT_ROOT", defaultContentRoot()),
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
	return fmt.Sprintf("config{http:%s content:%s cors:%q}", c.HTTPAddr, c.ContentRoot, c.AllowedOrigin)
}
