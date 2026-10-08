import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// NUI pages are served from https://cfx-nui-<resource>/web/dist/index.html (fx_version 'cerulean'),
// so every asset URL must be relative (base: './').
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Legacy FiveM ships CEF/Chromium 103 (V8 JIT disabled since 2026-10). Vite 8's default target
    // (baseline-widely-available, ~Chrome 111) is too new: syntax is lowered here, APIs are NOT polyfilled.
    target: 'chrome103',
    cssTarget: 'chrome103',
  },
});
