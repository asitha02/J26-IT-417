import type { LabelRequest, LabelStats, LibraryItem, ModelInfo, RankRequest, RankResponse } from "./types";

const BASE = "/api/segments";

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  const res = await fetch(input, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const getLibrary = () => request<LibraryItem[]>(`${BASE}/library`);

export const rankSegments = (body: RankRequest) =>
  request<RankResponse>(`${BASE}/rank`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const setLabel = async (body: LabelRequest) => {
  const res = await fetch(`${BASE}/labels`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(res.statusText);
};

export const getLabelStats = () => request<LabelStats>(`${BASE}/labels/stats`);

export const getModel = () => request<ModelInfo>(`${BASE}/model`);

export const trainRanker = () => request<ModelInfo>(`${BASE}/train`, { method: "POST" });

export const labelsExportUrl = `${BASE}/labels`;

