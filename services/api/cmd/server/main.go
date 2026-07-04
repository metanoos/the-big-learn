// Command server runs The Big Learn API.
//
// Usage:
//
//	cd services/api
//	go run ./cmd/server
//
// Requires Postgres (see ../../docker-compose.yml) and the content/ tree.
// Set GLM_API_KEY to enable the posit-feedback loop.
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"thebiglearn/api/internal/config"
	"thebiglearn/api/internal/content"
	"thebiglearn/api/internal/feedback"
	"thebiglearn/api/internal/httpapi"
	"thebiglearn/api/internal/mailer"
	"thebiglearn/api/internal/storage"
	"thebiglearn/api/internal/zai"
)

func main() {
	cfg := config.Load()
	log.Printf("starting the-big-learn api: %s", cfg)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	db, err := storage.Open(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("storage: %v", err)
	}
	defer db.Close()

	cs := content.New(cfg.ContentRoot)
	zaic := zai.NewClient(cfg.GLMAPIKey, cfg.GLMBaseURL, nil)
	fs := feedback.New(zaic, cfg.GLMModel)
	ml := mailer.New(mailer.Config{
		Host: cfg.SMTPHost, Port: cfg.SMTPPort,
		Username: cfg.SMTPUser, Password: cfg.SMTPPass,
		From: cfg.SMTPFrom,
	}, cfg.AppURL)

	srv := httpapi.New(cfg, db, cs, fs, ml)
	httpSrv := &http.Server{
		Addr:              cfg.HTTPAddr,
		Handler:           srv,
		ReadHeaderTimeout: 10 * time.Second,
		// No WriteTimeout: the feedback endpoint can hold a connection open
		// while GLM thinks (~10–30s). On a VPS there's no serverless ceiling.
		IdleTimeout: 120 * time.Second,
	}

	// Graceful shutdown on SIGINT/SIGTERM.
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		log.Println("shutdown signal received")
		shutdownCtx, c := context.WithTimeout(context.Background(), 15*time.Second)
		defer c()
		_ = httpSrv.Shutdown(shutdownCtx)
	}()

	log.Printf("listening on %s", cfg.HTTPAddr)
	if err := httpSrv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("server: %v", err)
	}
	log.Println("stopped")
}
