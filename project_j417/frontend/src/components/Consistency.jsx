export default function Consistency({ data }) {
  if (!data || data.mean_score == null) return null;
  return (
    <div className="consistency">
      <div>
        Translation consistency: mean {data.mean_score}, lowest {data.min_score} (threshold {data.threshold}),{" "}
        {data.flagged.length} sentence(s) flagged
      </div>
      {data.flagged.map((f, i) => (
        <div className="flag" key={i}>
          <div>{f.score} · EN: {f.source}</div>
          <div>SI: {f.translation}</div>
        </div>
      ))}
    </div>
  );
}