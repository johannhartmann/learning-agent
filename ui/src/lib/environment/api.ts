export function getInternalApiBase() {
  return process.env.NEXT_PUBLIC_INTERNAL_API_BASE || "http://127.0.0.1:8001";
}

