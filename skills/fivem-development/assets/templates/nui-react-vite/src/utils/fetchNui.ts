import { isEnvBrowser } from './misc';

declare function GetParentResourceName(): string;

/**
 * POST to a RegisterNUICallback handler in Lua.
 * `mock` is returned when developing in a normal browser.
 */
export async function fetchNui<T = unknown>(event: string, data?: unknown, mock?: T): Promise<T> {
  if (isEnvBrowser()) return mock as T;

  const resource = GetParentResourceName();
  const resp = await fetch(`https://${resource}/${event}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=UTF-8' },
    body: JSON.stringify(data ?? {}),
  });
  return (await resp.json()) as T;
}
