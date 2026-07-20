package httpapi

import (
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"thebiglearn/api/internal/content"
)

func testServer(allowedOrigin string) *Server {
	root := filepath.Join("..", "..", "..", "..", "content")
	return New(content.New(root), allowedOrigin)
}

func TestHealthAndSecurityHeaders(t *testing.T) {
	recorder := httptest.NewRecorder()
	testServer("").ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/api/v1/health", nil))

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusOK)
	}
	if got := recorder.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Fatalf("X-Content-Type-Options = %q, want nosniff", got)
	}
	if got := recorder.Header().Get("Access-Control-Allow-Origin"); got != "" {
		t.Fatalf("unexpected open CORS header %q", got)
	}
}

func TestCORSOnlyAllowsConfiguredOrigin(t *testing.T) {
	const allowed = "https://reader.example.com"
	for _, test := range []struct {
		origin string
		want   string
	}{
		{origin: allowed, want: allowed},
		{origin: "https://evil.example", want: ""},
	} {
		recorder := httptest.NewRecorder()
		request := httptest.NewRequest(http.MethodGet, "/api/v1/health", nil)
		request.Header.Set("Origin", test.origin)
		testServer(allowed).ServeHTTP(recorder, request)
		if got := recorder.Header().Get("Access-Control-Allow-Origin"); got != test.want {
			t.Errorf("origin %q: allow header = %q, want %q", test.origin, got, test.want)
		}
	}
}

func TestUnknownChapterIsNotFound(t *testing.T) {
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/books/not-a-book/chapters/1", nil)
	testServer("").ServeHTTP(recorder, request)
	if recorder.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusNotFound)
	}
}

func TestCharacterBatchRejectsOversizedBody(t *testing.T) {
	recorder := httptest.NewRecorder()
	body := strings.NewReader(`{"chars":["` + strings.Repeat("大", 130_000) + `"]}`)
	request := httptest.NewRequest(http.MethodPost, "/api/v1/characters/batch", body)
	testServer("").ServeHTTP(recorder, request)
	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusBadRequest)
	}
}
