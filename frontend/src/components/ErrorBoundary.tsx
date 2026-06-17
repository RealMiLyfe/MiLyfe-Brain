"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex items-center justify-center min-h-[200px] p-6">
          <div className="max-w-md w-full bg-[var(--card)] border border-red-500/30 rounded-xl p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
              <span className="text-red-400 text-xl">!</span>
            </div>
            <h2 className="text-lg font-bold text-[var(--foreground)] mb-2">Something went wrong</h2>
            <p className="text-sm text-[var(--muted-foreground)] mb-4">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
            <details className="text-left mb-4">
              <summary className="text-xs text-[var(--muted-foreground)] cursor-pointer hover:text-[var(--foreground)]">
                Technical details
              </summary>
              <pre className="text-xs text-[var(--muted-foreground)] mt-2 p-3 bg-[var(--background)] rounded overflow-auto max-h-40">
                {this.state.error?.stack || "No stack trace available"}
              </pre>
            </details>
            <button
              onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
              className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm hover:opacity-90"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
