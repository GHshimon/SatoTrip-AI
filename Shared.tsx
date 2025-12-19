import React, { useState, useRef, useEffect } from 'react';
import { currentUser } from '../mockData';
import { ChatMessage } from '../types';
import { GoogleGenAI, Chat, GenerateContentResponse } from "@google/genai";

interface HeaderProps {
  onNavigate: (path: string) => void;
  currentPath: string;
  isAuthenticated: boolean;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onNavigate, currentPath, isAuthenticated, onLogout }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => onNavigate('/')}>
            <img 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCfMSI_vEQcW6uWaOllfqi75Njj5epUUHan7iKYq2ddAZoSthgXSLKdhXLtyvGQeDOWHCvMIb9zHR29P6R1MHTCyE0GBmQFcmGptEhCWUuL8GTANN3rvEBzwrgvyl2srrrUMRms1iDYE5uxYWZET7_hlJDkiMX5A9SRf5w0qYmIJZMQq94roefVcSp5yXCk6-cjB3diA5SN8xBWRjHxaLVpf_bvPHdIi4cn84z3ACcaFosupiz3lF_kn0umIyl14BROFmriQ29o9iI" 
              alt="SatoTrip Logo" 
              className="h-8 w-8"
            />
            <span className="font-display font-bold text-xl text-text-light">SatoTrip</span>
          </div>

          <nav className="hidden md:flex items-center gap-8">
            <button 
              onClick={() => onNavigate('/')} 
              className={`text-sm font-medium transition-colors ${currentPath === '/' ? 'text-primary' : 'text-text-light hover:text-primary'}`}
            >
              Home
            </button>
            <button 
              onClick={() => onNavigate('/plans')} 
              className={`text-sm font-medium transition-colors ${currentPath === '/plans' ? 'text-primary' : 'text-text-light hover:text-primary'}`}
            >
              My Trips
            </button>
            <button 
              onClick={() => onNavigate('/myspots')} 
              className={`text-sm font-medium transition-colors ${currentPath === '/myspots' ? 'text-primary' : 'text-text-light hover:text-primary'}`}
            >
              My Spot
            </button>
            {isAuthenticated && currentUser.role === 'admin' && (
              <button 
                onClick={() => onNavigate('/admin/ai')} 
                className={`text-sm font-medium transition-colors ${currentPath.startsWith('/admin') ? 'text-primary' : 'text-text-light hover:text-primary'}`}
              >
                Admin
              </button>
            )}
          </nav>

          <div className="hidden md:flex items-center gap-4">
             <button 
              onClick={() => onNavigate('/create')} 
              className="bg-primary text-white px-4 py-2 rounded-full text-sm font-bold hover:bg-opacity-90 transition-all shadow-lg shadow-primary/20 flex items-center gap-1"
             >
               <span className="material-symbols-outlined text-lg">auto_awesome</span>
               Create Plan
             </button>
             
             {isAuthenticated ? (
               <div className="relative">
                 <button onClick={() => setIsUserMenuOpen(!isUserMenuOpen)} className="w-10 h-10 rounded-full bg-gray-200 overflow-hidden border border-gray-300 focus:ring-2 focus:ring-primary focus:outline-none">
                   <img src={currentUser.avatar} alt="User" className="w-full h-full object-cover" />
                 </button>
                 {isUserMenuOpen && (
                   <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-xl border border-gray-100 py-2 animate-fade-in z-50">
                     <div className="px-4 py-2 border-b border-gray-100 mb-2">
                       <p className="font-bold text-sm truncate">{currentUser.name}</p>
                       <p className="text-xs text-text-muted">Premium Plan</p>
                     </div>
                     <button onClick={() => { onNavigate('/favorites'); setIsUserMenuOpen(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center gap-2"><span className="material-symbols-outlined text-base text-primary">favorite</span> お気に入り</button>
                     <button onClick={() => { onNavigate('/profile'); setIsUserMenuOpen(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center gap-2"><span className="material-symbols-outlined text-base">person</span> プロフィール</button>
                     <button onClick={() => { onNavigate('/settings'); setIsUserMenuOpen(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center gap-2"><span className="material-symbols-outlined text-base">settings</span> 設定</button>
                     <button onClick={() => { onLogout(); setIsUserMenuOpen(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center gap-2 text-red-500"><span className="material-symbols-outlined text-base">logout</span> ログアウト</button>
                   </div>
                 )}
               </div>
             ) : (
               <button 
                onClick={() => onNavigate('/login')}
                className="text-sm font-bold text-text-light hover:text-primary transition-colors flex items-center gap-1"
               >
                 <span className="material-symbols-outlined">login</span>
                 ログイン
               </button>
             )}
          </div>

          <button className="md:hidden p-2" onClick={() => setIsMenuOpen(!isMenuOpen)}>
            <span className="material-symbols-outlined text-2xl text-text-light">menu</span>
          </button>
        </div>
      </div>
      {/* Mobile Menu */}
      {isMenuOpen && (
        <div className="md:hidden bg-white border-t border-gray-100 absolute w-full left-0 animate-fade-in shadow-lg z-40">
           <nav className="flex flex-col p-4">
              <button onClick={() => { onNavigate('/'); setIsMenuOpen(false); }} className="py-3 text-left font-medium border-b border-gray-50">Home</button>
              <button onClick={() => { onNavigate('/plans'); setIsMenuOpen(false); }} className="py-3 text-left font-medium border-b border-gray-50">My Trips</button>
              <button onClick={() => { onNavigate('/myspots'); setIsMenuOpen(false); }} className="py-3 text-left font-medium border-b border-gray-50">My Spot</button>
              <button onClick={() => { onNavigate('/create'); setIsMenuOpen(false); }} className="py-3 text-left font-medium text-primary flex items-center gap-2 border-b border-gray-50"><span className="material-symbols-outlined">auto_awesome</span> Create Plan</button>
              {isAuthenticated ? (
                <button onClick={() => { onLogout(); setIsMenuOpen(false); }} className="py-3 text-left font-medium text-red-500 flex items-center gap-2"><span className="material-symbols-outlined">logout</span> ログアウト</button>
              ) : (
                <button onClick={() => { onNavigate('/login'); setIsMenuOpen(false); }} className="py-3 text-left font-medium text-primary flex items-center gap-2"><span className="material-symbols-outlined">login</span> ログイン</button>
              )}
           </nav>
        </div>
      )}
    </header>
  );
};

export const Layout: React.FC<{
  children: React.ReactNode;
  onNavigate: (path: string) => void;
  currentPath: string;
  isAuthenticated?: boolean;
  onLogout?: () => void;
}> = ({ children, onNavigate, currentPath, isAuthenticated = false, onLogout = () => {} }) => {
  return (
    <div className="min-h-screen bg-background-light font-display text-text-light flex flex-col">
      <Header onNavigate={onNavigate} currentPath={currentPath} isAuthenticated={isAuthenticated} onLogout={onLogout} />
      <main className="flex-1">
        {children}
      </main>
      <footer className="bg-white border-t border-gray-200 py-10 mt-auto">
        <div className="max-w-7xl mx-auto px-4 text-center text-text-muted text-sm">
          <div className="flex justify-center gap-6 mb-4">
            <button className="hover:text-primary">利用規約</button>
            <button className="hover:text-primary">プライバシーポリシー</button>
            <button className="hover:text-primary">お問い合わせ</button>
          </div>
          <p>© 2024 SatoTrip AI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};