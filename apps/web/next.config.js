const { PHASE_DEVELOPMENT_SERVER } = require("next/constants");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Local QA tools may use the loopback IP instead of `localhost`. Next 16
  // blocks cross-origin dev assets by default, so allow this one equivalent
  // local origin explicitly (production is unaffected).
  allowedDevOrigins: ["127.0.0.1"],
  // Proxy /api to the Go backend in dev so the browser shares the session cookie.
  async rewrites() {
    const api = process.env.API_BASE_URL || "http://localhost:8180";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), geolocation=(), microphone=()",
          },
        ],
      },
    ];
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
