
import React, { useState, useMemo, useEffect } from 'react';
import { plans, spots, hotels } from '../mockData';
import * as hotelApi from '../src/api/hotels';
import { HotelCategory, HotelSearchRequest, HotelSearchResult } from '../types';
import { AppConfig } from '../config';
import * as planApi from '../src/api/plans';
import * as spotApi from '../src/api/spots';
import { Plan, Spot } from '../types';
import { SpotMap } from '../components/SpotMap';
import { useToast } from '../components/Toast';
import { FolderTree } from '../components/FolderTree';
import * as folderApi from '../src/api/folders';
import { PlanFolder } from '../types';

export const PlanList: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  const [plansList, setPlansList] = useState<Plan[]>([]);
  const [folders, setFolders] = useState<PlanFolder[]>([]);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selection & Favorite States
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  
  // Move Modal
  const [isMoveModalOpen, setIsMoveModalOpen] = useState(false);
  const [targetMoveFolderId, setTargetMoveFolderId] = useState<string>('');

  const { showSuccess, showError, showWarning } = useToast();

  const fetchFolders = async () => {
    try {
      const fetchedFolders = await folderApi.getFolders();
      setFolders(fetchedFolders);
    } catch (err) {
      console.error('Failed to fetch folders', err);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        // getPlansとgetFoldersを個別に処理して、getFoldersが失敗してもgetPlansの結果を表示できるようにする
        const [fetchedPlansResult, fetchedFoldersResult] = await Promise.allSettled([
          planApi.getPlans(),
          folderApi.getFolders()
        ]);
        
        // getPlansの結果を処理
        if (fetchedPlansResult.status === 'fulfilled') {
          setPlansList(fetchedPlansResult.value);
        } else {
          throw fetchedPlansResult.reason;
        }
        
        // getFoldersの結果を処理（失敗してもエラーにしない）
        if (fetchedFoldersResult.status === 'fulfilled') {
          setFolders(fetchedFoldersResult.value);
        } else {
          // フォルダの取得に失敗してもエラーにしない（空配列を設定）
          setFolders([]);
          console.warn('Failed to fetch folders:', fetchedFoldersResult.reason);
        }
      } catch (err: any) {
        console.error('Failed to fetch data:', err);
        setError(err.detail || err.message || 'データの取得に失敗しました');
        // フォールバック: モックデータを使用
        if (AppConfig.IS_DEMO_MODE) {
          setPlansList(plans);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filter Plans based on selected folder
  const displayPlans = useMemo(() => {
    if (selectedFolderId === null) return plansList;
    return plansList.filter(p => p.folderId === selectedFolderId);
  }, [plansList, selectedFolderId]);

  // Toggle Selection Mode
  const toggleSelectionMode = () => {
    setIsSelectionMode(!isSelectionMode);
    setSelectedIds([]);
  };

  // Toggle Selection based on ID
  const toggleSelection = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  // Select/Deselect All (Scoped to current view)
  const toggleSelectAll = () => {
    if (selectedIds.length === displayPlans.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(displayPlans.map(p => p.id));
    }
  };

  // Toggle Favorite
  const handleToggleFavorite = async (e: React.MouseEvent, plan: Plan) => {
    e.stopPropagation();
    try {
      const newStatus = !plan.isFavorite;
      // Optimistic update
      setPlansList(prev => prev.map(p => p.id === plan.id ? { ...p, isFavorite: newStatus } : p));

      await planApi.updatePlan(plan.id, { is_favorite: newStatus });
    } catch (err) {
      console.error('Failed to update favorite:', err);
      setPlansList(prev => prev.map(p => p.id === plan.id ? { ...p, isFavorite: !plan.isFavorite } : p));
      showError('お気に入りの更新に失敗しました');
    }
  };

  // Delete Single Plan
  const handleDeletePlan = async (e: React.MouseEvent, planId: string) => {
    e.stopPropagation();

    const plan = plansList.find(p => p.id === planId);
    if (plan?.isFavorite) {
      showWarning('お気に入りのプランは削除できません');
      return;
    }

    if (!window.confirm('このプランを削除してもよろしいですか？\n削除すると元に戻すことはできません。')) {
      return;
    }

    try {
      await planApi.deletePlan(planId);
      setPlansList(prev => prev.filter(p => p.id !== planId));
      showSuccess('プランを削除しました');
    } catch (err: any) {
      console.error('Failed to delete plan:', err);
      showError(err.detail || 'プランの削除に失敗しました');
    }
  };

  // Bulk Delete
  const handleBulkDelete = async () => {
    const targets = plansList.filter(p => selectedIds.includes(p.id));
    const favorites = targets.filter(p => p.isFavorite);
    const deletables = targets.filter(p => !p.isFavorite);

    if (favorites.length > 0) {
      showWarning(`${favorites.length}件のお気に入りプランが含まれているため、それらはスキップされます`);
    }

    if (deletables.length === 0) {
      if (favorites.length > 0) return;
      showWarning('削除対象が選択されていません');
      return;
    }

    if (!window.confirm(`${deletables.length}件のプランを削除しますか？\nこの操作は取り消せません。`)) {
      return;
    }

    try {
      await Promise.all(deletables.map(p => planApi.deletePlan(p.id)));

      setPlansList(prev => prev.filter(p => !selectedIds.includes(p.id) || (p.isFavorite && selectedIds.includes(p.id))));
      setSelectedIds([]);
      setIsSelectionMode(false);
      showSuccess(`${deletables.length}件のプランを削除しました`);
    } catch (err) {
      console.error('Bulk delete failed:', err);
      showError('一部のプランの削除に失敗しました');
      const fetched = await planApi.getPlans();
      setPlansList(fetched);
    }
  };
  
  // Bulk Move
  const handleBulkMove = async () => {
    if (selectedIds.length === 0) return;
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FeaturePages.tsx:187',message:'handleBulkMove called',data:{targetMoveFolderId,selectedIds,foldersCount:folders.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
    // #endregion
    try {
      const folderId = targetMoveFolderId === 'root' ? null : targetMoveFolderId;
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FeaturePages.tsx:192',message:'Before updatePlan calls',data:{folderId,selectedIds,validFolderId:folderId !== null ? folders.find(f => f.id === folderId) !== undefined : true},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      await Promise.all(selectedIds.map(id => planApi.updatePlan(id, { folder_id: folderId })));
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FeaturePages.tsx:195',message:'Plans moved successfully',data:{folderId,selectedIdsCount:selectedIds.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      
      // Update local state
      setPlansList(prev => prev.map(p => selectedIds.includes(p.id) ? { ...p, folderId: folderId || undefined } : p));
      
      setSelectedIds([]);
      setIsSelectionMode(false);
      setIsMoveModalOpen(false);
      showSuccess('プランを移動しました');
    } catch (err) {
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FeaturePages.tsx:204',message:'Move failed',data:{error:String(err),targetMoveFolderId,selectedIds},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      console.error('Move failed:', err);
      showError('移動に失敗しました');
    }
  };

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
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10 pb-32">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-black">あなたの旅行プラン</h1>
        <div className="flex gap-2">
          {isSelectionMode ? (
            <div className="flex gap-2">
              <button
                onClick={toggleSelectAll}
                className="px-4 py-2 text-sm font-bold text-primary bg-primary/10 rounded-full hover:bg-primary/20 transition-colors"
              >
                {selectedIds.length === displayPlans.length && displayPlans.length > 0 ? '全解除' : '全選択'}
              </button>
              <button
                onClick={toggleSelectionMode}
                className="px-4 py-2 text-sm font-bold text-text-muted bg-gray-100 rounded-full hover:bg-gray-200 transition-colors"
              >
                完了
              </button>
            </div>
          ) : (
            displayPlans.length > 0 && (
              <button
                onClick={toggleSelectionMode}
                className="px-4 py-2 text-sm font-bold text-text-muted bg-gray-100 rounded-full hover:bg-gray-200 transition-colors flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-lg">checklist</span> 選択
              </button>
            )
          )}
        </div>
      </div>

      <div className="flex gap-8 items-start">
        {/* Sidebar: Folder Tree */}
        <div className="w-64 flex-shrink-0 sticky top-4 hidden md:block" style={{ height: 'calc(100vh - 120px)' }}>
             <FolderTree 
                folders={folders} 
                selectedFolderId={selectedFolderId} 
                onSelect={setSelectedFolderId} 
                onUpdate={fetchFolders}
             />
        </div>

        {/* Main Content */}
        <div className="flex-1">
            {displayPlans.length === 0 ? (
                <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
                <p className="text-text-muted text-lg mb-4">プランがありません</p>
                {selectedFolderId === null && (
                    <button
                        onClick={() => onNavigate('/create')}
                        className="bg-primary text-white px-6 py-3 rounded-full font-bold shadow-lg hover:opacity-90 transition-opacity"
                    >
                        プランを作成する
                    </button>
                )}
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {displayPlans.map((plan) => {
                    const isSelected = selectedIds.includes(plan.id);
                    return (
                    <div
                        key={plan.id}
                        onClick={() => isSelectionMode ? toggleSelection(plan.id) : onNavigate(`/plan/${plan.id}`)}
                        className={`group bg-white rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-300 cursor-pointer border relative ${isSelected ? 'ring-4 ring-primary ring-offset-2 border-primary' : 'border-transparent hover:border-primary/20 hover:-translate-y-1'}`}
                    >
                        <div className="relative aspect-[4/3] overflow-hidden">
                        <img
                            src={plan.thumbnail}
                            alt={plan.title}
                            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />

                        {/* Selection Checkbox Overlay */}
                        {isSelectionMode && (
                            <div className={`absolute inset-0 bg-black/10 z-30 flex items-center justify-center transition-opacity ${isSelected ? 'opacity-100' : 'opacity-0 hover:opacity-100'}`}>
                            <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${isSelected ? 'bg-primary text-white scale-100' : 'bg-white/80 text-gray-400 scale-90'}`}>
                                <span className="material-symbols-outlined text-3xl">check</span>
                            </div>
                            </div>
                        )}

                        {/* Favorite Button (Top Left) */}
                        <button
                            onClick={(e) => handleToggleFavorite(e, plan)}
                            className={`absolute top-2 left-2 w-8 h-8 rounded-full flex items-center justify-center transition-all z-20 ${plan.isFavorite ? 'bg-yellow-400 text-white shadow-md' : 'bg-black/30 text-white/70 hover:bg-black/50 hover:text-white'}`}
                            title={plan.isFavorite ? "お気に入りから削除" : "お気に入りに追加"}
                        >
                            <span className="material-symbols-outlined text-lg fill">{plan.isFavorite ? 'star' : 'star_border'}</span>
                        </button>

                        {/* Delete Button (Top Right) */}
                        {!isSelectionMode && (
                           <button
                             onClick={(e) => handleDeletePlan(e, plan.id)}
                             className={`absolute top-2 right-2 w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-red-500 transition-colors z-20 opacity-0 group-hover:opacity-100 md:opacity-0 md:group-hover:opacity-100 opacity-100 ${plan.isFavorite ? 'hidden' : ''}`}
                             title="プランを削除"
                           >
                              <span className="material-symbols-outlined text-sm">delete</span>
                           </button>
                        )}

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
                        <h3 className="text-lg font-bold leading-tight group-hover:text-primary transition-colors flex items-start gap-1">
                            {plan.title}
                            {plan.isFavorite && <span className="material-symbols-outlined text-yellow-500 text-base fill">star</span>}
                        </h3>
                        <div className="flex justify-between items-baseline mt-2">
                            <div className="flex items-center gap-1 text-primary font-bold">
                            <span className="material-symbols-outlined">payments</span>
                            ¥{plan.budget.toLocaleString()}
                            </div>
                            <span className="text-xs text-text-muted">{plan.createdAt}作成</span>
                        </div>
                        </div>
                    </div>
                    );
                })}
                </div>
            )}
        </div>
      </div>

      {/* Bulk Action Bar */}
      {isSelectionMode && selectedIds.length > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white pl-6 pr-2 py-2 rounded-full shadow-2xl flex items-center gap-4 z-50 animate-bounce-in border border-gray-700">
          <div className="flex flex-col border-r border-gray-700 pr-4">
            <span className="font-bold text-sm">{selectedIds.length}件選択中</span>
          </div>
          
          <button
            onClick={() => {
                setTargetMoveFolderId('');
                setIsMoveModalOpen(true);
            }}
            className="hover:bg-gray-700 px-4 py-2 rounded-full font-bold text-sm transition-colors flex items-center gap-2"
          >
             <span className="material-symbols-outlined">drive_file_move</span>
             移動
          </button>
          
          <button
            onClick={handleBulkDelete}
            className="bg-red-500 hover:bg-red-600 text-white px-6 py-2 rounded-full font-bold text-sm shadow-lg transition-all flex items-center gap-2"
          >
            <span className="material-symbols-outlined">delete</span>
            削除
          </button>
        </div>
      )}
      
      {/* Move Folder Modal */}
      {isMoveModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl w-full max-w-sm p-6 shadow-2xl animate-fade-in-up">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary">folder_open</span>
                    移動先のフォルダを選択
                </h3>
                <div className="mb-6">
                    <select
                        className="w-full p-3 border border-gray-300 rounded-xl bg-gray-50 focus:ring-2 focus:ring-primary outline-none"
                        value={targetMoveFolderId}
                        onChange={(e) => setTargetMoveFolderId(e.target.value)}
                    >
                        <option value="" disabled>フォルダを選択してください</option>
                        <option value="root">すべてのプラン (フォルダなし)</option>
                        {folders.map(f => (
                            <option key={f.id} value={f.id}>{f.name}</option>
                        ))}
                    </select>
                </div>
                <div className="flex gap-3 justify-end">
                    <button
                        onClick={() => setIsMoveModalOpen(false)}
                        className="px-4 py-2 text-gray-500 hover:bg-gray-100 rounded-lg font-bold"
                    >
                        キャンセル
                    </button>
                    <button
                        onClick={handleBulkMove}
                        disabled={!targetMoveFolderId}
                        className="px-6 py-2 bg-primary text-white rounded-full font-bold shadow-lg disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-all"
                    >
                        移動する
                    </button>
                </div>
            </div>
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
    '観光': 'Tourism',
    '体験': 'Experience',
    'イベント': 'Event',
    '温泉': 'HotSpring',
    '絶景': 'ScenicView',
    'カフェ': 'Cafe',
    '宿泊': 'Hotel',
    'お酒': 'Drink',
    'ファッション': 'Fashion',
    'デート': 'Date',
    'ドライブ': 'Drive',
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
      'Culture': '文化', 'Shopping': '買い物', 'Art': 'アート', 'Relax': 'リラックス',
      'Tourism': '観光', 'Experience': '体験', 'Event': 'イベント', 'HotSpring': '温泉',
      'ScenicView': '絶景', 'Cafe': 'カフェ', 'Hotel': '宿泊', 'Drink': 'お酒',
      'Fashion': 'ファッション', 'Date': 'デート', 'Drive': 'ドライブ'
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fade-in">
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
  const [area, setArea] = useState<string>('東京');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [hotelName, setHotelName] = useState<string>('');
  const [checkIn, setCheckIn] = useState<string>('');
  const [checkOut, setCheckOut] = useState<string>('');
  const [numGuests, setNumGuests] = useState<number>(2);
  const [hotelCategories, setHotelCategories] = useState<HotelCategory[]>([]);
  const [searchResult, setSearchResult] = useState<HotelSearchResult | null>(null);
  const [isSearching, setIsSearching] = useState(false);

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

  const handleSearch = async () => {
    setIsSearching(true);
    try {
      const searchRequest: HotelSearchRequest = {
        area,
        category: selectedCategory || undefined,
        hotelName: hotelName || undefined,
        checkIn: checkIn || undefined,
        checkOut: checkOut || undefined,
        numGuests
      };

      const result = await hotelApi.searchHotels(searchRequest);
      setSearchResult(result);
    } catch (err: any) {
      console.error('Failed to search hotels:', err);
      alert(err.detail || err.message || '宿泊施設の検索に失敗しました');
    } finally {
      setIsSearching(false);
    }
  };

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
                <input
                  type="text"
                  placeholder="例: 東京、大阪、京都"
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm"
                  value={area}
                  onChange={e => setArea(e.target.value)}
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">宿泊施設の種類</label>
                <select
                  className="w-full rounded-lg border-gray-200 text-sm"
                  value={selectedCategory || ''}
                  onChange={e => setSelectedCategory(e.target.value || null)}
                >
                  <option value="">すべて</option>
                  {hotelCategories.map(cat => (
                    <option key={cat.name} value={cat.name}>{cat.icon} {cat.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">ホテル名（オプション）</label>
                <input
                  type="text"
                  placeholder="例: 鹿児島中央駅前ホテル"
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm"
                  value={hotelName}
                  onChange={e => setHotelName(e.target.value)}
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">チェックイン日</label>
                <input
                  type="date"
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm"
                  value={checkIn}
                  onChange={e => setCheckIn(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">チェックアウト日</label>
                <input
                  type="date"
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm"
                  value={checkOut}
                  onChange={e => setCheckOut(e.target.value)}
                  min={checkIn || new Date().toISOString().split('T')[0]}
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">予約人数</label>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setNumGuests(Math.max(1, numGuests - 1))}
                    className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200"
                  >
                    -
                  </button>
                  <span className="flex-1 text-center font-bold">{numGuests}名</span>
                  <button
                    onClick={() => setNumGuests(Math.min(20, numGuests + 1))}
                    className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200"
                  >
                    +
                  </button>
                </div>
              </div>

              <button
                onClick={handleSearch}
                disabled={isSearching || !area}
                className="w-full bg-primary text-white py-3 rounded-full font-bold shadow-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSearching ? '検索中...' : '検索'}
              </button>
            </div>
          </div>
        </aside>

        <div className="lg:col-span-3">
          <h1 className="text-3xl font-bold mb-2">{area}のホテル</h1>
          <p className="text-text-muted mb-6">AIがおすすめする、あなたの旅にぴったりのホテルを見つけよう！</p>

          {searchResult ? (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                <h3 className="font-bold text-lg mb-4">予約サイトで検索</h3>
                <div className="grid grid-cols-1 gap-4">
                  {searchResult.links.rakuten && !searchResult.links.rakuten.error && (
                    <a
                      href={searchResult.links.rakuten.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-4 p-4 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <span className="text-3xl">🏨</span>
                      <div className="flex-1">
                        <p className="font-bold">楽天トラベルで検索</p>
                        <p className="text-sm text-text-muted">{searchResult.links.rakuten.description}</p>
                      </div>
                      <span className="material-symbols-outlined text-red-500">open_in_new</span>
                    </a>
                  )}
                  {searchResult.links.yahoo && !searchResult.links.yahoo.error && (
                    <a
                      href={searchResult.links.yahoo.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-4 p-4 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      <span className="text-3xl">🏨</span>
                      <div className="flex-1">
                        <p className="font-bold">Yahoo!トラベルで検索</p>
                        <p className="text-sm text-text-muted">{searchResult.links.yahoo.description}</p>
                      </div>
                      <span className="material-symbols-outlined text-blue-500">open_in_new</span>
                    </a>
                  )}
                  {searchResult.links.jalan && !searchResult.links.jalan.error && (
                    <a
                      href={searchResult.links.jalan.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-4 p-4 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors"
                    >
                      <span className="text-3xl">🏨</span>
                      <div className="flex-1">
                        <p className="font-bold">じゃらんで検索</p>
                        <p className="text-sm text-text-muted">{searchResult.links.jalan.description}</p>
                      </div>
                      <span className="material-symbols-outlined text-green-500">open_in_new</span>
                    </a>
                  )}
                </div>
                {searchResult.errors && searchResult.errors.length > 0 && (
                  <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm font-bold text-yellow-800 mb-1">一部の検索に問題があります:</p>
                    {searchResult.errors.map((error, i) => (
                      <p key={i} className="text-xs text-yellow-700">- {error.affiliate}: {error.error}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 text-center">
              <span className="material-symbols-outlined text-6xl text-gray-300 mb-4">hotel</span>
              <p className="text-text-muted">左側の検索条件を入力して、宿泊施設を検索してください。</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const MySpots: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedArea, setSelectedArea] = useState('すべて');
  const [selectedCategory, setSelectedCategory] = useState('すべて');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [filteredSpots, setFilteredSpots] = useState<Spot[]>([]);
  const [allSpots, setAllSpots] = useState<Spot[]>([]); // For adding new spots locally before refresh
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Spot addition states
  const [isAddingSpot, setIsAddingSpot] = useState(false);
  const [addSearchQuery, setAddSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Spot[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Fetch available filter options (Mock or from API if available)
  const availableAreas = useMemo(() => ['すべて', '北海道', '東京', '京都', '大阪', '福岡', '沖縄'], []);
  const availableCategories = useMemo(() => ['すべて', 'History', 'Nature', 'Food', 'Culture', 'Shopping', 'Art', 'Relax', 'Tourism', 'Experience', 'Event', 'HotSpring', 'ScenicView', 'Cafe', 'Hotel', 'Drink', 'Fashion', 'Date', 'Drive'], []);

  // Translate categories for display
  const getCategoryLabel = (cat: string) => {
    const map: { [key: string]: string } = {
      'History': '歴史', 'Nature': '自然', 'Food': 'グルメ',
      'Culture': '文化', 'Shopping': '買い物', 'Art': 'アート', 'Relax': 'リラックス',
      'Tourism': '観光', 'Experience': '体験', 'Event': 'イベント', 'HotSpring': '温泉',
      'ScenicView': '絶景', 'Cafe': 'カフェ', 'Hotel': '宿泊', 'Drink': 'お酒',
      'Fashion': 'ファッション', 'Date': 'デート', 'Drive': 'ドライブ'
    };
    return map[cat] || cat;
  };

  // Server-side filtering effect
  useEffect(() => {
    const fetchSpots = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const filters: any = {};
        if (selectedArea !== 'すべて') filters.area = selectedArea;
        if (selectedCategory !== 'すべて') filters.category = selectedCategory;
        if (searchTerm) filters.keyword = searchTerm;

        const fetchedSpots = await spotApi.getSpots(filters);
        setFilteredSpots(fetchedSpots);
        // Also keep track of all fetched for local addition context if needed
        // but primarily we use filteredSpots for display
      } catch (err: any) {
        console.error('Failed to fetch spots:', err);
        setError(err.detail || err.message || 'スポットの取得に失敗しました');
        if (AppConfig.IS_DEMO_MODE) {
          // Demo fallback logic
          let result = spots;
          if (selectedArea !== 'すべて') result = result.filter(s => s.area === selectedArea);
          if (selectedCategory !== 'すべて') result = result.filter(s => s.category === selectedCategory);
          if (searchTerm) result = result.filter(s => s.name.includes(searchTerm));
          setFilteredSpots(result);
        }
      } finally {
        setIsLoading(false);
      }
    };

    // Debounce search
    const timeoutId = setTimeout(fetchSpots, 300);
    return () => clearTimeout(timeoutId);
  }, [selectedArea, selectedCategory, searchTerm]);

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
    setFilteredSpots(prev => [spot, ...prev]);
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
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black text-text-light">My Spot</h1>
          <p className="text-text-muted">登録済みの観光スポット一覧です。ここから旅の計画を始めましょう。</p>
        </div>
        <div className="flex gap-2">
          <div className="bg-white rounded-full p-1 border border-gray-200 flex shadow-sm">
            <button
              onClick={() => setViewMode('list')}
              className={`px-4 py-2 rounded-full text-sm font-bold flex items-center gap-1 transition-all ${viewMode === 'list' ? 'bg-primary text-white shadow-md' : 'text-text-muted hover:bg-gray-50'}`}
            >
              <span className="material-symbols-outlined text-lg">list</span> リスト
            </button>
            <button
              onClick={() => setViewMode('map')}
              className={`px-4 py-2 rounded-full text-sm font-bold flex items-center gap-1 transition-all ${viewMode === 'map' ? 'bg-primary text-white shadow-md' : 'text-text-muted hover:bg-gray-50'}`}
            >
              <span className="material-symbols-outlined text-lg">map</span> マップ
            </button>
          </div>
          <button
            onClick={toggleAddForm}
            className="bg-primary text-white px-6 py-3 rounded-full font-bold shadow-lg flex items-center gap-2 hover:opacity-90 transition-opacity"
          >
            <span className="material-symbols-outlined">{isAddingSpot ? 'close' : 'add'}</span>
            {isAddingSpot ? 'キャンセル' : 'スポットを追加'}
          </button>
        </div>
      </div>

      {/* Filters Section */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mb-8 space-y-6">
        {/* Search */}
        <div className="relative">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-text-muted">search</span>
          <input
            type="text"
            placeholder="スポット名で検索"
            className="w-full pl-12 pr-4 py-3 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
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


      {viewMode === 'map' ? (
        <div className="mb-8 animate-fade-in">
          <SpotMap
            spots={filteredSpots}
            height="600px"
            onSpotClick={(spot) => {
              // Could implement scroll to row or modal
              console.log('Clicked', spot.name);
            }}
          />
          <p className="text-right text-xs text-text-muted mt-2">
            表示件数: {filteredSpots.length}件 (位置情報のないスポットは表示されません)
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden animate-fade-in">
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
      )}

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
