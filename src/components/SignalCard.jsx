import { useRef } from "react";
import { arrow, dirLabel, articlesOf } from "../lib/format.js";

export default function SignalCard({ item, index, onOpen }) {
  const ref = useRef(null);
  const articles = articlesOf(item);
  const extra = articles.length - 1;

  const open = () => onOpen({ item, returnFocus: ref.current });

  const onKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      open();
    }
  };

  const onClick = (e) => {
    if (e.target.closest("a")) return; // let the source link open normally
    open();
  };

  return (
    <article
      ref={ref}
      className={`card ${item.direction}`}
      style={{ animationDelay: `${index * 35}ms` }}
      role="button"
      tabIndex={0}
      aria-label={`${item.ticker}, open source overview`}
      onClick={onClick}
      onKeyDown={onKeyDown}
    >
      <div className="card-top">
        <div>
          <div className="ticker">{item.ticker}</div>
          <div className="company">{item.company || " "}</div>
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

      <p className="reason">{item.reason || ""}</p>

      <div className="src">
        <span className="tag">SRC</span>
        {item.headline ? (
          <span className="src-line">
            {item.url ? (
              <a href={item.url} target="_blank" rel="noopener">
                {item.headline}
              </a>
            ) : (
              <span>{item.headline}</span>
            )}
            <span className="tag">
              {item.source || ""}
              {extra > 0 ? ` +${extra}` : ""}
            </span>
          </span>
        ) : (
          <span className="faint">no source</span>
        )}
      </div>
    </article>
  );
}
