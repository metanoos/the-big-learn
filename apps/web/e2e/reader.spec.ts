import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    for (const key of [
      "tbl:bookmarks",
      "tbl:bookmark-details",
      "tbl:review-chars",
      "tbl:pinyin",
      "tbl:theme",
    ]) {
      localStorage.removeItem(key);
    }
  });
});

test("serves metadata, security headers, and real 404 responses", async ({ page }) => {
  const home = await page.goto("/");
  expect(home?.status()).toBe(200);
  expect(home?.headers()["x-content-type-options"]).toBe("nosniff");
  expect(home?.headers()["x-frame-options"]).toBe("DENY");
  await expect(page).toHaveTitle("The Big Learn");

  const missing = await page.goto("/books/not-a-book");
  expect(missing?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "This page is not in the library." })).toBeVisible();
});

test("shows the correct Sanguo translation provenance", async ({ page }) => {
  await page.goto("/books/sanguo-yanyi");
  await expect(page.getByText(/seed translation: C\. H\. Brewitt-Taylor · 1925 · public domain/)).toBeVisible();
  await expect(page.getByText(/seed translation: James Legge/)).toHaveCount(0);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "http://localhost:3100/books/sanguo-yanyi",
  );
});

test("opens character definitions entirely from the keyboard", async ({ page }) => {
  await page.goto("/books/da-xue/1");
  const chars = page.locator("article").first().locator("[data-cjk-interactive]");
  await chars.first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(chars.nth(1)).toBeFocused();
  await expect(chars.nth(1)).toHaveAttribute("tabindex", "0");

  await page.keyboard.press("Enter");
  await expect(page.getByRole("note", { name: "Definition of 学" })).toBeVisible();
  await expect(chars.nth(1)).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("note", { name: "Definition of 学" })).toBeHidden();
});

test("persists saved-line text and exposes a portable backup", async ({ page }) => {
  await page.goto("/books/da-xue/1");
  await page.locator("article").first().getByRole("button", { name: "Save this line" }).click();
  await page.goto("/dashboard");

  await expect(page.getByText("大学之道，在明明德，在亲民，在止于至善。")).toBeVisible();
  await expect(page.getByText(/The way of great learning lies in illuminating luminous virtue/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Download backup" })).toBeVisible();
  const preview = await page.evaluate(() => JSON.parse(localStorage.getItem("tbl:bookmark-details") || "{}"));
  expect(preview["da-xue:1:1"].text).toContain("大学之道");
});

test("keeps long chapters paint-contained while preserving all lines", async ({ page }) => {
  await page.goto("/books/sanguo-yanyi/60");
  const lines = page.locator(".reading-line");
  await expect(lines).toHaveCount(89);
  expect(await lines.first().evaluate((element) => getComputedStyle(element).contentVisibility)).toBe("auto");
});
