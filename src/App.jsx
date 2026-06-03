import { useEffect, useMemo, useState } from "react";
import Header from "./components/Header.jsx";
import Controls from "./components/Controls.jsx";
import Section from "./components/Section.jsx";
import SourcePanel from "./components/SourcePanel.jsx";

// Data lives on main's root (committed by analyze.py every ~30 min). The
// deployed app is a build artifact, so we read the data from the public raw
// URL, then fall back to the bundled snapshot if raw is unreachable.
const RAW_URL =
  "https://raw.githubusercontent.com/singhh-piyush/trading-advisor/main/results.json";

async function loadData() {
  const candidates = [`${RAW_URL}?t=${Date.now()}`, `./results.json?t=${Date.now()}`];
  let lastErr;
  for (const url of candidates) {
    try {
      const res = await fetch(url);
      if (res.ok) return await res.json();
      lastErr = new Error(`HTTP ${res.status}`);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("no data");
}

export default function App() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null); // { item, returnFocus }

  useEffect(() => {
    let alive = true;
    loadData()
      .then((d) => alive && (setData(d), setStatus("ready")))
      .catch(() => alive && setStatus("error"));
    return () => {
      alive = false;
    };
  }, []);

  const items = data?.items || [];

  // Shareable deep link: ?open=NVDA opens that ticker's source panel on load.
  useEffect(() => {
    if (status !== "ready") return;
    const want = new URLSearchParams(window.location.search).get("open");
    if (!want) return;
    const hit = items.find((it) => (it.ticker || "").toUpperCase() === want.toUpperCase());
    if (hit) setSelected({ item: hit, returnFocus: null });
  }, [status, items]);

  const { watch, radar } = useMemo(() => {
    const q = query.trim().toUpperCase();
    const match = (it) =>
      (filter === "all" || it.direction === filter) &&
      (!q || (it.ticker || "").includes(q));
    return {
      watch: items.filter((it) => it.on_watchlist && match(it)),
      radar: items.filter((it) => !it.on_watchlist && match(it)),
    };
  }, [items, filter, query]);

  return (
    <div className="wrap">
      <Header data={data} status={status} signals={items.length} />

      {status === "error" ? (
        <div className="empty" style={{ marginTop: 28 }}>
          No data yet. Run the Update Trading Advisor workflow once to generate it.
        </div>
      ) : (
        <>
          <Controls filter={filter} setFilter={setFilter} query={query} setQuery={setQuery} />
          <Section
            title="WATCHLIST"
            count={watch.length}
            items={watch}
            onOpen={setSelected}
          />
          <Section
            title="ON THE RADAR"
            count={radar.length}
            items={radar}
            onOpen={setSelected}
          />
        </>
      )}

      {selected && (
        <SourcePanel
          item={selected.item}
          returnFocus={selected.returnFocus}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
