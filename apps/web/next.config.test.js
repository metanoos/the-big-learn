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
