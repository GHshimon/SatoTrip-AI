import React, { useState, useEffect } from 'react';
import { Spot } from '../types';
import * as spotApi from '../src/api/spots';

interface SpotAddModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddSpot: (spot: Spot) => void;
  area?: string;
  existingSpotIds?: Set<string>; // 既存のプラン内スポットID（重複チェック用）
}

export const SpotAddModal: React.FC<SpotAddModalProps> = ({
  isOpen,
  onClose,
  onAddSpot,
  area,
  existingSpotIds = new Set(),
}) => {
  const [spots, setSpots] = useState<Spot[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [filteredArea, setFilteredArea] = useState(area || '');

  const categories: Array<{ value: string; label: string }> = [
    { value: '', label: 'すべて' },
    { value: 'History', label: '歴史' },
    { value: 'Nature', label: '自然' },
    { value: 'Food', label: 'グルメ' },
    { value: 'Culture', label: '文化' },
    { value: 'Shopping', label: 'ショッピング' },
    { value: 'Art', label: 'アート' },
    { value: 'Relax', label: 'リラックス' },
    { value: 'Tourism', label: '観光' },
    { value: 'Experience', label: '体験' },
    { value: 'Event', label: 'イベント' },
    { value: 'HotSpring', label: '温泉' },
    { value: 'ScenicView', label: '絶景' },
    { value: 'Cafe', label: 'カフェ' },
    { value: 'Hotel', label: 'ホテル' },
    { value: 'Drink', label: '飲み物' },
    { value: 'Fashion', label: 'ファッション' },
    { value: 'Date', label: 'デート' },
    { value: 'Drive', label: 'ドライブ' },
  ];

  useEffect(() => {
    if (isOpen) {
      loadSpots();
    }
  }, [isOpen, filteredArea, selectedCategory, searchKeyword]);

  const loadSpots = async () => {
    setIsLoading(true);
    try {
      const filters: spotApi.SpotsFilters = {
        area: filteredArea || undefined,
        category: selectedCategory || undefined,
        keyword: searchKeyword || undefined,
        limit: 100,
      };
      const fetchedSpots = await spotApi.getSpots(filters);
      setSpots(fetchedSpots);
    } catch (err) {
      console.error('Failed to load spots:', err);
      alert('スポットの取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddSpot = (spot: Spot) => {
    // 重複チェック
    if (existingSpotIds.has(spot.id)) {
      alert('このスポットは既にプランに含まれています');
      return;
    }
    onAddSpot(spot);
    onClose();
  };

  if (!isOpen) return null;

  // フィルタリングされたスポット（既存のスポットを除外）
  const availableSpots = spots.filter(spot => !existingSpotIds.has(spot.id));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[80vh] flex flex-col shadow-2xl overflow-hidden">
        {/* ヘッダー */}
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <h3 className="font-bold text-lg">スポットを追加</h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-full transition-colors"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* フィルター */}
        <div className="p-4 border-b border-gray-100 bg-white">
          <div className="space-y-4">
            {/* エリア検索 */}
            <div>
              <label className="block text-sm font-bold text-text-muted mb-2">エリア</label>
              <input
                type="text"
                placeholder="エリア名を入力（例: 京都、大阪）"
                className="w-full px-4 py-2 bg-gray-50 rounded-lg border border-gray-200 focus:border-primary focus:outline-none"
                value={filteredArea}
                onChange={(e) => setFilteredArea(e.target.value)}
              />
            </div>

            {/* カテゴリ選択 */}
            <div>
              <label className="block text-sm font-bold text-text-muted mb-2">カテゴリ</label>
              <select
                className="w-full px-4 py-2 bg-gray-50 rounded-lg border border-gray-200 focus:border-primary focus:outline-none"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                {categories.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            {/* キーワード検索 */}
            <div>
              <label className="block text-sm font-bold text-text-muted mb-2">キーワード検索</label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-text-muted">search</span>
                <input
                  type="text"
                  placeholder="スポット名で検索..."
                  className="w-full pl-12 pr-4 py-2 bg-gray-50 rounded-lg border border-gray-200 focus:border-primary focus:outline-none"
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                />
              </div>
            </div>

            {/* 検索ボタン */}
            <button
              onClick={loadSpots}
              disabled={isLoading}
              className="w-full bg-primary text-white py-2 rounded-lg font-bold shadow-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isLoading ? '検索中...' : '検索'}
            </button>
          </div>
        </div>

        {/* スポット一覧 */}
        <div className="flex-1 overflow-y-auto p-4 bg-white">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : availableSpots.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <p className="font-bold mb-2">スポットが見つかりません</p>
              <p className="text-sm">検索条件を変更して再度お試しください</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {availableSpots.map((spot) => (
                <div
                  key={spot.id}
                  onClick={() => handleAddSpot(spot)}
                  className="cursor-pointer hover:bg-primary/5 hover:border-primary p-3 rounded-xl border border-gray-100 flex gap-3 items-center transition-all group"
                >
                  <img
                    src={spot.image}
                    className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
                    alt={spot.name}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm group-hover:text-primary truncate">{spot.name}</p>
                    <p className="text-xs text-text-muted truncate">
                      {spot.area} / {categories.find(c => c.value === spot.category)?.label || spot.category}
                    </p>
                    {spot.description && (
                      <p className="text-xs text-text-muted mt-1 line-clamp-2">{spot.description}</p>
                    )}
                  </div>
                  <div className="ml-auto opacity-0 group-hover:opacity-100 text-primary">
                    <span className="material-symbols-outlined">add_circle</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

