// Small presentation helpers, ported from the original vanilla dashboard.
// JSX escapes text for us, so there is no esc() here.

export function fmtAge(iso) {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  const h = Math.floor(mins / 60);
  if (h < 24) return h + "h ago";
  return Math.floor(h / 24) + "d ago";
}

export function arrow(d) {
  return d === "up" ? "▲" : d === "down" ? "▼" : "■";
}

export function dirLabel(d) {
  return d === "up" ? "BULLISH" : d === "down" ? "BEARISH" : "NEUTRAL";
}

// Tolerate older results.json with no "articles": synthesize one article from
// the single headline/source/url so nothing downstream throws.
export function articlesOf(item) {
  if (Array.isArray(item.articles) && item.articles.length) return item.articles;
  if (item.headline) {
    return [
      {
        headline: item.headline,
        source: item.source || "",
        url: item.url || "",
        used_by_ai: true,
      },
    ];
  }
  return [];
}

// Counts of articles per source, falling back to deriving them from articlesOf
// when the backend did not provide source_breakdown.
export function breakdown(item) {
  const bd = item.source_breakdown;
  if (bd && Object.keys(bd).length) return bd;
  const out = {};
  for (const a of articlesOf(item)) {
    const name = a.source || "unknown";
    out[name] = (out[name] || 0) + 1;
  }
  return out;
}
