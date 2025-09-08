// Client-side base path that proxies through Next.js
export function getInternalApiBase() {
  return "/api/internal";
}

// Server-side upstream base (used inside Next route handlers)
export function getInternalUpstreamBase() {
  return process.env.INTERNAL_API_BASE || "http://server:8001";
}
