import React, { useCallback, useEffect, useState } from 'react';
import { apiRequest } from '../lib/api/client';
import { flushOfflineQueue, listQueuedOfflineActions } from '../lib/offline/indexedDbQueue';

export const OfflineSyncBanner: React.FC = () => {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true,
  );
  const [pendingCount, setPendingCount] = useState(0);

  const syncPending = useCallback(async () => {
    const queued = await listQueuedOfflineActions().catch(() => []);
    setPendingCount(queued.length);
    if (!navigator.onLine || queued.length === 0) return;

    const result = await flushOfflineQueue(async (action) => {
      await apiRequest(action.endpoint, {
        method: action.method,
        body: action.payload,
        idempotencyKey: action.idempotencyKey,
      });
    });
    setPendingCount(result.remaining);
  }, []);

  useEffect(() => {
    syncPending();
    const handleOnline = () => {
      setIsOnline(true);
      void syncPending();
    };
    const handleOffline = () => {
      setIsOnline(false);
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [syncPending]);

  if (isOnline && pendingCount === 0) return null;

  return (
    <div
      role="status"
      className="flex items-center justify-between bg-[#231F20] px-4 py-2 text-xs text-[#FFFFFF]"
    >
      <span>
        {!isOnline
          ? 'Offline mode active — saved submissions will sync automatically once reconnected.'
          : `Syncing ${pendingCount} saved submission(s)...`}
      </span>
      {isOnline && pendingCount > 0 && (
        <button
          type="button"
          onClick={() => void syncPending()}
          className="rounded bg-[#F4C823] px-2.5 py-1 font-semibold text-[#231F20]"
        >
          Sync Now
        </button>
      )}
    </div>
  );
};
