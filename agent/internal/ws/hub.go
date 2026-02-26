package ws

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/HsiangNianian/AMonItor/agent/internal/protocol"
	"github.com/HsiangNianian/AMonItor/agent/internal/store"
	"github.com/gorilla/websocket"
)

type clientConn struct {
	conn *websocket.Conn
	mu   sync.Mutex
}

func (c *clientConn) WriteJSON(v any) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.conn.WriteJSON(v)
}

type Hub struct {
	store     store.Store
	authToken string
	sdkToken  string

	upgrader websocket.Upgrader

	panelMu sync.RWMutex
	panels  map[*clientConn]struct{}

	sdkMu sync.RWMutex
	sdks  map[string]*clientConn

	routeMu        sync.RWMutex
	routeAuthToken map[string]string
}

func NewHub(st store.Store, authToken, sdkToken string) *Hub {
	return &Hub{
		store:     st,
		authToken: authToken,
		sdkToken:  sdkToken,
		upgrader: websocket.Upgrader{
			CheckOrigin: func(_ *http.Request) bool { return true },
		},
		panels:         make(map[*clientConn]struct{}),
		sdks:           make(map[string]*clientConn),
		routeAuthToken: make(map[string]string),
	}
}

func (h *Hub) AddRoute(ctx context.Context, targetID, targetURL, authToken string) error {
	if targetID == "" || targetURL == "" {
		return errors.New("target_id and target_url are required")
	}
	if err := h.store.SetRoute(ctx, targetID, targetURL); err != nil {
		return err
	}
	h.routeMu.Lock()
	h.routeAuthToken[targetID] = authToken
	h.routeMu.Unlock()
	return nil
}

func (h *Hub) StartManagedUpstream(ctx context.Context, targetID, targetURL, authToken string, reconnectInterval time.Duration) {
	if reconnectInterval <= 0 {
		reconnectInterval = 5 * time.Second
	}

	go func() {
		for {
			if ctx.Err() != nil {
				return
			}

			if err := h.AddRoute(ctx, targetID, targetURL, authToken); err != nil {
				log.Printf("set route failed for %s: %v", targetID, err)
				time.Sleep(reconnectInterval)
				continue
			}

			if _, err := h.ensureSDKConn(ctx, targetID, targetURL, authToken); err != nil {
				log.Printf("connect upstream failed for %s: %v", targetID, err)
				time.Sleep(reconnectInterval)
				continue
			}

			for {
				if ctx.Err() != nil {
					return
				}
				time.Sleep(reconnectInterval)
				h.sdkMu.RLock()
				_, connected := h.sdks[targetID]
				h.sdkMu.RUnlock()
				if !connected {
					break
				}
			}
		}
	}()
}

func (h *Hub) HandlePanel(w http.ResponseWriter, r *http.Request) {
	if h.authToken != "" && r.Header.Get("Authorization") != "Bearer "+h.authToken {
		log.Printf("panel unauthorized: remote=%s", r.RemoteAddr)
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}

	conn, err := h.upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("upgrade panel ws failed: %v", err)
		return
	}
	client := &clientConn{conn: conn}

	h.panelMu.Lock()
	h.panels[client] = struct{}{}
	panelCount := len(h.panels)
	h.panelMu.Unlock()

	log.Printf("panel connected: remote=%s active_panels=%d", r.RemoteAddr, panelCount)
	h.readPanel(client)
}

func (h *Hub) readPanel(client *clientConn) {
	defer func() {
		h.panelMu.Lock()
		delete(h.panels, client)
		panelCount := len(h.panels)
		h.panelMu.Unlock()
		_ = client.conn.Close()
		log.Printf("panel disconnected: active_panels=%d", panelCount)
	}()

	for {
		var env protocol.Envelope
		if err := client.conn.ReadJSON(&env); err != nil {
			log.Printf("recv panel->agent failed: %v", err)
			return
		}
		h.logEvent("recv panel->agent", env)
		if env.Type != "action" {
			log.Printf("ignore non-action from panel: type=%s msg_id=%s target_id=%s", env.Type, env.MsgID, env.TargetID)
			continue
		}
		if err := h.handleAction(context.Background(), env); err != nil {
			log.Printf("handle action failed: %v", err)
			errEnv := protocol.Envelope{
				MsgID:     env.MsgID,
				TraceID:   env.TraceID,
				Type:      "error",
				TargetID:  env.TargetID,
				Timestamp: time.Now().UnixMilli(),
				Payload:   mustJSON(map[string]string{"code": "ACTION_FORWARD_FAILED", "message": err.Error()}),
			}
			h.logEvent("send agent->panel(error)", errEnv)
			h.broadcast(errEnv)
		}
	}
}

