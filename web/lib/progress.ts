// 学习进度（localStorage），与旧版站点共用同一存储键，进度无缝延续
"use client";

export const LS_KEY = "pycourse-done";

export type DoneMap = Record<string, true>;

export function getDone(): DoneMap {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || "{}") as DoneMap;
  } catch {
    return {};
  }
}

export function setDone(map: DoneMap) {
  localStorage.setItem(LS_KEY, JSON.stringify(map));
  window.dispatchEvent(new Event("pycourse-progress"));
}

export function isDone(key: string): boolean {
  return !!getDone()[key];
}

export function toggleDone(key: string) {
  const d = getDone();
  if (d[key]) delete d[key];
  else d[key] = true;
  setDone(d);
}
