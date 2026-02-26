package main

import (
	"log"
	"net/http"
	"os"

	"github.com/HsiangNianian/AMonItor/agent/internal/store"
	"github.com/HsiangNianian/AMonItor/agent/internal/ws"
)

func main() {
	listenAddr := envOrDefault("AGENT_LISTEN_ADDR", ":8080")
	panelToken := os.Getenv("PANEL_AUTH_TOKEN")
	sdkToken := os.Getenv("SDK_AUTH_TOKEN")
	redisAddr := os.Getenv("REDIS_ADDR")

	var st store.Store
	if redisAddr != "" {
		st = store.NewRedisStore(redisAddr)
		log.Printf("use redis store: %s", redisAddr)
	} else {
		st = store.NewMemoryStore()
		log.Printf("use memory store")
	}

	hub := ws.NewHub(st, panelToken, sdkToken)
	mux := http.NewServeMux()
	mux.HandleFunc("/ws/panel", hub.HandlePanel)
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})

	log.Printf("agent listening on %s", listenAddr)
	if err := http.ListenAndServe(listenAddr, mux); err != nil {
		log.Fatalf("agent server failed: %v", err)
	}
}

func envOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
