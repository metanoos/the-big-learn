// Command server runs The Big Learn API.
//
// Usage:
//
//	cd services/api
//	go run ./cmd/server
//
// Requires the content/ tree; all reader state stays in the browser.
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
	"thebiglearn/api/internal/httpapi"
)

func main() {
	cfg := config.Load()
	log.Printf("starting the-big-learn api: %s", cfg)

	cs := content.New(cfg.ContentRoot)

	srv := httpapi.New(cs, cfg.AllowedOrigin)
	httpSrv := &http.Server{
		Addr:              cfg.HTTPAddr,
		Handler:           srv,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       120 * time.Second,
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
