import { fmtAge } from "../lib/format.js";

export default function Header({ data, status, signals }) {
  let badge;
  if (status === "error") badge = <span className="badge nodata">NO DATA</span>;
  else if (status === "loading") badge = <span className="badge loading">SYNCING</span>;
  else if (data?.sample) badge = <span className="badge sample">SAMPLE</span>;
  else badge = <span className="badge live"><i className="pulse" />LIVE</span>;

  const watching = (data?.watchlist || []).length;

  return (
    <header className="head">
      <div className="head-row">
        <h1 className="brand">
          Trading <span className="brand-accent">Advisor</span>
        </h1>
        {badge}
      </div>
      <div className="status">
        <span>updated <b>{fmtAge(data?.updated_at)}</b></span>
        <span className="sep">/</span>
        <span>signals <b>{signals}</b></span>
        <span className="sep">/</span>
        <span>watching <b>{watching}</b></span>
      </div>
    </header>
  );
}
