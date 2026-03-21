/**
 * Typed event emitter with wildcard support and listener middleware.
 * Supports synchronous and asynchronous listeners, once-only listeners,
 * and pattern-based subscriptions.
 */

type Listener = (...args: unknown[]) => void | Promise<void>;
type Middleware = (eventName: string, args: unknown[], next: () => void) => void;

interface ListenerEntry {
  fn: Listener;
  once: boolean;
  priority: number;
}

class EventEmitter {
  private listeners = new Map<string, ListenerEntry[]>();
  private middlewares: Middleware[] = [];
  private maxListeners = 10;

  /**
   * Register a listener for an event.
   */
  on(event: string, fn: Listener, priority: number = 0): this {
    let entries = this.listeners.get(event);
    if (!entries) {
      entries = [];
      this.listeners.set(event, entries);
    }

    if (entries.length >= this.maxListeners) {
      console.warn(
        `MaxListenersExceeded: ${entries.length + 1} listeners for "${event}". ` +
        `Use setMaxListeners() to increase the limit.`
      );
    }

    entries.push({ fn, once: false, priority });

    // Sort by priority (higher priority first)
    entries.sort((a, b) => b.priority - a.priority);

    return this;
  }

  /**
   * Register a one-time listener that auto-removes after first invocation.
   */
  once(event: string, fn: Listener, priority: number = 0): this {
    let entries = this.listeners.get(event);
    if (!entries) {
      entries = [];
      this.listeners.set(event, entries);
    }

    entries.push({ fn, once: true, priority });
    entries.sort((a, b) => b.priority - a.priority);

    return this;
  }

  /**
   * Remove a specific listener from an event.
   */
  off(event: string, fn: Listener): this {
    const entries = this.listeners.get(event);
    if (!entries) return this;

    const index = entries.findIndex((e) => e.fn === fn);
    if (index !== -1) {
      entries.splice(index, 1);
    }

    if (entries.length === 0) {
      this.listeners.delete(event);
    }

    return this;
  }

  /**
   * Emit an event, invoking all registered listeners.
   * Supports wildcard patterns: "user.*" matches "user.login", "user.logout".
   */
  emit(event: string, ...args: unknown[]): boolean {
    let handled = false;

    // Run through middleware chain
    let middlewareIndex = 0;
    const runMiddleware = (): void => {
      if (middlewareIndex < this.middlewares.length) {
        const mw = this.middlewares[middlewareIndex++];
        mw(event, args, runMiddleware);
      } else {
        handled = this.invokeListeners(event, args);
      }
    };
    runMiddleware();

    return handled;
  }

  /**
   * Invoke listeners for an event, including wildcard matches.
   */
  private invokeListeners(event: string, args: unknown[]): boolean {
    let invoked = false;

    // Direct match
    const directEntries = this.listeners.get(event);
    if (directEntries) {
      this.fireEntries(event, directEntries, args);
      invoked = true;
    }

    // Wildcard match — check all registered patterns
    for (const [pattern, entries] of this.listeners) {
      if (pattern === event) continue; // Already handled
      if (this.matchesWildcard(pattern, event)) {
        this.fireEntries(pattern, entries, args);
        invoked = true;
      }
    }

    return invoked;
  }

  /**
   * Fire all entries for a given event key, removing once-listeners.
   */
  private fireEntries(
    eventKey: string,
    entries: ListenerEntry[],
    args: unknown[]
  ): void {
    for (const entry of entries) {
      try {
        entry.fn(...args);
      } catch (err) {
        console.error(`Error in listener for "${eventKey}":`, err);
      }

      if (entry.once) {
        const current = this.listeners.get(eventKey);
        if (current) {
          const idx = current.indexOf(entry);
          if (idx !== -1) {
            current.splice(idx, 1);
          }
        }
      }
    }
  }

  /**
   * Check if a wildcard pattern matches an event name.
   * Supports * for single segment and ** for multiple segments.
   */
  private matchesWildcard(pattern: string, event: string): boolean {
    if (!pattern.includes("*")) return false;

    const patternParts = pattern.split(".");
    const eventParts = event.split(".");

    let pi = 0;
    let ei = 0;

    while (pi < patternParts.length && ei < eventParts.length) {
      if (patternParts[pi] === "**") {
        // ** matches zero or more segments
        if (pi === patternParts.length - 1) return true;
        // Try matching remaining pattern from each position
        for (let skip = ei; skip <= eventParts.length; skip++) {
          if (this.matchesWildcard(
            patternParts.slice(pi + 1).join("."),
            eventParts.slice(skip).join(".")
          )) {
            return true;
          }
        }
        return false;
      } else if (patternParts[pi] === "*") {
        // * matches exactly one segment
        pi++;
        ei++;
      } else if (patternParts[pi] === eventParts[ei]) {
        pi++;
        ei++;
      } else {
        return false;
      }
    }

    return pi === patternParts.length && ei === eventParts.length;
  }

  /**
   * Add middleware that intercepts all events before listeners fire.
   */
  use(middleware: Middleware): this {
    this.middlewares.push(middleware);
    return this;
  }

  /**
   * Set the maximum number of listeners per event before warning.
   */
  setMaxListeners(n: number): this {
    this.maxListeners = n;
    return this;
  }

  /**
   * Remove all listeners for a specific event, or all events if no name given.
   */
  removeAllListeners(event?: string): this {
    if (event) {
      this.listeners.delete(event);
    } else {
      this.listeners.clear();
    }
    return this;
  }

  /**
   * Get the count of listeners for an event.
   */
  listenerCount(event: string): number {
    return this.listeners.get(event)?.length ?? 0;
  }

  /**
   * Get all registered event names.
   */
  eventNames(): string[] {
    return Array.from(this.listeners.keys());
  }
}

export { EventEmitter };
export type { Listener, Middleware, ListenerEntry };
