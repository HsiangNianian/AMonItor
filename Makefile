SHELL := /bin/bash

.PHONY: proto lint test test-dedupe demo demo-multi demo-stress demo-scale build-agent build-sdk release-dry-run

proto:
	@echo "[proto] place generator command in scripts/gen_proto.sh"
	@bash scripts/gen_proto.sh

lint:
	@echo "[lint] go fmt check"
	@cd agent && gofmt -w $$(find . -name '*.go')
	@echo "[lint] python ruff"
	@cd python-sdk && uvx ruff check src

test:
	@echo "[test] go"
	@cd agent && go test ./...
	@echo "[test] python smoke"
	@cd python-sdk && uv run python -c "import amonitor_sdk"
	@if [ "$$RUN_E2E" = "1" ]; then \
		echo "[test] e2e dedupe"; \
		$(MAKE) test-dedupe; \
	else \
		echo "[test] e2e dedupe skipped (set RUN_E2E=1 to enable)"; \
	fi

test-dedupe:
	@cd python-sdk && env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy NO_PROXY=127.0.0.1,localhost uv run python ../scripts/test_dedupe_once.py

demo:
	@bash examples/run.sh

demo-multi:
	@bash examples/run.multi.sh

demo-stress:
	@bash examples/run.stress.sh

demo-scale:
	@bash examples/run.scale.sh

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
