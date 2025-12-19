
import React, { useState, useMemo, useEffect } from 'react';
import { plans, spots, hotels } from '../mockData';
import { AppConfig } from '../config';
import * as planApi from '../src/api/plans';
import * as spotApi from '../src/api/spots';
import { Plan, Spot } from '../types';

export const PlanList: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  const [plansList, setPlansList] = useState<Plan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const fetchedPlans = await planApi.getPlans();
        setPlansList(fetchedPlans);
      } catch (err: any) {
        console.error('Failed to fetch plans:', err);
        setError(err.detail || err.message || 'プランの取得に失敗しました');
        // フォールバック: モックデータを使用
        if (AppConfig.IS_DEMO_MODE) {
          setPlansList(plans);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchPlans();
  }, []);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
        <div className="flex justify-center items-center min-h-[400px]">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-muted">プランを読み込み中...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !AppConfig.IS_DEMO_MODE) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-600 font-bold mb-2">エラーが発生しました</p>
          <p className="text-red-500 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-black">あなたの旅行プラン</h1>
      </div>

      {plansList.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-text-muted text-lg mb-4">まだプランがありません</p>
          <button
            onClick={() => onNavigate('/create')}
            className="bg-primary text-white px-6 py-3 rounded-full font-bold shadow-lg hover:opacity-90 transition-opacity"
          >
            プランを作成する
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {plansList.map((plan) => (
            <div
              key={plan.id}
              onClick={() => onNavigate(`/plan/${plan.id}`)}
              className="group bg-white rounded-xl overflow-hidden shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 cursor-pointer border border-transparent hover:border-primary/20"
            >
              <div className="relative aspect-[4/3] overflow-hidden">
                <img
                  src={plan.thumbnail}
                  alt={plan.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                <div className="absolute bottom-3 right-3 flex gap-2 text-xs text-white font-medium">
                  <span className="bg-black/30 backdrop-blur-sm px-2 py-1 rounded-full flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">calendar_month</span> {plan.days}日間
                  </span>
                  <span className="bg-black/30 backdrop-blur-sm px-2 py-1 rounded-full flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">group</span> {plan.people}名
                  </span>
                </div>
              </div>
              <div className="p-4 flex flex-col gap-2">
                <h3 className="text-lg font-bold leading-tight group-hover:text-primary transition-colors">{plan.title}</h3>
                <div className="flex justify-between items-baseline mt-2">
                  <div className="flex items-center gap-1 text-primary font-bold">
                    <span className="material-symbols-outlined">payments</span>
                    ¥{plan.budget.toLocaleString()}
                  </div>
                  <span className="text-xs text-text-muted">{plan.createdAt}作成</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="fixed bottom-8 right-8 md:hidden">
        <button
          onClick={() => onNavigate('/create')}
          className="w-14 h-14 bg-primary text-white rounded-full shadow-lg flex items-center justify-center"
        >
          <span className="material-symbols-outlined text-3xl">add</span>
        </button>
      </div>
    </div>
  );
};

export const PrefectureSpots: React.FC<{ area: string; onNavigate: (path: string) => void }> = ({ area, onNavigate }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('すべて');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [areaSpots, setAreaSpots] = useState<Spot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const categoryMap: { [key: string]: string } = {
    '歴史': 'History',
    '自然': 'Nature',
    'グルメ': 'Food',
    '文化体験': 'Culture',
    'ショッピング': 'Shopping',
    'アート': 'Art'
  };

  useEffect(() => {
    const fetchSpots = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const fetchedSpots = await spotApi.getSpotsByArea(area);
        setAreaSpots(fetchedSpots);
      } catch (err: any) {
        console.error('Failed to fetch spots:', err);
        setError(err.detail || err.message || 'スポットの取得に失敗しました');
        // フォールバック: モックデータを使用
        if (AppConfig.IS_DEMO_MODE) {
          const filtered = spots.filter(s => s.area === area || area === 'Kyoto');
          setAreaSpots(filtered);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchSpots();
  }, [area]);

  const filteredSpots = useMemo(() => {
    return areaSpots.filter(s => {
      const matchSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.description.toLowerCase().includes(searchTerm.toLowerCase());

      let matchCategory = true;
      if (selectedCategory !== 'すべて') {
        const mappedCat = categoryMap[selectedCategory];
        matchCategory = s.category === mappedCat;
      }

      return matchSearch && matchCategory;
    });
  }, [areaSpots, searchTerm, selectedCategory]);

  const handleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation();
    alert('お気に入りに保存しました！（デモ）');
  };

  const toggleSelection = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleCreatePlan = () => {
    localStorage.setItem(AppConfig.STORAGE_KEYS.PENDING_SPOTS, JSON.stringify(selectedIds));
    onNavigate('/create');
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-10">
        <div className="flex justify-center items-center min-h-[400px]">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-muted">スポットを読み込み中...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !AppConfig.IS_DEMO_MODE) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-10">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-600 font-bold mb-2">エラーが発生しました</p>
          <p className="text-red-500 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10 pb-32">
      <header className="mb-8">
        <h1 className="text-5xl md:text-6xl font-bold mb-2">{area}</h1>
        <p className="text-text-muted">千年の都で、心に残る旅を。</p>
      </header>

      <div className="flex flex-col md:flex-row gap-4 mb-8">
        <div className="flex-grow relative">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-text-muted">search</span>
          <input
            type="text"
            placeholder="気になるスポットを検索！"
            className="w-full pl-12 pr-4 py-3 rounded-full border-none bg-white shadow-sm focus:ring-2 focus:ring-primary"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex-shrink-0 relative w-full md:w-48">
          <select className="w-full appearance-none pl-4 pr-10 py-3 rounded-full border-none bg-white shadow-sm focus:ring-2 focus:ring-primary">
            <option>人気順</option>
            <option>おすすめ順</option>
          </select>
          <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-text-muted">expand_more</span>
        </div>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-4 mb-6 scrollbar-hide">
        {['すべて', '歴史', '自然', 'グルメ', '文化体験', 'ショッピング', 'アート'].map((cat, i) => (
          <button
            key={i}
            onClick={() => setSelectedCategory(cat)}
            className={`px-6 py-2 rounded-full whitespace-nowrap font-medium text-sm transition-colors ${selectedCategory === cat ? 'bg-primary text-white shadow-md' : 'bg-white border border-gray-200 hover:border-primary text-text-light'}`}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {filteredSpots.length > 0 ? (
          filteredSpots.map(spot => {
            const isSelected = selectedIds.includes(spot.id);
            return (
              <div
                key={spot.id}
                onClick={() => toggleSelection(spot.id)}
                className={`bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 group border cursor-pointer relative ${isSelected ? 'ring-4 ring-primary ring-offset-2 border-primary' : 'border-gray-100 hover:-translate-y-1'}`}
              >
                <div className="relative aspect-[4/3] overflow-hidden">
                  <img src={spot.image} alt={spot.name} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />

                  {/* Selection Indicator Overlay */}
                  <div className={`absolute top-3 left-3 w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all z-10 ${isSelected ? 'bg-primary border-primary text-white' : 'bg-black/30 border-white text-transparent'}`}>
                    <span className="material-symbols-outlined text-lg">check</span>
                  </div>

                  <button onClick={handleFavorite} className="absolute top-3 right-3 w-10 h-10 bg-black/30 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-black/50 text-white transition-colors z-10">
                    <span className="material-symbols-outlined">bookmark</span>
                  </button>
                  <div className="absolute bottom-0 left-0 w-full p-4 bg-gradient-to-t from-black/70 to-transparent">
                    <h3 className="text-xl font-bold text-white">{spot.name}</h3>
                  </div>
                </div>
                <div className="p-4">
                  <p className="text-sm text-text-muted mb-3 line-clamp-2">{spot.description}</p>
                  <div className="flex items-center gap-4 text-sm text-text-muted">
                    <div className="flex items-center gap-1"><span className="material-symbols-outlined text-yellow-400 fill">star</span> <span className="text-text-light font-bold">{spot.rating}</span></div>
                    <div className="flex items-center gap-1"><span className="material-symbols-outlined">schedule</span> {spot.durationMinutes}分</div>
                    <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded-full font-medium">{spot.category}</span>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="col-span-full text-center py-12 text-text-muted">
            <span className="material-symbols-outlined text-4xl mb-2">search_off</span>
            <p>条件に一致するスポットが見つかりませんでした。</p>
          </div>
        )}
      </div>

      {/* Floating Action Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white pl-6 pr-2 py-2 rounded-full shadow-2xl flex items-center gap-6 z-50 animate-bounce-in border border-gray-700">
          <div className="flex flex-col">
            <span className="font-bold text-sm">{selectedIds.length}件選択中</span>
            <span className="text-xs text-gray-400">プラン作成に使用</span>
          </div>
          <button
            onClick={handleCreatePlan}
            className="bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-full font-bold text-sm shadow-lg transition-all flex items-center gap-2"
          >
            <span className="material-symbols-outlined">auto_awesome</span>
            プランを作成
          </button>
        </div>
      )}
    </div>
  );
};

export const FavoriteSpots: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedArea, setSelectedArea] = useState('すべて');
  const [selectedCategory, setSelectedCategory] = useState('すべて');
  const [sortBy, setSortBy] = useState<'rating' | 'name'>('rating');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Extract unique values for filters
  const availableAreas = useMemo(() => ['すべて', ...Array.from(new Set(spots.map(s => s.area)))], []);
  const availableCategories = useMemo(() => ['すべて', ...Array.from(new Set(spots.map(s => s.category)))], []);

  // Translate categories for display if needed (Simple mapping)
  const getCategoryLabel = (cat: string) => {
    const map: { [key: string]: string } = {
      'History': '歴史', 'Nature': '自然', 'Food': 'グルメ',
      'Culture': '文化', 'Shopping': '買い物', 'Art': 'アート', 'Relax': 'リラックス'
    };
    return map[cat] || cat;
  };

  const filteredSpots = useMemo(() => {
    let result = spots.filter(s => {
      const matchSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.description.toLowerCase().includes(searchTerm.toLowerCase());
      const matchArea = selectedArea === 'すべて' || s.area === selectedArea;
      const matchCategory = selectedCategory === 'すべて' || s.category === selectedCategory;

      return matchSearch && matchArea && matchCategory;
    });

    if (sortBy === 'rating') {
      result.sort((a, b) => b.rating - a.rating);
    } else {
      result.sort((a, b) => a.name.localeCompare(b.name, 'ja'));
    }

    return result;
  }, [searchTerm, selectedArea, selectedCategory, sortBy]);

  const toggleSelection = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleCreatePlan = () => {
    // Store selected spots in localStorage to pass to CreatePlan page
    localStorage.setItem(AppConfig.STORAGE_KEYS.PENDING_SPOTS, JSON.stringify(selectedIds));
    onNavigate('/create');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10 pb-32">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl md:text-4xl font-black text-text-light mb-2">お気に入りスポット</h1>
          <p className="text-text-muted">保存したスポットをエリアやカテゴリーで整理して、次の旅に備えましょう。</p>
        </div>
        <div className="flex gap-2">
          <button className="bg-primary/10 text-primary px-4 py-2 rounded-full font-bold text-sm hover:bg-primary/20 transition-colors">
            {filteredSpots.length} 件のスポット
          </button>
          {selectedIds.length > 0 && (
            <button onClick={() => setSelectedIds([])} className="text-text-muted hover:text-text-light px-4 py-2 text-sm">
              選択解除
            </button>
          )}
        </div>
      </div>

      {/* Filters Section */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mb-8 space-y-6">
        {/* Search & Sort */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-grow relative">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-text-muted">search</span>
            <input
              type="text"
              placeholder="スポット名やキーワードで検索"
              className="w-full pl-12 pr-4 py-3 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex-shrink-0 relative min-w-[200px]">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="w-full appearance-none pl-4 pr-10 py-3 rounded-xl border border-gray-200 bg-white focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="rating">評価が高い順</option>
              <option value="name">名前順</option>
            </select>
            <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-text-muted">sort</span>
          </div>
        </div>

        <div className="h-px bg-gray-100" />

        {/* Cross Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="text-xs font-bold text-text-muted uppercase tracking-wider mb-3 block">エリアで絞り込み</label>
            <div className="flex flex-wrap gap-2">
              {availableAreas.map(area => (
                <button
                  key={area}
                  onClick={() => setSelectedArea(area)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${selectedArea === area
                    ? 'bg-secondary text-text-light shadow-sm ring-2 ring-secondary ring-offset-1'
                    : 'bg-gray-50 text-text-muted hover:bg-gray-100'
                    }`}
                >
                  {area}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs font-bold text-text-muted uppercase tracking-wider mb-3 block">カテゴリーで絞り込み</label>
            <div className="flex flex-wrap gap-2">
              {availableCategories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${selectedCategory === cat
                    ? 'bg-primary text-white shadow-md ring-2 ring-primary ring-offset-1'
                    : 'bg-gray-50 text-text-muted hover:bg-gray-100'
                    }`}
                >
                  {cat !== 'すべて' && (
                    <span className="material-symbols-outlined text-sm">
                      {cat === 'Food' ? 'restaurant' : cat === 'Shopping' ? 'shopping_bag' : cat === 'Nature' ? 'forest' : cat === 'History' ? 'temple_buddhist' : 'local_activity'}
                    </span>
                  )}
                  {getCategoryLabel(cat)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredSpots.length > 0 ? (
          filteredSpots.map(spot => (
            <div
              key={spot.id}
              onClick={(e) => toggleSelection(e, spot.id)}
              className={`bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 group border flex flex-col cursor-pointer relative ${selectedIds.includes(spot.id) ? 'ring-4 ring-primary ring-offset-2 border-primary' : 'border-gray-100 hover:-translate-y-1'}`}
            >
              <div className="relative aspect-[16/9] overflow-hidden">
                <img src={spot.image} alt={spot.name} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />

                {/* Selection Indicator */}
                <div className={`absolute top-3 left-3 w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all ${selectedIds.includes(spot.id) ? 'bg-primary border-primary text-white' : 'bg-black/30 border-white text-transparent'}`}>
                  <span className="material-symbols-outlined text-lg">check</span>
                </div>

                <div className="absolute top-3 right-3">
                  <button className="w-10 h-10 bg-primary text-white rounded-full flex items-center justify-center shadow-lg transform hover:scale-110 transition-transform" title="お気に入りから削除">
                    <span className="material-symbols-outlined fill">bookmark</span>
                  </button>
                </div>
                <div className="absolute bottom-3 left-3">
                  <span className="px-3 py-1 bg-black/50 backdrop-blur-sm text-white text-xs font-bold rounded-full border border-white/20">
                    {spot.area}
                  </span>
                </div>
              </div>
              <div className="p-5 flex-1 flex flex-col">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-bold text-text-light line-clamp-1">{spot.name}</h3>
                  <div className="flex items-center gap-1 text-yellow-500 text-sm font-bold bg-yellow-50 px-2 py-1 rounded-md">
                    <span className="material-symbols-outlined text-sm fill">star</span> {spot.rating}
                  </div>
                </div>
                <p className="text-sm text-text-muted mb-4 line-clamp-2 flex-1">{spot.description}</p>

                <div className="flex items-center justify-between mt-auto pt-4 border-t border-gray-50">
                  <div className="flex items-center gap-2 text-xs font-medium text-primary bg-primary/5 px-3 py-1 rounded-full">
                    <span className="material-symbols-outlined text-sm">
                      {spot.category === 'Food' ? 'restaurant' : spot.category === 'Shopping' ? 'shopping_bag' : spot.category === 'Nature' ? 'forest' : spot.category === 'History' ? 'temple_buddhist' : 'local_activity'}
                    </span>
                    {getCategoryLabel(spot.category)}
                  </div>
                  <div className="text-xs text-text-muted flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">schedule</span> {spot.durationMinutes}分
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full py-20 text-center">
            <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="material-symbols-outlined text-4xl text-gray-400">filter_list_off</span>
            </div>
            <h3 className="text-xl font-bold text-text-light mb-2">条件に合うスポットが見つかりません</h3>
            <p className="text-text-muted mb-6">フィルター条件を変更するか、新しいスポットを探しに行きましょう。</p>
            <button onClick={() => { setSelectedArea('すべて'); setSelectedCategory('すべて'); setSearchTerm(''); }} className="text-primary font-bold hover:underline">
              すべてのフィルターをクリア
            </button>
          </div>
        )}
      </div>

      {/* Floating Action Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white pl-6 pr-2 py-2 rounded-full shadow-2xl flex items-center gap-6 z-50 animate-bounce-in border border-gray-700">
          <div className="flex flex-col">
            <span className="font-bold text-sm">{selectedIds.length}件選択中</span>
            <span className="text-xs text-gray-400">お気に入りから追加</span>
          </div>
          <button
            onClick={handleCreatePlan}
            className="bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-full font-bold text-sm shadow-lg transition-all flex items-center gap-2"
          >
            <span className="material-symbols-outlined">auto_awesome</span>
            プランを作成
          </button>
        </div>
      )}
    </div>
  );
};

export const HotelList: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <aside className="lg:col-span-1 lg:sticky lg:top-24 self-start space-y-6">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h3 className="font-bold text-lg mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">filter_alt</span> 検索条件
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">エリア</label>
                <select className="w-full rounded-lg border-gray-200 text-sm"><option>東京 (すべて)</option></select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">価格帯</label>
                <input type="range" className="w-full accent-primary" />
                <div className="flex justify-between text-xs text-text-muted"><span>¥5,000</span><span>¥50,000+</span></div>
              </div>
              <button className="w-full bg-primary text-white py-3 rounded-full font-bold shadow-lg hover:opacity-90">検索</button>
            </div>
          </div>
        </aside>

        <div className="lg:col-span-3">
          <h1 className="text-3xl font-bold mb-2">東京のホテル</h1>
          <p className="text-text-muted mb-6">AIがおすすめする、あなたの旅にぴったりのホテルを見つけよう！</p>

          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            <button className="px-4 py-2 bg-primary text-white rounded-full text-sm font-bold">人気順</button>
            <button className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium">価格が安い順</button>
          </div>

          <div className="space-y-6">
            {hotels.map(hotel => (
              <div key={hotel.id} className="flex flex-col md:flex-row bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow border border-gray-100">
                <div className="w-full md:w-1/3 aspect-video md:aspect-auto relative">
                  <img src={hotel.image} alt={hotel.name} className="w-full h-full object-cover" />
                  <button className="absolute top-3 right-3 p-2 bg-white/80 rounded-full text-primary hover:bg-white"><span className="material-symbols-outlined">favorite_border</span></button>
                </div>
                <div className="flex-1 p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="text-lg font-bold">{hotel.name}</h3>
                        <p className="text-sm text-text-muted">{hotel.address}</p>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-yellow-500 font-bold">
                          <span className="material-symbols-outlined fill text-lg">star</span> {hotel.rating} <span className="text-gray-400 font-normal text-xs">({hotel.reviewCount})</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 mt-3">
                      {hotel.tags.map((tag, i) => (
                        <span key={i} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-md font-medium">{tag}</span>
                      ))}
                    </div>
                  </div>
                  <div className="flex justify-between items-end mt-4">
                    <div className="flex gap-3 text-sm text-text-muted">
                      {hotel.features.map((f, i) => <span key={i} className="flex items-center gap-1"><span className="material-symbols-outlined text-base">check</span>{f}</span>)}
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-text-muted">1泊あたり</p>
                      <p className="text-xl font-bold text-primary">¥{hotel.pricePerNight.toLocaleString()}〜</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export const MySpots: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [allSpots, setAllSpots] = useState<Spot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Spot addition states
  const [isAddingSpot, setIsAddingSpot] = useState(false);
  const [addSearchQuery, setAddSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Spot[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const fetchSpots = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const fetchedSpots = await spotApi.getSpots();
        setAllSpots(fetchedSpots);
      } catch (err: any) {
        console.error('Failed to fetch spots:', err);
        setError(err.detail || err.message || 'スポットの取得に失敗しました');
        // フォールバック: モックデータを使用
        if (AppConfig.IS_DEMO_MODE) {
          setAllSpots(spots);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchSpots();
  }, []);

  const filteredSpots = useMemo(() => {
    return allSpots.filter(spot =>
      spot.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      spot.area.toLowerCase().includes(searchTerm.toLowerCase()) ||
      spot.category.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [allSpots, searchTerm]);

  const toggleSelection = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };


  const handleCreatePlan = () => {
    localStorage.setItem(AppConfig.STORAGE_KEYS.PENDING_SPOTS, JSON.stringify(selectedIds));
    onNavigate('/create');
  };

  // Search for spots to add
  useEffect(() => {
    const searchSpots = async () => {
      if (!addSearchQuery.trim() || !isAddingSpot) {
        setSearchResults([]);
        return;
      }

      setIsSearching(true);
      try {
        const results = await spotApi.getSpots({ keyword: addSearchQuery });
        // Filter out spots that are already in allSpots
        const existingIds = new Set(allSpots.map(s => s.id));
        const newSpots = results.filter(s => !existingIds.has(s.id));
        setSearchResults(newSpots);
      } catch (err: any) {
        console.error('Failed to search spots:', err);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    };

    // Debounce search
    const timeoutId = setTimeout(searchSpots, 300);
    return () => clearTimeout(timeoutId);
  }, [addSearchQuery, isAddingSpot, allSpots]);

  const handleAddSpot = (spot: Spot) => {
    setAllSpots(prev => [...prev, spot]);
    setAddSearchQuery('');
    setSearchResults([]);
    setIsAddingSpot(false);
  };

  const toggleAddForm = () => {
    setIsAddingSpot(!isAddingSpot);
    setAddSearchQuery('');
    setSearchResults([]);
  };


  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
        <div className="flex justify-center items-center min-h-[400px]">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-muted">スポットを読み込み中...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !AppConfig.IS_DEMO_MODE) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-600 font-bold mb-2">エラーが発生しました</p>
          <p className="text-red-500 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10 min-h-screen pb-32">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-black text-text-light">My Spot</h1>
          <p className="text-text-muted">登録済みの観光スポット一覧です。ここから旅の計画を始めましょう。</p>
        </div>
        <button
          onClick={toggleAddForm}
          className="bg-primary text-white px-6 py-3 rounded-full font-bold shadow-lg flex items-center gap-2 hover:opacity-90 transition-opacity"
        >
          <span className="material-symbols-outlined">{isAddingSpot ? 'close' : 'add'}</span>
          {isAddingSpot ? 'キャンセル' : 'スポットを追加'}
        </button>
      </div>

      {/* Inline Add Spot Form */}
      {isAddingSpot && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6 animate-fade-in">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">search</span>
            データベースから検索して追加
          </h2>
          <div className="relative mb-4">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-text-muted">search</span>
            <input
              type="text"
              placeholder="スポット名、エリア、カテゴリーで検索..."
              className="w-full pl-12 pr-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
              value={addSearchQuery}
              onChange={(e) => setAddSearchQuery(e.target.value)}
              autoFocus
            />
          </div>

          {/* Search Results */}
          {isSearching && (
            <div className="text-center py-8">
              <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              <p className="text-text-muted text-sm">検索中...</p>
            </div>
          )}

          {!isSearching && addSearchQuery && searchResults.length === 0 && (
            <div className="text-center py-8">
              <span className="material-symbols-outlined text-4xl text-gray-300 mb-2 block">search_off</span>
              <p className="text-text-muted">該当するスポットが見つかりません</p>
            </div>
          )}

          {!isSearching && searchResults.length > 0 && (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {searchResults.map(spot => (
                <div
                  key={spot.id}
                  className="flex items-center gap-4 p-4 border border-gray-200 rounded-xl hover:border-primary hover:bg-primary/5 transition-all group"
                >
                  <img src={spot.image} className="w-16 h-16 rounded-lg object-cover shadow-sm" alt="" />
                  <div className="flex-1">
                    <h3 className="font-bold text-text-light">{spot.name}</h3>
                    <div className="flex items-center gap-3 text-sm text-text-muted mt-1">
                      <span>{spot.area}</span>
                      <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full text-xs font-bold">{spot.category}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleAddSpot(spot)}
                    className="bg-primary text-white px-4 py-2 rounded-full font-bold text-sm hover:opacity-90 transition-opacity flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-sm">add</span>
                    追加
                  </button>
                </div>
              ))}
            </div>
          )}

          {!addSearchQuery && (
            <div className="text-center py-8 text-text-muted text-sm">
              <span className="material-symbols-outlined text-3xl mb-2 block opacity-30">info</span>
              スポット名やエリアを入力して検索してください
            </div>
          )}
        </div>
      )}


      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex gap-4">
          <div className="flex-1 relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">search</span>
            <input
              type="text"
              placeholder="スポット名、エリア、カテゴリーで検索..."
              className="w-full pl-10 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button className="px-4 py-2 border border-gray-200 rounded-xl flex items-center gap-2 text-sm font-bold hover:bg-gray-50"><span className="material-symbols-outlined">filter_list</span> フィルター</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-gray-50 text-text-muted text-sm">
              <tr>
                <th className="p-4 w-10"></th>
                <th className="p-4">スポット名</th>
                <th className="p-4">エリア</th>
                <th className="p-4">カテゴリー</th>
                <th className="p-4 text-right">アクション</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredSpots.length > 0 ? (
                filteredSpots.map(spot => {
                  const isSelected = selectedIds.includes(spot.id);
                  return (
                    <tr
                      key={spot.id}
                      className={`hover:bg-gray-50 transition-colors cursor-pointer ${isSelected ? 'bg-primary/5' : ''}`}
                      onClick={() => toggleSelection(spot.id)}
                    >
                      <td className="p-4 text-center">
                        <div className={`w-5 h-5 rounded border flex items-center justify-center ${isSelected ? 'bg-primary border-primary text-white' : 'border-gray-300 bg-white'}`}>
                          {isSelected && <span className="material-symbols-outlined text-sm">check</span>}
                        </div>
                      </td>
                      <td className="p-4 flex items-center gap-3">
                        <img src={spot.image} className="w-12 h-12 rounded-lg object-cover shadow-sm" alt="" />
                        <span className="font-bold">{spot.name}</span>
                      </td>
                      <td className="p-4">{spot.area}</td>
                      <td className="p-4"><span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-xs font-bold">{spot.category}</span></td>
                      <td className="p-4 text-right">
                        <button className="p-2 hover:bg-gray-200 rounded-full text-text-muted transition-colors mr-2" title="編集"><span className="material-symbols-outlined">edit</span></button>
                        <button className="p-2 hover:bg-red-100 rounded-full text-red-500 transition-colors" title="削除"><span className="material-symbols-outlined">delete</span></button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="p-12 text-center text-text-muted">
                    <span className="material-symbols-outlined text-4xl mb-2 block">search_off</span>
                    該当するスポットが見つかりません
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Floating Action Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white pl-6 pr-2 py-2 rounded-full shadow-2xl flex items-center gap-6 z-50 animate-bounce-in border border-gray-700">
          <div className="flex flex-col">
            <span className="font-bold text-sm">{selectedIds.length}件選択中</span>
            <span className="text-xs text-gray-400">選択したスポットで</span>
          </div>
          <button
            onClick={handleCreatePlan}
            className="bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-full font-bold text-sm shadow-lg transition-all flex items-center gap-2"
          >
            <span className="material-symbols-outlined">auto_awesome</span>
            プランを作成
          </button>
        </div>
      )}
    </div>
  );
};
