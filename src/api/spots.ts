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

/**
 * 都道府県名で複数キーワード検索してまとめてスポットを追加（管理者のみ）
 */
export async function bulkAddSpotsByPrefecture(
  prefecture: string,
  options?: { max_results_per_keyword?: number; max_keywords?: number; max_total_videos?: number; add_location?: boolean; run_async?: boolean }
): Promise<BulkAddResponse> {
  const request: BulkAddRequest = {
    prefecture,
    max_results_per_keyword: options?.max_results_per_keyword ?? 5,
    max_keywords: options?.max_keywords,
    max_total_videos: options?.max_total_videos,
    add_location: options?.add_location ?? true,
    run_async: options?.run_async
  };
  const response = await apiClient.post<BulkAddResponse>('/api/spots/bulk-add-by-prefecture', request);
  return response;
}

export async function getBulkAddJobStatus(jobId: string): Promise<BulkAddResponse> {
  const response = await apiClient.get<BulkAddResponse>(`/api/spots/bulk-add-jobs/${encodeURIComponent(jobId)}`);
  return response;
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
  };
}

