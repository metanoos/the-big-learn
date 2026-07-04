// Package mailer sends transactional email over SMTP. Provider-agnostic by
// design: works with any SMTP host (Gmail, SES, Postmark, Resend SMTP, a
// self-hosted Postfix) — no vendor SDK, no lock-in.
//
// In dev (SMTP_HOST empty) the verification link is logged to the server
// console instead of sent, so the local flow works without mail setup.
package mailer

import (
	"crypto/tls"
	"errors"
	"fmt"
	"log"
	"net"
	"net/smtp"
	"strings"
	"time"
)

// Config holds the SMTP connection details.
type Config struct {
	Host     string // smtp.example.com
	Port     int    // 587 (STARTTLS) or 465 (implicit TLS)
	Username string
	Password string
	From     string // "The Big Learn <noreply@example.com>"
}

// Sender sends (or, in dev, logs) a verification email.
type Sender struct {
	cfg      Config
	appURL   string // http://localhost:3000 in dev
	enabled  bool
}

// New constructs a Sender. If cfg.Host is empty, emails are logged (dev mode).
func New(cfg Config, appURL string) *Sender {
	return &Sender{
		cfg:     cfg,
		appURL:  strings.TrimRight(appURL, "/"),
		enabled: cfg.Host != "",
	}
}

// ErrDevLogged is returned in dev mode after logging the link to stderr.
var ErrDevLogged = errors.New("mailer: dev mode — link logged to server console")

// SendVerification sends (or logs) the email verification link.
func (s *Sender) SendVerification(toEmail, username, token string) error {
	link := fmt.Sprintf("%s/verify-email?token=%s", s.appURL, token)
	body := strings.Join([]string{
		"From: " + s.cfg.From,
		"To: " + toEmail,
		"Subject: Verify your email — The Big Learn",
		"MIME-Version: 1.0",
		"Content-Type: text/plain; charset=UTF-8",
		"",
		"Hi " + username + ",",
		"",
		"Verify your email to publish translations and comment on The Big Learn.",
		"",
		"Click this link (expires in 24 hours):",
		link,
		"",
		"If you didn't create an account, ignore this email.",
		"",
		"— The Big Learn",
	}, "\r\n")

	if !s.enabled {
		// Dev mode: log so the developer can click through.
		log.Printf("MAILER [dev] verification for %s:\n  %s", toEmail, link)
		return ErrDevLogged
	}
	return s.send(toEmail, body)
}

func (s *Sender) send(to, body string) error {
	addr := net.JoinHostPort(s.cfg.Host, fmt.Sprintf("%d", s.cfg.Port))
	var auth smtp.Auth
	if s.cfg.Username != "" {
		auth = smtp.PlainAuth("", s.cfg.Username, s.cfg.Password, s.cfg.Host)
	}
	// STARTTLS on 587; implicit TLS on 465; plaintext on 25 (not recommended).
	if s.cfg.Port == 465 {
		return s.sendTLS(addr, auth, to, body)
	}
	return smtp.SendMail(addr, auth, s.fromAddr(), []string{to}, []byte(body))
}

// sendTLS handles implicit-TLS port 465 (smtp.SendMail doesn't).
func (s *Sender) sendTLS(addr string, auth smtp.Auth, to, body string) error {
	conn, err := tls.Dial("tcp", addr, &tls.Config{ServerName: s.cfg.Host, MinVersion: tls.VersionTLS12})
	if err != nil {
		return fmt.Errorf("mailer: tls dial: %w", err)
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(30 * time.Second))

	c, err := smtp.NewClient(conn, s.cfg.Host)
	if err != nil {
		return fmt.Errorf("mailer: smtp client: %w", err)
	}
	defer c.Quit()

	if auth != nil {
		if err := c.Auth(auth); err != nil {
			return fmt.Errorf("mailer: auth: %w", err)
		}
	}
	if err := c.Mail(s.fromAddr()); err != nil {
		return fmt.Errorf("mailer: MAIL: %w", err)
	}
	if err := c.Rcpt(to); err != nil {
		return fmt.Errorf("mailer: RCPT: %w", err)
	}
	w, err := c.Data()
	if err != nil {
		return fmt.Errorf("mailer: DATA: %w", err)
	}
	if _, err := w.Write([]byte(body)); err != nil {
		return err
	}
	return w.Close()
}

// fromAddr extracts the bare address from "Name <addr>".
func (s *Sender) fromAddr() string {
	f := s.cfg.From
	if i := strings.Index(f, "<"); i >= 0 {
		if j := strings.Index(f, ">"); j > i {
			return f[i+1 : j]
		}
	}
	return f
}
