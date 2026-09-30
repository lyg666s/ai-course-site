// 章节跳转时的骨架屏：点击后立即出现，消除"卡顿感"
export default function Loading() {
  return (
    <div className="doc-wrap">
      <div className="doc" aria-busy="true" aria-label="加载中">
        <div className="mb-2 h-3.5 w-28 animate-pulse rounded bg-fill2" />
        <div className="mb-6 h-8 w-2/3 animate-pulse rounded bg-fill2" />
        <div className="space-y-3.5">
          {[92, 100, 96, 60].map((w, i) => (
            <div key={i} className="h-4 animate-pulse rounded bg-fill2" style={{ width: `${w}%` }} />
          ))}
        </div>
        <div className="my-8 h-32 animate-pulse rounded-xl bg-fill" />
        <div className="space-y-3.5">
          {[100, 88, 95, 72, 100].map((w, i) => (
            <div key={i} className="h-4 animate-pulse rounded bg-fill2" style={{ width: `${w}%` }} />
          ))}
        </div>
      </div>
    </div>
  );
}
