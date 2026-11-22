/**
 * Offline Resilience & Idempotency Helper
 * Generates deterministic request keys for financial payouts and offline sync replays
 * so unstable rural networks never create duplicate claims or disbursements.
 */
export interface QueuedOfflineAction<TPayload = unknown> {
  idempotencyKey: string;
  endpoint: string;
  method: 'POST' | 'PUT' | 'PATCH';
  payload: TPayload;
  queuedAtIso: string;
  retryCount: number;
}

export function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export function buildQueuedAction<TPayload>(
  endpoint: string,
  method: 'POST' | 'PUT' | 'PATCH',
  payload: TPayload,
): QueuedOfflineAction<TPayload> {
  return {
    idempotencyKey: createIdempotencyKey(),
    endpoint,
    method,
    payload,
    queuedAtIso: new Date().toISOString(),
    retryCount: 0,
  };
}
