export const SITE_NAME = "The Big Learn";
export const SITE_DESCRIPTION =
  "Read classical Chinese texts line by line with pinyin, public-domain translations, and character definitions.";

// Contact address, shipped split so the full string never appears in the
// server-rendered HTML (see components/Footer.tsx for the assembly + rationale).
// To change the address, edit these two halves — nothing else in the app
// hardcodes it.
export const CONTACT_EMAIL_USER = "metanoos92";
export const CONTACT_EMAIL_HOST = "gmail.com";

export function siteUrl(): URL {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  try {
    return new URL(configured || "http://localhost:3100");
  } catch {
    return new URL("http://localhost:3100");
  }
}

export function absoluteUrl(path: string): string {
  return new URL(path, siteUrl()).toString();
}
