// Package auth handles password hashing and signed session tokens (HMAC).
//
// We avoid a heavy session framework: a session is a signed (HMAC-SHA256)
// JSON blob carrying the user id + issued-at + role. Stateless, no session
// store, no DB lookup per request beyond resolving the user. Revocation is
// coarse (rotate JWT_SECRET invalidates everything) — acceptable for v1.
package auth

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

// Session is the payload carried inside a signed token.
type Session struct {
	UserID   uuid.UUID `json:"uid"`
	Role     string    `json:"role"`
	IssuedAt time.Time `json:"iat"`
}

// ErrInvalidToken indicates a malformed or bad-signature token.
var ErrInvalidToken = errors.New("auth: invalid token")

// HashPassword returns a bcrypt hash. bcrypt also incorporates the salt.
func HashPassword(password string) (string, error) {
	b, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return "", fmt.Errorf("auth: hash password: %w", err)
	}
	return string(b), nil
}

// VerifyPassword checks a password against a stored hash.
func VerifyPassword(hash, password string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(password)) == nil
}

// IssueToken signs a Session with secret and returns a transport-safe string.
func IssueToken(secret string, s Session) (string, error) {
	body, err := json.Marshal(s)
	if err != nil {
		return "", err
	}
	enc := base64.RawURLEncoding.EncodeToString(body)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(enc))
	sig := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	return enc + "." + sig, nil
}

// ParseToken validates a token's signature and returns the Session.
func ParseToken(secret, token string) (Session, error) {
	enc, sig, ok := splitOnce(token, ".")
	if !ok {
		return Session{}, ErrInvalidToken
	}
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(enc))
	want := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	if !hmac.Equal([]byte(sig), []byte(want)) {
		return Session{}, ErrInvalidToken
	}
	body, err := base64.RawURLEncoding.DecodeString(enc)
	if err != nil {
		return Session{}, ErrInvalidToken
	}
	var s Session
	if err := json.Unmarshal(body, &s); err != nil {
		return Session{}, ErrInvalidToken
	}
	return s, nil
}

// NewUUID generates a random uuid (used at account creation).
func NewUUID() (uuid.UUID, error) {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return uuid.Nil, err
	}
	return uuid.FromBytes(b[:])
}

func splitOnce(s, sep string) (a, b string, ok bool) {
	for i := 0; i+len(sep) <= len(s); i++ {
		if s[i:i+len(sep)] == sep {
			return s[:i], s[i+len(sep):], true
		}
	}
	return "", "", false
}
