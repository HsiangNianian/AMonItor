/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_PANEL_DEFAULT_WS?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
