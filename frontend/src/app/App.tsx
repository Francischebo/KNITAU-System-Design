import React from 'react';
import { MODULE_ACCESS_RULES, canAccessRoute } from '../lib/auth/rbac';
import { AuthProvider, useAuth } from './AuthProvider';
import { ErrorBoundary } from './ErrorBoundary';
import { OfflineSyncBanner } from './OfflineSyncBanner';

const PortalShell: React.FC = () => {
  const { user, isRestoringSession, logout } = useAuth();

  if (isRestoringSession) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#FFFFFF] text-sm text-[#231F20]">
        Loading KNITAU × KeNIP Portal...
      </div>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#FFFFFF] p-6 text-[#231F20]">
        <section className="w-full max-w-md rounded-lg border border-[#231F20]/15 p-6">
          <h1 className="text-xl font-bold">KNITAU × KeNIP Sign In</h1>
          <p className="mt-1 text-xs text-[#231F20]/70">
            Connect your React auth form to POST /api/v1/auth/login/.
          </p>
        </section>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#FFFFFF] text-[#231F20]">
      <OfflineSyncBanner />
      <header className="flex items-center justify-between border-b border-[#231F20]/15 px-6 py-3">
        <div>
          <span className="text-sm font-bold">KNITAU × KeNIP</span>
          <span className="ml-2 rounded bg-[#0F6B38] px-2 py-0.5 text-xs font-semibold text-[#FFFFFF]">
            {user.role}
          </span>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="rounded border border-[#231F20]/25 px-3 py-1 text-xs font-semibold"
        >
          Sign Out
        </button>
      </header>
      <main className="mx-auto max-w-6xl p-6">
        <nav className="flex flex-wrap gap-2 text-xs">
          {canAccessRoute(user, MODULE_ACCESS_RULES.globalCorridor) && (
            <span className="rounded bg-[#231F20] px-3 py-1.5 text-[#FFFFFF]">
              Global Corridor
            </span>
          )}
          {canAccessRoute(user, MODULE_ACCESS_RULES.welfareFinanceApproval) && (
            <span className="rounded bg-[#0F6B38] px-3 py-1.5 text-[#FFFFFF]">
              Welfare Finance Desk
            </span>
          )}
          {canAccessRoute(user, MODULE_ACCESS_RULES.grievanceCaseDesk) && (
            <span className="rounded bg-[#C82128] px-3 py-1.5 text-[#FFFFFF]">
              Grievance Case Desk
            </span>
          )}
          {canAccessRoute(user, MODULE_ACCESS_RULES.diasporaMentorOversight) && (
            <span className="rounded bg-[#F4C823] px-3 py-1.5 font-semibold text-[#231F20]">
              Diaspora Oversight
            </span>
          )}
        </nav>
      </main>
    </div>
  );
};

export const App: React.FC = () => (
  <ErrorBoundary>
    <AuthProvider>
      <PortalShell />
    </AuthProvider>
  </ErrorBoundary>
);
