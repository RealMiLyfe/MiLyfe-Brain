import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      bodySizeLimit: "2mb",
    },
    optimizePackageImports: ["lucide-react", "framer-motion", "@xyflow/react"],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8200/api/stream/ws",
  },
  images: {
    unoptimized: true, // No external image optimization needed for local-only
  },
  // Bundle analyzer can be enabled via ANALYZE=true
  ...(process.env.ANALYZE === "true" && {
    webpack: (config: any) => {
      const { BundleAnalyzerPlugin } = require("webpack-bundle-analyzer");
      config.plugins.push(new BundleAnalyzerPlugin({ analyzerMode: "static", openAnalyzer: false }));
      return config;
    },
  }),
};

export default nextConfig;
