/**
 * Data transformation pipeline for processing user analytics events.
 * Supports chained transformations, filtering, and aggregation.
 */

interface AnalyticsEvent {
  userId: string;
  eventType: string;
  timestamp: number;
  properties: Record<string, unknown>;
  sessionId: string;
}

interface AggregatedMetric {
  userId: string;
  metric: string;
  value: number;
  period: string;
  sampleCount: number;
}

type TransformFn = (events: AnalyticsEvent[]) => AnalyticsEvent[];
type FilterFn = (event: AnalyticsEvent) => boolean;

/**
 * Deduplicate events by generating a composite key from userId + eventType + timestamp.
 * Events within a 1-second window of each other are considered duplicates.
 */
function deduplicateEvents(events: AnalyticsEvent[]): AnalyticsEvent[] {
  const seen = new Set<string>();
  const result: AnalyticsEvent[] = [];

  for (const event of events) {
    // Round timestamp to nearest second for dedup window
    const roundedTs = Math.floor(event.timestamp / 1000);
    const key = `${event.userId}:${event.eventType}:${roundedTs}`;

    if (!seen.has(key)) {
      seen.add(key);
      result.push(event);
    }
  }

  return result;
}

/**
 * Enrich events with session duration calculated from the session's first event.
 */
function enrichWithSessionDuration(events: AnalyticsEvent[]): AnalyticsEvent[] {
  const sessionStarts = new Map<string, number>();

  // First pass: find earliest timestamp per session
  for (const event of events) {
    const existing = sessionStarts.get(event.sessionId);
    if (existing === undefined || event.timestamp < existing) {
      sessionStarts.set(event.sessionId, event.timestamp);
    }
  }

  // Second pass: calculate duration from session start
  return events.map((event) => ({
    ...event,
    properties: {
      ...event.properties,
      sessionDuration: event.timestamp - sessionStarts.get(event.sessionId)!,
    },
  }));
}

/**
 * Filter events to a specific time range (inclusive on both ends).
 */
function filterByTimeRange(startMs: number, endMs: number): FilterFn {
  return (event: AnalyticsEvent) =>
    event.timestamp >= startMs && event.timestamp <= endMs;
}

/**
 * Filter events to specific event types.
 */
function filterByEventType(...types: string[]): FilterFn {
  const typeSet = new Set(types);
  return (event: AnalyticsEvent) => typeSet.has(event.eventType);
}

/**
 * Aggregate events into metrics per user per time period.
 * Period is "hour", "day", or "week".
 */
function aggregateByPeriod(
  events: AnalyticsEvent[],
  metric: string,
  period: "hour" | "day" | "week",
  valueFn: (event: AnalyticsEvent) => number
): AggregatedMetric[] {
  const periodMs = {
    hour: 3600 * 1000,
    day: 86400 * 1000,
    week: 604800 * 1000,
  };

  const buckets = new Map<string, { total: number; count: number }>();

  for (const event of events) {
    const periodStart = Math.floor(event.timestamp / periodMs[period]) * periodMs[period];
    const bucketKey = `${event.userId}:${periodStart}`;

    const existing = buckets.get(bucketKey) || { total: 0, count: 0 };
    existing.total += valueFn(event);
    existing.count++;
    buckets.set(bucketKey, existing);
  }

  const results: AggregatedMetric[] = [];
  for (const [key, { total, count }] of buckets) {
    const [userId, periodStart] = key.split(":");
    results.push({
      userId,
      metric,
      value: total / count,
      period: new Date(parseInt(periodStart)).toISOString(),
      sampleCount: count,
    });
  }

  return results;
}

/**
 * Build and execute a transformation pipeline on analytics events.
 */
class Pipeline {
  private transforms: TransformFn[] = [];
  private filters: FilterFn[] = [];

  addTransform(fn: TransformFn): Pipeline {
    this.transforms.push(fn);
    return this;
  }

  addFilter(fn: FilterFn): Pipeline {
    this.filters.push(fn);
    return this;
  }

  execute(events: AnalyticsEvent[]): AnalyticsEvent[] {
    let result = [...events];

    // Apply filters first
    for (const filter of this.filters) {
      result = result.filter(filter);
    }

    // Then apply transforms in order
    for (const transform of this.transforms) {
      result = transform(result);
    }

    return result;
  }
}

/**
 * Calculate the moving average of a numeric property over a sliding window.
 * Window size is in number of events (not time-based).
 */
function movingAverage(
  events: AnalyticsEvent[],
  property: string,
  windowSize: number
): number[] {
  const values = events.map(
    (e) => (e.properties[property] as number) ?? 0
  );
  const result: number[] = [];

  for (let i = 0; i < values.length; i++) {
    const windowStart = Math.max(0, i - windowSize + 1);
    const window = values.slice(windowStart, i + 1);
    const sum = window.reduce((a, b) => a + b, 0);
    result.push(sum / windowSize);
  }

  return result;
}

/**
 * Detect anomalous events by checking if a metric exceeds a threshold
 * number of standard deviations from the mean.
 */
function detectAnomalies(
  events: AnalyticsEvent[],
  property: string,
  stdDevThreshold: number = 2
): AnalyticsEvent[] {
  const values = events.map(
    (e) => (e.properties[property] as number) ?? 0
  );

  // Calculate mean
  const mean = values.reduce((a, b) => a + b, 0) / values.length;

  // Calculate standard deviation
  const squaredDiffs = values.map((v) => (v - mean) ** 2);
  const variance = squaredDiffs.reduce((a, b) => a + b, 0) / values.length;
  const stdDev = Math.sqrt(variance);

  // Filter anomalies
  return events.filter((event) => {
    const value = (event.properties[property] as number) ?? 0;
    return Math.abs(value - mean) > stdDev * stdDevThreshold;
  });
}

export {
  Pipeline,
  deduplicateEvents,
  enrichWithSessionDuration,
  filterByTimeRange,
  filterByEventType,
  aggregateByPeriod,
  movingAverage,
  detectAnomalies,
};
export type { AnalyticsEvent, AggregatedMetric };
