"use client";

// SettingToggle: a small chapter-header on/off pill. The shared visual for
// word-labeled reader-display toggles (pinyin, english, and tones).
//
// The pill swaps between an outlined (off) and filled (on) look so the state is
// readable at a glance — the same affordance shape ToneColorToggle uses. When
// off, the label dims; when on, the label strengthens to match the active tint.
//
// Backed by a per-browser setting in lib/settings.ts (read reactive via a hook);
// the caller owns that, this just renders + toggles.

export function SettingToggle({
  on,
  onToggle,
  label,
  title,
  disabled = false,
}: {
  on: boolean;
  onToggle: (next: boolean) => void;
  label: string;
  title?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => onToggle(!on)}
      aria-pressed={on}
      title={title}
      disabled={disabled}
      className={`flex min-h-11 items-center gap-1.5 rounded px-2.5 py-1 text-xs transition-colors ${
        disabled
          ? "cursor-not-allowed text-stone-300 dark:text-stone-600"
          : on
          ? "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-200"
          : "text-stone-400 hover:text-stone-700 hover:bg-stone-100 dark:text-stone-500 dark:hover:text-stone-200 dark:hover:bg-stone-800"
      }`}
    >
      <span>{label}</span>
    </button>
  );
}
