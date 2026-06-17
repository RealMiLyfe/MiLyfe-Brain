"use client";

import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Toaster } from "sonner";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>MiLyfe Brain - AI Agent Orchestration</title>
        <meta name="description" content="AI Agent Orchestration Dashboard" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider>
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
          <Toaster
            position="bottom-right"
            theme="system"
            richColors
            closeButton
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
