/**
 * Formats a timestamp into an exact Swiss editorial timecode string: mm:ss.SS
 * Uses tabular-nums rendering.
 */
export function formatTimecode(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return "00:00.00";

  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const millis = Math.floor((seconds % 1) * 100);

  const mm = String(mins).padStart(2, "0");
  const ss = String(secs).padStart(2, "0");
  const ms = String(millis).padStart(2, "0");

  return `${mm}:${ss}.${ms}`;
}

/**
 * Formats a duration budget in seconds: e.g. "02.40s"
 */
export function formatDurationBudget(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return "0.00s";
  return `${seconds.toFixed(2)}s`;
}
