import { createIdempotencyKey } from '../offline/idempotency';

let inMemoryAccessToken: string | null = null;

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
}

const API_BASE =
  (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE_URL ??
  'http://localhost:8000/api/v1';

export async function apiRequest<TResponse>(
  path: string,
  options: RequestOptions = {},
): Promise<TResponse> {
  const method = (options.method ?? 'GET').toUpperCase();
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');

  if (inMemoryAccessToken) {
    headers.set('Authorization', `Bearer ${inMemoryAccessToken}`);
  }

  if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
    headers.set('X-Idempotency-Key', options.idempotencyKey ?? createIdempotencyKey());
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    credentials: 'include',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

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

  return (await response.json()) as TResponse;
}
