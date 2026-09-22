export function Skeleton({ width = "100%", height = 14 }: { width?: string | number; height?: number }) {
  return <div className="skeleton" style={{ width, height }} />;
}

export function CardSkeleton() {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <Skeleton width={70} height={18} />
        <Skeleton width={50} height={18} />
      </div>
      <Skeleton width="60%" height={12} />
      <Skeleton height={6} />
      <Skeleton width="40%" height={10} />
    </div>
  );
}
