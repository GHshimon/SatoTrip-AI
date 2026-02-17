import React, { useState, useEffect, useRef } from 'react';
import { adminStats, users } from '../mockData';
import { Spot, SPOT_CATEGORIES, SPOT_CATEGORY_LABELS } from '../types';
import * as spotApi from '../src/api/spots';
import { getBulkAddJobStatus, bulkAddSpotsByPrefecture, getSearchKeywordsConfig, BulkAddResponse, BulkAddJobStatus } from '../src/api/spots';
import { getUsers, updateUserRole, updateUserStatus, getSystemSettings, updateSystemSettings, AdminUser, SystemSettings, getAdminStats, getSystemAlerts, getTrendingAreas, AdminStats, SystemAlert, TrendingArea } from '../src/api/admin';
import { getTags, getRecommendedTags, normalizeTags, TagResponse, TagStats } from '../src/api/spots';
import { useToast } from '../components/Toast';
import { SpotMap } from '../components/SpotMap';

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

export const AdminDashboard: React.FC = () => {
  const { showError } = useToast();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [trendingAreas, setTrendingAreas] = useState<TrendingArea[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [statsData, alertsData, trendingData] = await Promise.all([
          getAdminStats(),
          getSystemAlerts(),
          getTrendingAreas(3)
        ]);
        setStats(statsData);
        setAlerts(alertsData);
        setTrendingAreas(trendingData);
      } catch (err: any) {
        console.error('Failed to fetch dashboard data:', err);
        setError(err.detail || err.message || 'ダッシュボードデータの取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const displayStats = stats ? [
    {
      label: 'プラン生成数 (本日)',
      value: stats.plans_today.toLocaleString(),
      change: `${stats.plans_change >= 0 ? '+' : ''}${stats.plans_change.toFixed(1)}%`,
      trend: stats.plans_trend,
      icon: 'auto_awesome',
      color: 'text-accent'
    },
    {
      label: 'APIコール数 (24h)',
      value: stats.api_calls_24h.toLocaleString(),
      change: `${stats.api_calls_change >= 0 ? '+' : ''}${stats.api_calls_change.toFixed(1)}%`,
      trend: stats.api_calls_trend,
      icon: 'api',
      color: 'text-primary'
    },
    {
      label: 'エラーレート',
      value: `${stats.error_rate.toFixed(2)}%`,
      change: `${stats.error_rate_change >= 0 ? '+' : ''}${stats.error_rate_change.toFixed(1)}%`,
      trend: stats.error_rate_trend,
      icon: 'error_outline',
      color: 'text-red-500'
    }
  ] : [];

  const getAlertBgColor = (type: string) => {
    switch (type) {
      case 'error': return 'bg-red-50 text-red-700';
      case 'warning': return 'bg-yellow-50 text-yellow-700';
      case 'success': return 'bg-green-50 text-green-700';
      default: return 'bg-gray-50 text-gray-700';
    }
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'success': return 'check_circle';
      default: return 'info';
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 md:p-10 bg-background-light min-h-full">
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 md:p-10 bg-background-light min-h-full">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <p className="font-bold">エラー</p>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-10 bg-background-light min-h-full">
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-text-light mb-2">管理者ダッシュボード</h1>
        <p className="text-text-muted">SatoTrip Commercialの現在のステータスとアクティビティ概要。</p>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        {displayStats.map((stat, i) => (
          <div key={i} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <div className="flex justify-between mb-2">
              <span className="text-text-muted font-medium">{stat.label}</span>
              <span className={`material-symbols-outlined ${stat.color}`}>{stat.icon}</span>
            </div>
            <div className="text-4xl font-bold text-text-light mb-1">{stat.value}</div>
            <div className={`text-sm font-bold flex items-center ${stat.trend === 'up' ? 'text-green-500' : 'text-red-500'}`}>
              <span className="material-symbols-outlined text-lg">{stat.trend === 'up' ? 'trending_up' : 'trending_down'}</span>
              {stat.change}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold mb-4">最近のシステムアラート</h2>
          <div className="space-y-4">
            {alerts.length === 0 ? (
              <p className="text-text-muted text-sm">アラートはありません</p>
            ) : (
              alerts.map((alert, i) => (
                <div key={i} className={`flex items-start gap-3 p-3 rounded-lg text-sm ${getAlertBgColor(alert.type)}`}>
                  <span className="material-symbols-outlined">{getAlertIcon(alert.type)}</span>
                  <div>
                    <p className="font-bold">{alert.title}</p>
                    <p className="opacity-80">{alert.message}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold mb-4">人気急上昇エリア</h2>
          <div className="space-y-4">
            {trendingAreas.length === 0 ? (
              <p className="text-text-muted text-sm">データがありません</p>
            ) : (
              trendingAreas.map((area, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold">{i + 1}</div>
                    <span className="font-bold">{area.area}</span>
                  </div>
                  <div className="text-sm text-text-muted flex items-center gap-1">
                    <span className="material-symbols-outlined text-green-500 text-sm">trending_up</span>
                    {area.change_rate >= 0 ? '+' : ''}{area.change_rate.toFixed(1)}%
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export const AdminSpots: React.FC = () => {
  const { showSuccess, showError, showWarning } = useToast();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPrefecture, setSelectedPrefecture] = useState<string | null>(null);
  const [expandedRegions, setExpandedRegions] = useState<Set<string>>(new Set());
  const [isAreaFilterOpen, setIsAreaFilterOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState<'bottom' | 'top'>('bottom');
  const areaFilterRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [spots, setSpots] = useState<Spot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isIndividualCreateModalOpen, setIsIndividualCreateModalOpen] = useState(false);
  const [isBulkAdding, setIsBulkAdding] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<BulkAddResponse | null>(null);
  const [prefecture, setPrefecture] = useState('');
  const [maxResultsPerKeyword, setMaxResultsPerKeyword] = useState<number>(3);
  const [maxKeywords, setMaxKeywords] = useState<number>(20);
  const [maxTotalVideos, setMaxTotalVideos] = useState<number>(30);
  const [addLocation, setAddLocation] = useState<boolean>(true);
  const [addCategory, setAddCategory] = useState<string>('');
  const [runAsync, setRunAsync] = useState<boolean>(true);
  const [jobId, setJobId] = useState<string | null>(null);
  const [sortField, setSortField] = useState<'created_at' | 'updated_at' | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Individual create form state
  const [createForm, setCreateForm] = useState<Partial<Spot>>({
    name: '',
    description: '',
    area: '',
    category: 'Culture',
    image: '',
    rating: 0,
    price: undefined,
    durationMinutes: 60,
    location: undefined
  });

  const [viewMode, setViewMode] = useState<'table' | 'grid' | 'map'>('table');
  const [filterCategory, setFilterCategory] = useState('All');
  const [filterMissingLocation, setFilterMissingLocation] = useState(false);
  const [filterMissingImage, setFilterMissingImage] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);

  // Editing State
  const [editingSpot, setEditingSpot] = useState<Spot | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editForm, setEditForm] = useState<Partial<Spot>>({});
  const [isResearching, setIsResearching] = useState(false);

  const [keywordConfig, setKeywordConfig] = useState<Record<string, any>>({});
  const [availableKeywords, setAvailableKeywords] = useState<string[]>([]);

  // Fetch spots and keyword config on mount
  useEffect(() => {
    fetchSpots();
    getSearchKeywordsConfig().then(setKeywordConfig).catch(e => console.error("Failed to load keywords", e));
  }, []);

  // Update available keywords when prefecture changes
  useEffect(() => {
    if (!prefecture || !keywordConfig) {
      setAvailableKeywords([]);
      return;
    }
    // config keys are "鹿児島県", "福岡県" etc.
    // User might input partial text, but for now exact match or simple includes?
    // Using exact match against keys for simplicity as config is structured by prefecture name.
    const prefKey = Object.keys(keywordConfig).find(k => k === prefecture || prefecture.includes(k) || k.includes(prefecture));

    if (prefKey && keywordConfig[prefKey] && keywordConfig[prefKey]['カテゴリ']) {
      setAvailableKeywords(keywordConfig[prefKey]['カテゴリ']);
    } else {
      setAvailableKeywords([]);
    }
  }, [prefecture, keywordConfig]);

  // ドロップダウンの位置を計算して調整
  useEffect(() => {
    const calculatePosition = () => {
      if (isAreaFilterOpen && areaFilterRef.current) {
        const rect = areaFilterRef.current.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const spaceBelow = viewportHeight - rect.bottom;
        const spaceAbove = rect.top;
        const estimatedDropdownHeight = 500; // 推定ドロップダウン高さ

        // 下側のスペースが不足している場合、かつ上側のスペースが十分な場合は上向きに表示
        if (spaceBelow < estimatedDropdownHeight && spaceAbove > spaceBelow) {
          setDropdownPosition('top');
        } else {
          setDropdownPosition('bottom');
        }
      }
    };

    calculatePosition();

    // ウィンドウリサイズ時にも再計算
    if (isAreaFilterOpen) {
      window.addEventListener('resize', calculatePosition);
      window.addEventListener('scroll', calculatePosition, true);
      return () => {
        window.removeEventListener('resize', calculatePosition);
        window.removeEventListener('scroll', calculatePosition, true);
      };
    }
  }, [isAreaFilterOpen]);

  // ドロップダウンの外側をクリックしたときに閉じる
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (areaFilterRef.current && !areaFilterRef.current.contains(event.target as Node)) {
        setIsAreaFilterOpen(false);
      }
    };

    if (isAreaFilterOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isAreaFilterOpen]);

  // ジョブ進捗ポーリング
  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const intervalId = window.setInterval(async () => {
      try {
        const status = await getBulkAddJobStatus(jobId);
        if (cancelled) return;
        setBulkProgress(status);
        if (status.job_status === 'succeeded' || status.job_status === 'failed') {
          window.clearInterval(intervalId);
          setIsBulkAdding(false);
          setJobId(null);

          if (status.job_status === 'succeeded' && status.success) {
            let message = `一括追加が完了しました。\n`;
            message += `追加件数: ${status.imported}件\n`;
            message += `処理キーワード数: ${status.processed_keywords}/${status.total_keywords}\n`;
            message += `取得動画数: ${status.total_videos}件`;
            if (status.quota_exceeded) {
              message += `\n\n⚠️ YouTube APIのクォータ制限に達しました。一部のキーワードは処理できませんでした。`;
            }
            // Gemini要約が全て失敗した場合の警告
            if (status.total_videos === 0 && status.processed_keywords > 0) {
              message = 'YouTube検索は成功しましたが、Gemini APIの要約が全て失敗しました。\n' +
                'Gemini APIのクォータ制限に達している可能性があります。\n' +
                'しばらく待ってから再度お試しください。';
            }
            if (status.location_updated !== undefined) {
              message += `\n位置情報付与: ${status.location_updated}件`;
            }
            showSuccess(message.replace(/\n/g, ' '));
            setIsModalOpen(false);
            setPrefecture('');
            fetchSpots();
          } else if (status.job_status === 'failed') {
            showError(`一括追加に失敗しました: ${status.error || '不明なエラー'}`);
          }
        }
      } catch (e) {
        // ポーリング失敗は一時的な可能性があるため黙殺（コンソールにのみ出す）
        console.error('Job polling failed:', e);
      }
    }, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [jobId]);

  const fetchSpots = async () => {
    setIsLoading(true);
    try {
      // 最大1000件まで一度に取得可能なので、limitを指定
      // 1000件を超える場合は複数回に分けて取得
      let allSpots: Spot[] = [];
      let skip = 0;
      const limit = 1000;
      let hasMore = true;

      while (hasMore) {
        const data = await spotApi.getSpots({ skip, limit });
        allSpots = [...allSpots, ...data];
        
        // 取得したデータがlimit未満なら、これ以上データがない
        if (data.length < limit) {
          hasMore = false;
        } else {
          skip += limit;
        }
      }

      setSpots(allSpots);
    } catch (error) {
      console.error('Failed to fetch spots:', error);
      showError('スポット情報の取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBulkAddSpots = async () => {
    if (!prefecture.trim()) {
      showWarning('都道府県名を入力してください（例: 鹿児島県）');
      return;
    }

    setIsBulkAdding(true);
    setBulkProgress(null);

    try {
      const result = await bulkAddSpotsByPrefecture(prefecture.trim(), {
        max_results_per_keyword: maxResultsPerKeyword,
        max_keywords: maxKeywords,
        max_total_videos: maxTotalVideos,
        add_location: addLocation,
        run_async: runAsync,
        category: addCategory || undefined
      });
      setBulkProgress(result);

      // 非同期ジョブの場合はポーリングで完了を待つ
      if (result.job_id) {
        setIsBulkAdding(true);
        setJobId(result.job_id);
        return;
      }

      if (result.success) {
        let message = `一括追加が完了しました。\n`;
        if (result.created !== undefined && result.merged !== undefined) {
          message += `新規作成: ${result.created}件、既存更新: ${result.merged}件（合計: ${result.imported}件）\n`;
        } else {
          message += `追加件数: ${result.imported}件\n`;
        }
        message += `処理キーワード数: ${result.processed_keywords}/${result.total_keywords}\n`;
        message += `取得動画数: ${result.total_videos}件`;
        if (result.skipped > 0) {
          message += `\nスキップ: ${result.skipped}件`;
        }

        if (result.quota_exceeded) {
          message += `\n\n⚠️ YouTube APIのクォータ制限に達しました。一部のキーワードは処理できませんでした。`;
        }

        // Gemini要約が全て失敗した場合の警告
        if (result.total_videos === 0 && result.processed_keywords > 0) {
          message = 'YouTube検索は成功しましたが、Gemini APIの要約が全て失敗しました。\n' +
            'Gemini APIのクォータ制限に達している可能性があります。\n' +
            'しばらく待ってから再度お試しください。';
        }

        if (result.location_updated !== undefined) {
          message += `\n位置情報付与: ${result.location_updated}件`;
        }

        showSuccess(message.replace(/\n/g, ' '));
        setIsModalOpen(false);
        setPrefecture('');
        fetchSpots(); // Refresh list
      } else {
        showError(`一括追加に失敗しました: ${result.error || '不明なエラー'}`);
      }
    } catch (error: any) {
      console.error('Bulk add failed:', error);

      let errorMessage = '一括追加に失敗しました';
      if (error?.detail) {
        errorMessage = error.detail;
      } else if (error?.message) {
        errorMessage = error.message;
      }

      showError(errorMessage);
    } finally {
      if (!jobId) setIsBulkAdding(false);
    }
  };

  const handleEditClick = (spot: Spot) => {
    setEditingSpot(spot);
    setEditForm({ ...spot });
    setIsEditModalOpen(true);
  };

  const handleUpdateSpot = async () => {
    if (!editingSpot || !editForm.name) return;

    try {
      setIsLoading(true);

      const updateData: any = { ...editForm };
      // Ensure number types
      if (updateData.location?.lat) updateData.latitude = Number(updateData.location.lat);
      if (updateData.location?.lng) updateData.longitude = Number(updateData.location.lng);

      // Construct API payload
      const apiData: any = {
        name: updateData.name,
        description: updateData.description,
        area: updateData.area,
        category: updateData.category,
        image: updateData.image,
        rating: updateData.rating,
        price: updateData.price,
        duration_minutes: updateData.durationMinutes,
      };

      if (updateData.location) {
        apiData.latitude = updateData.location.lat;
        apiData.longitude = updateData.location.lng;
      }

      await spotApi.updateSpot(editingSpot.id, apiData);

      showSuccess('スポット情報を更新しました');
      setIsEditModalOpen(false);
      setEditingSpot(null);
      fetchSpots();
    } catch (error) {
      console.error('Update failed:', error);
      showError('更新に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResearchSpot = async () => {
    if (!editForm.name || !editForm.name.trim()) {
      showWarning('スポット名を入力してください');
      return;
    }

    setIsResearching(true);
    try {
      const researchResult = await spotApi.researchSpot(editForm.name);

      // 取得した情報をフォームに反映
      setEditForm({
        ...editForm,
        name: researchResult.name || editForm.name,
        description: researchResult.description || editForm.description,
        area: researchResult.area || editForm.area,
        category: researchResult.category as any || editForm.category,
        image: researchResult.image || editForm.image,
        price: researchResult.price || editForm.price,
        durationMinutes: researchResult.duration_minutes || editForm.durationMinutes,
      });

      showSuccess('AIリサーチが完了しました。情報を確認してください。');
    } catch (error: any) {
      console.error('Research failed:', error);
      showError(error.detail || error.message || 'AIリサーチに失敗しました');
    } finally {
      setIsResearching(false);
    }
  };

  const handleDeleteSpot = async (id: string) => {
    if (!window.confirm('本当にこのスポットを削除しますか？')) return;
    try {
      await spotApi.deleteSpot(id);
      showSuccess('スポットを削除しました');
      fetchSpots();
    } catch (error) {
      console.error('Delete failed:', error);
      showError('削除に失敗しました');
    }
  };

  const handleCreateSpot = async () => {
    if (!createForm.name) {
      showWarning('スポット名を入力してください');
      return;
    }

    try {
      setIsLoading(true);
      const createData: any = {
        name: createForm.name,
        description: createForm.description || '',
        area: createForm.area || '',
        category: createForm.category || 'Culture',
        image: createForm.image || '',
        rating: createForm.rating || 0,
        price: createForm.price,
        duration_minutes: createForm.durationMinutes || 60,
      };

      if (createForm.location) {
        createData.latitude = createForm.location.lat;
        createData.longitude = createForm.location.lng;
      }

      await spotApi.createSpot(createData);
      showSuccess('スポットを作成しました');
      setIsIndividualCreateModalOpen(false);
      setCreateForm({
        name: '',
        description: '',
        area: '',
        category: 'Culture',
        image: '',
        rating: 0,
        price: undefined,
        durationMinutes: 60,
        location: undefined
      });
      fetchSpots();
    } catch (error) {
      console.error('Create failed:', error);
      showError('作成に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  // 日付フォーマット関数
  const formatDateTime = (dateString?: string): string => {
    if (!dateString) return '-';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '-';
    }
  };

  // ソート処理
  const handleSort = (field: 'created_at' | 'updated_at') => {
    if (sortField === field) {
      // 同じフィールドの場合はソート方向を切り替え
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // 新しいフィールドの場合は降順で開始
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Filter logic
  let filteredSpots = spots.filter(s => {
    const matchesSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase()) || s.area.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesPrefecture = selectedPrefecture === null || (selectedPrefecture && s.area.includes(selectedPrefecture));
    const matchesCategory = filterCategory === 'All' || s.category === filterCategory;
    const matchesLocation = !filterMissingLocation || !s.location;
    const matchesImage = !filterMissingImage || !s.image;
    
    return matchesSearch && matchesPrefecture && matchesCategory && matchesLocation && matchesImage;
  });

  // Sorting
  if (sortField) {
    filteredSpots = [...filteredSpots].sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      if (!aValue && !bValue) return 0;
      if (!aValue) return 1;
      if (!bValue) return -1;
      const aDate = new Date(aValue).getTime();
      const bDate = new Date(bValue).getTime();
      return sortDirection === 'asc' ? aDate - bDate : bDate - aDate;
    });
  }

  // Pagination
  const totalPages = Math.ceil(filteredSpots.length / itemsPerPage);
  const displayedSpots = filteredSpots.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  // カテゴリフィルタ: 定義されたカテゴリリストを使用し、データベースに存在するもののみ表示
  const existingCategories = new Set(spots.map(s => s.category).filter(Boolean));
  const categories = ['All', ...SPOT_CATEGORIES.filter(cat => existingCategories.has(cat))];

  // 地方の展開/折り畳みを切り替える
  const toggleRegion = (regionId: string) => {
    setExpandedRegions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(regionId)) {
        newSet.delete(regionId);
      } else {
        newSet.add(regionId);
      }
      return newSet;
    });
  };

  // 都道府県を選択する
  const handlePrefectureSelect = (pref: string) => {
    if (selectedPrefecture === pref) {
      setSelectedPrefecture(null); // 同じ都道府県をクリックした場合は選択解除
    } else {
      setSelectedPrefecture(pref);
    }
    setCurrentPage(1);
  };

  // CSVエクスポート機能
  const exportSpotsToCSV = () => {
    const headers = ['ID', '名前', '説明', 'エリア', 'カテゴリ', '評価', '価格', '所要時間(分)', '画像URL', '緯度', '経度', '追加日', '更新日'];
    const rows = filteredSpots.map(spot => [
      spot.id,
      spot.name || '',
      (spot.description || '').replace(/"/g, '""'),
      spot.area || '',
      spot.category || '',
      spot.rating || 0,
      spot.price || '',
      spot.durationMinutes || 0,
      spot.image || '',
      spot.location?.lat || '',
      spot.location?.lng || '',
      spot.created_at || '',
      spot.updated_at || ''
    ]);

    const csvContent = [
      headers.map(h => `"${h}"`).join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n');

    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `spots_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showSuccess('CSVファイルをエクスポートしました');
  };

  // Stats
  const stats = {
    total: spots.length,
    missingLocation: spots.filter(s => !s.location).length,
    missingImage: spots.filter(s => !s.image).length,
    categories: new Set(spots.map(s => s.category)).size
  };

  return (
    <div className="p-6 md:p-10 bg-background-light min-h-full relative pb-24">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text-light">スポット管理</h1>
          <p className="text-text-muted">登録されている観光スポットの管理、一括追加、編集。</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-primary text-white px-4 py-2 rounded-lg font-bold flex items-center gap-2 shadow-lg hover:bg-primary/90 transition-colors"
        >
          <span className="material-symbols-outlined">add</span> 新規スポット
        </button>
      </header>

      {/* Stats Dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-full"><span className="material-symbols-outlined">place</span></div>
          <div><div className="text-xs text-text-muted font-bold">総スポット数</div><div className="text-xl font-bold">{stats.total}</div></div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="p-3 bg-red-50 text-red-600 rounded-full"><span className="material-symbols-outlined">wrong_location</span></div>
          <div><div className="text-xs text-text-muted font-bold">位置情報なし</div><div className="text-xl font-bold text-red-600">{stats.missingLocation}</div></div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="p-3 bg-orange-50 text-orange-600 rounded-full"><span className="material-symbols-outlined">image_not_supported</span></div>
          <div><div className="text-xs text-text-muted font-bold">画像なし</div><div className="text-xl font-bold text-orange-600">{stats.missingImage}</div></div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="p-3 bg-green-50 text-green-600 rounded-full"><span className="material-symbols-outlined">category</span></div>
          <div><div className="text-xs text-text-muted font-bold">カテゴリ数</div><div className="text-xl font-bold">{stats.categories}</div></div>
        </div>
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-gray-100 flex flex-col md:flex-row gap-4 items-center justify-between bg-gray-50/50">
          <div className="flex gap-4 flex-1 w-full md:w-auto">
            <div className="relative flex-1 md:max-w-xs">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">search</span>
              <input
                type="text"
                placeholder="スポット名・エリアで検索"
                className="w-full pl-10 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                value={searchTerm}
                onChange={e => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              />
            </div>

            <div className="flex bg-gray-100 p-1 rounded-lg">
              <button
                onClick={() => setViewMode('table')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'table' ? 'bg-white shadow-sm text-primary' : 'text-text-muted hover:text-text-light'}`}
              >
                <span className="material-symbols-outlined text-lg align-bottom mr-1">table_rows</span>
                リスト
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'grid' ? 'bg-white shadow-sm text-primary' : 'text-text-muted hover:text-text-light'}`}
              >
                <span className="material-symbols-outlined text-lg align-bottom mr-1">grid_view</span>
                グリッド
              </button>
              <button
                onClick={() => setViewMode('map')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'map' ? 'bg-white shadow-sm text-primary' : 'text-text-muted hover:text-text-light'}`}
              >
                <span className="material-symbols-outlined text-lg align-bottom mr-1">map</span>
                マップ
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 w-full md:w-auto items-center">
            {/* エリア絞り: 地方→都道府県階層UI */}
            <div className="relative" ref={areaFilterRef}>
              <button
                onClick={() => setIsAreaFilterOpen(!isAreaFilterOpen)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white cursor-pointer hover:bg-gray-50 min-w-[200px] flex items-center justify-between"
              >
                <span className={selectedPrefecture ? 'font-bold text-primary' : 'text-text-muted'}>
                  {selectedPrefecture ? selectedPrefecture : '全エリア'}
                </span>
                <span className={`material-symbols-outlined text-sm text-text-muted transition-transform ${isAreaFilterOpen ? 'rotate-180' : ''}`}>expand_more</span>
              </button>
              {isAreaFilterOpen && (
                <div 
                  ref={dropdownRef}
                  className={`absolute left-0 bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-y-auto min-w-[280px] ${
                    dropdownPosition === 'top' 
                      ? 'bottom-full mb-1' 
                      : 'top-full mt-1'
                  }`}
                  style={{
                    maxHeight: dropdownPosition === 'top' 
                      ? `${Math.min(600, Math.max(300, window.innerHeight - areaFilterRef.current?.getBoundingClientRect().top - 20))}px`
                      : `${Math.min(600, Math.max(300, window.innerHeight - (areaFilterRef.current?.getBoundingClientRect().bottom || 0) - 20))}px`
                  }}
                >
                <div className="p-2">
                  {/* 全エリアオプション */}
                  <button
                    onClick={() => { setSelectedPrefecture(null); setCurrentPage(1); setIsAreaFilterOpen(false); }}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm hover:bg-gray-50 transition-colors ${
                      selectedPrefecture === null ? 'bg-primary/10 text-primary font-bold' : 'text-text-light'
                    }`}
                  >
                    全エリア
                  </button>
                  <div className="h-px bg-gray-200 my-2"></div>
                  
                  {/* 地方→都道府県階層 */}
                  {regions.map(region => (
                    <div key={region.id} className="mb-1">
                      <button
                        onClick={() => toggleRegion(region.id)}
                        className="w-full text-left px-3 py-2 rounded-md text-sm font-bold bg-gray-100 hover:bg-gray-200 transition-colors flex items-center justify-between"
                      >
                        <span>{region.name}</span>
                        <span className={`material-symbols-outlined text-sm transition-transform ${expandedRegions.has(region.id) ? 'rotate-90' : ''}`}>
                          chevron_right
                        </span>
                      </button>
                      {expandedRegions.has(region.id) && (
                        <div className="pl-4 mt-1 space-y-1">
                          {region.prefs.map(pref => (
                            <button
                              key={pref}
                              onClick={() => { handlePrefectureSelect(pref); setIsAreaFilterOpen(false); }}
                              className={`w-full text-left px-3 py-1.5 rounded-md text-sm hover:bg-gray-50 transition-colors ${
                                selectedPrefecture === pref ? 'bg-primary/10 text-primary font-bold' : 'text-text-light'
                              }`}
                            >
                              {pref}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                </div>
              )}
            </div>
            <select className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white" value={filterCategory} onChange={e => { setFilterCategory(e.target.value); setCurrentPage(1); }}>
              <option value="All">全カテゴリ</option>
              {categories.filter(c => c !== 'All').map(c => (
                <option key={c} value={c}>{SPOT_CATEGORY_LABELS[c as keyof typeof SPOT_CATEGORY_LABELS] || c}</option>
              ))}
            </select>

            <div className="h-6 w-px bg-gray-300 mx-1"></div>

            <label className="flex items-center gap-1 text-sm bg-white px-3 py-2 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50 select-none">
              <input type="checkbox" className="accent-red-500" checked={filterMissingLocation} onChange={e => { setFilterMissingLocation(e.target.checked); setCurrentPage(1); }} />
              <span className={filterMissingLocation ? 'text-red-600 font-bold' : 'text-text-muted'}>位置情報なし</span>
            </label>

            <label className="flex items-center gap-1 text-sm bg-white px-3 py-2 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50 select-none">
              <input type="checkbox" className="accent-orange-500" checked={filterMissingImage} onChange={e => { setFilterMissingImage(e.target.checked); setCurrentPage(1); }} />
              <span className={filterMissingImage ? 'text-orange-600 font-bold' : 'text-text-muted'}>画像なし</span>
            </label>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="p-20 text-center text-text-muted">
            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            読み込み中...
          </div>
        ) : viewMode === 'map' ? (
          <div className="p-4">
            <SpotMap spots={filteredSpots} height="600px" onSpotClick={handleEditClick} />
            <div className="mt-2 text-right text-xs text-text-muted">
              ※ マーカーをクリックすると編集画面が開きます
            </div>
          </div>
        ) : (
          <>
            {displayedSpots.length === 0 ? (
              <div className="p-20 text-center text-text-muted bg-gray-50">
                <span className="material-symbols-outlined text-4xl mb-2 opacity-30">search_off</span>
                <p>条件に一致するスポットが見つかりません</p>
              </div>
            ) : viewMode === 'table' ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left whitespace-nowrap">
                  <thead className="bg-gray-50 text-text-muted text-xs uppercase tracking-wider font-bold">
                    <tr>
                      <th className="p-4 w-16">画像</th>
                      <th className="p-4 cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort('created_at')}>
                        <div className="flex items-center gap-1">名前/ID {sortField && <span className="material-symbols-outlined text-xs">unfold_more</span>}</div>
                      </th>
                      <th className="p-4">エリア</th>
                      <th className="p-4">カテゴリ</th>
                      <th className="p-4 text-center">ステータス</th>
                      <th className="p-4 cursor-pointer hover:text-primary transition-colors" onClick={() => handleSort('updated_at')}>
                        <div className="flex items-center gap-1">更新日時 {sortField === 'updated_at' && <span className="material-symbols-outlined text-xs">{sortDirection === 'asc' ? 'expand_less' : 'expand_more'}</span>}</div>
                      </th>
                      <th className="p-4 text-right">アクション</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {displayedSpots.map(spot => (
                      <tr key={spot.id} className="hover:bg-gray-50 transition-colors">
                        <td className="p-4">
                          <img src={spot.image} className="w-10 h-10 rounded-md object-cover bg-gray-200 border border-gray-200" alt="" />
                        </td>
                        <td className="p-4">
                          <div className="font-bold text-text-light">{spot.name}</div>
                          <div className="text-xs text-text-muted font-mono">{spot.id.slice(0, 8)}...</div>
                        </td>
                        <td className="p-4"><span className="text-sm border border-gray-200 px-2 py-1 rounded bg-white">{spot.area}</span></td>
                        <td className="p-4"><span className="text-xs font-bold px-2 py-1 bg-primary/10 text-primary rounded-full">{spot.category}</span></td>
                        <td className="p-4 text-center">
                          <div className="flex justify-center gap-2">
                            {!spot.location && <span className="material-symbols-outlined text-red-500 text-lg" title="位置情報なし">wrong_location</span>}
                            {!spot.image && <span className="material-symbols-outlined text-orange-500 text-lg" title="画像なし">image_not_supported</span>}
                            {spot.location && spot.image && <span className="material-symbols-outlined text-green-500 text-lg" title="完全">check_circle</span>}
                          </div>
                        </td>
                        <td className="p-4 text-sm text-text-muted">{formatDateTime(spot.updated_at)}</td>
                        <td className="p-4 text-right">
                          <div className="flex justify-end gap-2">
                            <a
                              href={spot.location ? `https://www.google.com/maps/search/?api=1&query=${spot.location.lat},${spot.location.lng}` : '#'}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`p-2 rounded-full transition-colors ${spot.location ? 'text-green-600 hover:bg-green-50' : 'text-gray-300 cursor-not-allowed'}`}
                              title="Googleマップで確認"
                              onClick={(e) => !spot.location && e.preventDefault()}
                            >
                              <span className="material-symbols-outlined text-xl">map</span>
                            </a>
                            <button onClick={() => handleEditClick(spot)} className="p-2 hover:bg-blue-50 text-primary rounded-full transition-colors"><span className="material-symbols-outlined text-xl">edit_square</span></button>
                            <button onClick={() => handleDeleteSpot(spot.id)} className="p-2 hover:bg-red-50 text-red-500 rounded-full transition-colors"><span className="material-symbols-outlined text-xl">delete</span></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {displayedSpots.map(spot => (
                  <div key={spot.id} className="border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow bg-white flex flex-col">
                    <div className="relative aspect-video bg-gray-100">
                      <img src={spot.image} alt={spot.name} className="w-full h-full object-cover" />
                      <div className="absolute top-2 right-2 flex gap-1">
                        {!spot.location && <span className="p-1 bg-red-500 text-white rounded shadow-sm" title="位置情報なし"><span className="material-symbols-outlined text-xs">wrong_location</span></span>}
                      </div>
                      <div className="absolute bottom-2 left-2">
                        <span className="text-xs font-bold px-2 py-1 bg-black/60 text-white rounded-md backdrop-blur-sm">{spot.area}</span>
                      </div>
                    </div>
                    <div className="p-3 flex-1 flex flex-col">
                      <h3 className="font-bold text-sm mb-1 line-clamp-1">{spot.name}</h3>
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-primary font-bold bg-primary/5 px-2 py-0.5 rounded">{spot.category}</span>
                        <div className="flex items-center text-xs text-yellow-500 font-bold">
                          <span className="material-symbols-outlined text-sm">star</span>
                          {spot.rating}
                        </div>
                      </div>
                      <p className="text-xs text-text-muted line-clamp-2 mb-3 flex-1">{spot.description}</p>
                      <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
                        <a
                          href={spot.location ? `https://www.google.com/maps/search/?api=1&query=${spot.location.lat},${spot.location.lng}` : '#'}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`text-xs font-bold ${spot.location ? 'text-green-600 hover:underline' : 'text-gray-300 cursor-not-allowed'}`}
                          onClick={(e) => !spot.location && e.preventDefault()}
                        >
                          地図確認
                        </a>
                        <button onClick={() => handleEditClick(spot)} className="text-xs font-bold text-text-muted hover:text-primary">編集</button>
                        <button onClick={() => handleDeleteSpot(spot.id)} className="text-xs font-bold text-text-muted hover:text-red-500">削除</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="p-4 border-t border-gray-100 flex flex-col sm:flex-row justify-between items-center gap-4 bg-gray-50/50">
                <div className="text-sm text-text-muted">
                  <span className="font-bold">{filteredSpots.length}</span>件中 <span className="font-bold">{(currentPage - 1) * itemsPerPage + 1}</span> - <span className="font-bold">{Math.min(currentPage * itemsPerPage, filteredSpots.length)}</span>件を表示
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="material-symbols-outlined text-sm">chevron_left</span>
                  </button>

                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      // Simple pagination logic for windowing could be added here
                      // For now, just show first 5 or logic to shift
                      let pageNum = i + 1;
                      if (totalPages > 5) {
                        if (currentPage > 3) pageNum = currentPage - 2 + i;
                        if (pageNum > totalPages) pageNum = totalPages - (4 - i);
                      }

                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`w-8 h-8 rounded-lg text-sm font-bold flex items-center justify-center transition-colors ${currentPage === pageNum
                            ? 'bg-primary text-white shadow-md'
                            : 'bg-white border border-gray-200 hover:bg-gray-50 text-text-muted'
                            }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="material-symbols-outlined text-sm">chevron_right</span>
                  </button>
                </div>
                <select
                  className="p-2 border border-gray-200 rounded-lg text-sm bg-white"
                  value={itemsPerPage}
                  onChange={(e) => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                >
                  <option value="10">10件 / ページ</option>
                  <option value="20">20件 / ページ</option>
                  <option value="50">50件 / ページ</option>
                  <option value="100">100件 / ページ</option>
                </select>
              </div>
            )}
          </>
        )}
      </div>


      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center">
              <h2 className="text-xl font-bold">新規スポット登録</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-text-muted hover:text-text-light">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-bold text-text-muted mb-1">都道府県名 <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  placeholder="例: 鹿児島県、東京都"
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                  value={prefecture}
                  onChange={e => setPrefecture(e.target.value)}
                  disabled={isBulkAdding}
                />
                <p className="text-xs text-text-muted mt-1">
                  都道府県名を入力して「一括追加」を押すと、複数のキーワードで検索してスポットをまとめて追加します。
                </p>
              </div>

              <div>
                <label className="block text-sm font-bold text-text-muted mb-1">カテゴリ絞り込み (任意)</label>
                <select
                  className="w-full p-2 border border-gray-300 rounded-lg text-sm bg-white"
                  value={addCategory}
                  onChange={e => setAddCategory(e.target.value)}
                  disabled={isBulkAdding}
                >
                  <option value="">指定なし (全カテゴリ)</option>
                  {availableKeywords.length > 0 ? (
                    availableKeywords.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))
                  ) : (
                    SPOT_CATEGORIES.map(c => (
                      <option key={c} value={c}>{SPOT_CATEGORY_LABELS[c] || c}</option>
                    ))
                  )}
                </select>
                <p className="text-xs text-text-muted mt-1">
                  特定のカテゴリに絞って検索します（都道府県名を入力するとリストが更新されます）
                </p>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="font-bold text-sm mb-3 text-text-muted">詳細設定（上限・実行方式）</div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-text-muted mb-1">取得件数/キーワード</label>
                    <input
                      type="number"
                      min={1}
                      className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                      value={maxResultsPerKeyword}
                      onChange={e => setMaxResultsPerKeyword(Number(e.target.value))}
                      disabled={isBulkAdding}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-text-muted mb-1">最大キーワード数</label>
                    <input
                      type="number"
                      min={1}
                      className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                      value={maxKeywords}
                      onChange={e => setMaxKeywords(Number(e.target.value))}
                      disabled={isBulkAdding}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-text-muted mb-1">最大動画数</label>
                    <input
                      type="number"
                      min={1}
                      className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                      value={maxTotalVideos}
                      onChange={e => setMaxTotalVideos(Number(e.target.value))}
                      disabled={isBulkAdding}
                    />
                  </div>
                </div>

                <div className="mt-3 flex flex-col gap-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={addLocation}
                      onChange={e => setAddLocation(e.target.checked)}
                      disabled={isBulkAdding}
                    />
                    <span>位置情報を付与（今回追加分のみ）</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={runAsync}
                      onChange={e => setRunAsync(e.target.checked)}
                      disabled={isBulkAdding}
                    />
                    <span>バックグラウンドで実行（推奨）</span>
                  </label>
                </div>
              </div>

              {/* 進捗表示 */}
              {isBulkAdding && (
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"></span>
                    <span className="font-bold text-blue-700">一括追加処理中...</span>
                  </div>
                  <p className="text-sm text-blue-600">
                    YouTubeデータを収集し、スポットを追加しています。この処理には数分かかる場合があります。
                  </p>
                  {bulkProgress?.job_status && (
                    <p className="text-xs text-blue-700 mt-2">
                      状態: {bulkProgress.job_status} {bulkProgress.job_id ? `(job: ${bulkProgress.job_id.slice(0, 8)}...)` : ''}
                    </p>
                  )}
                </div>
              )}

              {/* 結果表示 */}
              {bulkProgress && !isBulkAdding && (
                <div className={`p-4 rounded-lg border ${bulkProgress.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                  <div className="font-bold mb-2">{bulkProgress.success ? '✅ 処理完了' : '❌ 処理失敗'}</div>
                  <div className="text-sm space-y-1">
                    <div>追加件数: {bulkProgress.imported}件</div>
                    <div>処理キーワード: {bulkProgress.processed_keywords}/{bulkProgress.total_keywords}</div>
                    <div>取得動画数: {bulkProgress.total_videos}件</div>
                    {bulkProgress.quota_exceeded && (
                      <div className="text-orange-600 font-bold">⚠️ YouTube APIのクォータ制限に達しました</div>
                    )}
                    {bulkProgress.error && (
                      <div className="text-red-600">エラー: {bulkProgress.error}</div>
                    )}
                  </div>
                </div>
              )}

              <div className="pt-4 flex gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsModalOpen(false);
                    setPrefecture('');
                    setBulkProgress(null);
                  }}
                  className="flex-1 py-3 font-bold border border-gray-300 rounded-xl hover:bg-gray-50"
                  disabled={isBulkAdding}
                >
                  キャンセル
                </button>
                <button
                  type="button"
                  onClick={handleBulkAddSpots}
                  disabled={isBulkAdding || !prefecture.trim()}
                  className="flex-1 py-3 font-bold bg-primary text-white rounded-xl shadow-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isBulkAdding ? (
                    <>
                      <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                      処理中...
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined">add_circle</span>
                      一括追加
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditModalOpen && editForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-2xl shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center sticky top-0 bg-white z-10">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">edit</span>
                スポット編集
              </h2>
              <button onClick={() => setIsEditModalOpen(false)} className="text-text-muted hover:text-text-light">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="col-span-1 md:col-span-2">
                  <div className="flex items-end gap-2">
                    <div className="flex-1">
                      <label className="block text-sm font-bold text-text-muted mb-1">スポット名</label>
                      <input
                        type="text"
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                        value={editForm.name || ''}
                        onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                      />
                    </div>
                    <button
                      onClick={handleResearchSpot}
                      disabled={isResearching || !editForm.name || !editForm.name.trim()}
                      className="px-4 py-2 bg-accent text-white rounded-lg font-bold text-sm shadow-lg hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap"
                    >
                      {isResearching ? (
                        <>
                          <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                          リサーチ中...
                        </>
                      ) : (
                        <>
                          <span className="material-symbols-outlined text-sm">auto_awesome</span>
                          AIリサーチ
                        </>
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-text-muted mt-1">
                    AIリサーチボタンをクリックすると、スポット名から情報を自動取得します
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-bold text-text-muted mb-1">エリア</label>
                  <input
                    type="text"
                    className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                    value={editForm.area || ''}
                    onChange={e => setEditForm({ ...editForm, area: e.target.value })}
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold text-text-muted mb-1">カテゴリ</label>
                  <select
                    className="w-full p-2 border border-gray-300 rounded-lg text-sm bg-white"
                    value={editForm.category || 'Culture'}
                    onChange={e => setEditForm({ ...editForm, category: e.target.value as any })}
                  >
                    {SPOT_CATEGORIES.map(c => (
                      <option key={c} value={c}>{SPOT_CATEGORY_LABELS[c] || c}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-bold text-text-muted mb-1">緯度 (Latitude)</label>
                  <input
                    type="number"
                    step="any"
                    className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                    value={editForm.location?.lat || ''}
                    onChange={e => {
                      const val = parseFloat(e.target.value);
                      setEditForm({
                        ...editForm,
                        location: {
                          ...(editForm.location || { lat: 0, lng: 0 }),
                          lat: isNaN(val) ? 0 : val
                        }
                      });
                    }}
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold text-text-muted mb-1">経度 (Longitude)</label>
                  <input
                    type="number"
                    step="any"
                    className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                    value={editForm.location?.lng || ''}
                    onChange={e => {
                      const val = parseFloat(e.target.value);
                      setEditForm({
                        ...editForm,
                        location: {
                          ...(editForm.location || { lat: 0, lng: 0 }),
                          lng: isNaN(val) ? 0 : val
                        }
                      });
                    }}
                  />
                </div>

                <div className="col-span-1 md:col-span-2">
                  <div className="flex justify-between items-center mb-1">
                    <label className="block text-sm font-bold text-text-muted">確認用リンク</label>
                  </div>
                  {editForm.location?.lat && editForm.location?.lng ? (
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${editForm.location.lat},${editForm.location.lng}`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
                    >
                      <span className="material-symbols-outlined text-sm">open_in_new</span>
                      Googleマップで位置を確認 ({editForm.location.lat}, {editForm.location.lng})
                    </a>
                  ) : (
                    <span className="text-sm text-gray-400">緯度経度が入力されていません</span>
                  )}
                </div>

                <div className="col-span-1 md:col-span-2">
                  <label className="block text-sm font-bold text-text-muted mb-1">画像URL</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                      value={editForm.image || ''}
                      onChange={e => setEditForm({ ...editForm, image: e.target.value })}
                    />
                  </div>
                  {editForm.image && (
                    <div className="mt-2 h-32 w-full bg-gray-100 rounded-lg overflow-hidden">
                      <img src={editForm.image} alt="Preview" className="w-full h-full object-contain" />
                    </div>
                  )}
                </div>

                <div className="col-span-1 md:col-span-2">
                  <label className="block text-sm font-bold text-text-muted mb-1">説明文</label>
                  <textarea
                    className="w-full p-2 border border-gray-300 rounded-lg text-sm h-24"
                    value={editForm.description || ''}
                    onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                  />
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-100 flex gap-3 justify-end sticky bottom-0 bg-white z-10 rounded-b-2xl">
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="px-6 py-2 rounded-lg border border-gray-200 text-sm font-bold hover:bg-gray-50"
              >
                キャンセル
              </button>
              <button
                onClick={handleUpdateSpot}
                className="px-6 py-2 rounded-lg bg-primary text-white text-sm font-bold shadow-lg hover:opacity-90 flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-sm">save</span>
                更新する
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const data = await getUsers();
      setUsers(data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      showError('ユーザー情報の取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRoleChange = async (userId: string, currentRole: string) => {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    if (!window.confirm(`このユーザーの権限を「${newRole}」に変更しますか？`)) return;

    try {
      await updateUserRole(userId, newRole);
      showSuccess(`ユーザーの権限を「${newRole}」に変更しました`);
      fetchUsers();
    } catch (error) {
      console.error('Failed to update role:', error);
      showError('権限の更新に失敗しました');
    }
  };

  const handleStatusChange = async (userId: string, currentStatus: boolean) => {
    const newStatus = !currentStatus;
    if (!window.confirm(`このユーザーのアカウントを${newStatus ? '有効' : '無効'}にしますか？`)) return;

    try {
      await updateUserStatus(userId, newStatus);
      showSuccess(`ユーザーのアカウントを${newStatus ? '有効' : '無効'}にしました`);
      fetchUsers();
    } catch (error) {
      console.error('Failed to update status:', error);
      showError('ステータスの更新に失敗しました');
    }
  };

  return (
    <div className="p-6 md:p-10 bg-background-light min-h-full">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text-light">ユーザー管理</h1>
          <p className="text-text-muted">登録ユーザーのアカウントステータス管理。</p>
        </div>
        <button
          onClick={() => {
            const headers = ['ID', 'ユーザー名', '表示名', 'メール', 'ロール', 'ステータス', '作成日時'];
            const rows = users.map(user => [
              user.id,
              user.username || '',
              user.name || '',
              (user as any).email || '',
              user.role || '',
              user.is_active ? '有効' : '無効',
              user.created_at || ''
            ]);

            const csvContent = [
              headers.map(h => `"${h}"`).join(','),
              ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
            ].join('\n');

            const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `users_${new Date().toISOString().split('T')[0]}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            showSuccess('CSVファイルをエクスポートしました');
          }}
          className="bg-green-600 text-white px-4 py-2 rounded-lg font-bold flex items-center gap-2 shadow-lg hover:bg-green-700 transition-colors"
        >
          <span className="material-symbols-outlined">download</span> CSV出力
        </button>
      </header>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {isLoading ? (
          <div className="p-20 text-center text-text-muted">読み込み中...</div>
        ) : (
          <table className="w-full text-left">
            <thead className="bg-gray-50 text-text-muted text-sm">
              <tr>
                <th className="p-4">ユーザー</th>
                <th className="p-4">ロール</th>
                <th className="p-4">ステータス</th>
                <th className="p-4">作成日時</th>
                <th className="p-4 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map(user => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-lg">
                      {(user.username || user.name || 'U').charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-bold">{user.username || user.name}</div>
                      {user.username && user.name && user.username !== user.name && (
                        <div className="text-xs text-text-muted">表示名: {user.name}</div>
                      )}
                      <div className="text-xs text-text-muted">ID: {user.id.slice(0, 8)}...</div>
                    </div>
                  </td>
                  <td className="p-4">
                    {user.role === 'admin' ? (
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-bold">Admin</span>
                    ) : (
                      <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">User</span>
                    )}
                  </td>
                  <td className="p-4">
                    {user.is_active ? (
                      <span className="flex items-center gap-1 text-green-600 text-sm font-bold">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span> Active
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-600 text-sm font-bold">
                        <span className="w-2 h-2 rounded-full bg-red-500"></span> Inactive
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-sm text-text-muted">
                    {user.created_at ? (() => {
                      try {
                        const date = new Date(user.created_at);
                        return date.toLocaleString('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
                      } catch (e) {
                        return '-';
                      }
                    })() : '-'}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleRoleChange(user.id, user.role)}
                        className="text-xs border border-gray-200 px-2 py-1 rounded hover:bg-gray-50"
                      >
                        権限変更
                      </button>
                      <button
                        onClick={() => handleStatusChange(user.id, user.is_active)}
                        className={`text-xs border px-2 py-1 rounded hover:opacity-80 text-white ${user.is_active ? 'bg-red-500 border-red-500' : 'bg-green-500 border-green-500'}`}
                      >
                        {user.is_active ? '無効化' : '有効化'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export const AdminAiSettings: React.FC = () => {
  const { showSuccess, showError } = useToast();
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await getSystemSettings();
        setSettings(data);
      } catch (error) {
        console.error('Failed to fetch settings:', error);
        showError('設定の取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setIsSaving(true);
    try {
      await updateSystemSettings(settings);
      showSuccess('設定を保存しました');
    } catch (error) {
      console.error('Failed to save settings:', error);
      showError('設定の保存に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !settings) return <div className="p-10 text-center">読み込み中...</div>;

  return (
    <div className="p-6 md:p-10 bg-background-light min-h-full">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-text-light">AI設定</h1>
        <p className="text-text-muted">Geminiモデルのパラメータとプロンプト設定。</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-bold mb-4">モデル設定</h2>

          <div className="mb-6">
            <label className="block font-bold mb-2 text-sm">使用モデル (Gemini)</label>
            <select
              className="w-full p-3 rounded-lg border border-gray-200 bg-gray-50"
              value={settings.gemini_model}
              onChange={e => setSettings({ ...settings, gemini_model: e.target.value })}
            >
              <option value="gemini-2.0-flash-exp">gemini-2.0-flash-exp</option>
              <option value="gemini-1.5-flash">gemini-1.5-flash</option>
              <option value="gemini-1.5-pro">gemini-1.5-pro</option>
              <option value="gemini-pro-vision">gemini-pro-vision</option>
            </select>
          </div>

          <div className="mb-6">
            <label className="block font-bold mb-2 text-sm">Temperature (創造性): {settings.temperature}</label>
            <input
              type="range"
              className="w-full accent-primary mb-1"
              min="0" max="1" step="0.1"
              value={settings.temperature}
              onChange={e => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
            />
            <div className="flex justify-between text-xs text-text-muted">
              <span>正確 (0.0)</span>
              <span>バランス (0.7)</span>
              <span>創造的 (1.0)</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-bold text-sm">Grounding (Google検索)</p>
              <p className="text-xs text-text-muted">最新情報の検索を有効化</p>
            </div>
            <div
              className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${settings.grounding ? 'bg-primary' : 'bg-gray-300'}`}
              onClick={() => setSettings({ ...settings, grounding: !settings.grounding })}
            >
              <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${settings.grounding ? 'right-1' : 'left-1'}`}></div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-bold mb-4">システムプロンプト管理</h2>
          <textarea
            className="w-full h-80 p-4 rounded-lg border border-gray-200 text-sm font-mono bg-gray-900 text-gray-200"
            value={settings.system_prompt}
            onChange={e => setSettings({ ...settings, system_prompt: e.target.value })}
          />
          <div className="mt-4 flex justify-end">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="bg-primary text-white px-6 py-2 rounded-lg font-bold shadow-lg hover:opacity-90 disabled:opacity-50"
            >
              {isSaving ? '保存中...' : '設定を保存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export const AdminTags: React.FC = () => {
  const { showSuccess, showError } = useToast();
  const [tagData, setTagData] = useState<TagResponse | null>(null);
  const [recommendedTags, setRecommendedTags] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [normalizeInput, setNormalizeInput] = useState('');
  const [normalizeResult, setNormalizeResult] = useState<any>(null);
  const [isNormalizing, setIsNormalizing] = useState(false);

  useEffect(() => {
    fetchTags();
    fetchRecommendedTags();
  }, [selectedCategory]);

  const fetchTags = async () => {
    setIsLoading(true);
    try {
      const data = await getTags(selectedCategory || undefined);
      setTagData(data);
    } catch (error) {
      console.error('Failed to fetch tags:', error);
      showError('タグ情報の取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchRecommendedTags = async () => {
    try {
      const data = await getRecommendedTags(selectedCategory || undefined);
      setRecommendedTags(data);
    } catch (error) {
      console.error('Failed to fetch recommended tags:', error);
    }
  };

  const handleNormalize = async () => {
    if (!normalizeInput.trim()) {
      showError('タグを入力してください');
      return;
    }

    setIsNormalizing(true);
    try {
      const tags = normalizeInput.split(',').map(t => t.trim()).filter(t => t);
      const result = await normalizeTags(tags);
      setNormalizeResult(result);
      showSuccess('タグを正規化しました');
    } catch (error) {
      console.error('Failed to normalize tags:', error);
      showError('タグの正規化に失敗しました');
    } finally {
      setIsNormalizing(false);
    }
  };

  const categories = tagData ? Object.keys(tagData.categories) : [];
  const filteredTags = tagData?.tags.filter(tag => 
    tag.value.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tag.normalized.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  return (
    <div className="p-6 md:p-10 bg-background-light min-h-full">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-text-light">タグ管理</h1>
        <p className="text-text-muted">スポットタグの管理、統計、正規化。</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <span className="material-symbols-outlined">label</span>
            </div>
            <div>
              <div className="text-xs text-text-muted font-bold">総タグ数</div>
              <div className="text-2xl font-bold">{tagData?.total || 0}</div>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-green-50 text-green-600 rounded-lg">
              <span className="material-symbols-outlined">category</span>
            </div>
            <div>
              <div className="text-xs text-text-muted font-bold">カテゴリ数</div>
              <div className="text-2xl font-bold">{categories.length}</div>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
              <span className="material-symbols-outlined">star</span>
            </div>
            <div>
              <div className="text-xs text-text-muted font-bold">推奨タグ数</div>
              <div className="text-2xl font-bold">{recommendedTags.length}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* タグ正規化ツール */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">auto_fix_high</span>
            タグ正規化ツール
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-text-muted mb-1">タグ（カンマ区切り）</label>
              <textarea
                className="w-full p-3 border border-gray-200 rounded-lg text-sm"
                placeholder="例: グルメ, 美食, レストラン"
                value={normalizeInput}
                onChange={e => setNormalizeInput(e.target.value)}
                rows={3}
              />
            </div>
            <button
              onClick={handleNormalize}
              disabled={isNormalizing || !normalizeInput.trim()}
              className="w-full py-2 bg-primary text-white rounded-lg font-bold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isNormalizing ? (
                <>
                  <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                  正規化中...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">check_circle</span>
                  正規化する
                </>
              )}
            </button>
            {normalizeResult && (
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="text-sm font-bold mb-2">正規化結果:</div>
                <div className="space-y-2">
                  {normalizeResult.normalized_tags.map((tag: any, idx: number) => (
                    <div key={idx} className="flex items-center gap-2 text-sm">
                      <span className="px-2 py-1 bg-white rounded border border-gray-200">{tag.value}</span>
                      <span className="text-text-muted">→</span>
                      <span className="px-2 py-1 bg-primary/10 text-primary rounded font-bold">{tag.normalized}</span>
                      {tag.category && (
                        <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">{tag.category}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 推奨タグ */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-green-600">recommend</span>
            推奨タグ
          </h2>
          <div className="mb-4">
            <select
              className="w-full p-2 border border-gray-200 rounded-lg text-sm bg-white"
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
            >
              <option value="">全カテゴリ</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{tagData?.categories[cat]?.name || cat}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-wrap gap-2 max-h-64 overflow-y-auto">
            {recommendedTags.length === 0 ? (
              <p className="text-sm text-text-muted">推奨タグがありません</p>
            ) : (
              recommendedTags.map((tag, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-bold cursor-pointer hover:bg-primary/20 transition-colors"
                  onClick={() => setSearchTerm(tag)}
                >
                  {tag}
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      {/* タグ一覧 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex gap-4 flex-1 w-full md:w-auto">
            <div className="relative flex-1 md:max-w-xs">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">search</span>
              <input
                type="text"
                placeholder="タグで検索"
                className="w-full pl-10 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
              />
            </div>
            <select
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
            >
              <option value="">全カテゴリ</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{tagData?.categories[cat]?.name || cat}</option>
              ))}
            </select>
          </div>
        </div>

        {isLoading ? (
          <div className="p-20 text-center text-text-muted">
            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            読み込み中...
          </div>
        ) : filteredTags.length === 0 ? (
          <div className="p-20 text-center text-text-muted">
            <span className="material-symbols-outlined text-4xl mb-2 opacity-30">search_off</span>
            <p>条件に一致するタグが見つかりません</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-50 text-text-muted text-xs uppercase tracking-wider font-bold">
                <tr>
                  <th className="p-4">タグ</th>
                  <th className="p-4">正規化値</th>
                  <th className="p-4">カテゴリ</th>
                  <th className="p-4 text-right">使用数</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredTags.map((tag, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <span className="font-bold text-text-light">{tag.value}</span>
                    </td>
                    <td className="p-4">
                      {tag.normalized !== tag.value ? (
                        <span className="text-sm text-text-muted">{tag.normalized}</span>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="p-4">
                      {tag.category ? (
                        <span className="px-2 py-1 bg-primary/10 text-primary rounded text-xs font-bold">
                          {tagData?.categories[tag.category]?.name || tag.category}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">未分類</span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <span className="font-bold text-text-light">{tag.count}</span>
                      <span className="text-sm text-text-muted ml-1">件</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};