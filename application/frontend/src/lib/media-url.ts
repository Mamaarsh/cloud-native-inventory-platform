const apiBaseUrl = import.meta.env.VITE_API_URL?.trim();
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
    ?? window.location.origin;
}

export function resolveMediaUrl(source: string | null | undefined): string | null {
  const normalizedSource = source?.trim();
  if (!normalizedSource) return null;

  if (normalizedSource.startsWith("blob:")) return normalizedSource;

  try {
    const sourceUrl = new URL(normalizedSource, mediaOrigin());
    const isHttpUrl =
      sourceUrl.protocol === "http:" || sourceUrl.protocol === "https:";
    const isProductMedia = sourceUrl.pathname.startsWith(productMediaPathPrefix);
    if (!isHttpUrl || !isProductMedia) return null;

    const browserUrl = new URL(sourceUrl.pathname, mediaOrigin());
    browserUrl.search = sourceUrl.search;
    browserUrl.hash = sourceUrl.hash;
    return browserUrl.toString();
  } catch {
    return null;
  }
}
