// Basic wrapper around fetch to call FastAPI
const API_BASE = "http://localhost:8001/api";

export interface SearchResult {
    type: "semantic" | "keyword" | string;
    path: string;
    score?: number;
    content_snippet?: string;
}

export interface SearchStatus {
    files: number;
    vectors: number;
    vector_metadata: number;
}

async function readJson<T>(response: Response, action: string): Promise<T> {
    if (!response.ok) {
        const detail = await response.text().catch(() => "");
        throw new Error(
            `${action} failed (${response.status})${detail ? `: ${detail}` : ""}`
        );
    }
    return response.json() as Promise<T>;
}

export async function searchFiles(query: string, limit = 20): Promise<SearchResult[]> {
    const response = await fetch(
        `${API_BASE}/search?q=${encodeURIComponent(query)}&limit=${limit}`
    );
    return readJson<SearchResult[]>(response, "Search");
}

export async function triggerIndex(path?: string): Promise<{ status: string }> {
    const suffix = path ? `?path=${encodeURIComponent(path)}` : "";
    const response = await fetch(`${API_BASE}/index${suffix}`, { method: "POST" });
    return readJson<{ status: string }>(response, "Indexing");
}

export async function getSearchStatus(): Promise<SearchStatus> {
    const response = await fetch(`${API_BASE}/search-status`);
    return readJson<SearchStatus>(response, "Status");
}
