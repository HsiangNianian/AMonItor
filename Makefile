SHELL := /bin/bash

.PHONY: proto lint test build-agent build-sdk release-dry-run

proto:
	@echo "[proto] place generator command in scripts/gen_proto.sh"
	@bash scripts/gen_proto.sh

lint:
	@echo "[lint] go fmt check"
	@cd agent && gofmt -w $$(find . -name '*.go')
	@echo "[lint] python ruff"
	@cd python-sdk && uv run --with dev ruff check src

test:
	@echo "[test] go"
	@cd agent && go test ./...
	@echo "[test] python smoke"
	@cd python-sdk && uv run python -c "import amonitor_sdk"

build-agent:
	@mkdir -p dist
	@cd agent && \
	GOOS=linux GOARCH=amd64 go build -ldflags "-s -w" -o ../dist/amonitor-agent-linux-amd64 ./cmd/agent && \
	GOOS=linux GOARCH=arm64 go build -ldflags "-s -w" -o ../dist/amonitor-agent-linux-arm64 ./cmd/agent && \
	GOOS=darwin GOARCH=arm64 go build -ldflags "-s -w" -o ../dist/amonitor-agent-darwin-arm64 ./cmd/agent && \
	GOOS=windows GOARCH=amd64 go build -ldflags "-s -w" -o ../dist/amonitor-agent-windows-amd64.exe ./cmd/agent
	@bash scripts/gen_checksums.sh

build-sdk:
	@cd python-sdk && uv build

release-dry-run: build-agent build-sdk
	@echo "release dry run complete"
