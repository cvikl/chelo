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

    // Parse SSE events from buffer
    const lines = buffer.split("\n");
    buffer = "";

    let currentEvent = null;
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ") && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          if (currentEvent === "thinking") {
            onThinking(data);
          } else if (currentEvent === "result") {
            onResult(data);
          } else if (currentEvent === "error") {
            onError(data.message);
          }
        } catch {
          // Incomplete JSON, put back in buffer
          buffer = line + "\n";
        }
        currentEvent = null;
      } else if (line.trim() === "") {
        currentEvent = null;
      } else {
        // Incomplete line, put back in buffer
        buffer += line + "\n";
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
