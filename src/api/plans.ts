/**
 * プラン管理API
 */
import { apiClient } from './client';
import { Plan, PlanRequest } from '../../types';

export interface PlanGenerateRequest {
  destination: string;
  days: number;
  budget: string;
  themes: string[];
  pending_spots: any[];
  check_in_date?: string;
  check_out_date?: string;
  num_guests?: number;
}

export interface PlanCreateRequest {
  title: string;
  area: string;
  days: number;
  people?: number;
  budget?: number;
  thumbnail?: string;
  spots: any[];
  grounding_urls?: string[];
}

export interface PlanSpotUpdate {
  id: string;
  startTime?: string;
  durationMinutes?: number;
  transportDuration?: number;
  transportMode?: string;
  order?: number;
}

export interface PlanUpdateRequest {
  title?: string;
  area?: string;
  days?: number;
  people?: number;
  budget?: number;
  thumbnail?: string;
  spots?: PlanSpotUpdate[];
  grounding_urls?: string[];
  is_favorite?: boolean;
  folder_id?: string | null;
  check_in_date?: string;
  check_out_date?: string;
}

export interface RouteInfo {
  geometry: [number, number][];
  distance_meters: number;
  distance_km: number;
  duration_seconds: number;
  duration_minutes: number;
  source: string;
}

export interface PlanRouteResponse {
  plan_id: string;
  day: number | null;
  route: RouteInfo;
}

/**
 * AIプラン生成
 */
export async function generatePlan(request: PlanGenerateRequest): Promise<Plan> {
  const response = await apiClient.post<any>('/api/plans/generate-plan', request);
  // バックエンドのレスポンスをフロントエンドのPlan型に変換
  return transformPlanResponse(response);
}

/**
 * プラン一覧取得
 */
export async function getPlans(): Promise<Plan[]> {
  const response = await apiClient.get<any[]>('/api/plans');
  return response.map(transformPlanResponse);
}

/**
 * プラン詳細取得
 */
export async function getPlan(id: string): Promise<Plan> {
  const response = await apiClient.get<any>(`/api/plans/${id}`);
  return transformPlanResponse(response);
}

/**
 * プラン作成
 */
export async function createPlan(planData: PlanCreateRequest): Promise<Plan> {
  const response = await apiClient.post<any>('/api/plans', planData);
  return transformPlanResponse(response);
}

/**
 * プラン更新
 */
export async function updatePlan(id: string, planData: PlanUpdateRequest): Promise<Plan> {
  const response = await apiClient.put<any>(`/api/plans/${id}`, planData);
  return transformPlanResponse(response);
}

/**
 * プラン削除
 */
export async function deletePlan(id: string): Promise<void> {
  await apiClient.delete(`/api/plans/${id}`);
}

/**
 * プランのルート情報取得
 */
export async function getPlanRoute(planId: string, day?: number): Promise<PlanRouteResponse> {
  const params = day !== undefined ? `?day=${day}` : '';
  const response = await apiClient.get<PlanRouteResponse>(`/api/plans/${planId}/route${params}`);
  return response;
}

/**
 * バックエンドのレスポンスをフロントエンドのPlan型に変換
 */
function transformPlanResponse(data: any): Plan {
  // spots内のタグを文字列のリストに変換
  const transformedSpots = (data.spots || []).map((spot: any) => {
    try {
      // spot.spot.tagsを処理
      if (spot && spot.spot && spot.spot.tags && Array.isArray(spot.spot.tags)) {
        const transformedTags = spot.spot.tags.map((tag: any) => {
          if (typeof tag === 'string') {
            return tag;
          } else if (tag && typeof tag === 'object') {
            // 構造化タグオブジェクトの場合はvalueまたはnormalizedを使用
            return tag.value || tag.normalized || String(tag);
          }
          return String(tag);
        });
        return {
          ...spot,
          spot: {
            ...spot.spot,
            tags: transformedTags
          }
        };
      }
      // spot.tagsを直接処理（spot.spotがない場合）
      if (spot && spot.tags && Array.isArray(spot.tags) && !spot.spot) {
        const transformedTags = spot.tags.map((tag: any) => {
          if (typeof tag === 'string') {
            return tag;
          } else if (tag && typeof tag === 'object') {
            return tag.value || tag.normalized || String(tag);
          }
          return String(tag);
        });
        return {
          ...spot,
          tags: transformedTags
        };
      }
    } catch (error) {
      // エラーが発生した場合は元のspotを返す
    }
    return spot;
  });

  return {
    id: data.id,
    title: data.title,
    area: data.area,
    days: data.days,
    people: data.people || 2,
    budget: data.budget || 0,
    createdAt: data.created_at || new Date().toLocaleDateString(),
    thumbnail: data.thumbnail || '',
    spots: transformedSpots,
    groundingUrls: data.grounding_urls || [],
    isFavorite: data.is_favorite || false,
    folderId: data.folder_id || null,
    excludedSpots: data.excluded_spots || null, // 除外されたスポット情報
    checkInDate: data.check_in_date || undefined,
    checkOutDate: data.check_out_date || undefined,
  };
}

