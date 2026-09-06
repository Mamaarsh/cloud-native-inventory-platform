import { useState } from "react";
import { ImageIcon } from "lucide-react";
import { resolveMediaUrl } from "@/lib/media-url";

type ProductImageSize = "sm" | "md" | "lg";

interface ProductImageProps {
  src: string | null | undefined;
  alt?: string;
  size?: ProductImageSize;
  className?: string;
}

const sizes: Record<ProductImageSize, string> = {
  sm: "size-12 rounded-xl",
  md: "size-14 rounded-xl",
  lg: "size-20 rounded-xl",
};

export function ProductImage({
  src,
  alt = "",
  size = "sm",
  className = "",
}: ProductImageProps) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const imageUrl = resolveMediaUrl(src);
  const canRenderImage = Boolean(imageUrl && failedSource !== imageUrl);

  return (
    <span
      className={`grid shrink-0 place-items-center overflow-hidden border border-slate-200 bg-slate-100 text-slate-400 ${sizes[size]} ${className}`}
    >
      {canRenderImage ? (
        <img
          src={imageUrl ?? undefined}
          alt={alt}
          loading="lazy"
          className="size-full object-cover"
          onError={() => setFailedSource(imageUrl)}
        />
      ) : (
        <ImageIcon className="size-2/5" aria-hidden="true" />
      )}
    </span>
  );
}
