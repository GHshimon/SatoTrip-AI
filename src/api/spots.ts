/**
 * スポット管理API
 */
import { apiClient } from './client';
import { Spot } from '@/types';

export interface SpotsFilters {
  area?: string;
  category?: string;
  keyword?: string;
  skip?: number;
  limit?: number;
}

export interface SpotCreateRequest {
  name: string;
  description?: string;
  area?: string;
  category?: string;
  duration_minutes?: number;
  rating?: number;
  image?: string;
  price?: number;
  tags?: string[];
  latitude?: number;
  longitude?: number;
}

export interface SpotUpdateRequest {
  name?: string;
  description?: string;
  area?: string;
  category?: string;
  duration_minutes?: number;
  rating?: number;
  image?: string;
  price?: number;
  tags?: string[];
  latitude?: number;
  longitude?: number;
}

/**
 * スポット一覧取得（フィルタリング対応）
 */
export async function getSpots(filters: SpotsFilters = {}): Promise<Spot[]> {
  const params = new URLSearchParams();
  if (filters.area) params.append('area', filters.area);
  if (filters.category) params.append('category', filters.category);
  if (filters.keyword) params.append('keyword', filters.keyword);
  if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
  if (filters.limit !== undefined) params.append('limit', filters.limit.toString());

  const queryString = params.toString();
  const endpoint = `/api/spots${queryString ? `?${queryString}` : ''}`;

  const response = await apiClient.get<any[]>(endpoint);
  return response.map(transformSpotResponse);
}

/**
 * スポット詳細取得
 */
export async function getSpot(id: string): Promise<Spot> {
  const response = await apiClient.get<any>(`/api/spots/${id}`);
  return transformSpotResponse(response);
}

/**
 * エリア別スポット取得
 */
export async function getSpotsByArea(area: string, skip: number = 0, limit: number = 100): Promise<Spot[]> {
  const response = await apiClient.get<any[]>(`/api/spots/area/${encodeURIComponent(area)}?skip=${skip}&limit=${limit}`);
  return response.map(transformSpotResponse);
}

/**
 * スポット作成（管理者のみ）
 */
export async function createSpot(spotData: SpotCreateRequest): Promise<Spot> {
  const response = await apiClient.post<any>('/api/spots', spotData);
  return transformSpotResponse(response);
}

/**
 * スポット更新（管理者のみ）
 */
export async function updateSpot(id: string, spotData: SpotUpdateRequest): Promise<Spot> {
  const response = await apiClient.put<any>(`/api/spots/${id}`, spotData);
  return transformSpotResponse(response);
}

/**
 * スポット削除（管理者のみ）
 */
export async function deleteSpot(id: string): Promise<void> {
  await apiClient.delete(`/api/spots/${id}`);
}


/**
 * スポットリサーチ（管理者のみ）
 */
export async function researchSpot(spotName: string): Promise<Partial<SpotCreateRequest>> {
  const response = await apiClient.post<any>('/api/spots/research', { spot_name: spotName });
  return {
    name: response.name,
    area: response.area,
    category: response.category,
    description: response.description,
    price: response.price,
    image: response.image,
    duration_minutes: response.duration_minutes
  };
}

export interface BulkAddRequest {
  prefecture: string;
  max_results_per_keyword?: number;
  max_keywords?: number;
  max_total_videos?: number;
  add_location?: boolean;
  run_async?: boolean;
  category?: string;
}

export interface BulkAddResponse {
  success: boolean;
  imported: number;
  errors: number;
  skipped: number;
  total_keywords: number;
  quota_exceeded: boolean;
  processed_keywords: number;
  failed_keywords: number;
  total_videos: number;
  location_updated?: number;
  location_errors?: number;
  error?: string;
  job_id?: string;
  job_status?: string;
}

export type BulkAddJobStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * 都道府県名で複数キーワード検索してまとめてスポットを追加（管理者のみ）
 */
export async function bulkAddSpotsByPrefecture(
  prefecture: string,
  options?: { max_results_per_keyword?: number; max_keywords?: number; max_total_videos?: number; add_location?: boolean; run_async?: boolean; category?: string }
): Promise<BulkAddResponse> {
  const request: BulkAddRequest = {
    prefecture,
    max_results_per_keyword: options?.max_results_per_keyword ?? 5,
    max_keywords: options?.max_keywords,
    max_total_videos: options?.max_total_videos,
    add_location: options?.add_location ?? true,
    run_async: options?.run_async,
    category: options?.category
  };
  const response = await apiClient.post<BulkAddResponse>('/api/spots/bulk-add-by-prefecture', request);
  return response;
}

export async function getBulkAddJobStatus(jobId: string): Promise<BulkAddResponse> {
  const response = await apiClient.get<BulkAddResponse>(`/api/spots/bulk-add-jobs/${encodeURIComponent(jobId)}`);
  return response;
}

export async function getSearchKeywordsConfig(): Promise<Record<string, any>> {
  const response = await apiClient.get<Record<string, any>>('/api/spots/config/search-keywords');
  return response;
}

// タグ管理API
export interface TagStats {
  value: string;
  count: number;
  category?: string;
  normalized: string;
}

export interface TagResponse {
  tags: TagStats[];
  total: number;
  categories: Record<string, { name: string; description: string }>;
}

export interface TagNormalizeRequest {
  tags: string[];
}

export interface TagNormalizeResponse {
  normalized_tags: Array<{
    value: string;
    category?: string;
    priority: number;
    source: string;
    normalized: string;
  }>;
  original_tags: string[];
}

/**
 * タグ一覧取得（統計情報付き）
 */
export async function getTags(category?: string): Promise<TagResponse> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  const queryString = params.toString();
  const endpoint = `/api/spots/tags${queryString ? `?${queryString}` : ''}`;
  return apiClient.get<TagResponse>(endpoint);
}

/**
 * 推奨タグ一覧取得
 */
export async function getRecommendedTags(category?: string): Promise<string[]> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  const queryString = params.toString();
  const endpoint = `/api/spots/tags/recommended${queryString ? `?${queryString}` : ''}`;
  return apiClient.get<string[]>(endpoint);
}

/**
 * タグ正規化
 */
export async function normalizeTags(tags: string[]): Promise<TagNormalizeResponse> {
  return apiClient.post<TagNormalizeResponse>('/api/spots/tags/normalize', { tags });
}

/**
 * バックエンドのレスポンスをフロントエンドのSpot型に変換
 */
function transformSpotResponse(data: any): Spot {
  return {
    id: data.id,
    name: data.name,
    description: data.description || '',
    area: data.area || '',
    category: data.category as any || 'Culture',
    durationMinutes: data.duration_minutes || 60,
    rating: data.rating || 0,
    image: data.image || '',
    price: data.price,
    tags: data.tags || [],
    location: data.latitude && data.longitude
      ? { lat: data.latitude, lng: data.longitude }
      : undefined,
    created_at: data.created_at,
    updated_at: data.updated_at,
  };
}

