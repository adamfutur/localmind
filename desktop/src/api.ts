// Basic wrapper around fetch to call FastAPI
const API_BASE = "http://localhost:8001/api";

export async function searchFiles(query: string) {
    const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
    return response.json();
}

export async function askQuestion(question: string) {
    const response = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
    });
    return response.json();
}

export async function triggerIndex() {
    const response = await fetch(`${API_BASE}/index`, {
        method: "POST"
    });
    return response.json();
}
