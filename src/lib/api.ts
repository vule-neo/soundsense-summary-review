import type { CallDetail, CallListItem } from "./types";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const fetchCalls = () => getJson<CallListItem[]>("/api/calls");
export const fetchCall = (id: string) => getJson<CallDetail>(`/api/calls/${id}`);
