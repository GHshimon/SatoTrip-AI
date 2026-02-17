
import React, { useState, useEffect, useRef } from 'react';
import { Plan, PlanSpot, PlanRequest, Spot, HotelCategory, HotelSearchRequest, HotelSearchResult } from '../types';
import { plans, spots } from '../mockData';
import { AppConfig } from '../config';
import * as planApi from '../src/api/plans';
import * as hotelApi from '../src/api/hotels';
import * as spotApi from '../src/api/spots';
import { SpotAddModal } from '../components/SpotAddModal';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// 47 Prefectures Data grouped by Region
const regions = [
  {
    id: 'hokkaido_tohoku',
    name: '北海道・東北',
    prefs: ['北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県']
  },
  {
    id: 'kanto',
    name: '関東',
    prefs: ['茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県']
  },
  {
    id: 'chubu',
    name: '中部',
    prefs: ['新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県']
  },
  {
    id: 'kinki',
    name: '近畿',
    prefs: ['三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県']
  },
  {
    id: 'chugoku_shikoku',
    name: '中国・四国',
    prefs: ['鳥取県', '島根県', '岡山県', '広島県', '山口県', '徳島県', '香川県', '愛媛県', '高知県']
  },
  {
    id: 'kyushu_okinawa',
    name: '九州・沖縄',
    prefs: ['福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']
  }
];

// Consistent Color Definitions
const DAY_COLORS = ['red', 'blue', 'green', 'orange', 'violet', 'gold', 'grey', 'black'];
const TAILWIND_COLORS = [
  { text: 'text-red-500', border: 'border-red-500', bg: 'bg-red-500', ring: 'ring-red-500' },
  { text: 'text-blue-500', border: 'border-blue-500', bg: 'bg-blue-500', ring: 'ring-blue-500' },
  { text: 'text-green-500', border: 'border-green-500', bg: 'bg-green-500', ring: 'ring-green-500' },
  { text: 'text-orange-500', border: 'border-orange-500', bg: 'bg-orange-500', ring: 'ring-orange-500' },
  { text: 'text-violet-500', border: 'border-violet-500', bg: 'bg-violet-500', ring: 'ring-violet-500' },
  { text: 'text-yellow-500', border: 'border-yellow-500', bg: 'bg-yellow-500', ring: 'ring-yellow-500' },
  { text: 'text-gray-500', border: 'border-gray-500', bg: 'bg-gray-500', ring: 'ring-gray-500' },
  { text: 'text-black', border: 'border-black', bg: 'bg-black', ring: 'ring-black' }
];

// --- Helper Functions for Plan Generation (To be moved to backend/services later) ---

const getPlaceholderImage = (category: string) => {
  const map: { [key: string]: string } = {
    'History': 'https://lh3.googleusercontent.com/aida-public/AB6AXuAShXYjdbz-HnK7UqIW4uc4AZ496i8tXykch0UKvnQwe6n_9a-cv___S2BV1YSadUeJVTnb6Ac-Xn9i8P895lfgnXKB2U_Ql8IrJtWNuPO5bTkYvlbHbTxaqI8zSTD6EDZgX0v1YPMM6z12OloKCQ9oTnD5cf5viHlpjgpDJZow2SEA22XtgaZFIgDrllAmfp-2dXo7BO3x0_r-wEZPTXsKb_Yu3XbV-TCPEc-e9_CB0HrJbOsJ_4A7dzX6ycs0hafPVW8HFBVX_Wc',
    'Nature': 'https://lh3.googleusercontent.com/aida-public/AB6AXuAeVnterwZUcIr_dHrmXTHWem-fhJZYrRIWmGMZwaJ5KBTdMdVCQMT6KKrR8xh6-l0UMa0T2adzosld8R0KhwIM-r1FcuFvrEqutfFparfHDvBKIMg51csqjQKS1vsXZwDbGrOyTQF2jjBtvUyAP3uCnTHRSNoDlBgQzR3rYtQmRKFkjlP_haiSWh8e27yLW5bualqrI1L_rL2cgDS_brxRCN2nhQDimZbzFS9uykDAREpHbJpzQfrwr3ccva-Suc4VexVJ1kbMN5g',
    'Food': 'https://lh3.googleusercontent.com/aida-public/AB6AXuBiz9O1N-rC38EKaCKrZkWnHlT3BNZ2_ioD-wgiVPdzSpMhKhO3bsYTdlN2d962ouh2Y6ndN2m2hwwi66cHtF8va1NmQDzbPm6gsD_f3ENFYpul8C5xCQdYyg5L4F2oehZ-RSaX3qsSkHVRo8VZHV29PQLIzodnZHTMLmXCXafeYw58rsj-upDlQ8YS0PO5cSMWGxG5cdIDktT9M9QWLREsNF9yEIr9OtF4iA9jik2eiDxlCKhBXzXvcWZ8ezofvaAEYUy0SSh-dLs',
    'Shopping': 'https://lh3.googleusercontent.com/aida-public/AB6AXuCdz-G_h0k6RJ3ry5mYzbSplIUw_uZ5qvm3fcvKuTI_XYyFKcG68gUEetqtlQsV6_U1xlG079Vpq_TmxVlDP2d2K96Sfhx1rjR-3m6bWu5Ku1CyVc2kxCAgomaqoyXdIumn0GcRGUIXu9M03dG1mDlpgkUnoSxGNOuJkRg14Zn1UxD0jfMbySj3L6sxEdOnU_UuEM0WYzUQm4ddP4z7fnsvSYyZ8lfcSe42HtmUn6qJPpDhy-vShozL-8t_hPBHxrFvo2btn6-mH-U',
    'Art': 'https://lh3.googleusercontent.com/aida-public/AB6AXuArmdAAUBEs4_kBwVdTmpuR2OfwVfsnuqpfOW8o6YWTUrdw0JI4zs3pJeMtgQpXsDVnHvoaRj71X4LCZjWiSWhNozFKug1GWGnWbuGJjbUpFz5cOnU05JAyR-ZPjvc3AFBjpphbBBQJP7OysashtY3lbHqk094CidIAJKIGNzTHdRA7CYfNkRDzFrbowwxcaAizYWLVJyznEgBOEQBUehT5glYdGF_rLl-QC2lRGHfMCIUGg6mg_xMYsBvBYOvctwU3eC0toiGleIk',
    'Culture': 'https://lh3.googleusercontent.com/aida-public/AB6AXuAIE9KY3NbwOR_uiyFxDVZghfvQkwD-MLEiMsYd3OWTd2PZVlugkL73UpjtfuR27PT9dGvsp6yba1AIFSkGvW9u9cVyWC8bNTlZY61SJIv92jn8jRNntaXLuEuyLDlKkMFLSpAAHq0aeUF-QQZE6KdIOnRYPTS4izKkioibuNR3vT83IorS0ejLIGlzO3Vuy2f4auwI2HounBs0OyWvPFsXbCpuE1aaGS6xTTFvICOVyv-2OJJc7dt4PaywbEmrpz9fhKDYDgM02wM',
    'Relax': 'https://lh3.googleusercontent.com/aida-public/AB6AXuByu9CNi9hOLtjiLiucijbtHgSiJCF6DviVaqhAUWPloauo1vytIhyD2RQuchAOWLCBhwSo0bXC2HAZUt-xxCFEkw5SdMPJRFlCrYEAfYsrJnSxj6AQ5F6wvR73B8IQig5ErAFJhGwgf6vWdl18Hx0XcPCmkrTch_3vpdGQJalTKBokTujisdDxfUHaPHsi4puHmwdxjkReaRs0-k1dhPpwg4q1M7KATonxNU62Bmss_eblgT7JH3VyLc9e03M06iN9aVXLOHvQ1Vk'
  }
  return map[category] || map['Culture'];
}

// Helper to generate jittered coordinates (MOCK: Replace with real Geocoding API)
const getSimulatedLocation = (area: string): { lat: number; lng: number } => {
  let center = { lat: 35.6895, lng: 139.6917 }; // Tokyo default
  if (area.includes('京都')) center = { lat: 35.0116, lng: 135.7681 };
  if (area.includes('鹿児島')) center = { lat: 31.5966, lng: 130.5571 };
  if (area.includes('大阪')) center = { lat: 34.6937, lng: 135.5023 };
  if (area.includes('北海道') || area.includes('札幌')) center = { lat: 43.0618, lng: 141.3545 };
  if (area.includes('沖縄') || area.includes('那覇')) center = { lat: 26.2124, lng: 127.6809 };
  if (area.includes('名古屋') || area.includes('愛知')) center = { lat: 35.1815, lng: 136.9066 };
  if (area.includes('福岡') || area.includes('博多')) center = { lat: 33.5902, lng: 130.4017 };
  if (area.includes('仙台') || area.includes('宮城')) center = { lat: 38.2682, lng: 140.8694 };
  if (area.includes('金沢') || area.includes('石川')) center = { lat: 36.5613, lng: 136.6562 };
  if (area.includes('広島')) center = { lat: 34.3853, lng: 132.4553 };

  // Add randomness to spread pins
  return {
    lat: center.lat + (Math.random() - 0.5) * 0.05,
    lng: center.lng + (Math.random() - 0.5) * 0.05
  };
};

// generateAiPlan関数は削除 - バックエンドAPIを使用

// SortableSpotItemコンポーネント
interface SortableSpotItemProps {
  spot: PlanSpot;
  index: number;
  isEditMode: boolean;
  currentColor: { text: string; border: string; bg: string; ring: string };
  editedSpots: Record<string, { durationMinutes?: number; transportDuration?: number }>;
  handleSpotEdit: (spotId: string, field: 'durationMinutes' | 'transportDuration', value: number) => void;
  calculateEndTime: (startTime: string, durationMinutes: number) => string;
  transportModes: Record<string, 'public' | 'car' | 'walk'>;
  handleModeChange: (id: string, mode: 'public' | 'car' | 'walk') => void;
  calculateDuration: (baseMode: string | undefined, baseDuration: number | undefined, targetMode: string) => number;
  totalSpots: number;
  onDelete?: (spotId: string) => void;
}

