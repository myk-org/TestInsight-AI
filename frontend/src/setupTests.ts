// Register Testing Library matchers for Vitest
import '@testing-library/jest-dom/vitest';
import { setupMsw } from './test/msw';

// Polyfill matchMedia for jsdom
if (typeof window.matchMedia !== 'function') {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string): MediaQueryList => {
      const listeners = new Set<(e: MediaQueryListEvent) => void>();

      const mql = {
        media: query,
        matches: false,
        onchange: null as ((this: MediaQueryList, ev: MediaQueryListEvent) => any) | null,
        addEventListener: vi.fn((type: string, listener: (e: MediaQueryListEvent) => void) => {
          if (type === 'change') listeners.add(listener);
        }),
        removeEventListener: vi.fn((type: string, listener: (e: MediaQueryListEvent) => void) => {
          if (type === 'change') listeners.delete(listener);
        }),
        addListener: vi.fn((listener: (e: MediaQueryListEvent) => void) => {
          listeners.add(listener);
        }),
        removeListener: vi.fn((listener: (e: MediaQueryListEvent) => void) => {
          listeners.delete(listener);
        }),
        dispatchEvent: vi.fn((event: Event) => {
          if ((event as any).type !== 'change') return false;
          const e = event as unknown as MediaQueryListEvent & { matches?: boolean; media?: string };
          if ((e as any).matches === undefined) (e as any).matches = (mql as any).matches;
          if ((e as any).media === undefined) (e as any).media = (mql as any).media;
          listeners.forEach((listener) => (listener as any).call(mql as unknown as MediaQueryList, e));
          mql.onchange?.call(mql as unknown as MediaQueryList, e);
          return true;
        }),
      } as unknown as MediaQueryList;

      return mql;
    },
  });
}

// Optional MSW server setup (enable with USE_MSW=true)
if (process.env.USE_MSW === 'true') {
  setupMsw();
}

// Basic fetch stub for SettingsProvider (disabled when MSW is enabled)
if (process.env.USE_MSW !== 'true') {
  const originalFetch = (globalThis as any).fetch?.bind(globalThis);
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const inputUrl = typeof input === 'string' || input instanceof URL ? input.toString() : (input as Request).url;
    const url = new URL(inputUrl, 'http://localhost');
    const method = (
      init?.method
        ? init.method
        : (typeof input !== 'string' && !(input instanceof URL))
          ? ((input as Request).method || 'GET')
          : (init?.method || 'GET')
    ).toUpperCase();

    if (url.pathname === '/api/v1/settings' && method === 'GET') {
      const body = {
        jenkins: { url: '', username: '', api_token: '', verify_ssl: true },
        github: { token: '' },
        ai: { gemini_api_key: '', model: '', temperature: 0.7, max_tokens: 4096 },
      };
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    const allowNetwork = process.env.ALLOW_TEST_NETWORK === 'true';
    if (allowNetwork && originalFetch) return originalFetch(input as any, init);
    return new Response(
      JSON.stringify({ error: 'Unhandled test fetch blocked: ' + url.pathname }),
      { status: 404, headers: { 'Content-Type': 'application/json' } }
    );
  }));
}
