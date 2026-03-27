const API_BASE = "http://localhost:8000";

export async function analyzeWithStream(articleText, onThinking, onResult, onError) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ article_text: articleText }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by double newlines
    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventType = null;
      let dataStr = "";

      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          dataStr += line.slice(6);
        }
      }

      if (eventType && dataStr) {
        try {
          const data = JSON.parse(dataStr);
          if (eventType === "thinking") {
            onThinking(data);
          } else if (eventType === "result") {
            onResult(data);
          } else if (eventType === "error") {
            onError(data.message);
          }
        } catch (e) {
          console.warn("Failed to parse SSE data:", e);
        }
      }
    }
  }
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
