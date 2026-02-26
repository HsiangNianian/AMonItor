package store

import (
	"context"
	"sync"
	"time"
)

type Store interface {
	SetRoute(ctx context.Context, targetID, sdkURL string) error
	GetRoute(ctx context.Context, targetID string) (string, error)
	IsProcessed(ctx context.Context, msgID string) (bool, error)
	MarkProcessed(ctx context.Context, msgID string, ttl time.Duration) error
	SetAckStatus(ctx context.Context, msgID, status string, ttl time.Duration) error
}

type MemoryStore struct {
	mu        sync.RWMutex
	routes    map[string]string
	processed map[string]time.Time
	acks      map[string]time.Time
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{
		routes:    make(map[string]string),
		processed: make(map[string]time.Time),
		acks:      make(map[string]time.Time),
	}
}

func (m *MemoryStore) SetRoute(_ context.Context, targetID, sdkURL string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.routes[targetID] = sdkURL
	return nil
}

func (m *MemoryStore) GetRoute(_ context.Context, targetID string) (string, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.routes[targetID], nil
}

func (m *MemoryStore) IsProcessed(_ context.Context, msgID string) (bool, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	expireAt, ok := m.processed[msgID]
	if !ok {
		return false, nil
	}
	return time.Now().Before(expireAt), nil
}

func (m *MemoryStore) MarkProcessed(_ context.Context, msgID string, ttl time.Duration) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.processed[msgID] = time.Now().Add(ttl)
	return nil
}

func (m *MemoryStore) SetAckStatus(_ context.Context, msgID, _ string, ttl time.Duration) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.acks[msgID] = time.Now().Add(ttl)
	return nil
}
