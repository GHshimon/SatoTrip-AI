
export interface User {
  id: string;
  name: string;
  avatar: string;
  role: 'user' | 'admin';
}

export interface Spot {
  id: string;
  name: string;
  description: string;
  area: string;
  category: 'History' | 'Nature' | 'Food' | 'Culture' | 'Shopping' | 'Art' | 'Relax';
  durationMinutes: number;
  rating: number;
  image: string;
  price?: number;
  tags?: string[]; // Added for AI/SNS tags
  location?: {
    lat: number;
    lng: number;
  };
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
}