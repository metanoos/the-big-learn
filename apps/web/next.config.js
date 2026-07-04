/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy /api to the Go backend in dev so the browser shares the session cookie.
  async rewrites() {
    const api = process.env.API_BASE_URL || "http://localhost:8080";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};
module.exports = nextConfig;
