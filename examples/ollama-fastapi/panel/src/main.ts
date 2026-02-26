type WsEnvelope = {
  type: string;
  payload?: Record<string, unknown>;
};

type TargetConfig = {
  target_id: string;
  target_url: string;
  api_base?: string;
};

const wsUrlInput = document.getElementById("wsUrl") as HTMLInputElement;
const connectBtn = document.getElementById("connectBtn") as HTMLButtonElement;
const disconnectBtn = document.getElementById("disconnectBtn") as HTMLButtonElement;
const sendActionBtn = document.getElementById("sendActionBtn") as HTMLButtonElement;
const generateBtn = document.getElementById("generateBtn") as HTMLButtonElement;
const targetSelect = document.getElementById("targetSelect") as HTMLSelectElement;
const actionName = document.getElementById("actionName") as HTMLSelectElement;
const actionValue = document.getElementById("actionValue") as HTMLInputElement;
const actionTargetId = document.getElementById("actionTargetId") as HTMLInputElement;
const actionTargetUrl = document.getElementById("actionTargetUrl") as HTMLInputElement;
const useAgentEnvelope = document.getElementById("useAgentEnvelope") as HTMLInputElement;
const promptInput = document.getElementById("promptInput") as HTMLTextAreaElement;
const statusEl = document.getElementById("status") as HTMLSpanElement;
const logBox = document.getElementById("logBox") as HTMLPreElement;
const generateOutput = document.getElementById("generateOutput") as HTMLPreElement;
const apiBaseUrlInput = document.getElementById("apiBaseUrl") as HTMLInputElement;

const serviceNameEl = document.getElementById("serviceName") as HTMLElement;
const modelNameEl = document.getElementById("modelName") as HTMLElement;
const totalTokenCharsEl = document.getElementById("totalTokenChars") as HTMLElement;
const lastTokenCharsEl = document.getElementById("lastTokenChars") as HTMLElement;
const gpuUsageEl = document.getElementById("gpuUsage") as HTMLElement;
const queueSizeEl = document.getElementById("queueSize") as HTMLElement;
const inProgressEl = document.getElementById("inProgress") as HTMLElement;
const totalReqEl = document.getElementById("totalReq") as HTMLElement;
const failedReqEl = document.getElementById("failedReq") as HTMLElement;

let ws: WebSocket | null = null;

const defaultWs = (import.meta as any).env?.VITE_PANEL_DEFAULT_WS as string | undefined;
const defaultApiBase = (import.meta as any).env?.VITE_PANEL_DEFAULT_API_BASE as string | undefined;
const rawTargets = (import.meta as any).env?.VITE_PANEL_TARGETS_JSON as string | undefined;
const targetConfigs: Record<string, TargetConfig> = (() => {
  if (!rawTargets) {
    return {};
  }
  try {
    return JSON.parse(rawTargets) as Record<string, TargetConfig>;
  } catch {
    return {};
  }
})();
if (defaultWs && defaultWs.trim()) {
  wsUrlInput.value = defaultWs;
}
if (defaultApiBase && defaultApiBase.trim()) {
  apiBaseUrlInput.value = defaultApiBase;
}

function initTargetSelect(): void {
  const entries = Object.entries(targetConfigs);
  if (entries.length === 0) {
    return;
  }
  for (const [name] of entries) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    targetSelect.appendChild(option);
  }
  targetSelect.addEventListener("change", () => {
    const selected = targetConfigs[targetSelect.value];
    if (!selected) {
      return;
    }
    actionTargetId.value = selected.target_id;
    actionTargetUrl.value = selected.target_url;
    if (selected.target_url) {
      wsUrlInput.value = selected.target_url;
    }
    if (selected.api_base) {
      apiBaseUrlInput.value = selected.api_base;
    }
    appendLog(`已载入目标配置: ${targetSelect.value}`);
  });
}

function appendLog(message: string): void {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  logBox.textContent = `${line}\n${logBox.textContent ?? ""}`.slice(0, 12000);
}

function setStatus(text: string, className: string): void {
  statusEl.textContent = text;
  statusEl.className = className;
}

