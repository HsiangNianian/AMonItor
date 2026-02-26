package store

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

type RedisStore struct {
	client *redis.Client
}

func NewRedisStore(addr string) *RedisStore {
	return &RedisStore{
		client: redis.NewClient(&redis.Options{Addr: addr}),
	}
}

func (r *RedisStore) SetRoute(ctx context.Context, targetID, sdkURL string) error {
	return r.client.Set(ctx, "route:"+targetID, sdkURL, 24*time.Hour).Err()
}

func (r *RedisStore) GetRoute(ctx context.Context, targetID string) (string, error) {
	result, err := r.client.Get(ctx, "route:"+targetID).Result()
	if err == redis.Nil {
		return "", nil
	}
	return result, err
}

func (r *RedisStore) IsProcessed(ctx context.Context, msgID string) (bool, error) {
	count, err := r.client.Exists(ctx, "processed:"+msgID).Result()
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

func (r *RedisStore) MarkProcessed(ctx context.Context, msgID string, ttl time.Duration) error {
	return r.client.Set(ctx, "processed:"+msgID, "1", ttl).Err()
}

func (r *RedisStore) SetAckStatus(ctx context.Context, msgID, status string, ttl time.Duration) error {
	return r.client.Set(ctx, "ack:"+msgID, status, ttl).Err()
}