const SortableSpotItem: React.FC<SortableSpotItemProps> = ({
  spot,
  index,
  isEditMode,
  currentColor,
  editedSpots,
  handleSpotEdit,
  calculateEndTime,
  transportModes,
  handleModeChange,
  calculateDuration,
  totalSpots,
  onDelete,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: spot.id, disabled: !isEditMode });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className={isDragging ? 'z-50' : ''}>
      <React.Fragment>
        <div className="relative flex items-start gap-4">
          {/* ドラッグハンドル（編集モード時のみ） */}
          {isEditMode && (
            <div
              {...attributes}
              {...listeners}
              className="cursor-move text-gray-400 hover:text-gray-600 mt-2"
              title="ドラッグして順番を変更"
            >
              <span className="material-symbols-outlined text-2xl">drag_handle</span>
            </div>
          )}
          {/* Dynamic Colored Icon */}
          <div className={`absolute -left-[4.5rem] w-12 h-12 rounded-full bg-white border-4 flex items-center justify-center shadow-sm z-10 transition-colors ${currentColor.border} ${currentColor.text}`}>
            <span className="material-symbols-outlined">
              {spot.spot.category === 'Food' ? 'restaurant' : 
               spot.spot.category === 'Shopping' ? 'shopping_bag' : 
               spot.spot.category === 'Hotel' ? 'hotel' : 
               'palette'}
            </span>
          </div>
          <div className="flex-1 pt-1 group">
            {isEditMode ? (
              <div className="space-y-2 mb-2">
                {spot.spot.category !== 'Hotel' && (
                  <div className="flex items-center gap-2">
                    <label className="text-text-muted text-xs font-medium w-20">滞在時間:</label>
                    <input
                      type="number"
                      min="5"
                      max="480"
                      value={editedSpots[spot.id]?.durationMinutes ?? spot.spot.durationMinutes ?? 60}
                      onChange={(e) => handleSpotEdit(spot.id, 'durationMinutes', parseInt(e.target.value) || 60)}
                      className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                    />
                    <span className="text-text-muted text-xs">分</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <label className="text-text-muted text-xs font-medium w-20">移動時間:</label>
                  <input
                    type="number"
                    min="0"
                    max="300"
                    value={editedSpots[spot.id]?.transportDuration ?? spot.transportDuration ?? 20}
                    onChange={(e) => handleSpotEdit(spot.id, 'transportDuration', parseInt(e.target.value) || 0)}
                    className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                  />
                  <span className="text-text-muted text-xs">分</span>
                </div>
                <p className="text-text-muted text-xs">
                  {spot.spot.category === 'Hotel' ? (
                    <>開始: {spot.startTime} - 終了: 翌日 (宿泊)</>
                  ) : (
                    <>開始: {spot.startTime} - 終了: {calculateEndTime(spot.startTime || '09:00', editedSpots[spot.id]?.durationMinutes ?? spot.spot.durationMinutes ?? 60)}</>
                  )}
                </p>
              </div>
            ) : (
              spot.spot.category === 'Hotel' ? (
                <p className="text-text-muted font-medium text-sm mb-1">
                  {spot.startTime} - 翌日 <span className="text-xs">(宿泊)</span>
                </p>
              ) : (
                <p className="text-text-muted font-medium text-sm mb-1">
                  {spot.startTime} - {calculateEndTime(spot.startTime || '09:00', spot.spot.durationMinutes || 60)}
                  {' '}
                  <span className="text-xs">(滞在: {spot.spot.durationMinutes || 60}分)</span>
                </p>
              )
            )}
            <h3 className="text-xl font-bold mb-1 flex items-center gap-2">
              {spot.spot.name}
              {spot.isMustVisit && (
                <span className="bg-primary text-white text-[10px] px-2 py-0.5 rounded-full font-bold shadow-sm animate-pulse flex items-center gap-1">
                  <span className="material-symbols-outlined text-[12px]">check</span> MUST
                </span>
              )}
            </h3>
            <p className="text-text-muted text-sm mb-2 line-clamp-2">{spot.spot.description}</p>
            {/* SNS Tag Display */}
            <div className="flex gap-2 flex-wrap">
              {spot.spot.tags && spot.spot.tags.length > 0 ? (
                spot.spot.tags.map((tag, i) => {
                  // タグがオブジェクトの場合はvalueまたはnormalizedを使用、文字列の場合はそのまま使用
                  const tagText = typeof tag === 'string' ? tag : (tag?.value || tag?.normalized || String(tag));
                  return (
                    <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-gradient-to-r from-pink-500 to-purple-500 text-white text-[10px] rounded-full font-bold shadow-sm">
                      <span className="material-symbols-outlined text-[10px]">trending_up</span> {tagText}
                    </span>
                  );
                })
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-text-muted text-[10px] rounded-full font-bold">
                  4.8 <span className="material-symbols-outlined text-[10px] text-yellow-500 fill">star</span>
                </span>
              )}
            </div>
          </div>
          <div className="w-20 h-20 rounded-lg overflow-hidden shadow-sm flex-shrink-0 hidden sm:block">
            <img src={spot.spot.image} alt="" className="w-full h-full object-cover" />
          </div>
          {isEditMode && onDelete && (
            <button
              onClick={() => onDelete(spot.id)}
              className="w-8 h-8 flex items-center justify-center text-text-muted hover:bg-red-100 hover:text-red-500 rounded-full transition-colors"
              title="スポットを削除"
            >
              <span className="material-symbols-outlined text-lg">delete</span>
            </button>
          )}
        </div>
        {spot.transportMode && index < totalSpots - 1 && (
          <TransportLine
            mode={transportModes[spot.id] || 'public'}
            duration={(() => {
              const selectedMode = transportModes[spot.id] || 'public';
              // 元のプランのtransportModeを使用（spot.transportModeは既に元の値）
              const baseMode = spot.transportMode;
              // 選択された移動手段が元の移動手段と異なる場合、またはtransportDurationが存在しない場合は再計算
              const needsRecalc = selectedMode !== baseMode && 
                !(selectedMode === 'public' && (baseMode === 'train' || baseMode === 'bus'));
              return needsRecalc || !spot.transportDuration
                ? calculateDuration(baseMode, spot.transportDuration || 20, selectedMode)
                : spot.transportDuration;
            })()}
            onModeChange={(m) => handleModeChange(spot.id, m)}
          />
        )}
      </React.Fragment>
    </div>
  );
};

// Helper to display transport
const TransportLine: React.FC<{
  mode: string;
  duration: number;
  onModeChange: (mode: 'car' | 'walk' | 'public') => void;
}> = ({ mode, duration, onModeChange }) => {
  return (
    <div className="flex items-center gap-4 py-2 animate-fade-in relative z-0">
      {/* Main pill */}
      <div className="flex items-center gap-2 text-primary bg-primary/5 px-3 py-1.5 rounded-full border border-primary/10 transition-all">
        <span className="material-symbols-outlined text-lg">
          {mode === 'car' ? 'directions_car' : mode === 'walk' ? 'directions_walk' : 'train'}
        </span>
        <span className="text-sm font-bold whitespace-nowrap">
          <span className="text-lg mx-1">{duration}</span> 分
        </span>
      </div>

      {/* Switcher */}
      <div className="flex items-center p-1 bg-white border border-gray-200 rounded-full shadow-sm">
        {[
          { id: 'car', icon: 'directions_car', label: '車' },
          { id: 'public', icon: 'train', label: '公共' },
          { id: 'walk', icon: 'directions_walk', label: '徒歩' }
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => onModeChange(m.id as any)}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${mode === m.id
              ? 'bg-primary text-white shadow-sm transform scale-105'
              : 'text-text-muted hover:bg-gray-100 hover:text-text-light'
              }`}
            title={`${m.label}に切り替え`}
          >
            <span className="material-symbols-outlined text-sm">{m.icon}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

// Leaflet Map Component
const LeafletMap: React.FC<{
  planSpots: PlanSpot[],
  areaName: string,
  selectedDay: number,
  planId?: string,
  visibleDays?: Set<number>,
  onRouteInfoUpdate?: (day: number, info: { distance: number; duration: number; transportation?: string; spotDurations?: Array<{ spotId: string; duration: number }> }) => void
}> = ({ planSpots, areaName, selectedDay, planId, visibleDays, onRouteInfoUpdate }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const layerGroupRef = useRef<any>(null);

  // Initialize Map (Run once)
  useEffect(() => {
    if (!(window as any).L || !mapRef.current) return;
    const L = (window as any).L;

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const map = L.map(mapRef.current).setView(AppConfig.MAP.DEFAULT_CENTER, AppConfig.MAP.DEFAULT_ZOOM);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    mapInstanceRef.current = map;
    layerGroupRef.current = L.layerGroup().addTo(map);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Markers (Run when data changes)
  useEffect(() => {
    if (!mapInstanceRef.current || !layerGroupRef.current || !(window as any).L) return;

    const L = (window as any).L;
    const map = mapInstanceRef.current;
    const layers = layerGroupRef.current;
    let isMounted = true;

    // Clear existing
    layers.clearLayers();

    const bounds = L.latLngBounds();
    let hasMarkers = false;

    // Group spots by day
    const spotsByDay: Record<number, PlanSpot[]> = {};
    planSpots.forEach(s => {
      if (!spotsByDay[s.day]) spotsByDay[s.day] = [];
      spotsByDay[s.day].push(s);
    });

    // 1. Draw Markers (Synchronous)
    planSpots.forEach((ps, idx) => {
      if (ps.spot.location) {
        hasMarkers = true;
        const isSelectedDay = ps.day === selectedDay;
        const color = DAY_COLORS[(ps.day - 1) % DAY_COLORS.length] || 'blue';

        const opacity = isSelectedDay ? 1.0 : 0.5;
        const zIndexOffset = isSelectedDay ? 1000 : 0;

        const icon = new L.Icon({
          iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
          shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
          iconSize: [25, 41],
          iconAnchor: [12, 41],
          popupAnchor: [1, -34],
          shadowSize: [41, 41]
        });

        const marker = L.marker([ps.spot.location.lat, ps.spot.location.lng], {
          icon,
          opacity: opacity,
          zIndexOffset: zIndexOffset
        }).bindPopup(`
           <div class="text-center p-2" style="min-width: 200px;">
             <strong class="text-sm text-gray-500">${ps.day}日目</strong>
             ${ps.startTime ? `<br/><span class="text-xs text-gray-400">🕐 ${ps.startTime}</span>` : ''}
             <br/><b class="text-lg">${ps.spot.name}</b>
             ${ps.spot.area ? `<br/><span class="text-xs text-gray-500">📍 ${ps.spot.area}</span>` : ''}
             <br/><span class="text-xs text-gray-500">${ps.spot.category}</span>
             ${ps.note ? `<br/><p class="text-xs text-gray-600 mt-1">${ps.note}</p>` : ''}
             ${ps.spot.description ? `<br/><p class="text-xs text-gray-500 mt-1">${ps.spot.description.substring(0, 100)}${ps.spot.description.length > 100 ? '...' : ''}</p>` : ''}
             ${ps.isMustVisit ? '<br/><span class="text-red-500 font-bold">★ MUST VISIT</span>' : ''}
           </div>
         `);

        layers.addLayer(marker);
        bounds.extend(marker.getLatLng());
      }
    });

    // 2. Draw Routes (Using Backend API with OSRM fallback) - Parallelized
    const drawRoutes = async () => {
      // 表示する日のリストを作成（選択された日を優先）
      const daysToRender = Object.keys(spotsByDay)
        .map(d => parseInt(d))
        .filter(day => !visibleDays || visibleDays.has(day))
        .sort((a, b) => {
          // 選択された日を最初に
          if (a === selectedDay) return -1;
          if (b === selectedDay) return 1;
          return a - b;
        });

      // 各日のルート取得関数
      const fetchRouteForDay = async (day: number) => {
        if (!isMounted) return null;

        const daySpotsList = spotsByDay[day];
        const locations = daySpotsList
          .filter(s => s.spot.location)
          .map(s => s.spot.location!);

        if (locations.length < 2) return null;

        const isSelected = day === selectedDay;
        const colorName = DAY_COLORS[(day - 1) % DAY_COLORS.length];

        let routeLatlngs = locations.map(l => [l.lat, l.lng]); // Fallback: Straight lines
        let routeInfo: { distance?: number; duration?: number; transportation?: string; spotDurations?: Array<{ spotId: string; duration: number }> } = {};

        try {
          // バックエンドAPIを使用（planIdが利用可能な場合）
          if (planId) {
            try {
              const routeResponse = await planApi.getPlanRoute(planId, day);
              if (routeResponse && routeResponse.route) {
                const route = routeResponse.route;
                if (route.geometry && route.geometry.length > 0) {
                  routeLatlngs = route.geometry;
                }
                routeInfo.distance = route.distance_km;
                routeInfo.duration = route.duration_minutes;
                routeInfo.transportation = route.source === 'osrm' ? '車' : '電車';

                // ルート情報を親コンポーネントに通知
                if (onRouteInfoUpdate) {
                  onRouteInfoUpdate(day, {
                    distance: route.distance_km,
                    duration: route.duration_minutes,
                    transportation: routeInfo.transportation
                  });
                }
              }
            } catch (apiError) {
              console.warn(`Backend API route fetch failed for day ${day}, falling back to OSRM`, apiError);
              throw apiError;
            }
          }

          // バックエンドAPIが失敗した場合、またはplanIdがない場合はOSRM直接呼び出し
          if (!routeInfo.distance && !routeInfo.duration) {
            const coordsString = locations.map(l => `${l.lng},${l.lat}`).join(';');
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const response = await fetch(
              `https://router.project-osrm.org/route/v1/driving/${coordsString}?overview=full&geometries=geojson`,
              { signal: controller.signal }
            );

            clearTimeout(timeoutId);

            if (!response.ok) {
              throw new Error(`OSRM request failed: ${response.status}`);
            }

            const data = await response.json();

            if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
              routeLatlngs = data.routes[0].geometry.coordinates.map((c: number[]) => [c[1], c[0]]);
              const route = data.routes[0];
              if (route.legs && route.legs.length > 0) {
                routeInfo.distance = route.legs.reduce((sum: number, leg: any) => sum + (leg.distance || 0), 0) / 1000;
                routeInfo.duration = route.legs.reduce((sum: number, leg: any) => sum + (leg.duration || 0), 0) / 60;
                routeInfo.transportation = '車';

                // 個々のスポット間の移動時間を計算
                const spotDurations: Array<{ spotId: string; duration: number }> = [];
                for (let i = 0; i < route.legs.length && i < daySpotsList.length - 1; i++) {
                  const leg = route.legs[i];
                  const spot = daySpotsList[i];
                  const durationMinutes = Math.round(leg.duration / 60); // 秒を分に変換
                  spotDurations.push({
                    spotId: spot.id,
                    duration: durationMinutes
                  });
                }
                routeInfo.spotDurations = spotDurations;

                // ルート情報を親コンポーネントに通知（個々のスポット間の移動時間を含む）
                if (onRouteInfoUpdate) {
                  onRouteInfoUpdate(day, {
                    distance: routeInfo.distance,
                    duration: routeInfo.duration,
                    transportation: routeInfo.transportation,
                    spotDurations: spotDurations
                  });
                }
              }
            } else {
              throw new Error('No route found in OSRM response');
            }
          }
        } catch (e) {
          console.warn(`Route fetch failed for day ${day}, using straight lines`, e);
          routeLatlngs = locations.map(l => [l.lat, l.lng]);
        }

        return { day, routeLatlngs, routeInfo, isSelected, colorName };
      };

      // 並列でルートを取得
      const routeResults = await Promise.all(
        daysToRender.map(day => fetchRouteForDay(day))
      );

      // 取得したルートを描画
      for (const result of routeResults) {
        if (!isMounted || !result || !layerGroupRef.current) continue;

        const { day, routeLatlngs, routeInfo, isSelected, colorName } = result;

        let routeLayer: any;
        const routeWeight = isSelected ? 6 : 3;
        const routeOpacity = isSelected ? 0.9 : 0.4;

        if (isSelected && (window as any).L && (window as any).L.antPath) {
          routeLayer = (window as any).L.antPath(routeLatlngs, {
            color: colorName,
            weight: routeWeight,
            opacity: routeOpacity,
            dashArray: [10, 20],
            pulseColor: colorName,
            delay: 400,
            paused: false,
            reverse: false
          });
        } else {
          routeLayer = L.polyline(routeLatlngs as any, {
            color: colorName,
            weight: routeWeight,
            opacity: routeOpacity,
            dashArray: isSelected ? undefined : '5, 10',
            lineCap: 'round',
            lineJoin: 'round'
          });
        }

        // ルート情報をポップアップに追加（詳細情報）
        const routePopup = `
            <div style="text-align: center; padding: 8px; min-width: 180px;">
              <strong style="font-size: 14px; color: ${colorName};">${day}日目のルート</strong><br/>
              ${routeInfo.distance ? `<div style="margin-top: 5px;"><span style="font-weight: bold;">距離:</span> ${routeInfo.distance.toFixed(1)} km</div>` : ''}
              ${routeInfo.duration ? `<div><span style="font-weight: bold;">時間:</span> ${Math.round(routeInfo.duration)} 分</div>` : ''}
              ${routeInfo.transportation ? `<div style="margin-top: 3px; font-size: 11px; color: #666;">🚗 ${routeInfo.transportation}</div>` : ''}
            </div>
          `;
        routeLayer.bindPopup(routePopup);

        // 方向矢印を追加（選択された日のルートのみ）
        if (isSelected && routeLatlngs.length > 1) {
          const arrowInterval = Math.max(1, Math.floor(routeLatlngs.length / 5));
          for (let i = arrowInterval; i < routeLatlngs.length - 1; i += arrowInterval) {
            const point1 = routeLatlngs[i - 1];
            const point2 = routeLatlngs[i];
            const angle = Math.atan2(point2[0] - point1[0], point2[1] - point1[1]) * 180 / Math.PI;

            const arrowIcon = L.divIcon({
              className: 'route-arrow',
              html: `<div style="transform: rotate(${angle}deg); color: ${colorName}; font-size: 16px;">▶</div>`,
              iconSize: [16, 16],
              iconAnchor: [8, 8]
            });

            const arrowMarker = L.marker([point2[0], point2[1]], { icon: arrowIcon });
            layerGroupRef.current.addLayer(arrowMarker);
          }
        }

        layerGroupRef.current.addLayer(routeLayer);
      }
    };

    drawRoutes();

    // Fit bounds - Optimized for better view area
    if (hasMarkers) {
      setTimeout(() => {
        if (isMounted && map) {
          map.invalidateSize();
          // オーバーレイカードが右上にあるため、右側のパディングを減らす
          // 上部のパディングも減らして表示領域を拡大
          map.fitBounds(bounds, {
            padding: [20, 20, 20, 20], // top, right, bottom, left
            maxZoom: 15 // より近くまでズーム可能に
          });
        }
      }, 100);
    } else {
      // Fallback centers
      let center = AppConfig.MAP.DEFAULT_CENTER;
      if (areaName.includes('京都')) center = [35.0116, 135.7681];
      if (areaName.includes('大阪')) center = [34.6937, 135.5023];
      if (areaName.includes('鹿児島')) center = [31.5966, 130.5571];
      if (areaName.includes('北海道') || areaName.includes('札幌')) center = [43.0618, 141.3545];
      if (areaName.includes('沖縄')) center = [26.2124, 127.6809];
      map.setView(center, 12);
    }

    return () => {
      isMounted = false;
    };
  }, [planSpots, selectedDay, areaName]);

  return <div ref={mapRef} className="w-full h-full rounded-2xl min-h-[400px] z-0" />;
};


