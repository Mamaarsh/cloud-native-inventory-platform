import { useEffect, useId, useRef, useState } from "react";
import { ProductImage } from "@/components/products/ProductImage";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { getApiErrorMessage } from "@/lib/api-error";
import type { Product, ProductRequest } from "@/types";

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const SUPPORTED_IMAGE_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
]);

type ProductFormErrors = Partial<
  Record<"name" | "sku" | "price", string>
>;

interface SelectedImage {
  file: File;
  previewUrl: string;
}

interface ProductFormProps {
  product?: Product;
  onSubmit: (payload: ProductRequest) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
  serverError?: unknown;
}

export function ProductForm({ product, onSubmit, onCancel, isSubmitting, serverError }: ProductFormProps) {
  const [form, setForm] = useState<ProductRequest>({
    name: product?.name ?? "",
    sku: product?.sku ?? "",
    price: product?.price ?? "",
    is_active: product?.is_active ?? true,
  });
  const [errors, setErrors] = useState<ProductFormErrors>({});
  const [selectedImage, setSelectedImage] = useState<SelectedImage | null>(null);
  const [removeImage, setRemoveImage] = useState(false);
  const [imageError, setImageError] = useState<string | undefined>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputId = useId();
  const imageDescriptionId = `${imageInputId}-description`;

  useEffect(() => {
    return () => {
      if (selectedImage) URL.revokeObjectURL(selectedImage.previewUrl);
    };
  }, [selectedImage]);

  function clearSelectedImage(): void {
    setSelectedImage(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleImageChange(event: React.ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!SUPPORTED_IMAGE_TYPES.has(file.type)) {
      setImageError("Choose a JPEG, PNG, or WebP image.");
      clearSelectedImage();
      return;
    }
    if (file.size > MAX_IMAGE_SIZE) {
      setImageError("Image size must not exceed 5 MB.");
      clearSelectedImage();
      return;
    }

    setImageError(undefined);
    setRemoveImage(false);
    setSelectedImage({ file, previewUrl: URL.createObjectURL(file) });
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const nextErrors: ProductFormErrors = {};
    if (!form.name.trim()) nextErrors.name = "Product name is required.";
    if (!form.sku.trim()) nextErrors.sku = "SKU is required.";
    if (!form.price || Number(form.price) < 0) nextErrors.price = "Enter a valid non-negative price.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0 || imageError) return;
    await onSubmit({
      ...form,
      name: form.name.trim(),
      sku: form.sku.trim(),
      ...(selectedImage ? { image: selectedImage.file } : {}),
      ...(removeImage ? { remove_image: true } : {}),
    });
  }

  const displayedImage = selectedImage?.previewUrl
    ?? (removeImage ? null : product?.image);

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
      {serverError ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700" role="alert">{getApiErrorMessage(serverError)}</p> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Product name" dir="auto" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} error={errors.name} autoFocus />
        <Input label="SKU" value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value })} error={errors.sku} placeholder="SKU-001" />
      </div>
      <Input label="Unit price" type="number" min="0" step="0.01" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} error={errors.price} />
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <div className="flex items-start gap-4">
          <ProductImage
            src={displayedImage}
            alt={displayedImage ? "Product image preview" : ""}
            size="lg"
          />
          <div className="min-w-0 flex-1">
            <label
              htmlFor={imageInputId}
              className="mb-2 block text-[13px] font-bold text-slate-700"
            >
              Product image
            </label>
            <input
              ref={fileInputRef}
              id={imageInputId}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              aria-invalid={Boolean(imageError)}
              aria-describedby={imageDescriptionId}
              disabled={isSubmitting}
              onChange={handleImageChange}
              className="block w-full text-sm text-slate-600 file:mr-3 file:min-h-9 file:cursor-pointer file:rounded-lg file:border file:border-slate-300 file:bg-white file:px-3 file:text-sm file:font-semibold file:text-slate-700 hover:file:border-slate-400 hover:file:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-70"
            />
            <p
              id={imageDescriptionId}
              className={`mt-2 text-xs ${imageError ? "text-rose-600" : "text-slate-500"}`}
            >
              {imageError ?? "JPEG, PNG, or WebP. Maximum size 5 MB."}
            </p>
            {selectedImage ? (
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => {
                  clearSelectedImage();
                  setImageError(undefined);
                }}
                className="mt-2 text-xs font-semibold text-slate-600 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Clear selected image
              </button>
            ) : product?.image && !removeImage ? (
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => {
                  setRemoveImage(true);
                  setImageError(undefined);
                }}
                className="mt-2 text-xs font-semibold text-rose-600 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Remove image
              </button>
            ) : removeImage ? (
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => setRemoveImage(false)}
                className="mt-2 text-xs font-semibold text-slate-600 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Keep current image
              </button>
            ) : null}
          </div>
        </div>
      </div>
      <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} className="size-4 accent-brand-600" />
        <span>
          <span className="block text-sm font-semibold text-slate-800">Active product</span>
          <span className="block text-xs text-slate-500">Only active products can be added to new orders.</span>
        </span>
      </label>
      <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" isLoading={isSubmitting}>{product ? "Save changes" : "Create product"}</Button>
      </div>
    </form>
  );
}
