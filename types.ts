
export interface User {
  id: string;
  name: string;
  avatar: string;
  role: 'user' | 'admin';
}

// スポットカテゴリの定義（全画面で統一）
export type SpotCategory = 'History' | 'Nature' | 'Food' | 'Culture' | 'Shopping' | 'Art' | 'Relax' | 'Tourism' | 'Experience' | 'Event' | 'HotSpring' | 'ScenicView' | 'Cafe' | 'Hotel' | 'Drink' | 'Fashion' | 'Date' | 'Drive';

// カテゴリリスト（表示順序を統一）
export const SPOT_CATEGORIES: SpotCategory[] = [
  'History',
  'Nature',
  'Food',
  'Culture',
  'Shopping',
  'Art',
  'Relax',
  'Tourism',
  'Experience',
  'Event',
  'HotSpring',
  'ScenicView',
  'Cafe',
  'Hotel',
  'Drink',
  'Fashion',
  'Date',
  'Drive'
];

// カテゴリの日本語名マッピング
export const SPOT_CATEGORY_LABELS: Record<SpotCategory, string> = {
  'History': '歴史',
  'Nature': '自然',
  'Food': 'グルメ',
  'Culture': '文化',
  'Shopping': 'ショッピング',
  'Art': 'アート',
  'Relax': 'リラックス',
  'Tourism': '観光',
  'Experience': '体験',
  'Event': 'イベント',
  'HotSpring': '温泉',
  'ScenicView': '絶景',
  'Cafe': 'カフェ',
  'Hotel': 'ホテル',
  'Drink': '飲み物',
  'Fashion': 'ファッション',
  'Date': 'デート',
  'Drive': 'ドライブ'
};

export interface Spot {
  id: string;
  name: string;
  description: string;
  area: string;
  category: SpotCategory;
  durationMinutes: number;
  rating: number;
  image: string;
  price?: number;
  tags?: string[]; // Added for AI/SNS tags
  location?: {
    lat: number;
    lng: number;
  };
  created_at?: string;  // ISO 8601形式の日時文字列
  updated_at?: string;  // ISO 8601形式の日時文字列
}

export interface PlanSpot {
  id: string; // Unique ID for this instance in the plan
  spotId: string;
  spot: Spot;
  day: number;
  startTime?: string;
  note?: string;
  transportMode?: 'walk' | 'train' | 'car' | 'bus';
  transportDuration?: number;
  isMustVisit?: boolean; // Flag for user-selected spots
  originalQuery?: string; // Log the search query used if generated dynamically
}

export interface Plan {
  id: string;
  title: string;
  area: string;
  days: number;
  people: number;
  budget: number;
  createdAt: string;
  thumbnail: string;
  spots: PlanSpot[];
  groundingUrls?: string[];
  isFavorite?: boolean;
  folderId?: string | null;
  excludedSpots?: Array<{ name: string; reason: string }> | null; // 除外されたスポット情報（プラン生成時のみ）
  checkInDate?: string; // チェックイン日（YYYY-MM-DD形式）
  checkOutDate?: string; // チェックアウト日（YYYY-MM-DD形式）
}

export interface PlanFolder {
  id: string;
  name: string;
  parentId?: string | null;
  createdAt: string;
  children?: PlanFolder[]; // For tree structure in UI
}

export interface Hotel {
  id: string;
  name: string;
  area: string;
  address: string;
  pricePerNight: number;
  rating: number;
  reviewCount: number;
  image: string;
  tags: string[];
  features: string[];
}

export interface AdminStat {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  icon: string;
  color: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: Date;
}

export interface PlanRequest {
  destination: string;
  days: number;
  budget: string;
  themes: string[];
  checkInDate?: string;
  checkOutDate?: string;
  numGuests?: number;
}

export interface HotelCategory {
  name: string;
  description: string;
  icon: string;
}

export interface HotelSearchLink {
  name: string;
  area: string;
  link: string;
  type: string;
  affiliate: string;
  description: string;
  error?: string;
}

export interface HotelSearchRequest {
  area: string;
  category?: string;
  hotelName?: string;
  checkIn?: string;
  checkOut?: string;
  numGuests?: number;
}

export interface HotelSearchResult {
  area: string;
  category?: string;
  hotel_name?: string;
  check_in?: string;
  check_out?: string;
  num_guests: number;
  search_query: string;
  links: {
    rakuten: HotelSearchLink;
    yahoo: HotelSearchLink;
    jalan: HotelSearchLink;
  };
  errors?: Array<{
    site: string;
    affiliate: string;
    error: string;
  }>;
}