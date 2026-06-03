const FILTERS = [
  { f: "all", label: "ALL" },
  { f: "up", label: "▲ BULLISH" },
  { f: "down", label: "▼ BEARISH" },
];

export default function Controls({ filter, setFilter, query, setQuery }) {
  return (
    <div className="controls">
      <div className="filters" role="group" aria-label="Filter by direction">
        {FILTERS.map(({ f, label }) => (
          <button
            key={f}
            className={"filter" + (filter === f ? " active" : "")}
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
          >
            {label}
          </button>
        ))}
      </div>
      <label className="search">
        <span className="search-mark">$</span>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="filter ticker"
          autoComplete="off"
          aria-label="Filter by ticker"
        />
      </label>
    </div>
  );
}
