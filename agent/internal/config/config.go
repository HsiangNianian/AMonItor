package config

import (
	"encoding/json"
	"fmt"
	"os"
)

type Config struct {
	Server ServerConfig `json:"server"`
	Store  StoreConfig  `json:"store"`
	Client ClientConfig `json:"client"`
	Routes []Route      `json:"routes"`
}

type ServerConfig struct {
	Enabled             bool   `json:"enabled"`
	ListenAddr          string `json:"listen_addr"`
	Host                string `json:"host"`
	Port                int    `json:"port"`
	PanelPath           string `json:"panel_path"`
	PanelAuthToken      string `json:"panel_auth_token"`
	DefaultSDKAuthToken string `json:"default_sdk_auth_token"`
}

type StoreConfig struct {
	RedisAddr string `json:"redis_addr"`
}

type ClientConfig struct {
	Enabled                  bool       `json:"enabled"`
	ReconnectIntervalSeconds int        `json:"reconnect_interval_seconds"`
	Upstreams                []Upstream `json:"upstreams"`
}

type Route struct {
	TargetID  string `json:"target_id"`
	URL       string `json:"url"`
	AuthToken string `json:"auth_token,omitempty"`
}

type Upstream struct {
	TargetID  string `json:"target_id"`
	URL       string `json:"url"`
	AuthToken string `json:"auth_token,omitempty"`
}

func Default() Config {
	return Config{
		Server: ServerConfig{
			Enabled:             true,
			ListenAddr:          ":8080",
			PanelPath:           "/ws/panel",
			PanelAuthToken:      os.Getenv("PANEL_AUTH_TOKEN"),
			DefaultSDKAuthToken: os.Getenv("SDK_AUTH_TOKEN"),
		},
		Store: StoreConfig{
			RedisAddr: os.Getenv("REDIS_ADDR"),
		},
		Client: ClientConfig{
			Enabled:                  false,
			ReconnectIntervalSeconds: 5,
			Upstreams:                nil,
		},
		Routes: nil,
	}
}

func Load(path string) (Config, error) {
	cfg := Default()
	if path == "" {
		return cfg, nil
	}

	content, err := os.ReadFile(path)
	if err != nil {
		return Config{}, fmt.Errorf("read config failed: %w", err)
	}

	if err := json.Unmarshal(content, &cfg); err != nil {
		return Config{}, fmt.Errorf("parse config failed: %w", err)
	}

	if cfg.Server.PanelPath == "" {
		cfg.Server.PanelPath = "/ws/panel"
	}
	if cfg.Server.ListenAddr == "" {
		if cfg.Server.Host != "" && cfg.Server.Port > 0 {
			cfg.Server.ListenAddr = fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
		} else {
			cfg.Server.ListenAddr = ":8080"
		}
	}
	if cfg.Client.ReconnectIntervalSeconds <= 0 {
		cfg.Client.ReconnectIntervalSeconds = 5
	}

	return cfg, nil
}
