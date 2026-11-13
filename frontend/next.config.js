/** @type {import('next').NextConfig} */
const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendInternalUrl}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
