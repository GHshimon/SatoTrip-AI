/**
 * 宿泊施設検索API
 */
import { apiClient } from './client';
import { HotelCategory, HotelSearchRequest, HotelSearchResult } from '../../types';

/**
 * 宿泊施設カテゴリ一覧を取得
 */
export async function getHotelCategories(): Promise<{ categories: HotelCategory[] }> {
  return await apiClient.get<{ categories: HotelCategory[] }>('/api/hotels/categories');
}

/**
 * 宿泊施設検索
 */
export async function searchHotels(request: HotelSearchRequest): Promise<HotelSearchResult> {
  const params = new URLSearchParams();
  params.append('area', request.area);
  
  if (request.category) {
    params.append('category', request.category);
  }
  if (request.hotelName) {
    params.append('hotel_name', request.hotelName);
  }
  if (request.checkIn) {
    params.append('check_in', request.checkIn);
  }
  if (request.checkOut) {
    params.append('check_out', request.checkOut);
  }
  if (request.numGuests) {
    params.append('num_guests', request.numGuests.toString());
  }
  
  return await apiClient.get<HotelSearchResult>(`/api/hotels/search?${params.toString()}`);
}