function updateMetrics(payload: Record<string, unknown>): void {
  serviceNameEl.textContent = String(payload.service_name ?? "-");
  modelNameEl.textContent = String(payload.model ?? "-");
  totalTokenCharsEl.textContent = String(payload.total_token_chars ?? 0);
  lastTokenCharsEl.textContent = String(payload.last_request_token_chars ?? 0);
  gpuUsageEl.textContent = `${String(payload.gpu_utilization ?? -1)}%`;
  queueSizeEl.textContent = String(payload.queue_size ?? 0);
  inProgressEl.textContent = String(payload.in_progress_requests ?? 0);
  totalReqEl.textContent = String(payload.total_requests ?? 0);
  failedReqEl.textContent = String(payload.failed_requests ?? 0);
}

function connect(): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    appendLog("连接已存在");
    return;
  }

  const url = wsUrlInput.value.trim();
  if (!url) {
    appendLog("请输入 WS 地址");
    return;
  }

  ws = new WebSocket(url);
  setStatus("连接中...", "warn");

  ws.onopen = () => {
    setStatus("已连接", "ok");
    appendLog(`已连接: ${url}`);
  };

  ws.onmessage = (event) => {
    appendLog(`收到: ${event.data}`);
    try {
      const envelope = JSON.parse(event.data) as WsEnvelope;
      if (!envelope.payload) {
        return;
      }
      if (envelope.type === "metrics" || envelope.type === "welcome") {
        updateMetrics(envelope.payload);
      }
    } catch {
      appendLog("消息解析失败");
    }
  };

  ws.onerror = () => {
    setStatus("连接异常", "err");
    appendLog("WS 连接异常");
  };

  ws.onclose = () => {
    setStatus("已断开", "warn");
    appendLog("WS 已断开");
  };
}

function disconnect(): void {
  if (!ws) {
    return;
  }
  ws.close();
  ws = null;
}

function sendAction(): void {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    appendLog("未连接，无法发送 action");
    return;
  }

  let value: unknown = actionValue.value;
  if (actionName.value === "set_max_concurrency") {
    const parsed = Number(actionValue.value);
    if (!Number.isFinite(parsed) || parsed < 1) {
      appendLog("set_max_concurrency 需要 >= 1 的数字");
      return;
    }
    value = parsed;
  }

  let message: Record<string, unknown>;
  if (useAgentEnvelope.checked) {
    const targetId = actionTargetId.value.trim();
    const targetUrl = actionTargetUrl.value.trim();
    if (!targetId || !targetUrl) {
      appendLog("通过 Agent 转发时，target_id 和 target_url 必填");
      return;
    }
    message = {
      msg_id: crypto.randomUUID(),
      trace_id: crypto.randomUUID(),
      type: "action",
      target_id: targetId,
      timestamp: Date.now(),
      payload: {
        action: actionName.value,
        params: { value },
        target_url: targetUrl,
      },
    };
  } else {
    message = {
      type: "action",
      action: actionName.value,
      value,
    };
  }
  ws.send(JSON.stringify(message));
  appendLog(`发送 action: ${JSON.stringify(message)}`);
}

function resolveApiBaseFromWs(wsUrl: string): string {
  const url = new URL(wsUrl);
  const protocol = url.protocol === "wss:" ? "https:" : "http:";
  return `${protocol}//${url.host}`;
}

async function generateWithPrompt(): Promise<void> {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    appendLog("请输入 prompt");
    return;
  }

  const wsUrl = wsUrlInput.value.trim();
  if (!wsUrl) {
    appendLog("请先填写 WS 地址");
    return;
  }

  const apiBase = apiBaseUrlInput.value.trim() || resolveApiBaseFromWs(wsUrl);
  const url = `${apiBase}/api/generate`;

  generateBtn.disabled = true;
  try {
    appendLog(`调用生成接口: ${url}`);
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      const text = await response.text();
      appendLog(`生成失败(${response.status}): ${text}`);
      return;
    }

    const data = (await response.json()) as {
      service_name?: string;
      model?: string;
      text?: string;
      token_chars?: number;
    };
    generateOutput.textContent = data.text ?? "";
    appendLog(
      `生成完成: service=${data.service_name ?? "-"}, model=${data.model ?? "-"}, token_chars=${data.token_chars ?? 0}`,
    );
  } catch (error) {
    appendLog(`生成异常: ${String(error)}`);
  } finally {
    generateBtn.disabled = false;
  }
}

connectBtn.addEventListener("click", connect);
disconnectBtn.addEventListener("click", disconnect);
sendActionBtn.addEventListener("click", sendAction);
generateBtn.addEventListener("click", () => {
  void generateWithPrompt();
});

initTargetSelect();
