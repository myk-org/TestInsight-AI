// Register Testing Library matchers for Vitest
import '@testing-library/jest-dom/vitest';

// Polyfill matchMedia for jsdom
if (!window.matchMedia) {
  // @ts-ignore
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  });
}

// Basic fetch stub for SettingsProvider
{
  const originalFetch = (globalThis as any).fetch?.bind(globalThis);
  (globalThis as any).fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.includes('/api/v1/settings') && (!init || !init.method || init.method === 'GET')) {
      const body = {
        jenkins: { url: '', username: '', api_token: '', verify_ssl: true },
        github: { token: '' },
        ai: { gemini_api_key: '', model: '', temperature: 0.7, max_tokens: 4096 },
      };
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (originalFetch) return originalFetch(input as any, init);
    return new Response(JSON.stringify({ error: 'Unhandled test fetch: ' + url }), { status: 501, headers: { 'Content-Type': 'application/json' } });
  };
}
