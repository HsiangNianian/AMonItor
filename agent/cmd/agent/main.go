package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/HsiangNianian/AMonItor/agent/internal/config"
	"github.com/HsiangNianian/AMonItor/agent/internal/store"
	"github.com/HsiangNianian/AMonItor/agent/internal/ws"
)

func main() {
	var cfgPath string
	var listenAddrOverride string
	var panelPathOverride string
	var panelTokenOverride string
	var sdkTokenOverride string
	var redisAddrOverride string
	var enableServerOverride string
	var enableClientOverride string
	var reconnectIntervalOverride int

	routeMap := keyValueMap{}
	routeTokenMap := keyValueMap{}
	upstreamMap := keyValueMap{}
	upstreamTokenMap := keyValueMap{}

	flag.StringVar(&cfgPath, "config", "", "agent config file path (json)")
	flag.StringVar(&listenAddrOverride, "listen-addr", "", "agent ws server listen address, e.g. :8080")
	flag.StringVar(&panelPathOverride, "panel-path", "", "panel ws path, e.g. /ws/panel")
	flag.StringVar(&panelTokenOverride, "panel-token", "", "panel auth token")
	flag.StringVar(&sdkTokenOverride, "sdk-token", "", "default sdk auth token for upstream dials")
	flag.StringVar(&redisAddrOverride, "redis-addr", "", "redis address")
	flag.StringVar(&enableServerOverride, "enable-server", "", "override server mode: true/false")
	flag.StringVar(&enableClientOverride, "enable-client", "", "override client mode: true/false")
	flag.IntVar(&reconnectIntervalOverride, "client-reconnect-seconds", 0, "client reconnect interval seconds")
	flag.Var(&routeMap, "route", "route mapping: target_id=ws://host:port/path")
	flag.Var(&routeTokenMap, "route-token", "route auth token: target_id=token")
	flag.Var(&upstreamMap, "upstream", "managed upstream: target_id=ws://host:port/path")
	flag.Var(&upstreamTokenMap, "upstream-token", "managed upstream auth token: target_id=token")
	flag.Parse()

	cfg, err := config.Load(cfgPath)
	if err != nil {
		log.Fatalf("load config failed: %v", err)
	}

	if envListen := os.Getenv("AGENT_LISTEN_ADDR"); envListen != "" {
		cfg.Server.ListenAddr = envListen
	}
	if listenAddrOverride != "" {
		cfg.Server.ListenAddr = listenAddrOverride
	}
	if panelPathOverride != "" {
		cfg.Server.PanelPath = panelPathOverride
	}
	if panelTokenOverride != "" {
		cfg.Server.PanelAuthToken = panelTokenOverride
	}
	if sdkTokenOverride != "" {
		cfg.Server.DefaultSDKAuthToken = sdkTokenOverride
	}
	if redisAddrOverride != "" {
		cfg.Store.RedisAddr = redisAddrOverride
	}
	if reconnectIntervalOverride > 0 {
		cfg.Client.ReconnectIntervalSeconds = reconnectIntervalOverride
	}

	if enableServerOverride != "" {
		enabled, parseErr := parseBool(enableServerOverride)
		if parseErr != nil {
			log.Fatalf("invalid --enable-server: %v", parseErr)
		}
		cfg.Server.Enabled = enabled
	}
	if enableClientOverride != "" {
		enabled, parseErr := parseBool(enableClientOverride)
		if parseErr != nil {
			log.Fatalf("invalid --enable-client: %v", parseErr)
		}
		cfg.Client.Enabled = enabled
	}

	for targetID, targetURL := range routeMap {
		cfg.Routes = upsertRoute(cfg.Routes, config.Route{
			TargetID:  targetID,
			URL:       targetURL,
			AuthToken: routeTokenMap[targetID],
		})
	}
	for targetID, token := range routeTokenMap {
		if _, ok := routeMap[targetID]; ok {
			continue
		}
		cfg.Routes = upsertRoute(cfg.Routes, config.Route{
			TargetID:  targetID,
			AuthToken: token,
		})
	}

	for targetID, targetURL := range upstreamMap {
		cfg.Client.Upstreams = upsertUpstream(cfg.Client.Upstreams, config.Upstream{
			TargetID:  targetID,
			URL:       targetURL,
			AuthToken: upstreamTokenMap[targetID],
		})
	}
	for targetID, token := range upstreamTokenMap {
		if _, ok := upstreamMap[targetID]; ok {
			continue
		}
		cfg.Client.Upstreams = upsertUpstream(cfg.Client.Upstreams, config.Upstream{
			TargetID:  targetID,
			AuthToken: token,
		})
	}

	if len(upstreamMap) > 0 && enableClientOverride == "" {
		cfg.Client.Enabled = true
	}

	if cfg.Server.PanelPath == "" {
		cfg.Server.PanelPath = "/ws/panel"
	}
	if cfg.Server.ListenAddr == "" {
		cfg.Server.ListenAddr = ":8080"
	}
	if cfg.Client.ReconnectIntervalSeconds <= 0 {
		cfg.Client.ReconnectIntervalSeconds = 5
	}

	if !cfg.Server.Enabled && !cfg.Client.Enabled {
		log.Fatalf("both server and client modes are disabled")
	}

	var st store.Store
	if cfg.Store.RedisAddr != "" {
		st = store.NewRedisStore(cfg.Store.RedisAddr)
		log.Printf("use redis store: %s", cfg.Store.RedisAddr)
	} else {
		st = store.NewMemoryStore()
		log.Printf("use memory store")
	}

	hub := ws.NewHub(st, cfg.Server.PanelAuthToken, cfg.Server.DefaultSDKAuthToken)
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	for _, route := range cfg.Routes {
		if route.TargetID == "" || route.URL == "" {
			continue
		}
		if err := hub.AddRoute(ctx, route.TargetID, route.URL, route.AuthToken); err != nil {
			log.Printf("set route failed: target=%s err=%v", route.TargetID, err)
		} else {
			log.Printf("route loaded: target=%s url=%s", route.TargetID, route.URL)
		}
	}

	if cfg.Client.Enabled {
		reconnect := time.Duration(cfg.Client.ReconnectIntervalSeconds) * time.Second
		for _, upstream := range cfg.Client.Upstreams {
			if upstream.TargetID == "" || upstream.URL == "" {
				log.Printf("skip invalid upstream: target_id/url required")
				continue
			}
			hub.StartManagedUpstream(ctx, upstream.TargetID, upstream.URL, upstream.AuthToken, reconnect)
			log.Printf("managed upstream enabled: target=%s url=%s", upstream.TargetID, upstream.URL)
		}
	}

	errCh := make(chan error, 1)
	if cfg.Server.Enabled {
		mux := http.NewServeMux()
		mux.HandleFunc(cfg.Server.PanelPath, hub.HandlePanel)
		mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("ok"))
		})

		server := &http.Server{
			Addr:    cfg.Server.ListenAddr,
			Handler: mux,
		}

		go func() {
			log.Printf("agent ws server listening on %s%s", cfg.Server.ListenAddr, cfg.Server.PanelPath)
			if serveErr := server.ListenAndServe(); serveErr != nil && serveErr != http.ErrServerClosed {
				errCh <- serveErr
			}
		}()

		go func() {
			<-ctx.Done()
			shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer shutdownCancel()
			_ = server.Shutdown(shutdownCtx)
		}()
	}

	if cfg.Server.Enabled {
		select {
		case runErr := <-errCh:
			log.Fatalf("agent server failed: %v", runErr)
		case <-ctx.Done():
			log.Printf("agent stopped")
		}
		return
	}

	<-ctx.Done()
	log.Printf("agent stopped")
}

