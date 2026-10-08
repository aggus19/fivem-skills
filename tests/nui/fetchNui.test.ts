import { afterEach, expect, test } from 'bun:test';
import { fetchNui } from '../../skills/fivem-development/assets/templates/nui-react-vite/src/utils/fetchNui';

const originalFetch = globalThis.fetch;
const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');
const originalParent = Object.getOwnPropertyDescriptor(globalThis, 'GetParentResourceName');

function inGame() {
  Object.defineProperty(globalThis, 'window', { value: { invokeNative() {} }, configurable: true });
  Object.defineProperty(globalThis, 'GetParentResourceName', { value: () => 'demo', configurable: true });
}

afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const [name, original] of [['window', originalWindow], ['GetParentResourceName', originalParent]] as const) {
    if (original) Object.defineProperty(globalThis, name, original);
    else Reflect.deleteProperty(globalThis, name);
  }
});

test('browser preview returns the mock without a network request', async () => {
  Object.defineProperty(globalThis, 'window', { value: {}, configurable: true });
  globalThis.fetch = (() => { throw new Error('must not fetch'); }) as typeof fetch;
  expect(await fetchNui('action', {}, { ok: true })).toEqual({ ok: true });
});

test('posts intent to the current resource and decodes the reply', async () => {
  inGame();
  globalThis.fetch = (async (url, init) => {
    expect(url).toBe('https://demo/action');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(init?.body as string)).toEqual({ kind: 'example' });
    return Response.json({ ok: true });
  }) as typeof fetch;
  expect(await fetchNui('action', { kind: 'example' })).toEqual({ ok: true });
});

test('HTTP errors are rejected', async () => {
  inGame();
  globalThis.fetch = (async () => new Response('', { status: 500 })) as typeof fetch;
  await expect(fetchNui('action')).rejects.toThrow('HTTP 500');
});

test('invalid JSON is rejected', async () => {
  inGame();
  globalThis.fetch = (async () => new Response('not JSON')) as typeof fetch;
  await expect(fetchNui('action')).rejects.toThrow();
});

test('a hung callback is aborted at the deadline', async () => {
  inGame();
  let aborted = false;
  globalThis.fetch = ((_url, init) => new Promise((_resolve, reject) => {
    init!.signal!.addEventListener('abort', () => {
      aborted = true;
      reject(new DOMException('Timed out', 'AbortError'));
    });
  })) as typeof fetch;
  await expect(fetchNui('action', {}, undefined, 10)).rejects.toThrow('Timed out');
  expect(aborted).toBe(true);
});
