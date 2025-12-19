import React, { useState, useEffect } from 'react';
import { adminStats, users } from '../mockData';
import { Spot } from '../types';
import * as spotApi from '../src/api/spots';
import { bulkAddSpotsByPrefecture, getBulkAddJobStatus, BulkAddResponse } from '../src/api/spots';

export const AdminDashboard: React.FC = () => {
  return (
    <div className="p-6 md:p-10 bg-background-light min-h-full">
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-text-light mb-2">管理者ダッシュボード</h1>
        <p className="text-text-muted">SatoTrip Commercialの現在のステータスとアクティビティ概要。</p>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        {adminStats.map((stat, i) => (
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
            <div className="flex items-start gap-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              <span className="material-symbols-outlined">error</span>
              <div>
                <p className="font-bold">API Rate Limit Warning</p>
                <p className="opacity-80">Gemini APIの使用率が80%を超えました。</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
              <span className="material-symbols-outlined">check_circle</span>
              <div>
                <p className="font-bold">Backup Completed</p>
                <p className="opacity-80">日次データベースバックアップが正常に完了しました。</p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold mb-4">人気急上昇エリア</h2>
          <div className="space-y-4">
            {['京都', '金沢', '福岡'].map((city, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold">{i + 1}</div>
                  <span className="font-bold">{city}</span>
                </div>
                <div className="text-sm text-text-muted flex items-center gap-1">
                  <span className="material-symbols-outlined text-green-500 text-sm">trending_up</span> +{(30 - i * 5)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export const AdminSpots: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterArea, setFilterArea] = useState('All');
  const [spots, setSpots] = useState<Spot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBulkAdding, setIsBulkAdding] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<BulkAddResponse | null>(null);
  const [prefecture, setPrefecture] = useState('');
  const [maxResultsPerKeyword, setMaxResultsPerKeyword] = useState<number>(3);
  const [maxKeywords, setMaxKeywords] = useState<number>(20);
  const [maxTotalVideos, setMaxTotalVideos] = useState<number>(30);
  const [addLocation, setAddLocation] = useState<boolean>(true);
  const [runAsync, setRunAsync] = useState<boolean>(true);
  const [jobId, setJobId] = useState<string | null>(null);

  // Fetch spots on mount
  useEffect(() => {
    fetchSpots();
  }, []);

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
            if (status.location_updated !== undefined) {
              message += `\n位置情報付与: ${status.location_updated}件`;
            }
            alert(message);
            setIsModalOpen(false);
            setPrefecture('');
            fetchSpots();
          } else if (status.job_status === 'failed') {
            alert(`一括追加に失敗しました: ${status.error || '不明なエラー'}`);
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
      const data = await spotApi.getSpots();
      setSpots(data);
    } catch (error) {
      console.error('Failed to fetch spots:', error);
      alert('スポット情報の取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBulkAddSpots = async () => {
    if (!prefecture.trim()) {
      alert('都道府県名を入力してください（例: 鹿児島県）');
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
        message += `追加件数: ${result.imported}件\n`;
        message += `処理キーワード数: ${result.processed_keywords}/${result.total_keywords}\n`;
        message += `取得動画数: ${result.total_videos}件`;
        
        if (result.quota_exceeded) {
          message += `\n\n⚠️ YouTube APIのクォータ制限に達しました。一部のキーワードは処理できませんでした。`;
        }
        
        if (result.location_updated !== undefined) {
          message += `\n位置情報付与: ${result.location_updated}件`;
        }
        
        alert(message);
        setIsModalOpen(false);
        setPrefecture('');
        fetchSpots(); // Refresh list
      } else {
        alert(`一括追加に失敗しました: ${result.error || '不明なエラー'}`);
      }
    } catch (error: any) {
      console.error('Bulk add failed:', error);
      
      let errorMessage = '一括追加に失敗しました';
      if (error?.detail) {
        errorMessage = error.detail;
      } else if (error?.message) {
        errorMessage = error.message;
      }
      
      alert(errorMessage);
    } finally {
      if (!jobId) setIsBulkAdding(false);
    }
  };

  // Filter logic applied to the FETECHED spots, not mock data
  const filteredSpots = spots.filter(s =>
    (s.name.toLowerCase().includes(searchTerm.toLowerCase()) || s.area.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (filterArea === 'All' || s.area === filterArea)
  );

  const areas = ['All', ...Array.from(new Set(spots.map(s => s.area)))];

  return (
    <div className="p-6 md:p-10 bg-background-light min-h-full relative">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text-light">スポット管理</h1>
          <p className="text-text-muted">登録されている観光スポット情報の編集・削除。</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-primary text-white px-4 py-2 rounded-lg font-bold flex items-center gap-2 shadow-lg hover:bg-primary/90 transition-colors"
        >
          <span className="material-symbols-outlined">add</span> 新規スポット
        </button>
      </header>

      {/* Spots List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex gap-4">
          <div className="flex-1 relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">search</span>
            <input
              type="text"
              placeholder="スポット名で検索..."
              className="w-full pl-10 py-2 rounded-lg border border-gray-200"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
          <select
            className="px-4 py-2 border border-gray-200 rounded-lg bg-gray-50"
            value={filterArea}
            onChange={e => setFilterArea(e.target.value)}
          >
            {areas.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>

        {isLoading ? (
          <div className="p-10 text-center text-text-muted">読み込み中...</div>
        ) : (
          <table className="w-full text-left">
            <thead className="bg-gray-50 text-text-muted text-sm">
              <tr>
                <th className="p-4">画像</th>
                <th className="p-4">名前</th>
                <th className="p-4">エリア</th>
                <th className="p-4">カテゴリ</th>
                <th className="p-4 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredSpots.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-text-muted">スポットが見つかりません</td>
                </tr>
              ) : (
                filteredSpots.map(spot => (
                  <tr key={spot.id} className="hover:bg-gray-50">
                    <td className="p-4 w-20">
                      <img src={spot.image} className="w-12 h-12 rounded-lg object-cover bg-gray-200" alt="" />
                    </td>
                    <td className="p-4 font-bold">{spot.name}</td>
                    <td className="p-4 text-sm">{spot.area}</td>
                    <td className="p-4"><span className="px-2 py-1 bg-gray-100 rounded text-xs">{spot.category}</span></td>
                    <td className="p-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button className="text-primary font-bold text-sm">編集</button>
                        <button className="text-red-500 font-bold text-sm">削除</button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
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
    </div>
  );
};

export const AdminUsers: React.FC = () => {
  return (
    <div className="p-6 md:p-10 bg-background-light min-h-full">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-text-light">ユーザー管理</h1>
        <p className="text-text-muted">登録ユーザーのアカウントステータス管理。</p>
      </header>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 text-text-muted text-sm">
            <tr>
              <th className="p-4">ユーザー</th>
              <th className="p-4">ロール</th>
              <th className="p-4">ステータス</th>
              <th className="p-4 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users.map(user => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="p-4 flex items-center gap-3">
                  <img src={user.avatar} className="w-10 h-10 rounded-full bg-gray-200" alt="" />
                  <div>
                    <div className="font-bold">{user.name}</div>
                    <div className="text-xs text-text-muted">ID: {user.id}</div>
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
                  <span className="flex items-center gap-1 text-green-600 text-sm font-bold">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span> Active
                  </span>
                </td>
                <td className="p-4 text-right">
                  <button className="text-text-muted hover:text-text-light"><span className="material-symbols-outlined">more_horiz</span></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export const AdminAiSettings: React.FC = () => {
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
            <select className="w-full p-3 rounded-lg border border-gray-200 bg-gray-50">
              <option>gemini-2.5-flash (現在)</option>
              <option>gemini-pro-vision</option>
            </select>
          </div>

          <div className="mb-6">
            <label className="block font-bold mb-2 text-sm">Temperature (創造性)</label>
            <input type="range" className="w-full accent-primary mb-1" defaultValue="70" />
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
            <div className="w-12 h-6 bg-primary rounded-full relative cursor-pointer">
              <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-bold mb-4">システムプロンプト管理</h2>
          <textarea
            className="w-full h-48 p-4 rounded-lg border border-gray-200 text-sm font-mono bg-gray-900 text-gray-200"
            defaultValue={`あなたは旅行代理店AIエージェント「SatoTrip」です。
ユーザーの要望に基づいて、最適な旅行プランを作成してください。
出力は必ずJSON形式で行い、以下のスキーマに従ってください...`}
          />
          <div className="mt-4 flex justify-end">
            <button className="bg-primary text-white px-6 py-2 rounded-lg font-bold shadow-lg hover:opacity-90">
              設定を保存
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};