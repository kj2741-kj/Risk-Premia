import { useEffect, useState } from "react";

/**
 * Debounces a value on release rather than firing a request on every
 * keystroke/drag tick -- every param change here re-runs a real pandas
 * backtest server-side, not just a local re-render, so per-keystroke firing
 * would be both slow-feeling and wasteful (see webapp build plan's
 * "interaction model" section).
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}
