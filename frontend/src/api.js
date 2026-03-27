const API_BASE = "http://localhost:8000";

export async function extractClaims(articleText) {
  const response = await fetch(`${API_BASE}/api/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ article_text: articleText }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fullAnalyze(articleText) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ article_text: articleText }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function sendSatelliteData(satelliteResponse) {
  const response = await fetch(`${API_BASE}/api/satellite-data`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(satelliteResponse),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
