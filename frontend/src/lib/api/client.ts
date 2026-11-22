import { buildQueuedAction, createIdempotencyKey } from '../offline/idempotency';
import { enqueueOfflineAction } from '../offline/indexedDbQueue';

let inMemoryAccessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export class ApiClientError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly fieldErrors: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  idempotencyKey?: string;
  queueWhenOffline?: boolean;
  skipAuthRefresh?: boolean;
}

const API_BASE =
  (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE_URL ??
  'http://localhost:8000/api/v1';

async function refreshAccessTokenOnce(): Promise<string | null> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': createIdempotencyKey(),
        },
      });
      if (!res.ok) {
        inMemoryAccessToken = null;
        return null;
      }
      const data = (await res.json()) as { access?: string };
      inMemoryAccessToken = data.access ?? null;
      return inMemoryAccessToken;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

export async function apiRequest<TResponse>(
  path: string,
  options: RequestOptions = {},
): Promise<TResponse> {
  const method = (options.method ?? 'GET').toUpperCase();
  const idempotencyKey = options.idempotencyKey ?? createIdempotencyKey();

  if (
    options.queueWhenOffline &&
    typeof navigator !== 'undefined' &&
    !navigator.onLine &&
    (method === 'POST' || method === 'PUT' || method === 'PATCH')
  ) {
    const queued = buildQueuedAction(path, method, options.body);
    queued.idempotencyKey = idempotencyKey;
    await enqueueOfflineAction(queued);
    return { queued: true, idempotencyKey } as TResponse;
  }

  const execute = async (token: string | null) => {
    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    headers.set('X-Request-ID', createIdempotencyKey());
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
      headers.set('X-Idempotency-Key', idempotencyKey);
    }

    return fetch(`${API_BASE}${path}`, {
      ...options,
      method,
      credentials: 'include',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  };

  let response = await execute(inMemoryAccessToken);

  if (response.status === 401 && !options.skipAuthRefresh && path !== '/auth/refresh/') {
    const renewed = await refreshAccessTokenOnce();
    if (renewed) {
      response = await execute(renewed);
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const err = payload?.error;
    throw new ApiClientError(
      err?.code ?? 'http_error',
      err?.message ?? 'Request failed.',
      response.status,
      err?.field_errors ?? {},
    );
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }
  return (await response.json()) as TResponse;
}
