const path = require("node:path");
const { PHASE_DEVELOPMENT_SERVER } = require("next/constants");

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: path.join(__dirname, "../.."),
  // The raw repository content is only a build-time input. Runtime requests
  // read the projected files under .content-cache/, so exclude the source tree
  // from every function trace to avoid shipping the same ~130 MB twice.
  outputFileTracingExcludes: {
    "/*": ["../../content/**/*"],
  },
  // Local QA tools may use the loopback IP instead of `localhost`. Next 16
  // blocks cross-origin dev assets by default, so allow this one equivalent
  // local origin explicitly (production is unaffected).
  allowedDevOrigins: ["127.0.0.1"],
  // /api/v1/* is served by Next route handlers under app/api/v1 — no external
  // backend to proxy to. (Previously this rewrote to the Go content service,
  // which has been replaced by the in-process @/lib/content layer.)
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
