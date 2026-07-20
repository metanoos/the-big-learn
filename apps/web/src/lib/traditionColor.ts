// Tradition → accent color. Mirrors the `colors.tradition` tokens in
// tailwind.config.ts; kept here as a plain map so it can be applied via inline
// style on cards (a per-card dynamic value isn't a good fit for class-based
// Tailwind). Used for the card spine + the leading dot in the tag row, so the
// shelf reads by tradition at a glance.
//
// Values are the muted -700/-600 ramp: they sit next to stone-50/stone-950
// without competing with the title, and stay legible in dark mode.

const TRADITION_COLOR: Record<string, string> = {
  confucian: "#b45309", // gold
  daoist:    "#047857", // jade
  buddhist:  "#be185d", // pink
  secular:   "#475569", // slate
};

// Fallback for unknown/missing tradition — a quiet neutral that matches the
// card's existing stone border, so an untagged book doesn't get a loud
// mismatched spine.
const TRADITION_COLOR_DEFAULT = "#a8a29e"; // stone-400

export function traditionColor(tradition: string | undefined): string {
  if (!tradition) return TRADITION_COLOR_DEFAULT;
  return TRADITION_COLOR[tradition] ?? TRADITION_COLOR_DEFAULT;
}
