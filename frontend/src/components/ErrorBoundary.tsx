"use client";

import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  showDetails: boolean;
}

export default class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, showDetails: false };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, showDetails: false });
  };

  toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-[300px] p-8">
          <div className="max-w-md w-full p-6 rounded-xl border border-[var(--destructive)] border-opacity-40 bg-[var(--card)]">
            <div className="flex items-center gap-3 mb-4">
              <span className="flex items-center justify-center w-10 h-10 rounded-full bg-[var(--destructive)] bg-opacity-15 text-[var(--destructive)] text-lg">
                !
              </span>
              <div>
                <h2 className="text-lg font-bold">Something went wrong</h2>
                <p className="text-sm text-[var(--muted-foreground)]">
                  An unexpected error occurred in this section.
                </p>
              </div>
            </div>

            <div className="flex gap-3 mb-4">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
              >
                Try Again
              </button>
              <button
                onClick={this.toggleDetails}
                className="px-4 py-2 rounded-lg border border-[var(--border)] text-sm font-medium hover:bg-[var(--muted)] transition-colors"
              >
                {this.state.showDetails ? "Hide Details" : "Show Details"}
              </button>
            </div>

            {this.state.showDetails && this.state.error && (
              <div className="mt-2 p-3 rounded-lg bg-[var(--muted)] overflow-auto max-h-48">
                <p className="text-xs font-mono text-[var(--destructive)] mb-1">
                  {this.state.error.name}: {this.state.error.message}
                </p>
                {this.state.error.stack && (
                  <pre className="text-[10px] font-mono text-[var(--muted-foreground)] whitespace-pre-wrap">
                    {this.state.error.stack}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
