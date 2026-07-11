import React, { useState, useEffect } from 'react';
import { confirmPasswordReset } from '../src/api/auth';
import { useToast } from '../components/Toast';

/**
 * パスワード再設定ページ（メールのリンク /reset-password?token=... から遷移）
 */
export const ResetPasswordPage: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  const { showSuccess, showError } = useToast();
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    // ハッシュルーターのため #/reset-password?token=... からクエリを取り出す
    const hash = window.location.hash; // 例: #/reset-password?token=abc
    const queryIndex = hash.indexOf('?');
    if (queryIndex !== -1) {
      const params = new URLSearchParams(hash.substring(queryIndex + 1));
      setToken(params.get('token') || '');
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    if (!token) {
      showError('リンクが不正です。メールのリンクを再度お開きください。');
      return;
    }
    if (newPassword !== confirmPassword) {
      showError('パスワードが一致しません');
      return;
    }
    if (newPassword.length < 8) {
      showError('パスワードは8文字以上で入力してください');
      return;
    }
    setIsSubmitting(true);
    try {
      await confirmPasswordReset(token, newPassword);
      setDone(true);
      showSuccess('パスワードを再設定しました');
    } catch (err: any) {
      showError(err?.detail || 'リンクが無効か有効期限が切れています。再度お試しください。');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-2xl font-bold mb-6 text-center">パスワードの再設定</h1>
      {done ? (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center space-y-4">
          <span className="material-symbols-outlined text-5xl text-primary">check_circle</span>
          <p className="text-text-light">パスワードを再設定しました。新しいパスワードでログインしてください。</p>
          <button
            onClick={() => onNavigate('/login')}
            className="bg-primary text-white px-8 py-3 rounded-full font-bold hover:opacity-90 transition-opacity"
          >
            ログインへ
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">新しいパスワード</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary/40 focus:outline-none"
              placeholder="8文字以上"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">新しいパスワード（確認）</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary/40 focus:outline-none"
              placeholder="もう一度入力"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-primary text-white py-3 rounded-full font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isSubmitting ? '設定中...' : 'パスワードを再設定'}
          </button>
        </form>
      )}
    </div>
  );
};
