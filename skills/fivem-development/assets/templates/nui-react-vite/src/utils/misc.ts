/** True when running in a normal browser (vite dev server) instead of FiveM's CEF. */
export const isEnvBrowser = (): boolean => !(window as unknown as { invokeNative?: unknown }).invokeNative;