export const CreatePlan: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  const [step, setStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationPhase, setGenerationPhase] = useState<string>('');
  const [request, setRequest] = useState<PlanRequest>({
    destination: '',
    days: 2,
    budget: 'standard',
    themes: [],
    checkInDate: undefined,
    checkOutDate: undefined,
    numGuests: 2
  });
  const [pendingSpots, setPendingSpots] = useState<Spot[]>([]);
  const [activeRegion, setActiveRegion] = useState(regions[1].id); // Default to Kanto

  // Check for pending spots passed from Favorites page
  useEffect(() => {
    const stored = localStorage.getItem(AppConfig.STORAGE_KEYS.PENDING_SPOTS);
    if (stored) {
      const ids = JSON.parse(stored);
      const selected = spots.filter(s => ids.includes(s.id));
      setPendingSpots(selected);

      if (selected.length > 0) {
        // Pre-fill destination from the first selected spot's area
        setRequest(prev => ({ ...prev, destination: selected[0].area }));
      }
    }
  }, []);


  const handleThemeToggle = (theme: string) => {
    setRequest(prev => ({
      ...prev,
      themes: prev.themes.includes(theme)
        ? prev.themes.filter(t => t !== theme)
        : [...prev.themes, theme]
    }));
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationPhase('データベースから候補地を選定中...');

    // Clear the pending spots from storage
    localStorage.removeItem(AppConfig.STORAGE_KEYS.PENDING_SPOTS);

    // Simulate phases for UI effect
    setTimeout(() => setGenerationPhase('トレンドデータと照合中...'), 1500);
    setTimeout(() => setGenerationPhase('最適なルートとタイムラインを生成中...'), 3500);

    try {
      // バックエンドAPIを呼び出し
      const newPlan = await planApi.generatePlan({
        destination: request.destination,
        days: request.days,
        budget: request.budget,
        themes: request.themes,
        pending_spots: pendingSpots.map(spot => ({
          name: spot.name,
          description: spot.description,
          area: spot.area,
          category: spot.category,
          durationMinutes: spot.durationMinutes,
          rating: spot.rating,
          image: spot.image,
          price: spot.price,
          tags: spot.tags,
          location: spot.location,
        })),
        check_in_date: request.checkInDate,
        check_out_date: request.checkOutDate,
        num_guests: request.numGuests,
      });

      // 除外されたスポットがある場合、ユーザーに通知
      if (newPlan.excludedSpots && newPlan.excludedSpots.length > 0) {
        const excludedNames = newPlan.excludedSpots.map(s => s.name).join('、');
        const message = `以下のスポットはデータベースに存在しないため、プランから除外されました:\n${excludedNames}\n\n管理者画面に登録されているスポットのみ使用できます。`;
        alert(message);
      }

      // プラン詳細ページに遷移
      onNavigate(`/plan/${newPlan.id}`);

    } catch (e: any) {
      console.error("AI Generation Error", e);
      const errorMessage = e.detail || e.message || "プラン生成中にエラーが発生しました。";
      alert(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  };

  if (isGenerating) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white px-4">
        <div className="relative w-32 h-32 mb-8">
          <div className="absolute inset-0 border-4 border-gray-100 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuCfMSI_vEQcW6uWaOllfqi75Njj5epUUHan7iKYq2ddAZoSthgXSLKdhXLtyvGQeDOWHCvMIb9zHR29P6R1MHTCyE0GBmQFcmGptEhCWUuL8GTANN3rvEBzwrgvyl2srrrUMRms1iDYE5uxYWZET7_hlJDkiMX5A9SRf5w0qYmIJZMQq94roefVcSp5yXCk6-cjB3diA5SN8xBWRjHxaLVpf_bvPHdIi4cn84z3ACcaFosupiz3lF_kn0umIyl14BROFmriQ29o9iI" alt="Logo" className="w-16 h-16 animate-pulse" />
          </div>
        </div>
        <h2 className="text-2xl font-bold mb-2 animate-pulse">{generationPhase}</h2>
        <p className="text-text-muted mb-8 text-center max-w-md">
          SatoTripの膨大な観光データベースから、{request.destination}の最適プランを構築中。<br />
          事前に収集されたトレンド情報を活用しています。
        </p>

        <div className="w-full max-w-md bg-gray-100 rounded-full h-2 overflow-hidden">
          <div className="h-full bg-primary animate-progress"></div>
        </div>

        <style>{`
          @keyframes progress {
            0% { width: 0%; }
            100% { width: 100%; }
          }
          .animate-progress {
            animation: progress 8s ease-in-out forwards;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background-light py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-10">
          <h1 className="text-3xl md:text-4xl font-black mb-4">AI Travel Planner</h1>
          <div className="flex justify-center gap-2">
            {[1, 2, 3].map(s => (
              <div key={s} className={`h-2 w-12 rounded-full transition-colors ${step >= s ? 'bg-primary' : 'bg-gray-200'}`} />
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-10 relative overflow-hidden">
          {/* Step 1: Destination & Days */}
          {step === 1 && (
            <div className="animate-fade-in">
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="bg-primary/10 text-primary w-8 h-8 rounded-full flex items-center justify-center text-sm">1</span>
                どこへ行きますか？
              </h2>

              {pendingSpots.length > 0 && (
                <div className="mb-6 bg-secondary/20 text-text-light p-4 rounded-xl flex items-center gap-3 border border-secondary/30">
                  <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-secondary shadow-sm">
                    <span className="material-symbols-outlined">bookmark_added</span>
                  </div>
                  <div>
                    <p className="font-bold text-sm">お気に入りから追加</p>
                    <p className="text-xs opacity-80">選択した {pendingSpots.length} 件のスポットを含めてプランを作成します。</p>
                  </div>
                </div>
              )}

              <div className="space-y-6">
                <div>
                  <label className="block font-bold text-text-muted text-sm mb-2">目的地・エリア</label>

                  {/* Region Tabs */}
                  <div className="flex gap-2 overflow-x-auto pb-2 mb-4 scrollbar-hide">
                    {regions.map(region => (
                      <button
                        key={region.id}
                        onClick={() => setActiveRegion(region.id)}
                        className={`px-4 py-2 rounded-full text-sm font-bold whitespace-nowrap transition-colors ${activeRegion === region.id
                          ? 'bg-secondary text-text-light border border-secondary shadow-sm'
                          : 'bg-gray-50 text-text-muted border border-gray-200 hover:bg-gray-100'
                          }`}
                      >
                        {region.name}
                      </button>
                    ))}
                  </div>

                  {/* Prefecture Grid */}
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 mb-6 max-h-48 overflow-y-auto">
                    {regions.find(r => r.id === activeRegion)?.prefs.map(pref => (
                      <button
                        key={pref}
                        onClick={() => setRequest({ ...request, destination: pref })}
                        className={`py-2 px-1 rounded-lg text-sm transition-all ${request.destination === pref
                          ? 'bg-primary text-white font-bold shadow-md'
                          : 'bg-white border border-gray-100 text-text-light hover:border-primary/50'
                          }`}
                      >
                        {pref}
                      </button>
                    ))}
                  </div>

                  {/* Free Input Fallback */}
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-text-muted">search</span>
                    <input
                      type="text"
                      placeholder="詳細なエリアや都市名を入力 (例: 箱根、金沢)..."
                      className="w-full pl-12 pr-4 py-3 bg-gray-50 rounded-xl border border-gray-200 focus:border-primary focus:bg-white transition-all text-base outline-none font-medium"
                      value={request.destination}
                      onChange={e => setRequest({ ...request, destination: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-text-muted text-sm mb-2">日数</label>
                  <div className="flex items-center gap-4">
                    <button onClick={() => setRequest({ ...request, days: Math.max(1, request.days - 1) })} className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200 font-bold text-xl">-</button>
                    <span className="text-2xl font-black w-20 text-center">{request.days}日間</span>
                    <button onClick={() => setRequest({ ...request, days: Math.min(14, request.days + 1) })} className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200 font-bold text-xl">+</button>
                  </div>
                </div>

                <button
                  onClick={() => request.destination && setStep(2)}
                  disabled={!request.destination}
                  className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg shadow-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all mt-4"
                >
                  次へ進む
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Budget & Style */}
          {step === 2 && (
            <div className="animate-fade-in">
              <button onClick={() => setStep(1)} className="text-text-muted text-sm mb-4 flex items-center gap-1 hover:text-primary"><span className="material-symbols-outlined text-sm">arrow_back</span> 戻る</button>
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="bg-primary/10 text-primary w-8 h-8 rounded-full flex items-center justify-center text-sm">2</span>
                予算とスタイル
              </h2>

              <div className="space-y-8">
                <div>
                  <label className="block font-bold text-text-muted text-sm mb-4">予算の目安</label>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { id: 'budget', label: '節約', icon: 'savings' },
                      { id: 'standard', label: '標準', icon: 'payments' },
                      { id: 'luxury', label: '贅沢', icon: 'diamond' }
                    ].map((opt) => (
                      <button
                        key={opt.id}
                        onClick={() => setRequest({ ...request, budget: opt.id })}
                        className={`p-4 rounded-xl border-2 flex flex-col items-center gap-2 transition-all ${request.budget === opt.id ? 'border-primary bg-primary/5 text-primary' : 'border-gray-200 hover:border-gray-300 text-text-muted'}`}
                      >
                        <span className="material-symbols-outlined text-2xl">{opt.icon}</span>
                        <span className="font-bold text-sm">{opt.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => setStep(3)}
                  className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg shadow-lg hover:opacity-90 transition-all"
                >
                  次へ進む
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Interests & Generate */}
          {step === 3 && (
            <div className="animate-fade-in">
              <button onClick={() => setStep(2)} className="text-text-muted text-sm mb-4 flex items-center gap-1 hover:text-primary"><span className="material-symbols-outlined text-sm">arrow_back</span> 戻る</button>
              <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                <span className="bg-primary/10 text-primary w-8 h-8 rounded-full flex items-center justify-center text-sm">3</span>
                どんな旅にしたい？
              </h2>
              <p className="text-text-muted mb-6 text-sm">AIがデータベースから最適なスポットを選び出します。複数選択可。</p>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
                {[
                  'SNS映え', '歴史・文化', '食べ歩き', '自然・絶景',
                  'アート', '温泉・癒し', '穴場スポット', '体験・アクティビティ'
                ].map(theme => (
                  <button
                    key={theme}
                    onClick={() => handleThemeToggle(theme)}
                    className={`py-3 px-2 rounded-lg text-sm font-bold transition-all ${request.themes.includes(theme) ? 'bg-primary text-white shadow-md transform scale-105' : 'bg-gray-50 text-text-muted hover:bg-gray-100'}`}
                  >
                    {theme}
                  </button>
                ))}
              </div>

              {/* 宿泊先情報入力セクション */}
              <div className="mb-8">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">hotel</span>
                  宿泊情報（オプション）
                </h3>
                <div className="space-y-4 bg-gray-50 p-4 rounded-xl">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block font-bold text-text-muted text-sm mb-2">チェックイン日</label>
                      <input
                        type="date"
                        className="w-full px-4 py-2 bg-white rounded-lg border border-gray-200 focus:border-primary focus:outline-none"
                        value={request.checkInDate || ''}
                        onChange={e => setRequest({ ...request, checkInDate: e.target.value })}
                        min={new Date().toISOString().split('T')[0]}
                      />
                    </div>
                    <div>
                      <label className="block font-bold text-text-muted text-sm mb-2">チェックアウト日</label>
                      <input
                        type="date"
                        className="w-full px-4 py-2 bg-white rounded-lg border border-gray-200 focus:border-primary focus:outline-none"
                        value={request.checkOutDate || ''}
                        onChange={e => setRequest({ ...request, checkOutDate: e.target.value })}
                        min={request.checkInDate || new Date().toISOString().split('T')[0]}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block font-bold text-text-muted text-sm mb-2">予約人数</label>
                    <div className="flex items-center gap-4">
                      <button
                        onClick={() => setRequest({ ...request, numGuests: Math.max(1, (request.numGuests || 2) - 1) })}
                        className="w-10 h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center hover:bg-gray-100 font-bold"
                      >
                        -
                      </button>
                      <span className="text-lg font-bold w-12 text-center">{request.numGuests || 2}名</span>
                      <button
                        onClick={() => setRequest({ ...request, numGuests: Math.min(20, (request.numGuests || 2) + 1) })}
                        className="w-10 h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center hover:bg-gray-100 font-bold"
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
              </div>


              <div className="bg-gradient-to-r from-secondary/20 to-primary/10 p-4 rounded-xl mb-8 flex items-start gap-3">
                <span className="material-symbols-outlined text-primary mt-1">database</span>
                <div className="text-sm">
                  <span className="font-bold text-primary block mb-1">Project SatoTrip 連携</span>
                  バックグラウンドで収集された最新のSNS・Webトレンド情報を基に、高精度なプランを作成します。
                </div>
              </div>

              <button
                onClick={handleGenerate}
                className="w-full bg-gradient-to-r from-primary to-purple-600 text-white py-4 rounded-xl font-black text-xl shadow-xl hover:opacity-90 transition-all transform hover:-translate-y-1 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined">auto_awesome</span>
                プランを生成する
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const PlanDetail: React.FC<{ planId: string; onNavigate: (path: string) => void }> = ({ planId, onNavigate }) => {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transportModes, setTransportModes] = useState<Record<string, 'public' | 'car' | 'walk'>>({});
  const [selectedDay, setSelectedDay] = useState(1);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedSpots, setEditedSpots] = useState<Record<string, { durationMinutes?: number; transportDuration?: number }>>({});
  const [isUpdating, setIsUpdating] = useState(false);
  const [reorderedSpots, setReorderedSpots] = useState<PlanSpot[]>([]);
  const [visibleDays, setVisibleDays] = useState<Set<number>>(new Set());
  const [routeInfoByDay, setRouteInfoByDay] = useState<Record<number, { distance: number; duration: number; transportation?: string }>>({});
  const [isOverlayExpanded, setIsOverlayExpanded] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [localPlanSpots, setLocalPlanSpots] = useState<PlanSpot[]>([]);
  const [checkInDate, setCheckInDate] = useState<string>('');
  const [checkOutDate, setCheckOutDate] = useState<string>('');
  const [isUpdatingDates, setIsUpdatingDates] = useState(false);

  // ドラッグ&ドロップ用のセンサー設定
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // 宿泊施設検索関連のstate
  const [hotelCategories, setHotelCategories] = useState<HotelCategory[]>([]);
  const [selectedHotelCategory, setSelectedHotelCategory] = useState<string | null>(null);
  const [hotelName, setHotelName] = useState<string>('');
  const [hotelSearchResult, setHotelSearchResult] = useState<HotelSearchResult | null>(null);
  const [isSearchingHotels, setIsSearchingHotels] = useState(false);

  useEffect(() => {
    const fetchPlan = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const fetchedPlan = await planApi.getPlan(planId);
        setPlan(fetchedPlan);
        setLocalPlanSpots(JSON.parse(JSON.stringify(fetchedPlan.spots)));
        // チェックイン日・チェックアウト日を設定
        setCheckInDate(fetchedPlan.checkInDate || '');
        setCheckOutDate(fetchedPlan.checkOutDate || '');
        // 初期状態ではすべての日を表示
        if (fetchedPlan) {
          const allDays = new Set(Array.from({ length: fetchedPlan.days }, (_, i) => i + 1));
          setVisibleDays(allDays);
        }
      } catch (err: any) {
        console.error('Failed to fetch plan:', err);
        setError(err.detail || err.message || 'プランの取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPlan();
  }, [planId]);

  useEffect(() => {
    if (!plan) return;
    // Initialize with default modes from plan data
    const initial: Record<string, 'public' | 'car' | 'walk'> = {};
    plan.spots.forEach(s => {
      if (s.transportMode) {
        let m: 'public' | 'car' | 'walk' = 'public';
        if (s.transportMode === 'walk') {
          m = 'walk';
        } else if (s.transportMode === 'car') {
          m = 'car';
        } else if (s.transportMode === 'train' || s.transportMode === 'bus') {
          m = 'public';
        }
        initial[s.id] = m;
        // #region agent log
        fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanPages.tsx:1153',message:'transportModes init',data:{spotId:s.id,transportMode:s.transportMode,mappedMode:m},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
        // #endregion
      } else {
        initial[s.id] = 'public';
      }
    });
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanPages.tsx:1158',message:'transportModes set',data:{initialModes:Object.keys(initial).length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
    // #endregion
    setTransportModes(initial);
  }, [plan]);

  // 宿泊施設カテゴリを取得
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const result = await hotelApi.getHotelCategories();
        setHotelCategories(result.categories);
      } catch (err) {
        console.error('Failed to fetch hotel categories:', err);
      }
    };
    fetchCategories();
  }, []);

  // 宿泊施設検索
  // 宿泊施設検索結果からスポットを取得してプランに追加
  const handleAddHotelFromSearch = async (hotelName: string) => {
    if (!plan) return;
    
    try {
      // データベースから宿泊施設のスポットを検索
      const hotelSpots = await spotApi.getSpots({
        area: plan.area,
        category: 'Hotel',
        keyword: hotelName
      });
      
      if (hotelSpots.length === 0) {
        alert(`「${hotelName}」に一致する宿泊施設がデータベースに見つかりませんでした。\n管理者画面で宿泊施設を登録してください。`);
        return;
      }
      
      // 最初に見つかった宿泊施設を使用
      const hotelSpot = hotelSpots[0];
      
      // その日の最後のスポットの終了時刻を計算
      const currentDaySpots = localPlanSpots.length > 0
        ? localPlanSpots.filter(s => s.day === selectedDay)
        : plan.spots.filter(s => s.day === selectedDay);
      
      let lastEndTime = '18:00';
      if (currentDaySpots.length > 0) {
        const lastSpot = currentDaySpots[currentDaySpots.length - 1];
        const startTime = lastSpot.startTime || '09:00';
        const durationMinutes = lastSpot.spot.durationMinutes || 60;
        
        // 時刻を分単位に変換
        const timeToMinutes = (timeStr: string): number => {
          const parts = timeStr.split(':');
          return parseInt(parts[0]) * 60 + parseInt(parts[1]);
        };
        
        const minutesToTime = (minutes: number): string => {
          const hours = Math.floor(minutes / 60);
          const mins = minutes % 60;
          return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
        };
        
        const startMinutes = timeToMinutes(startTime);
        const endMinutes = startMinutes + durationMinutes;
        lastEndTime = minutesToTime(endMinutes);
      }
      
      // 宿泊施設をプランに追加
      const newHotelSpot: PlanSpot = {
        id: `hotel_${Date.now()}`,
        spotId: hotelSpot.id,
        spot: hotelSpot,
        day: selectedDay,
        startTime: lastEndTime,
        note: '宿泊',
        transportMode: 'walk',
        transportDuration: 0,
        isMustVisit: false
      };
      
      setLocalPlanSpots(prev => [...prev, newHotelSpot]);
      alert(`「${hotelSpot.name}」をプランに追加しました。`);
    } catch (err: any) {
      console.error('宿泊施設の追加エラー:', err);
      alert(err.detail || err.message || '宿泊施設の追加に失敗しました');
    }
  };

  const handleHotelSearch = async () => {
    if (!plan) return;

    setIsSearchingHotels(true);
    try {
      const searchRequest: HotelSearchRequest = {
        area: plan.area,
        category: selectedHotelCategory || undefined,
        hotelName: hotelName || undefined,
        checkIn: undefined, // プラン生成時の日付を使用する場合はここで設定
        checkOut: undefined,
        numGuests: 2
      };

      const result = await hotelApi.searchHotels(searchRequest);
      setHotelSearchResult(result);
    } catch (err: any) {
      console.error('Failed to search hotels:', err);
      alert(err.detail || err.message || '宿泊施設の検索に失敗しました');
    } finally {
      setIsSearchingHotels(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-text-muted">プランを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center max-w-md">
          <p className="text-red-600 font-bold mb-2">エラーが発生しました</p>
          <p className="text-red-500 text-sm mb-4">{error || 'プランが見つかりません'}</p>
          <button
            onClick={() => onNavigate('/plans')}
            className="bg-primary text-white px-6 py-3 rounded-full font-bold shadow-lg hover:opacity-90 transition-opacity"
          >
            プラン一覧に戻る
          </button>
        </div>
      </div>
    );
  }

  const handleModeChange = (id: string, mode: 'public' | 'car' | 'walk') => {
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanPages.tsx:1302',message:'handleModeChange',data:{id,mode,currentValue:transportModes[id]},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
    // #endregion
    // transportModesのみ更新（localPlanSpotsのtransportModeは更新しない - 元の値を保持）
    setTransportModes(prev => {
      const updated = { ...prev, [id]: mode };
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanPages.tsx:1304',message:'transportModes updated',data:{id,mode,updatedValue:updated[id]},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      return updated;
    });
  };

  const handleShare = async () => {
    const url = window.location.href;
    let shared = false;

    // Try Web Share API first
    if (navigator.share) {
      try {
        await navigator.share({
          title: plan.title,
          text: `SatoTripで作成した旅行プラン: ${plan.title}`,
          url: url,
        });
        shared = true;
      } catch (err: any) {
        // Ignore AbortError (user cancelled)
        if (err.name !== 'AbortError') {
          console.log('Share API failed', err);
        } else {
          // User cancelled, so we stop here and don't copy
          return;
        }
      }
    }

    // Fallback to Clipboard if Share API unavailable or failed (not cancelled)
    if (!shared) {
      try {
        await navigator.clipboard.writeText(url);
        alert('URLをクリップボードにコピーしました！');
      } catch (err) {
        console.error('Clipboard failed', err);
        // Fallback for secure context issues or browser restrictions
        alert('URLのコピーに失敗しました。ブラウザのアドレスバーからコピーしてください。');
      }
    }
  };

  const handleDownload = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(plan, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `satotrip_plan_${plan.id}.json`);
    document.body.appendChild(downloadAnchorNode); // required for firefox
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  // 編集モードの切り替え
  const handleEditModeToggle = () => {
    setIsEditMode(!isEditMode);
    if (!isEditMode) {
      // 編集モード開始時、現在の値をeditedSpotsにコピー
      const initialEdits: Record<string, { durationMinutes?: number; transportDuration?: number }> = {};
      plan?.spots.forEach(spot => {
        initialEdits[spot.id] = {
          durationMinutes: spot.spot.durationMinutes,
          transportDuration: spot.transportDuration
        };
      });
      setEditedSpots(initialEdits);
      // 並び替え状態をリセット
      setReorderedSpots([]);
      // ローカル状態をリセット
      setLocalPlanSpots(JSON.parse(JSON.stringify(plan?.spots || [])));
    } else {
      // 編集モード終了時、変更をリセット
      setEditedSpots({});
      setReorderedSpots([]);
      setLocalPlanSpots(JSON.parse(JSON.stringify(plan?.spots || [])));
    }
  };

  // スポットの削除
  const handleDeleteSpot = (spotId: string) => {
    if (!confirm('このスポットを削除しますか？')) return;
    setLocalPlanSpots(prev => prev.filter(s => s.id !== spotId));
    setReorderedSpots(prev => prev.filter(s => s.id !== spotId));
  };

  // スポットの追加
  const handleAddSpot = (spot: Spot) => {
    if (!plan) return;
    const newSpot: PlanSpot = {
      id: `new_${Date.now()}`,
      spotId: spot.id,
      spot: spot,
      day: selectedDay,
      startTime: '10:00'
    };
    setLocalPlanSpots(prev => [...prev, newSpot]);
    setIsAddModalOpen(false);
  };

  // スポットの編集値を更新
  const handleSpotEdit = (spotId: string, field: 'durationMinutes' | 'transportDuration', value: number) => {
    setEditedSpots(prev => ({
      ...prev,
      [spotId]: {
        ...prev[spotId],
        [field]: value
      }
    }));

    // localPlanSpotsも更新（即座に反映）
    setLocalPlanSpots(prev => prev.map(spot => {
      if (spot.id === spotId) {
        const updatedSpot = { ...spot };
        if (field === 'durationMinutes') {
          updatedSpot.spot = {
            ...updatedSpot.spot,
            durationMinutes: value
          };
        } else if (field === 'transportDuration') {
          updatedSpot.transportDuration = value;
        }
        return updatedSpot;
      }
      return spot;
    }));
  };

  // プラン更新
  const handlePlanUpdate = async () => {
    if (!plan) return;

    setIsUpdating(true);
    try {
      // ローカル状態のスポットを使用（削除・追加が反映されている）
      // reorderedSpotsが更新されている場合はそれを使用、なければlocalPlanSpotsを使用
      let spotsToUpdate: PlanSpot[] = [];

      if (reorderedSpots.length > 0) {
        // 並び替えが行われている場合は、reorderedSpotsを使用
        spotsToUpdate = [...reorderedSpots];
      } else if (localPlanSpots.length > 0) {
        // ローカル状態がある場合はそれを使用
        spotsToUpdate = [...localPlanSpots];
      } else {
        // どちらもない場合は元のプランから
        spotsToUpdate = [...plan.spots];
      }

      // 編集された値（滞在時間・移動時間・移動手段）を反映
      spotsToUpdate = spotsToUpdate.map(spot => {
        const edits = editedSpots[spot.id] || {};
        const updatedSpot: PlanSpot = {
          ...spot,
          spot: { ...spot.spot }
        };

        // 滞在時間の更新
        if (edits.durationMinutes !== undefined) {
          updatedSpot.spot.durationMinutes = edits.durationMinutes;
        }

        // 移動時間の更新
        if (edits.transportDuration !== undefined) {
          updatedSpot.transportDuration = edits.transportDuration;
        }

        // 移動手段の更新（transportModesから取得）
        if (transportModes[spot.id]) {
          const mode = transportModes[spot.id];
          if (mode === 'car') {
            updatedSpot.transportMode = 'car';
          } else if (mode === 'walk') {
            updatedSpot.transportMode = 'walk';
          } else {
            updatedSpot.transportMode = 'train';
          }
        }

        return updatedSpot;
      });

      console.log('更新するスポット:', spotsToUpdate.map(s => ({
        id: s.id,
        name: s.spot.name,
        durationMinutes: s.spot.durationMinutes,
        transportDuration: s.transportDuration,
        transportMode: s.transportMode,
        startTime: s.startTime
      })));
      console.log('編集された値:', editedSpots);
      console.log('移動手段:', transportModes);

      // 完全なスポット配列として送信（PlanEditorと同じ形式）
      const updatedPlan = await planApi.updatePlan(plan.id, {
        spots: spotsToUpdate
      });

      console.log('更新後のプラン:', updatedPlan.spots.map((s: PlanSpot) => ({
        id: s.id,
        name: s.spot.name,
        durationMinutes: s.spot.durationMinutes,
        transportDuration: s.transportDuration,
        transportMode: s.transportMode
      })));

      setPlan(updatedPlan);
      setLocalPlanSpots(JSON.parse(JSON.stringify(updatedPlan.spots)));
      setIsEditMode(false);
      setEditedSpots({});
      setReorderedSpots([]);
      alert('プランを更新しました');
    } catch (err: any) {
      console.error('プラン更新エラー:', err);
      alert(err.detail || err.message || 'プランの更新に失敗しました');
    } finally {
      setIsUpdating(false);
    }
  };

  // ドラッグ&ドロップ完了時のハンドラー
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over || active.id === over.id || !plan) return;

    const currentDaySpots = localPlanSpots.length > 0
      ? localPlanSpots.filter(s => s.day === selectedDay)
      : (reorderedSpots.length > 0
        ? reorderedSpots.filter(s => s.day === selectedDay)
        : plan.spots.filter(s => s.day === selectedDay));

    const oldIndex = currentDaySpots.findIndex(spot => spot.id === active.id);
    const newIndex = currentDaySpots.findIndex(spot => spot.id === over.id);

    if (oldIndex !== -1 && newIndex !== -1) {
      const newOrderedSpots = arrayMove(currentDaySpots, oldIndex, newIndex) as PlanSpot[];

      // 新しい順序で時刻を再計算
      const recalculatedSpots = recalculateTimesForDay(newOrderedSpots, selectedDay);

      // 全体のスポットリストを更新
      const baseSpots = localPlanSpots.length > 0 ? localPlanSpots : plan.spots;
      const allSpots = baseSpots.filter(s => s.day !== selectedDay);
      const updatedAllSpots = [...allSpots, ...recalculatedSpots].sort((a, b) => {
        if (a.day !== b.day) return a.day - b.day;
        return a.startTime?.localeCompare(b.startTime || '') || 0;
      });

      // localPlanSpotsとreorderedSpotsの両方を更新
      setLocalPlanSpots(updatedAllSpots);
      setReorderedSpots(updatedAllSpots);
    }
  };

  // 日ごとの時刻を再計算
  const recalculateTimesForDay = (spots: PlanSpot[], day: number): PlanSpot[] => {
    if (spots.length === 0) return spots;

    const startTime = "09:00"; // デフォルト開始時間
    const recalculated: PlanSpot[] = [];

    let currentTime = timeToMinutes(startTime);

    spots.forEach((spot, index) => {
      // 編集された値を使用、なければ元の値を使用
      const durationMinutes = editedSpots[spot.id]?.durationMinutes ?? spot.spot.durationMinutes ?? 60;

      // 前のスポットの移動時間を取得（編集された値を使用）
      let transportDuration = 0;
      if (index > 0) {
        const prevSpot = spots[index - 1];
        transportDuration = editedSpots[prevSpot.id]?.transportDuration ?? prevSpot.transportDuration ?? 20;
        currentTime += transportDuration;
      }

      const newSpot: PlanSpot = {
        ...spot,
        startTime: minutesToTime(currentTime),
        transportDuration: editedSpots[spot.id]?.transportDuration ?? spot.transportDuration ?? 20,
        spot: {
          ...spot.spot,
          durationMinutes: durationMinutes
        }
      };

      recalculated.push(newSpot);

      // 次のスポットの開始時刻を計算（滞在時間を加算）
      currentTime += durationMinutes;
    });

    return recalculated;
  };

  // 時刻を分単位に変換
  const timeToMinutes = (timeStr: string): number => {
    if (!timeStr) return 0;
    const [hours, minutes] = timeStr.split(':').map(Number);
    return hours * 60 + (minutes || 0);
  };

  // 分を時刻文字列に変換
  const minutesToTime = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
  };

  // 終了時刻を計算
  const calculateEndTime = (startTime: string, durationMinutes: number): string => {
    const startMinutes = timeToMinutes(startTime);
    const endMinutes = startMinutes + durationMinutes;
    return minutesToTime(endMinutes);
  };

  // 移動時間の計算（実際の値を使用、変更時のみ概算）
  const calculateDuration = (baseMode: string | undefined, baseDuration: number | undefined, targetMode: string): number => {
    if (!baseMode || baseDuration === undefined) {
      return 0;
    }

    // 同じ移動手段の場合はそのまま返す
    const isSameMode = baseMode === targetMode || (targetMode === 'public' && (baseMode === 'train' || baseMode === 'bus'));
    
    if (isSameMode) {
      return baseDuration;
    }

    // 移動手段が変更された場合のみ概算変換
    // 実際のルート情報がある場合はそれを使用（baseDurationが実際の値）
    // 概算が必要な場合のみ変換

    // 概算の速度（km/h）
    const speeds: Record<string, number> = {
      'walk': 4,      // 徒歩: 4km/h
      'car': 40,      // 車: 40km/h
      'train': 30,    // 電車: 30km/h
      'bus': 25,      // バス: 25km/h
      'public': 30    // 公共交通機関: 30km/h
    };

    const baseSpeed = speeds[baseMode] || 30;
    const targetSpeed = speeds[targetMode] || 30;

    // 距離を計算（baseDurationから逆算）
    // 距離 = 速度 × 時間（時間は分から時間に変換）
    const distance = baseSpeed * (baseDuration / 60); // km
    
    // 新しい移動手段での時間を計算
    // 時間（分） = (距離 / 速度) × 60
    const targetDuration = Math.round((distance / targetSpeed) * 60);

    // 待ち時間や乗り換え時間を考慮
    if (targetMode === 'car') {
      return Math.max(5, targetDuration + 5); // 駐車時間
    } else if (targetMode === 'public') {
      return Math.max(10, targetDuration + 10); // 待ち時間・乗り換え
    } else {
      return Math.max(5, targetDuration);
    }
  };

  // 並び替え済みのスポットがある場合はそれを使用、なければローカル状態から取得
  const currentDaySpots = localPlanSpots.length > 0
    ? localPlanSpots.filter(s => s.day === selectedDay)
    : (reorderedSpots.length > 0
      ? reorderedSpots.filter(s => s.day === selectedDay)
      : (plan?.spots.filter(s => s.day === selectedDay) || []));

  // startTimeでソート（念のため）
  const sortedCurrentDaySpots = [...currentDaySpots].sort((a, b) => {
    return (a.startTime || '00:00').localeCompare(b.startTime || '00:00');
  });

  // Get color for current day selection
  const currentColor = TAILWIND_COLORS[(selectedDay - 1) % TAILWIND_COLORS.length] || TAILWIND_COLORS[0];
  const pinColorName = ['赤', '青', '緑', 'オレンジ', '紫', '金', '灰', '黒'][(selectedDay - 1) % 8];

  return (
    <div className="min-h-screen bg-background-light pb-20">
      {/* Header & Hero */}
      <div className="bg-white border-b border-primary/10">
        <div className="max-w-7xl mx-auto px-4 py-8 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex-1">
            <h1 className="text-4xl lg:text-5xl font-black tracking-tighter text-text-light mb-2">{plan.title}</h1>
            <p className="text-text-muted text-lg mb-4">エリア: {plan.area}</p>
            
            {/* チェックイン日変更フォーム */}
            <div className="bg-white/50 backdrop-blur-sm rounded-lg p-4 border border-primary/20 max-w-md">
              <h3 className="text-sm font-bold text-text-muted mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-base">calendar_today</span>
                チェックイン日・チェックアウト日
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-text-muted mb-1">チェックイン日</label>
                  <input
                    type="date"
                    value={checkInDate}
                    onChange={(e) => setCheckInDate(e.target.value)}
                    min={new Date().toISOString().split('T')[0]}
                    className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-text-muted mb-1">チェックアウト日</label>
                  <input
                    type="date"
                    value={checkOutDate}
                    onChange={(e) => setCheckOutDate(e.target.value)}
                    min={checkInDate || new Date().toISOString().split('T')[0]}
                    className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:border-primary focus:outline-none"
                  />
                </div>
              </div>
              {(checkInDate !== plan.checkInDate || checkOutDate !== plan.checkOutDate) && (
                <button
                  onClick={async () => {
                    if (checkInDate && checkOutDate && checkInDate >= checkOutDate) {
                      alert('チェックアウト日はチェックイン日より後の日付を指定してください');
                      return;
                    }
                    setIsUpdatingDates(true);
                    try {
                      const updatedPlan = await planApi.updatePlan(plan.id, {
                        check_in_date: checkInDate || undefined,
                        check_out_date: checkOutDate || undefined,
                      });
                      setPlan(updatedPlan);
                      alert('チェックイン日・チェックアウト日を更新しました');
                    } catch (err: any) {
                      console.error('日付更新エラー:', err);
                      alert(err.detail || err.message || '日付の更新に失敗しました');
                      // エラー時は元の値に戻す
                      setCheckInDate(plan.checkInDate || '');
                      setCheckOutDate(plan.checkOutDate || '');
                    } finally {
                      setIsUpdatingDates(false);
                    }
                  }}
                  disabled={isUpdatingDates}
                  className="mt-3 w-full px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isUpdatingDates ? (
                    <>
                      <span className="material-symbols-outlined animate-spin text-base">hourglass_empty</span>
                      更新中...
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-base">save</span>
                      日付を保存
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleShare} className="w-12 h-12 rounded-full bg-white border border-primary/20 flex items-center justify-center text-primary hover:bg-primary/5 transition-colors" title="シェア"><span className="material-symbols-outlined">share</span></button>
            <button onClick={handleEditModeToggle} className={`w-12 h-12 rounded-full border flex items-center justify-center transition-colors ${isEditMode ? 'bg-primary text-white border-primary' : 'bg-white border-primary/20 text-primary hover:bg-primary/5'}`} title="編集モード">
              <span className="material-symbols-outlined">{isEditMode ? 'close' : 'edit'}</span>
            </button>
            {isEditMode && (
              <button onClick={handlePlanUpdate} disabled={isUpdating} className="px-4 h-12 rounded-full bg-primary text-white flex items-center justify-center shadow-lg hover:opacity-90 transition-opacity disabled:opacity-50" title="更新">
                {isUpdating ? '更新中...' : '更新'}
              </button>
            )}
            <button onClick={handleDownload} className="w-12 h-12 rounded-full bg-primary text-white flex items-center justify-center shadow-lg hover:opacity-90 transition-opacity" title="ダウンロード"><span className="material-symbols-outlined">download</span></button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div className="flex flex-col gap-8 order-2 lg:order-1">
          {/* AI Opt Banner */}
          <div className="bg-white p-6 rounded-xl shadow-lg shadow-primary/5 border border-primary/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <p className="text-primary font-bold text-lg mb-1 flex items-center gap-2">
                <span className="material-symbols-outlined">auto_awesome</span>
                AI最適化プラン
              </p>
              <p className="text-text-muted text-sm">
                SatoTrip独自のトレンドデータベースに基づき、<br className="hidden sm:block" />
                最適なスポットとルートを組み合わせました。
              </p>
            </div>
            <div className="flex gap-2">
              <div className="w-10 h-10 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center shadow-sm" title="Database"><span className="material-symbols-outlined">database</span></div>
            </div>
          </div>

          {/* Day Toggles */}
          <div className="flex flex-col sm:flex-row justify-between items-end gap-4">
            <div className="flex border-b border-gray-200 overflow-x-auto w-full scrollbar-hide">
              {Array.from({ length: plan.days }, (_, i) => i + 1).map(day => {
                const dayColor = TAILWIND_COLORS[(day - 1) % TAILWIND_COLORS.length];
                const isActive = day === selectedDay;
                return (
                  <button
                    key={day}
                    onClick={() => setSelectedDay(day)}
                    className={`px-6 py-3 font-bold border-b-2 transition-colors whitespace-nowrap ${isActive
                      ? `${dayColor.border} ${dayColor.text}`
                      : 'border-transparent text-text-muted hover:text-text-light'
                      }`}
                  >
                    {day}日目
                  </button>
                );
              })}
            </div>
          </div>


          {/* Timeline */}
          <div className={`relative pl-12 border-l-2 ml-6 space-y-8 py-4 transition-colors ${currentColor.border} border-opacity-30`}>
            {sortedCurrentDaySpots.length === 0 ? (
              <div className="text-text-muted italic">この日のスポットはまだありません。編集モードから追加してください。</div>
            ) : isEditMode ? (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={sortedCurrentDaySpots.map(s => s.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {sortedCurrentDaySpots.map((pSpot, idx) => (
                    <SortableSpotItem
                      key={pSpot.id}
                      spot={pSpot}
                      index={idx}
                      isEditMode={isEditMode}
                      currentColor={currentColor}
                      editedSpots={editedSpots}
                      handleSpotEdit={handleSpotEdit}
                      calculateEndTime={calculateEndTime}
                      transportModes={transportModes}
                      handleModeChange={handleModeChange}
                      calculateDuration={calculateDuration}
                      totalSpots={sortedCurrentDaySpots.length}
                      onDelete={handleDeleteSpot}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            ) : (
              sortedCurrentDaySpots.map((pSpot, idx) => (
                <React.Fragment key={pSpot.id}>
                  <div className="relative flex items-start gap-4">
                    {/* Dynamic Colored Icon */}
                    <div className={`absolute -left-[4.5rem] w-12 h-12 rounded-full bg-white border-4 flex items-center justify-center shadow-sm z-10 transition-colors ${currentColor.border} ${currentColor.text}`}>
                      <span className="material-symbols-outlined">
                        {pSpot.spot.category === 'Food' ? 'restaurant' : 
                         pSpot.spot.category === 'Shopping' ? 'shopping_bag' : 
                         pSpot.spot.category === 'Hotel' ? 'hotel' : 
                         'palette'}
                      </span>
                    </div>
                    <div className="flex-1 pt-1 group">
                      {pSpot.spot.category === 'Hotel' ? (
                        <p className="text-text-muted font-medium text-sm mb-1">
                          {pSpot.startTime} - 翌日 <span className="text-xs">(宿泊)</span>
                        </p>
                      ) : (
                        <p className="text-text-muted font-medium text-sm mb-1">
                          {pSpot.startTime} - {calculateEndTime(pSpot.startTime || '09:00', pSpot.spot.durationMinutes || 60)}
                          {' '}
                          <span className="text-xs">(滞在: {pSpot.spot.durationMinutes || 60}分)</span>
                        </p>
                      )}
                      <h3 className="text-xl font-bold mb-1 flex items-center gap-2">
                        {pSpot.spot.name}
                        {pSpot.isMustVisit && (
                          <span className="bg-primary text-white text-[10px] px-2 py-0.5 rounded-full font-bold shadow-sm animate-pulse flex items-center gap-1">
                            <span className="material-symbols-outlined text-[12px]">check</span> MUST
                          </span>
                        )}
                      </h3>
                      <p className="text-text-muted text-sm mb-2 line-clamp-2">{pSpot.spot.description}</p>
                      {/* SNS Tag Display */}
                      <div className="flex gap-2 flex-wrap">
                        {pSpot.spot.tags && pSpot.spot.tags.length > 0 ? (
                          pSpot.spot.tags.map((tag, i) => {
                            // タグがオブジェクトの場合はvalueまたはnormalizedを使用、文字列の場合はそのまま使用
                            const tagText = typeof tag === 'string' ? tag : (tag?.value || tag?.normalized || String(tag));
                            return (
                              <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-gradient-to-r from-pink-500 to-purple-500 text-white text-[10px] rounded-full font-bold shadow-sm">
                                <span className="material-symbols-outlined text-[10px]">trending_up</span> {tagText}
                              </span>
                            );
                          })
                        ) : (
                          // Fallback if no tags
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-text-muted text-[10px] rounded-full font-bold">
                            4.8 <span className="material-symbols-outlined text-[10px] text-yellow-500 fill">star</span>
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="w-20 h-20 rounded-lg overflow-hidden shadow-sm flex-shrink-0 hidden sm:block">
                      <img src={pSpot.spot.image} alt="" className="w-full h-full object-cover" />
                    </div>
                  </div>
                  {pSpot.transportMode && idx < currentDaySpots.length - 1 && (
                    <TransportLine
                      mode={(() => {
                        const modeValue = transportModes[pSpot.id] || 'public';
                        // #region agent log
                        fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PlanPages.tsx:1968',message:'TransportLine mode prop',data:{spotId:pSpot.id,transportModesValue:transportModes[pSpot.id],modeValue,transportMode:pSpot.transportMode},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
                        // #endregion
                        return modeValue;
                      })()}
                      duration={(() => {
                        const selectedMode = transportModes[pSpot.id] || 'public';
                        // 元のプランのtransportModeを取得（plan.spotsから）
                        const originalSpot = plan?.spots.find(s => s.id === pSpot.id);
                        const baseMode = originalSpot?.transportMode || pSpot.transportMode;
                        // 選択された移動手段が元の移動手段と異なる場合、またはtransportDurationが存在しない場合は再計算
                        const needsRecalc = selectedMode !== baseMode && 
                          !(selectedMode === 'public' && (baseMode === 'train' || baseMode === 'bus'));
                        return needsRecalc || !pSpot.transportDuration
                          ? calculateDuration(baseMode, pSpot.transportDuration || 20, selectedMode)
                          : pSpot.transportDuration;
                      })()}
                      onModeChange={(m) => handleModeChange(pSpot.id, m)}
                    />
                  )}
                </React.Fragment>
              )))}
            {isEditMode && (
              <button
                onClick={() => setIsAddModalOpen(true)}
                className="w-full py-3 border-2 border-dashed border-primary/30 text-primary font-bold rounded-xl hover:bg-primary/5 transition-colors flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined">add_circle</span> スポットを追加
              </button>
            )}
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => {
                const baseUrl = "https://www.google.com/maps/dir/";
                const destinations = currentDaySpots.map(s => s.spot.name).join("/");
                window.open(`${baseUrl}${destinations}`, '_blank');
              }}
              className="flex items-center gap-2 bg-white border border-gray-300 px-6 py-3 rounded-full font-bold hover:bg-gray-50 transition-colors shadow-sm"
            >
              <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Google_Maps_icon_%282020%29.svg/512px-Google_Maps_icon_%282020%29.svg.png" className="w-6 h-6" alt="Google Maps" />
              Googleマップでルートを開く
            </button>
          </div>

          {/* 宿泊施設検索セクション */}
          <div className="bg-white p-6 rounded-xl shadow-lg border border-primary/10">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">hotel</span>
              宿泊施設検索
            </h3>

            <div className="mb-4">
              <p className="text-sm text-text-muted mb-2">
                <span className="font-bold">推薦エリア: {plan.area}</span>
              </p>
            </div>

            {/* 宿泊施設カテゴリ選択 */}
            {hotelCategories.length > 0 && (
              <div className="mb-4">
                <label className="block font-bold text-text-muted text-sm mb-2">宿泊施設の種類</label>
                <div className="grid grid-cols-2 gap-2">
                  {hotelCategories.map(category => (
                    <button
                      key={category.name}
                      onClick={() => setSelectedHotelCategory(category.name === selectedHotelCategory ? null : category.name)}
                      className={`p-3 rounded-lg border-2 flex items-center gap-2 transition-all text-sm font-bold ${selectedHotelCategory === category.name
                        ? 'border-primary bg-primary/5 text-primary'
                        : 'border-gray-200 hover:border-gray-300 text-text-muted'
                        }`}
                    >
                      <span>{category.icon}</span>
                      <span>{category.name}</span>
                    </button>
                  ))}
                </div>
                {selectedHotelCategory && (
                  <p className="text-xs text-text-muted mt-2">
                    {hotelCategories.find(c => c.name === selectedHotelCategory)?.description}
                  </p>
                )}
              </div>
            )}

            {/* ホテル名入力 */}
            <div className="mb-4">
              <label className="block font-bold text-text-muted text-sm mb-2">ホテル名で検索（オプション）</label>
              <input
                type="text"
                placeholder="例: 鹿児島中央駅前ホテル"
                className="w-full px-4 py-2 bg-gray-50 rounded-lg border border-gray-200 focus:border-primary focus:outline-none"
                value={hotelName}
                onChange={e => setHotelName(e.target.value)}
              />
            </div>

            {/* 検索ボタン */}
            <button
              onClick={handleHotelSearch}
              disabled={isSearchingHotels}
              className="w-full bg-primary text-white py-3 rounded-lg font-bold shadow-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all mb-4"
            >
              {isSearchingHotels ? '検索中...' : '宿泊施設を検索'}
            </button>

            {/* 検索結果表示 */}
            {hotelSearchResult && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <h4 className="font-bold text-sm mb-3">予約サイトで検索</h4>
                <div className="grid grid-cols-1 gap-3">
                  {hotelSearchResult.links.rakuten && !hotelSearchResult.links.rakuten.error && (
                    <div className="flex items-center gap-2">
                      <a
                        href={hotelSearchResult.links.rakuten.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
                      >
                        <span className="text-2xl">🏨</span>
                        <div className="flex-1">
                          <p className="font-bold text-sm">楽天トラベルで検索</p>
                          <p className="text-xs text-text-muted">{hotelSearchResult.links.rakuten.description}</p>
                        </div>
                        <span className="material-symbols-outlined text-red-500">open_in_new</span>
                      </a>
                      {hotelName && (
                        <button
                          onClick={() => handleAddHotelFromSearch(hotelName)}
                          className="px-4 py-3 bg-primary text-white rounded-lg font-bold hover:opacity-90 transition-opacity flex items-center gap-2"
                          title="プランに追加"
                        >
                          <span className="material-symbols-outlined">add</span>
                        </button>
                      )}
                    </div>
                  )}
                  {hotelSearchResult.links.yahoo && !hotelSearchResult.links.yahoo.error && (
                    <div className="flex items-center gap-2">
                      <a
                        href={hotelSearchResult.links.yahoo.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
                      >
                        <span className="text-2xl">🏨</span>
                        <div className="flex-1">
                          <p className="font-bold text-sm">Yahoo!トラベルで検索</p>
                          <p className="text-xs text-text-muted">{hotelSearchResult.links.yahoo.description}</p>
                        </div>
                        <span className="material-symbols-outlined text-blue-500">open_in_new</span>
                      </a>
                      {hotelName && (
                        <button
                          onClick={() => handleAddHotelFromSearch(hotelName)}
                          className="px-4 py-3 bg-primary text-white rounded-lg font-bold hover:opacity-90 transition-opacity flex items-center gap-2"
                          title="プランに追加"
                        >
                          <span className="material-symbols-outlined">add</span>
                        </button>
                      )}
                    </div>
                  )}
                  {hotelSearchResult.links.jalan && !hotelSearchResult.links.jalan.error && (
                    <div className="flex items-center gap-2">
                      <a
                        href={hotelSearchResult.links.jalan.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center gap-3 p-3 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors"
                      >
                        <span className="text-2xl">🏨</span>
                        <div className="flex-1">
                          <p className="font-bold text-sm">じゃらんで検索</p>
                          <p className="text-xs text-text-muted">{hotelSearchResult.links.jalan.description}</p>
                        </div>
                        <span className="material-symbols-outlined text-green-500">open_in_new</span>
                      </a>
                      {hotelName && (
                        <button
                          onClick={() => handleAddHotelFromSearch(hotelName)}
                          className="px-4 py-3 bg-primary text-white rounded-lg font-bold hover:opacity-90 transition-opacity flex items-center gap-2"
                          title="プランに追加"
                        >
                          <span className="material-symbols-outlined">add</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>
                {hotelSearchResult.errors && hotelSearchResult.errors.length > 0 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-xs font-bold text-yellow-800 mb-1">一部の検索に問題があります:</p>
                    {hotelSearchResult.errors.map((error, i) => (
                      <p key={i} className="text-xs text-yellow-700">- {error.affiliate}: {error.error}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Map Area */}
        <div className="order-1 lg:order-2 lg:sticky lg:top-24 h-[400px] lg:h-[600px] bg-gray-100 rounded-2xl overflow-hidden shadow-inner relative z-0">
          <LeafletMap
            planSpots={localPlanSpots.length > 0 ? localPlanSpots : plan.spots}
            areaName={plan.area}
            selectedDay={selectedDay}
            planId={plan.id}
            visibleDays={visibleDays}
            onRouteInfoUpdate={(day, info) => {
              setRouteInfoByDay(prev => ({
                ...prev,
                [day]: info
              }));

              // 個々のスポット間の移動時間をPlanSpotと同期
              if (info.spotDurations && plan) {
                const spotsToUse = localPlanSpots.length > 0 ? localPlanSpots : plan.spots;
                const daySpots = spotsToUse.filter(s => s.day === day);
                const updatedSpots = [...spotsToUse];

                info.spotDurations.forEach(({ spotId, duration }) => {
                  const spotIndex = updatedSpots.findIndex(s => s.id === spotId);
                  if (spotIndex !== -1 && updatedSpots[spotIndex].transportDuration !== duration) {
                    // transportDurationを更新（表示のみ、保存はしない）
                    updatedSpots[spotIndex] = {
                      ...updatedSpots[spotIndex],
                      transportDuration: duration
                    };
                  }
                });

                // 状態を更新（表示のみ）
                if (localPlanSpots.length > 0) {
                  setLocalPlanSpots(updatedSpots);
                } else {
                  setPlan({ ...plan, spots: updatedSpots });
                }
              }
            }}
          />

          {/* Map Overlay Card - Compact and Top Right */}
          <div className="absolute top-4 right-4 w-64 bg-white/95 backdrop-blur-sm p-3 rounded-lg shadow-lg border border-gray-200 transition-all z-[400]">
            <div className="flex flex-col gap-2">
              {/* ヘッダー: 折りたたみボタンとタイトル */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors text-white shadow-sm ${currentColor.bg}`}>
                    <span className="material-symbols-outlined text-sm">map</span>
                  </div>
                  <div>
                    <p className="font-bold text-xs">
                      {selectedDay}日目
                    </p>
                    <p className="text-[10px] text-text-muted">
                      <span className={`font-semibold ${currentColor.text}`}>{pinColorName}</span>
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setIsOverlayExpanded(!isOverlayExpanded)}
                  className="w-6 h-6 rounded flex items-center justify-center hover:bg-gray-100 transition-colors"
                  title={isOverlayExpanded ? "折りたたむ" : "展開"}
                >
                  <span className="material-symbols-outlined text-sm text-text-muted">
                    {isOverlayExpanded ? 'expand_less' : 'expand_more'}
                  </span>
                </button>
              </div>

              {/* 折りたたみ可能なコンテンツ */}
              {isOverlayExpanded && (
                <>
                  {/* ルート情報の詳細表示 - コンパクト */}
                  {routeInfoByDay[selectedDay] && (
                    <div className="bg-gray-50 rounded p-2 border border-gray-200">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1">
                          <span className="text-text-muted">距離:</span>
                          <span className="font-bold">{routeInfoByDay[selectedDay].distance.toFixed(1)} km</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-text-muted">時間:</span>
                          <span className="font-bold">{Math.round(routeInfoByDay[selectedDay].duration)} 分</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-text-muted">🚗</span>
                          <span className="font-bold text-[10px]">{routeInfoByDay[selectedDay].transportation || '車'}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 日ごとの表示切り替え - コンパクト */}
                  {plan.days > 1 && (
                    <div className="flex flex-wrap gap-1.5 pt-1.5 border-t border-gray-200">
                      <span className="text-[10px] font-bold text-text-muted w-full mb-1">表示:</span>
                      {Array.from({ length: plan.days }, (_, i) => i + 1).map(day => {
                        const isVisible = visibleDays.has(day);
                        const dayColor = TAILWIND_COLORS[(day - 1) % TAILWIND_COLORS.length];
                        return (
                          <button
                            key={day}
                            onClick={() => {
                              const newVisibleDays = new Set(visibleDays);
                              if (isVisible) {
                                newVisibleDays.delete(day);
                              } else {
                                newVisibleDays.add(day);
                              }
                              setVisibleDays(newVisibleDays);
                            }}
                            className={`px-2 py-1 rounded-full text-[10px] font-bold transition-all ${isVisible
                              ? `${dayColor.bg} text-white shadow-sm`
                              : 'bg-gray-100 text-text-muted hover:bg-gray-200'
                              }`}
                          >
                            {day}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add Spot Modal */}
      <SpotAddModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAddSpot={handleAddSpot}
        area={plan?.area}
        existingSpotIds={new Set(localPlanSpots.map(s => s.spotId))}
      />
    </div>
  );
};

export const PlanEditor: React.FC<{ planId: string; onNavigate: (path: string) => void }> = ({ planId, onNavigate }) => {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Deep copy to create a local editing state
  const [localPlanSpots, setLocalPlanSpots] = useState<PlanSpot[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Drag & Drop refs
  const dragItem = useRef<number | null>(null);
  const dragOverItem = useRef<number | null>(null);

  useEffect(() => {
    const fetchPlan = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const fetchedPlan = await planApi.getPlan(planId);
        setPlan(fetchedPlan);
        setLocalPlanSpots(JSON.parse(JSON.stringify(fetchedPlan.spots)));
      } catch (err: any) {
        console.error('Failed to fetch plan:', err);
        setError(err.detail || err.message || 'プランの取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPlan();
  }, [planId]);

  useEffect(() => {
    if (!plan) return;
    setHasChanges(JSON.stringify(plan.spots) !== JSON.stringify(localPlanSpots));
  }, [localPlanSpots, plan]);

  const handleDelete = (id: string) => {
    setLocalPlanSpots(prev => prev.filter(s => s.id !== id));
  };

  const handleAddSpot = (spot: Spot) => {
    const newSpot: PlanSpot = {
      id: `new_${Date.now()}`,
      spotId: spot.id,
      spot: spot,
      day: 1,
      startTime: '10:00'
    };
    setLocalPlanSpots(prev => [...prev, newSpot]);
    setIsAddModalOpen(false);
  };

  const handleSave = async () => {
    if (!plan) return;

    try {
      setIsSaving(true);
      // バックエンドAPIでプランを更新
      const updatedPlan = await planApi.updatePlan(plan.id, {
        spots: localPlanSpots,
      });
      setPlan(updatedPlan);
      setLocalPlanSpots(JSON.parse(JSON.stringify(updatedPlan.spots)));
      onNavigate(`/plan/${plan.id}`);
    } catch (err: any) {
      console.error('Failed to save plan:', err);
      alert(err.detail || err.message || 'プランの保存に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-text-muted">プランを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center max-w-md">
          <p className="text-red-600 font-bold mb-2">エラーが発生しました</p>
          <p className="text-red-500 text-sm mb-4">{error || 'プランが見つかりません'}</p>
          <button
            onClick={() => onNavigate('/plans')}
            className="bg-primary text-white px-6 py-3 rounded-full font-bold shadow-lg hover:opacity-90 transition-opacity"
          >
            プラン一覧に戻る
          </button>
        </div>
      </div>
    );
  }

  const onDragStart = (e: React.DragEvent<HTMLDivElement>, index: number) => {
    dragItem.current = index;
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = "move";
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>, index: number) => {
    e.preventDefault(); // Necessary for allowing drop
    dragOverItem.current = index;
  };

  const onDragEnd = () => {
    setDraggedIndex(null);
    if (dragItem.current === null || dragOverItem.current === null) return;
    if (dragItem.current === dragOverItem.current) {
      dragItem.current = null;
      dragOverItem.current = null;
      return;
    }

    const _list = [...localPlanSpots];
    const draggedItemContent = _list[dragItem.current];

    // Remove
    _list.splice(dragItem.current, 1);
    // Add at new position
    _list.splice(dragOverItem.current, 0, draggedItemContent);

    dragItem.current = null;
    dragOverItem.current = null;
    setLocalPlanSpots(_list);
  };

  // --- Mobile Touch Logic (Custom) ---
  const onTouchStart = (e: React.TouchEvent, index: number) => {
    // Prevent scrolling when starting drag on the handle could be handled via CSS 'touch-action: none'
    dragItem.current = index;
    setDraggedIndex(index);
    document.body.style.overflow = 'hidden'; // Lock screen scroll during drag
  };

  const onTouchMove = (e: React.TouchEvent) => {
    if (dragItem.current === null) return;

    const touch = e.touches[0];
    const target = document.elementFromPoint(touch.clientX, touch.clientY);

    if (!target) return;

    // Find closest row defined by data-plan-item
    const row = target.closest('[data-plan-item]');
    if (!row) return;

    const targetIndex = parseInt(row.getAttribute('data-index') || '-1');
    if (targetIndex === -1 || targetIndex === dragItem.current) return;

    // Perform "Live Reorder" (Swap)
    const _list = [...localPlanSpots];
    const draggedItemContent = _list[dragItem.current];

    _list.splice(dragItem.current, 1);
    _list.splice(targetIndex, 0, draggedItemContent);

    setLocalPlanSpots(_list);
    dragItem.current = targetIndex;
    setDraggedIndex(targetIndex);
  };

  const onTouchEnd = () => {
    setDraggedIndex(null);
    dragItem.current = null;
    document.body.style.overflow = ''; // Unlock scroll
  };

  // 既存のプラン内スポットIDセットを作成（重複チェック用）
  const existingSpotIds = new Set(localPlanSpots.map(s => s.spotId));

  return (
    <div className="min-h-screen bg-background-light pb-20">
      <div className="sticky top-16 z-40 bg-white/80 backdrop-blur-sm border-b border-gray-200 px-4 py-4 flex items-center justify-between shadow-sm">
        <h1 className="text-2xl font-black truncate">{plan?.title || 'プラン編集'} <span className="text-sm font-normal text-text-muted ml-2 hidden sm:inline">編集モード</span></h1>
        <div className="flex gap-3 items-center">
          <button
            onClick={() => onNavigate(`/plan/${plan.id}`)}
            className="px-4 py-2 text-sm font-bold text-text-muted hover:text-text-light"
          >
            キャンセル
          </button>
          <button
            onClick={handleSave}
            className={`px-6 py-2 rounded-full text-sm font-bold shadow-lg flex items-center gap-2 transition-all ${hasChanges && !isSaving ? 'bg-primary text-white hover:opacity-90' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}`}
            disabled={!hasChanges || isSaving}
          >
            <span className="material-symbols-outlined text-lg">{isSaving ? 'hourglass_empty' : 'save'}</span>
            {isSaving ? '保存中...' : '変更を保存'}
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 flex flex-col lg:flex-row gap-8">
        <div className="w-full lg:w-3/5 space-y-8">
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">1日目: ルート編集</h2>
              <button className="text-text-muted hover:text-text-light"><span className="material-symbols-outlined">more_vert</span></button>
            </div>

            <div className="space-y-4">
              {localPlanSpots.map((item, index) => (
                <React.Fragment key={item.id}>
                  <div
                    data-plan-item
                    data-index={index}
                    draggable
                    onDragStart={(e) => onDragStart(e, index)}
                    onDragOver={(e) => onDragOver(e, index)}
                    onDragEnd={onDragEnd}
                    className={`group relative flex gap-4 p-3 rounded-xl transition-all select-none ${draggedIndex === index
                      ? 'bg-primary/5 border-2 border-dashed border-primary opacity-50'
                      : 'bg-background-light hover:ring-2 ring-primary/50'
                      }`}
                  >
                    <img src={item.spot.image} className="w-16 h-16 rounded-lg object-cover pointer-events-none" alt={item.spot.name} />
                    <div className="flex-1 min-w-0 pointer-events-none">
                      <p className="font-bold truncate">{item.spot.name}</p>
                      <p className="text-sm text-text-muted">滞在{item.spot.durationMinutes}分・{item.spot.category}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => handleDelete(item.id)} className="w-8 h-8 flex items-center justify-center text-text-muted hover:bg-red-100 hover:text-red-500 rounded-full transition-colors"><span className="material-symbols-outlined">delete</span></button>

                      {/* Drag Handle with Touch Support */}
                      <div
                        className="w-10 h-10 flex items-center justify-center cursor-grab active:cursor-grabbing text-text-muted hover:bg-gray-200 rounded-full"
                        onTouchStart={(e) => onTouchStart(e, index)}
                        onTouchMove={onTouchMove}
                        onTouchEnd={onTouchEnd}
                        style={{ touchAction: 'none' }}
                      >
                        <span className="material-symbols-outlined">drag_indicator</span>
                      </div>
                    </div>
                  </div>
                  {index < localPlanSpots.length - 1 && (
                    <div className="flex justify-center text-sm text-text-muted font-medium py-2">
                      <span className="material-symbols-outlined mr-1 text-base">directions_walk</span> 徒歩15分
                    </div>
                  )}
                </React.Fragment>
              ))}

              <button onClick={() => setIsAddModalOpen(true)} className="w-full py-3 border-2 border-dashed border-primary/30 text-primary font-bold rounded-xl hover:bg-primary/5 transition-colors flex items-center justify-center gap-2">
                <span className="material-symbols-outlined">add_circle</span> スポットを追加
              </button>
            </div>
          </div>
        </div>

        <div className="w-full lg:w-2/5 lg:sticky lg:top-28 self-start">
          <div className="aspect-[4/3] bg-gray-100 rounded-xl overflow-hidden shadow-sm relative z-0">
            {/* Reuse Leaflet Map for editor visualization context */}
            {plan && <LeafletMap planSpots={localPlanSpots} areaName={plan.area} selectedDay={1} planId={plan.id} />}
          </div>
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 mt-4">
            <h3 className="font-bold mb-2">編集のヒント</h3>
            <p className="text-sm text-text-muted">スポットの右側にある「<span className="material-symbols-outlined align-middle text-sm">drag_indicator</span>」をドラッグして、順番を並び替えることができます。</p>
          </div>
        </div>
      </div>

      {/* Add Spot Modal */}
      <SpotAddModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAddSpot={handleAddSpot}
        area={plan?.area}
        existingSpotIds={existingSpotIds}
      />
    </div>
  );
};
