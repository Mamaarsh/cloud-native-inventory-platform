import { apiClient } from "@/api/client";
import type { PaginatedResponse, Product, ProductQueryParams, ProductRequest } from "@/types";

const path = "/v1/products/";

export async function listProducts(params: ProductQueryParams = {}): Promise<PaginatedResponse<Product>> {
  const { data } = await apiClient.get<PaginatedResponse<Product>>(path, { params });
  return data;
}

export async function listAllProducts(): Promise<Product[]> {
  const products: Product[] = [];
  let page = 1;
  let response = await listProducts({ page, ordering: "name" });
  products.push(...response.results);
  while (response.next) {
    page += 1;
    response = await listProducts({ page, ordering: "name" });
    products.push(...response.results);
  }
  return products;
}

export async function getProduct(id: number): Promise<Product> {
  const { data } = await apiClient.get<Product>(`${path}${id}/`);
  return data;
}

export async function createProduct(payload: ProductRequest): Promise<Product> {
  const { data } = await apiClient.post<Product>(path, payload);
  return data;
}

export async function updateProduct(id: number, payload: Partial<ProductRequest>): Promise<Product> {
  const { data } = await apiClient.patch<Product>(`${path}${id}/`, payload);
  return data;
}

export async function deleteProduct(id: number): Promise<void> {
  await apiClient.delete(`${path}${id}/`);
}
