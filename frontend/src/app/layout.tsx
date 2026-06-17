import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MiLyfe Brain",
  description:
    "Local-first AI orchestration dashboard — 100% private, zero cloud dependencies",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[var(--background)] text-[var(--foreground)] antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
