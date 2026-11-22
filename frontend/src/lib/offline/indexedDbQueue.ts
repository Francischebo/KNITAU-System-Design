import type { QueuedOfflineAction } from './idempotency';

const DB_NAME = 'knitau_sync_store';
const STORE_NAME = 'pending_actions';
const DB_VERSION = 1;

function openSyncDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'idempotencyKey' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function enqueueOfflineAction<TPayload>(
  action: QueuedOfflineAction<TPayload>,
): Promise<void> {
  const db = await openSyncDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).put(action);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function listQueuedOfflineActions(): Promise<QueuedOfflineAction[]> {
  const db = await openSyncDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const req = tx.objectStore(STORE_NAME).getAll();
    req.onsuccess = () => {
      const items = (req.result as QueuedOfflineAction[]).sort((a, b) =>
        a.queuedAtIso.localeCompare(b.queuedAtIso),
      );
      resolve(items);
    };
    req.onerror = () => reject(req.error);
  });
}

export async function removeQueuedOfflineAction(idempotencyKey: string): Promise<void> {
  const db = await openSyncDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).delete(idempotencyKey);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function flushOfflineQueue(
  sender: (action: QueuedOfflineAction) => Promise<void>,
): Promise<{ flushed: number; remaining: number }> {
  const items = await listQueuedOfflineActions();
  let flushed = 0;

  for (const item of items) {
    try {
      await sender(item);
      await removeQueuedOfflineAction(item.idempotencyKey);
      flushed += 1;
    } catch {
      // Stop on transient network failure to preserve submission ordering
      break;
    }
  }

  const remainingItems = await listQueuedOfflineActions();
  return { flushed, remaining: remainingItems.length };
}
