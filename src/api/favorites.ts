/**
 * スポットお気に入りAPI
 */
import { apiClient } from './client';
import { Spot } from '@/types';
import { transformSpotResponse } from './spots';

/** お気に入りスポット一覧を取得 */
export async function getFavoriteSpots(): Promise<Spot[]> {
  const response = await apiClient.get<any[]>('/api/favorites');
  return response.map(transformSpotResponse);
}

/** お気に入りスポットのIDのみ取得（一覧画面での状態表示用） */
export async function getFavoriteSpotIds(): Promise<string[]> {
  return apiClient.get<string[]>('/api/favorites/ids');
}

/** スポットをお気に入りに追加 */
export async function addFavoriteSpot(spotId: string): Promise<Spot> {
  const response = await apiClient.post<any>(`/api/favorites/${spotId}`);
  return transformSpotResponse(response);
}

/** お気に入りから削除 */
export async function removeFavoriteSpot(spotId: string): Promise<void> {
  await apiClient.delete<void>(`/api/favorites/${spotId}`);
}
