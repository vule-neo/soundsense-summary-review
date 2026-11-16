import type { NextConfig } from "next";

// In development the FastAPI server runs separately on :8000.
// On Vercel, /api/* is served by the Python function in api/index.py.
const nextConfig: NextConfig = {
  rewrites: async () => [
    {
      source: "/api/:path*",
      destination:
        process.env.NODE_ENV === "development"
          ? "http://127.0.0.1:8000/api/:path*"
          : "/api/",
    },
  ],
};

export default nextConfig;
