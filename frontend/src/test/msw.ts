import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

export const server = setupServer(
  http.get('http://localhost/api/v1/settings', () =>
    HttpResponse.json({
      jenkins: { url: '', username: '', api_token: '', verify_ssl: true },
      github: { token: '' },
      ai: { gemini_api_key: '', model: '', temperature: 0.7, max_tokens: 4096 },
    })
  )
);

export function setupMsw(): void {
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
}
