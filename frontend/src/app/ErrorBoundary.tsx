import React from 'react';

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[#FFFFFF] p-6 text-[#231F20]">
          <div className="max-w-md rounded-lg border border-[#C82128] bg-[#FFFFFF] p-6 text-center">
            <h1 className="text-lg font-bold text-[#C82128]">Something went wrong</h1>
            <p className="mt-2 text-sm text-[#231F20]/80">
              Please reload this page to restore your KNITAU session.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-4 rounded bg-[#231F20] px-4 py-2 text-xs font-semibold text-[#FFFFFF]"
            >
              Reload Portal
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
