import { useEffect, useRef } from "react";
import { arrow, dirLabel, articlesOf, breakdown } from "../lib/format.js";

export default function SourcePanel({ item, returnFocus, onClose }) {
  const closeRef = useRef(null);
  const articles = articlesOf(item);
  // AI-used sources first, then coverage.
  const ordered = [...articles].sort(
    (a, b) => (b.used_by_ai ? 1 : 0) - (a.used_by_ai ? 1 : 0)
  );
  const bd = breakdown(item);
  const bdParts = Object.entries(bd).map(([name, n]) => `${name} ×${n}`);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      if (returnFocus && document.contains(returnFocus)) returnFocus.focus();
    };
  }, [onClose, returnFocus]);

  return (
    <div
      className="backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="panel" role="dialog" aria-modal="true" aria-labelledby="panel-ticker">
        <div className="panel-bar">
          <span className="panel-mark">source overview</span>
          <button ref={closeRef} className="panel-close" onClick={onClose} aria-label="Close">
            ESC ✕
          </button>
        </div>

        <div className={`panel-body ${item.direction}`}>
          <div className="panel-head">
            <div>
              <div className="ticker" id="panel-ticker">{item.ticker}</div>
              <div className="company">{item.company || " "}</div>
            </div>
            <span className={`dir ${item.direction}`}>
              {arrow(item.direction)} {dirLabel(item.direction)}
            </span>
          </div>

          <div className="conf">
            <div className="conf-row">
              <span>CONFIDENCE</span>
              <span>{item.confidence}%</span>
            </div>
            <div className="bar">
              <i style={{ width: `${item.confidence}%` }} />
            </div>
          </div>

          <p className="panel-reason">{item.reason || ""}</p>

          {bdParts.length > 0 && (
            <div className="coverage">
              COVERAGE <b>{bdParts.join(" · ")}</b>
            </div>
          )}

          <div className="sources-title">
            <span>SOURCES</span>
            <span className="n">[{ordered.length}]</span>
          </div>

          {ordered.length === 0 ? (
            <div className="source-item">
              <span className="faint">no sources</span>
            </div>
          ) : (
            ordered.map((a, i) => (
              <div className="source-item" key={i}>
                {a.url ? (
                  <a href={a.url} target="_blank" rel="noopener">
                    {a.headline || "(untitled)"}
                  </a>
                ) : (
                  <span className="plain">{a.headline || "(untitled)"}</span>
                )}
                <div className="source-meta">
                  <span className="tag">{a.source || "unknown"}</span>
                  {a.used_by_ai ? (
                    <span className="used">✓ used by AI</span>
                  ) : (
                    <span className="used muted">· coverage</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
