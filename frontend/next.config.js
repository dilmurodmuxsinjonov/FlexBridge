/** @type {import('next').NextConfig} */
const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/backend/opportunities",
        destination: `${backendInternalUrl}/api/v1/opportunities`,
      },
      {
        source: "/api/backend/health/live",
        destination: `${backendInternalUrl}/api/v1/health/live`,
      },
    ];
  },
};

module.exports = nextConfig;
