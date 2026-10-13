export async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch { /* not JSON */ }
  if (!res.ok) {
    const d = data && data.detail;
    throw new Error(d ? (typeof d === "string" ? d : JSON.stringify(d)) : `${res.status} ${res.statusText}`);
  }
  return data;
}

export const postJSON = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });