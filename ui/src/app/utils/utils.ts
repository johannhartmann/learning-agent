import { Message } from "@langchain/langgraph-sdk";

type TextBlock = { type: "text"; text?: string };
const isTextBlock = (val: unknown): val is TextBlock =>
  typeof val === "object" && val !== null &&
  "type" in (val as Record<string, unknown>) &&
  (val as Record<string, unknown>).type === "text";

export function extractStringFromMessageContent(message: Message): string {
  return typeof message.content === "string"
    ? message.content
    : Array.isArray(message.content)
      ? message.content
          .filter((c: unknown) => isTextBlock(c) || typeof c === "string")
          .map((c: unknown) => (typeof c === "string" ? c : (c as TextBlock).text || ""))
          .join("")
      : "";
}