type keyValueMap map[string]string

func (m *keyValueMap) String() string {
	if m == nil {
		return ""
	}
	parts := make([]string, 0, len(*m))
	for key, value := range *m {
		parts = append(parts, fmt.Sprintf("%s=%s", key, value))
	}
	return strings.Join(parts, ",")
}

func (m *keyValueMap) Set(raw string) error {
	parts := strings.SplitN(raw, "=", 2)
	if len(parts) != 2 || strings.TrimSpace(parts[0]) == "" || strings.TrimSpace(parts[1]) == "" {
		return fmt.Errorf("invalid key/value pair: %s", raw)
	}
	if *m == nil {
		*m = make(map[string]string)
	}
	(*m)[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
	return nil
}

func parseBool(raw string) (bool, error) {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "1", "true", "yes", "on":
		return true, nil
	case "0", "false", "no", "off":
		return false, nil
	default:
		return false, fmt.Errorf("unsupported bool value: %s", raw)
	}
}

func upsertRoute(routes []config.Route, route config.Route) []config.Route {
	for index := range routes {
		if routes[index].TargetID != route.TargetID {
			continue
		}
		if route.URL != "" {
			routes[index].URL = route.URL
		}
		if route.AuthToken != "" {
			routes[index].AuthToken = route.AuthToken
		}
		return routes
	}
	if route.TargetID == "" {
		return routes
	}
	return append(routes, route)
}

func upsertUpstream(upstreams []config.Upstream, upstream config.Upstream) []config.Upstream {
	for index := range upstreams {
		if upstreams[index].TargetID != upstream.TargetID {
			continue
		}
		if upstream.URL != "" {
			upstreams[index].URL = upstream.URL
		}
		if upstream.AuthToken != "" {
			upstreams[index].AuthToken = upstream.AuthToken
		}
		return upstreams
	}
	if upstream.TargetID == "" {
		return upstreams
	}
	return append(upstreams, upstream)
}
