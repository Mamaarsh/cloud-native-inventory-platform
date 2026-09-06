const apiBaseUrl = import.meta.env.VITE_API_URL?.trim();
const developmentProxyTarget = import.meta.env.DEV
  ? import.meta.env.VITE_API_PROXY_TARGET?.trim()
  : undefined;
const productMediaPathPrefix = "/media/products/";

function absoluteOrigin(value: string | undefined): string | null {
  if (!value) return null;

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function mediaOrigin(): string {
  return absoluteOrigin(apiBaseUrl)
    ?? absoluteOrigin(developmentProxyTarget)
    ?? window.location.origin;
}

export function resolveMediaUrl(source: string | null | undefined): string | null {
  const normalizedSource = source?.trim();
  if (!normalizedSource) return null;

  if (normalizedSource.startsWith("blob:")) return normalizedSource;

  try {
    const url = new URL(normalizedSource, mediaOrigin());
    const isHttpUrl = url.protocol === "http:" || url.protocol === "https:";
    const isProductMedia = url.pathname.startsWith(productMediaPathPrefix);
    return isHttpUrl && isProductMedia ? url.toString() : null;
  } catch {
    return null;
  }
}
