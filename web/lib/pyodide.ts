// Pyodide（浏览器里的 CPython）单例加载器
"use client";

let promise: Promise<any> | null = null;

const LOCAL = `${process.env.NEXT_PUBLIC_BASE_PATH || ""}/pyodide/`;
const CDN = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";

function loadFrom(indexURL: string): Promise<any> {
  // webpackIgnore: 运行时加载 Pyodide 的 ESM 入口，不参与打包
  return import(/* webpackIgnore: true */ indexURL + "pyodide.mjs").then((m) =>
    m.loadPyodide({ indexURL })
  );
}

export function ensurePyodide(): Promise<any> {
  if (!promise) {
    promise = loadFrom(LOCAL).catch(() => loadFrom(CDN));
  }
  return promise;
}
