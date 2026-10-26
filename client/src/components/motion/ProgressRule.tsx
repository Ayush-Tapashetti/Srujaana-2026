/*
 * A thin indeterminate bar along the top edge of a panel, shown only while
 * something is working (the AI reading a chat, the chain being verified).
 * Replaces the earlier glowing border trail: same meaning, no glow.
 */
export function ProgressRule() {
  return (
    <div
      role="progressbar"
      aria-label="Working"
      className="pointer-events-none absolute inset-x-0 top-0 h-0.5 overflow-hidden rounded-t-md"
    >
      <div className="h-full w-1/3 animate-progress bg-navy-600" />
    </div>
  );
}
