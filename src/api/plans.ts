/**
 * プラン管理API
 */
import { apiClient } from './client';
import { Plan, PlanRequest } from '../types';

export interface PlanGenerateRequest {
  destination: string;
  days: number;
  budget: string;
  themes: string[];
  pending_spots: any[];
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

export interface PlanUpdateRequest {
  title?: string;
  
  people?: number;
  budget?: number;
  thumbnail?: string;
  spots?: any[];
  grounding_urls?: string[];
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
 * バックエンドのレスポンスをフロントエンドのPlan型に変換
 */
function transformPlanResponse(data: any): Plan {
  return {
    id: data.id,
    title: data.title,
    area: data.area,
    days: data.days,
    people: data.people || 2,
    budget: data.budget || 0,
    createdAt: data.created_at || new Date().toLocaleDateString(),
    thumbnail: data.thumbnail || '',
    spots: data.spots || [],
    groundingUrls: data.grounding_urls || [],
  };
}

