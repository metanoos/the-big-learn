const { PHASE_DEVELOPMENT_SERVER } = require("next/constants");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy /api to the Go backend in dev so the browser shares the session cookie.
  async rewrites() {
    const api = process.env.API_BASE_URL || "http://localhost:8080";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};

// `next dev` and `next build` must not write to the same directory. A build
// can replace webpack chunks while the dev server is still serving requests,
// leaving its runtime pointed at files that no longer exist. Keep production
// output in the conventional `.next` directory and isolate the dev cache.
module.exports = (phase) => ({
  ...nextConfig,
  distDir: phase === PHASE_DEVELOPMENT_SERVER ? ".next-dev" : ".next",
});
