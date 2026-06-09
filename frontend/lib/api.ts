import axios from "axios";
import type { UploadResponse, ComparisonResult, Annotation, ComparisonListItem, ChatMessage } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "pl_token";


export async function postChatStream(
  comparisonId: string,
  messages: ChatMessage[],
  token?: string | null
): Promise<Response> {
  const authToken = token || (typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null);

  return fetch(`${API_URL}/api/chat/${comparisonId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
    body: JSON.stringify({ messages }),
  });
}

const api = axios.create({ baseURL: API_URL, timeout: 180_000 });

// Attach token to every axios call (mirrors the interceptor in AuthContext)
api.interceptors.request.use((config) => {
  const t = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// ── Documents ──────────────────────────────────────────────────────────────────
export async function uploadDocument(
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await api.post<UploadResponse>("/api/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return res.data;
}

// ── Comparisons ────────────────────────────────────────────────────────────────
export async function analyzeDocuments(doc1Id: string, doc2Id: string): Promise<ComparisonResult> {
  const res = await api.post<ComparisonResult>("/api/comparison/analyze", {
    doc1_id: doc1Id, doc2_id: doc2Id,
  });
  return res.data;
}

export async function getComparison(id: string): Promise<ComparisonResult> {
  const res = await api.get<ComparisonResult>(`/api/comparison/${id}`);
  return res.data;
}

export async function listHistory(): Promise<ComparisonListItem[]> {
  const res = await api.get<ComparisonListItem[]>("/api/comparison/history");
  return res.data;
}

export async function deleteComparison(id: string): Promise<void> {
  await api.delete(`/api/comparison/${id}`);
}

// ── Annotations ────────────────────────────────────────────────────────────────
export async function getAnnotations(comparisonId: string): Promise<Annotation[]> {
  const res = await api.get<Annotation[]>(`/api/annotations/${comparisonId}`);
  return res.data;
}

export async function createAnnotation(payload: {
  comparison_id: string;
  change_id: string;
  change_type?: string;
  author?: string;
  text: string;
}): Promise<Annotation> {
  const res = await api.post<Annotation>("/api/annotations/", payload);
  return res.data;
}

export async function resolveAnnotation(id: string): Promise<Annotation> {
  const res = await api.patch<Annotation>(`/api/annotations/${id}/resolve`);
  return res.data;
}

export async function deleteAnnotation(id: string): Promise<void> {
  await api.delete(`/api/annotations/${id}`);
}

// ── Export ─────────────────────────────────────────────────────────────────────
export async function exportComparison(
  comparisonId: string,
  format: "pdf" | "docx"
): Promise<void> {
  const res = await api.get<Blob>(`/api/export/${comparisonId}/${format}`, {
    responseType: "blob",
    headers: {
      Accept: format === "pdf"
        ? "application/pdf"
        : "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
  });

  const blob = res.data;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `comparison_${comparisonId.slice(0, 8)}.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function healthCheck(): Promise<boolean> {
  try { await api.get("/health"); return true; } catch { return false; }
}
