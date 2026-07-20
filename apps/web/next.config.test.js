const assert = require("node:assert/strict");
const test = require("node:test");
const {
  PHASE_DEVELOPMENT_SERVER,
  PHASE_PRODUCTION_BUILD,
  PHASE_PRODUCTION_SERVER,
} = require("next/constants");

const createConfig = require("./next.config");

test("development and production use isolated Next output directories", () => {
  assert.equal(createConfig(PHASE_DEVELOPMENT_SERVER).distDir, ".next-dev");
  assert.equal(createConfig(PHASE_PRODUCTION_BUILD).distDir, ".next");
  assert.equal(createConfig(PHASE_PRODUCTION_SERVER).distDir, ".next");
});

test("all pages receive baseline security headers", async () => {
  const [rule] = await createConfig(PHASE_PRODUCTION_BUILD).headers();
  assert.equal(rule.source, "/(.*)");
  const headers = Object.fromEntries(rule.headers.map(({ key, value }) => [key, value]));
  assert.equal(headers["X-Content-Type-Options"], "nosniff");
  assert.equal(headers["X-Frame-Options"], "DENY");
  assert.match(headers["Permissions-Policy"], /camera=\(\)/);
});

test("development allows the loopback QA origin", () => {
  assert.deepEqual(createConfig(PHASE_DEVELOPMENT_SERVER).allowedDevOrigins, ["127.0.0.1"]);
});