func (h *Hub) handleAction(ctx context.Context, env protocol.Envelope) error {
	if env.MsgID == "" {
		return errors.New("missing msg_id")
	}

	seen, err := h.store.IsProcessed(ctx, env.MsgID)
	if err != nil {
		return err
	}
	if seen {
		ack := protocol.Envelope{
			MsgID:     env.MsgID,
			TraceID:   env.TraceID,
			Type:      "action_ack",
			TargetID:  env.TargetID,
			Timestamp: time.Now().UnixMilli(),
			Payload: mustJSON(protocol.ActionAckPayload{
				ActionMsgID: env.MsgID,
				Success:     true,
				Message:     "duplicate ignored",
			}),
		}
		h.logEvent("send agent->panel(action_ack duplicate)", ack)
		h.broadcast(ack)
		return nil
	}

	var payload protocol.ActionPayload
	if err := json.Unmarshal(env.Payload, &payload); err != nil {
		return err
	}

	targetURL := payload.TargetURL
	if targetURL == "" && env.TargetID != "" {
		targetURL, err = h.store.GetRoute(ctx, env.TargetID)
		if err != nil {
			return err
		}
	}
	if targetURL == "" {
		return errors.New("missing target url")
	}
	log.Printf("resolve route: target_id=%s target_url=%s msg_id=%s", env.TargetID, targetURL, env.MsgID)

	sdkConn, err := h.ensureSDKConn(ctx, env.TargetID, targetURL, h.getRouteAuthToken(env.TargetID))
	if err != nil {
		return err
	}

	if err := sdkConn.WriteJSON(env); err != nil {
		return err
	}
	h.logEvent("send agent->sdk", env)
	if err := h.store.MarkProcessed(ctx, env.MsgID, 24*time.Hour); err != nil {
		return err
	}
	return nil
}

func (h *Hub) ensureSDKConn(ctx context.Context, targetID, targetURL, authToken string) (*clientConn, error) {
	h.sdkMu.RLock()
	if conn, ok := h.sdks[targetID]; ok {
		h.sdkMu.RUnlock()
		return conn, nil
	}
	h.sdkMu.RUnlock()

	header := http.Header{}
	if authToken == "" {
		authToken = h.sdkToken
	}
	if authToken != "" {
		header.Set("Authorization", "Bearer "+authToken)
	}
	log.Printf("dial sdk: target_id=%s target_url=%s", targetID, targetURL)
	conn, _, err := websocket.DefaultDialer.DialContext(ctx, targetURL, header)
	if err != nil {
		return nil, err
	}
	log.Printf("sdk connected: target_id=%s target_url=%s", targetID, targetURL)
	client := &clientConn{conn: conn}

	h.sdkMu.Lock()
	h.sdks[targetID] = client
	h.sdkMu.Unlock()

	if targetID != "" {
		_ = h.store.SetRoute(ctx, targetID, targetURL)
		h.routeMu.Lock()
		h.routeAuthToken[targetID] = authToken
		h.routeMu.Unlock()
	}

	go h.readSDK(targetID, client)
	return client, nil
}

func (h *Hub) readSDK(targetID string, client *clientConn) {
	defer func() {
		h.sdkMu.Lock()
		if cur, ok := h.sdks[targetID]; ok && cur == client {
			delete(h.sdks, targetID)
		}
		h.sdkMu.Unlock()
		_ = client.conn.Close()
		log.Printf("sdk disconnected: target_id=%s", targetID)
	}()

	for {
		var env protocol.Envelope
		if err := client.conn.ReadJSON(&env); err != nil {
			log.Printf("recv sdk->agent failed: target_id=%s err=%v", targetID, err)
			return
		}
		h.logEvent("recv sdk->agent", env)
		if env.Type == "register" {
			var p protocol.RegisterPayload
			if err := json.Unmarshal(env.Payload, &p); err == nil && p.TargetID != "" && p.SDKURL != "" {
				_ = h.store.SetRoute(context.Background(), p.TargetID, p.SDKURL)
				log.Printf("register route from sdk: target_id=%s sdk_url=%s", p.TargetID, p.SDKURL)
			}
		}
		if env.Type == "action_ack" {
			_ = h.store.SetAckStatus(context.Background(), env.MsgID, "done", 24*time.Hour)
			log.Printf("ack status updated: msg_id=%s target_id=%s", env.MsgID, env.TargetID)
		}
		h.logEvent("send agent->panel(broadcast)", env)
		h.broadcast(env)
	}
}

func (h *Hub) broadcast(env protocol.Envelope) {
	h.panelMu.RLock()
	panelCount := len(h.panels)
	defer h.panelMu.RUnlock()
	log.Printf("broadcast to panels: count=%d type=%s msg_id=%s target_id=%s", panelCount, env.Type, env.MsgID, env.TargetID)
	for panel := range h.panels {
		if err := panel.WriteJSON(env); err != nil {
			log.Printf("broadcast to panel failed: %v", err)
		}
	}
}

func mustJSON(v any) json.RawMessage {
	b, _ := json.Marshal(v)
	return b
}

func (h *Hub) getRouteAuthToken(targetID string) string {
	h.routeMu.RLock()
	defer h.routeMu.RUnlock()
	return h.routeAuthToken[targetID]
}

func (h *Hub) logEvent(prefix string, env protocol.Envelope) {
	log.Printf("%s: type=%s msg_id=%s trace_id=%s target_id=%s timestamp=%d", prefix, env.Type, env.MsgID, env.TraceID, env.TargetID, env.Timestamp)
}
