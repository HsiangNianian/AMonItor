# Ubuntu 从零部署教程

本文用于在一台全新的 Ubuntu 机器上，从 0 开始部署并运行 AMonitor（Agent + Python SDK）。

## 1. 适用范围

- 系统：Ubuntu 22.04 / 24.04
- 网络：可访问 GitHub（或已配置企业镜像）
- 权限：具备 `sudo`

## 2. 准备系统基础工具

```bash
sudo apt update
sudo apt install -y curl wget git ca-certificates build-essential pkg-config
```

建议设置时区（可选）：

```bash
sudo timedatectl set-timezone Asia/Shanghai
```

## 3. 安装 Go（>= 1.23）

方式 A（推荐，二进制包）：

```bash
cd /tmp
wget https://go.dev/dl/go1.23.7.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.23.7.linux-amd64.tar.gz
```

将 Go 加入 PATH：

```bash
echo 'export PATH=/usr/local/go/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
go version
```

## 4. 安装 Python 与 uv

安装 Python（Ubuntu 24.04 默认已较新；此处统一安装）：

```bash
sudo apt install -y python3 python3-venv python3-pip
python3 --version
```

安装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

让当前 shell 识别 uv（如未自动生效）：

```bash
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

## 5. （中国大陆可选）镜像与网络建议

如果下载较慢，可优先使用国内源：

- `apt`：替换为阿里云/清华镜像
- `pip/uv`：

```bash
mkdir -p ~/.pip
cat > ~/.pip/pip.conf <<'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
EOF
```

- `go` 模块代理：

```bash
go env -w GOPROXY=https://goproxy.cn,direct
```

## 6. 拉取项目

```bash
mkdir -p ~/apps
cd ~/apps
git clone https://github.com/HsiangNianian/AMonItor.git
cd AMonItor
```

## 7. 初始化依赖与构建

### 7.1 Python SDK 依赖

```bash
cd python-sdk
uv sync
cd ..
```

### 7.2 Go 依赖与构建

```bash
cd agent
go mod tidy
go test ./...
cd ..
make build-agent
```

构建产物在 `dist/`：

- `amonitor-agent-linux-amd64`
- `amonitor-agent-linux-arm64`
- `amonitor-agent-darwin-arm64`
- `amonitor-agent-windows-amd64.exe`

## 8. 快速运行（单机联调）

### 8.1 启动 Agent

```bash
cd ~/apps/AMonItor/agent
go run ./cmd/agent
```

### 8.2 启动 SDK 示例

新开终端：

```bash
cd ~/apps/AMonItor/python-sdk
uv run python -m amonitor_sdk.example
```

### 8.3 启动面板模拟

再开新终端：

```bash
cd ~/apps/AMonItor/python-sdk
uv run python ../scripts/panel_sim.py
```

看到 `heartbeat` 与 `action_ack` 即说明链路可用。

## 9. 一键示例运行

在仓库根目录：

```bash
make demo
```

更多模式：

```bash
make demo-multi
make demo-stress
SDK_COUNT=20 make demo-scale
```

## 10. 生产化建议（systemd 托管）

以下示例将 Agent 作为系统服务托管。

### 10.1 准备运行用户（可选）

```bash
sudo useradd -r -s /usr/sbin/nologin amonitor || true
sudo mkdir -p /opt/amonitor
sudo cp ~/apps/AMonItor/dist/amonitor-agent-linux-amd64 /opt/amonitor/amonitor-agent
sudo chown -R amonitor:amonitor /opt/amonitor
sudo chmod +x /opt/amonitor/amonitor-agent
```

### 10.2 配置环境变量

```bash
sudo tee /etc/amonitor-agent.env >/dev/null <<'EOF'
AGENT_LISTEN_ADDR=:8080
PANEL_AUTH_TOKEN=
SDK_AUTH_TOKEN=
REDIS_ADDR=
EOF
```

### 10.3 创建 systemd 服务

```bash
sudo tee /etc/systemd/system/amonitor-agent.service >/dev/null <<'EOF'
[Unit]
Description=AMonitor Agent
After=network.target

[Service]
Type=simple
User=amonitor
Group=amonitor
EnvironmentFile=/etc/amonitor-agent.env
WorkingDirectory=/opt/amonitor
ExecStart=/opt/amonitor/amonitor-agent
Restart=always
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF
```

### 10.4 启动与开机自启

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now amonitor-agent
sudo systemctl status amonitor-agent
```

查看日志：

```bash
journalctl -u amonitor-agent -f
```

## 11. 验收清单

- `curl http://127.0.0.1:8080/healthz` 返回 `ok`
- 面板连接 `ws://<host>:8080/ws/panel` 成功
- 能看到 SDK 的 `heartbeat`
- 下发 `action` 后收到 `action_ack`
- 同一 `msg_id` 重复下发时返回 `duplicate ignored`

## 12. 常见问题

### 12.1 端口被占用

```bash
sudo ss -lntp | grep -E '8080|8765|8766|88[0-9]{2}'
```

修改 `AGENT_LISTEN_ADDR` 或 examples 配置端口后重试。

### 12.2 本机代理导致 WS 连接失败

报错类似 `connecting through a SOCKS proxy requires python-socks`，可在启动命令前清理代理变量：

```bash
env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy NO_PROXY=127.0.0.1,localhost <your-command>
```

### 12.3 uv 命令不可用

确认 `~/.local/bin` 已加入 PATH：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
uv --version
```

### 12.4 Go 依赖下载慢

```bash
go env -w GOPROXY=https://goproxy.cn,direct
go clean -modcache
```

---

如果你要部署到多台机器（Agent 与 SDK 分离），建议先按本文完成单机验收，再把 `AGENT_LISTEN_ADDR`、`target_url`、防火墙与 Token 分发策略拆开配置。
