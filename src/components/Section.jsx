import SignalCard from "./SignalCard.jsx";

export default function Section({ title, count, items, onOpen }) {
  return (
    <section className="block">
      <div className="block-title">
        <span>{title}</span>
        <span className="n">[{count}]</span>
      </div>
      {items.length === 0 ? (
        <div className="empty">nothing matches the current filter</div>
      ) : (
        <div className="grid">
          {items.map((it, i) => (
            <SignalCard key={`${it.ticker}-${i}`} item={it} index={i} onOpen={onOpen} />
          ))}
        </div>
      )}
    </section>
  );
}
