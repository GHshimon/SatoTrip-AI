import React, { useState, useEffect } from 'react';
import { Layout } from './components/Shared';
import { Home, NotFound, UserProfile, Settings, LoginPage } from './pages/PublicPages';
import { PlanList, PrefectureSpots, HotelList, FavoriteSpots, MySpots } from './pages/FeaturePages';
import { PlanDetail, PlanEditor, CreatePlan } from './pages/PlanPages';
import { AdminDashboard, AdminUsers, AdminSpots, AdminAiSettings, AdminTags } from './pages/AdminPages';
import { plans, currentUser } from './mockData';
import { AppConfig } from './config';
import { AuthProvider, useAuth } from './src/contexts/AuthContext';
import { ToastProvider } from './components/Toast';

// Simple Hash Router Implementation
const AppContent: React.FC = () => {
  const [route, setRoute] = useState(window.location.hash.replace('#', '') || '/');
  const { isAuthenticated, user, logout: handleLogout } = useAuth();

  useEffect(() => {
    const handleHashChange = () => {
      setRoute(window.location.hash.replace('#', '') || '/');
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigate = (path: string) => {
    window.location.hash = path;
  };

  const handleLogin = () => {
    navigate('/');
  };

  const onLogout = async () => {
    await handleLogout();
    navigate('/');
  };

  const renderPage = () => {
    // Admin Routes - Protect
    if (route.startsWith('/admin')) {
      if (!isAuthenticated || user?.role !== 'admin') {
         // Redirect to login if not authenticated or not admin
         return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><LoginPage onLogin={handleLogin} /></Layout>;
      }
      
      if (route === '/admin/users') return <AdminUsers />;
      if (route === '/admin/spots') return <AdminSpots />;
      if (route === '/admin/tags') return <AdminTags />;
      if (route === '/admin/settings') return <AdminAiSettings />;
      return <AdminDashboard />;
    }
    
    // Auth Routes
    if (route === '/login') return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><LoginPage onLogin={handleLogin} /></Layout>;

    // Static Layout Routes
    if (route === '/') return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><Home onNavigate={navigate} /></Layout>;
    if (route === '/plans') return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><PlanList onNavigate={navigate} /></Layout>;
    if (route === '/myspots') return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><MySpots onNavigate={navigate} /></Layout>;
    if (route === '/favorites') return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><FavoriteSpots onNavigate={navigate} /></Layout>;
    if (route === '/profile') return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><UserProfile /></Layout>;
    if (route === '/settings') return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><Settings /></Layout>;
    
    // Route to Plan Creator
    if (route === '/create') return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><CreatePlan onNavigate={navigate} /></Layout>;
    
    // Dynamic Routes (Matching logic)
    if (route.startsWith('/plan/')) {
      const parts = route.split('/');
      const planId = parts[2];
      const isEdit = parts[3] === 'edit';
      // PlanDetailとPlanEditorコンポーネント内でAPIから取得するように変更
      if (isEdit) {
        return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><PlanEditor planId={planId} onNavigate={navigate} /></Layout>;
      } else {
        return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><PlanDetail planId={planId} onNavigate={navigate} /></Layout>;
      }
    }

    if (route.startsWith('/prefecture/')) {
      const area = decodeURIComponent(route.split('/')[2]);
      return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><PrefectureSpots area={area} onNavigate={navigate} /></Layout>;
    }

    if (route.startsWith('/hotels/')) {
      // For demo, ignore area param and show list
      return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><HotelList onNavigate={navigate} /></Layout>;
    }

    return <Layout onNavigate={navigate} currentPath={route} isAuthenticated={isAuthenticated} onLogout={onLogout}><NotFound onNavigate={navigate} /></Layout>;
  };

  // Special layout for admin to add side-nav
  if (route.startsWith('/admin') && isAuthenticated) {
    return (
       <div className="flex h-screen bg-background-light font-display">
          <aside className="w-64 bg-white border-r border-gray-200 hidden md:flex flex-col">
             <div className="p-6 flex items-center gap-2 border-b border-gray-100 cursor-pointer" onClick={() => navigate('/')}>
                <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuCfMSI_vEQcW6uWaOllfqi75Njj5epUUHan7iKYq2ddAZoSthgXSLKdhXLtyvGQeDOWHCvMIb9zHR29P6R1MHTCyE0GBmQFcmGptEhCWUuL8GTANN3rvEBzwrgvyl2srrrUMRms1iDYE5uxYWZET7_hlJDkiMX5A9SRf5w0qYmIJZMQq94roefVcSp5yXCk6-cjB3diA5SN8xBWRjHxaLVpf_bvPHdIi4cn84z3ACcaFosupiz3lF_kn0umIyl14BROFmriQ29o9iI" className="w-8 h-8" alt="Logo"/>
                <span className="font-bold text-lg">SatoTrip</span>
             </div>
             <nav className="p-4 space-y-1">
                <button onClick={() => navigate('/admin')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors ${route === '/admin' ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-gray-50'}`}>
                  <span className="material-symbols-outlined">dashboard</span> ダッシュボード
                </button>
                <button onClick={() => navigate('/admin/spots')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors ${route === '/admin/spots' ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-gray-50'}`}>
                  <span className="material-symbols-outlined">place</span> スポット管理
                </button>
                <button onClick={() => navigate('/admin/users')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors ${route === '/admin/users' ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-gray-50'}`}>
                  <span className="material-symbols-outlined">group</span> ユーザー管理
                </button>
                <button onClick={() => navigate('/admin/tags')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors ${route === '/admin/tags' ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-gray-50'}`}>
                  <span className="material-symbols-outlined">label</span> タグ管理
                </button>
                <button onClick={() => navigate('/admin/settings')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors ${route === '/admin/settings' ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-gray-50'}`}>
                  <span className="material-symbols-outlined">settings_suggest</span> AI設定
                </button>
             </nav>
             <div className="mt-auto p-4 border-t border-gray-100">
                <button onClick={() => navigate('/')} className="w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium text-text-muted hover:bg-gray-50">
                  <span className="material-symbols-outlined">logout</span> サイトに戻る
                </button>
             </div>
          </aside>
          <main className="flex-1 overflow-auto">
             {renderPage()}
          </main>
       </div>
    );
  }

  return renderPage();
};

// Appコンポーネント（AuthProviderとToastProviderでラップ）
const App: React.FC = () => {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;