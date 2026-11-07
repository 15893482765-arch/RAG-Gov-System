import axios from "axios";

export const api = axios.create({ baseURL: "/api" });

export type Citation = {
  chunk_id: string;
  document_id: string;
  filename: string;
  section?: string;
  page?: number;
  quote: string;
  score: number;
  label: string;
};

export async function streamChat(
  payload: Record<string, unknown>,
  onEvent: (name: string, data: any) => void,
) {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok || !response.body) throw new Error("聊天请求失败");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const name = block.match(/^event: (.+)$/m)?.[1] ?? "message";
      const raw = block.match(/^data: (.+)$/m)?.[1];
      if (raw) onEvent(name, JSON.parse(raw));
    }
  }
}

