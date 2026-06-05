import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // In production (deployed), set NEXT_PUBLIC_API_URL to the backend URL (e.g. Render URL).
    // In local development, the backend runs on port 8000.
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
