import React, { useState, useEffect } from 'react';
import { currentUser } from '../mockData';
import { useAuth } from '../src/hooks/useAuth';
import { useToast } from '../components/Toast';
import * as userApi from '../src/api/users';
import { getErrorMessage } from '../src/utils/errorHandler';

export const Home: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative py-20 md:py-32 px-4 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-50 via-rose-50 to-amber-50 -z-10" />
        {/* Decorative background elements */}
        <div className="absolute top-20 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-secondary/10 rounded-full blur-3xl" />

        <div className="max-w-6xl mx-auto flex flex-col-reverse md:flex-row items-center gap-12">
          <div className="flex-1 text-center md:text-left flex flex-col gap-6 z-10">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-sm self-center md:self-start border border-gray-100">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              <span className="text-xs font-bold text-text-muted tracking-wide">SatoTrip AI v3.5 ONLINE</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-black leading-tight tracking-tighter text-text-light">
              最高の旅を、<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-purple-600">AIとデザイン</span>で。
            </h1>
            <p className="text-lg md:text-xl text-text-muted leading-relaxed">
              SatoTripが、SNSやWebのトレンド情報を分析し、あなただけの理想の旅行プランを瞬時に生成。
              <br className="hidden md:block" />
              まだ見ぬ「地元体験」へ、AIがエスコートします。
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center md:justify-start">
              <button
                onClick={() => onNavigate('/create')}
                className="bg-primary text-white px-8 py-4 rounded-full text-lg font-bold shadow-lg shadow-primary/30 hover:scale-105 transition-transform flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined">auto_awesome</span>
                AIでプランを作成
              </button>
              <button
                onClick={() => onNavigate('/plans')}
                className="bg-white text-text-light border border-gray-200 px-8 py-4 rounded-full text-lg font-bold hover:bg-gray-50 transition-colors"
              >
                人気のプランを見る
              </button>
            </div>
          </div>
          <div className="flex-1 w-full relative group">
            <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-transparent rounded-3xl transform rotate-3 group-hover:rotate-2 transition-transform duration-500"></div>
            <img
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuD9pn-owuVzYkxlZm8J3VLBQe-2z2eTLju4tFq1O7iR38wp73ROOUW7Tgp5OvTE27vuBvRf5x-XmXtklsrr5ymAubqCtOmeWMXSm4__M3uOsjOyZA6h0SG4u8JQDF2kT0IwgAGFYBsdaDnmn5AovEHWvBevtqu-fvaBceP2xsersIZadrhC07JxcMVo4ALGFUiRMoykUxUN2yTTPjTNkVxCRgFo1x-jXQC9ZT2r42zqUDUUvYjN7XQrL-6TFaGVOgSmeeOuoEWHmrI"
              alt="Travel AI Dashboard"
              className="w-full h-auto object-contain rounded-3xl shadow-2xl relative z-10 transform -rotate-2 group-hover:rotate-0 transition-transform duration-500 bg-white"
            />



          </div>
        </div>
      </section>

      {/* Steps Section */}
      <section className="py-24 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">たった3ステップで、冒険の計画は完了</h2>
            <p className="text-text-muted">インテリジェントなプラットフォームが、あなたの旅行計画を3つの簡単なステップに。</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: 'edit_note', title: '1. 好みを入力', desc: '目的地、予算、興味を教えてください。SNSのトレンドを含めるかも選択できます。' },
              { icon: 'smart_toy', title: '2. AIがプランを生成', desc: 'Gemini搭載のAIが膨大なデータを分析し、あなただけの最適化された旅程を構築します。' },
              { icon: 'map', title: '3. カスタマイズして出発', desc: 'プランを確認し、ドラッグ&ドロップで微調整。友人と共有して出発しましょう。' }
            ].map((step, i) => (
              <div key={i} className="bg-background-light p-8 rounded-2xl text-center hover:-translate-y-2 transition-transform duration-300 group cursor-default">
                <div className="w-16 h-16 bg-secondary text-white rounded-full flex items-center justify-center text-3xl mx-auto mb-6 shadow-lg group-hover:scale-110 transition-transform">
                  <span className="material-symbols-outlined">{step.icon}</span>
                </div>
                <h3 className="text-xl font-bold mb-3">{step.title}</h3>
                <p className="text-text-muted text-sm leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export const LoginPage: React.FC<{ onLogin: () => void }> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const { login: handleLogin, register: handleRegister } = useAuth();
  const { showInfo } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      if (isRegistering) {
        await handleRegister(username, email, password, name);
      } else {
        await handleLogin(username, password);
      }
      onLogin();
    } catch (err: any) {
      setError(err.detail || err.message || 'ログインに失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-200px)] px-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 md:p-12 w-full max-w-md border border-gray-100">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-4 text-primary">
            <span className="material-symbols-outlined text-3xl">lock</span>
          </div>
          <h1 className="text-3xl font-black text-text-light mb-2">
            {isRegistering ? '新規登録' : 'おかえりなさい'}
          </h1>
          <p className="text-text-muted">
            {isRegistering
              ? 'SatoTripアカウントを作成して、<br/>旅の計画を始めましょう。'
              : 'SatoTripアカウントにログインして、<br/>旅の続きを始めましょう。'}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegistering && (
            <div>
              <label className="block text-sm font-bold text-text-muted mb-1">お名前</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                placeholder="山田 太郎"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-bold text-text-muted mb-1">
              {isRegistering ? 'メールアドレス' : 'ユーザー名'}
            </label>
            <input
              type={isRegistering ? 'email' : 'text'}
              value={isRegistering ? email : username}
              onChange={(e) => isRegistering ? setEmail(e.target.value) : setUsername(e.target.value)}
              required
              className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
              placeholder={isRegistering ? 'user@satotrip.com' : 'username'}
            />
          </div>
          {isRegistering && (
            <div>
              <label className="block text-sm font-bold text-text-muted mb-1">ユーザー名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                placeholder="username"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-bold text-text-muted mb-1">パスワード</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 focus:bg-white focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
              placeholder="••••••••"
            />
          </div>

          {!isRegistering && (
            <div className="flex justify-between items-center text-sm">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="accent-primary"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span className="text-text-muted">ログイン状態を保持</span>
              </label>
              <button
                type="button"
                onClick={() => showInfo('パスワードリセット機能は現在準備中です')}
                className="text-primary font-bold hover:underline"
              >
                パスワードを忘れた場合
              </button>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg shadow-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 mt-4"
          >
            {isLoading ? '処理中...' : (isRegistering ? '登録' : 'ログイン')}
          </button>

          <div className="relative py-4">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-100"></div></div>
            <div className="relative flex justify-center text-sm"><span className="px-2 bg-white text-gray-400">または</span></div>
          </div>

          <button
            type="button"
            onClick={() => showInfo('Googleログインは現在準備中です')}
            className="w-full bg-white border border-gray-200 text-text-light py-3 rounded-xl font-bold hover:bg-gray-50 transition-all flex items-center justify-center gap-2"
          >
            <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" className="w-5 h-5" alt="Google" />
            Googleで続ける
          </button>
        </form>

        <p className="text-center text-sm text-text-muted mt-8">
          {isRegistering ? (
            <>
              アカウントをお持ちですか？{' '}
              <button
                type="button"
                onClick={() => setIsRegistering(false)}
                className="text-primary font-bold hover:underline"
              >
                ログイン
              </button>
            </>
          ) : (
            <>
              アカウントをお持ちでないですか？{' '}
              <button
                type="button"
                onClick={() => setIsRegistering(true)}
                className="text-primary font-bold hover:underline"
              >
                新規登録
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
};

export const NotFound: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="relative mb-8">
        <div className="text-[10rem] font-black text-primary/10 select-none">404</div>
        <img
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuA4FTGcY7eOoD-6ryKqLyaGv_ovjUijGJC3s4mCmnV2ZTRtDEDzB4QTB0hZaeS40dGgIxMbDXaKpl9-Iibf5Nudzuq8ZwGy-Bo4dzCruPTwDovIVXdRPWisdvDwT1-5f3bSbZ6topewMvZ3r2qDvYosdW1sM3tzUfh1VelBj6pz-QX1pQsomDmRIyjxmvb6KsYh5vPYO6AaUzMJszIIeRxNNMTr1nwxJNrvX_OIDKrzGyULndTYEPsQnje32js5xvk3M5TIn3GEq54"
          alt="404 Robot"
          className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 h-48 object-contain"
        />
      </div>
      <h1 className="text-3xl font-bold mb-4">お探しのページは見つかりませんでした</h1>
      <p className="text-text-muted mb-8 max-w-md">
        ご指定のページは、移動または削除されたか、URLが間違っている可能性があります。
      </p>
      <button
        onClick={() => onNavigate('/')}
        className="bg-primary text-white px-8 py-3 rounded-full font-bold shadow-lg hover:opacity-90 transition-opacity flex items-center gap-2"
      >
        トップページへ戻る <span className="material-symbols-outlined">arrow_forward</span>
      </button>
    </div>
  );
};

export const UserProfile: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const { showInfo } = useToast();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [avatar, setAvatar] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const userData = await userApi.getCurrentUser();
        setName(userData.name);
        // バックエンド(PUT /api/users/me)はemail更新を受け付けるが、getCurrentUser()
        // (src/api/users.ts) がレスポンスからemailを除いているため、現状この画面では
        // 現在値を取得できない。avatarを入れていたコピペバグを修正し、emailから初期化する。
        setEmail((userData as { email?: string }).email ?? '');
        setAvatar(userData.avatar || '');
      } catch (err: any) {
        console.error('Failed to fetch user:', err);
        setError(err.detail || err.message || 'ユーザー情報の取得に失敗しました');
        // フォールバック: モックデータを使用
        if (user) {
          setName(user.name);
          setAvatar(user.avatar);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchUser();
  }, []);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setError(null);
      const payload: userApi.UserUpdateRequest = { name, avatar };
      // メールアドレスが入力されている場合のみ送信する。
      // 空文字はバックエンドのEmailStr検証で422となり保存全体が失敗するため除外する。
      if (email.trim()) {
        payload.email = email.trim();
      }
      await userApi.updateUser(payload);
      await refreshUser();
      alert('プロフィールを更新しました');
    } catch (err: any) {
      console.error('Failed to update user:', err);
      setError(err.detail || err.message || 'プロフィールの更新に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="flex justify-center items-center min-h-[400px]">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-muted">プロフィールを読み込み中...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-black mb-6">プロフィール</h1>
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
          {error}
        </div>
      )}
      <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 flex flex-col md:flex-row gap-8 items-center md:items-start">
        <div className="flex-shrink-0 flex flex-col items-center gap-4">
          <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-gray-100">
            <img src={avatar || currentUser.avatar} alt={name || currentUser.name} className="w-full h-full object-cover" />
          </div>
          <button
            type="button"
            onClick={() => showInfo('アイコンのアップロードは現在準備中です')}
            className="text-primary text-sm font-bold hover:underline"
          >
            アイコンを変更
          </button>
        </div>
        <div className="flex-1 w-full space-y-6">
          <div>
            <label className="block text-text-muted text-sm font-bold mb-1">お名前</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 text-text-light font-medium focus:bg-white focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label className="block text-text-muted text-sm font-bold mb-1">メールアドレス</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="新しいメールアドレスを入力"
              className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 text-text-light font-medium focus:bg-white focus:ring-2 focus:ring-primary"
            />
            <p className="mt-1 text-xs text-text-muted">空欄のままにすると、現在のメールアドレスは変更されません。</p>
          </div>
          <div>
            <label className="block text-text-muted text-sm font-bold mb-1">プラン</label>
            <div className="p-3 rounded-xl bg-gradient-to-r from-primary/10 to-purple-100 border border-primary/20 text-primary font-bold flex justify-between items-center">
              <span>Premium Plan</span>
              <span className="text-xs bg-white px-2 py-1 rounded-full">Active</span>
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="bg-primary text-white px-6 py-3 rounded-full font-bold shadow-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {isSaving ? '保存中...' : '保存する'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const Settings: React.FC = () => {
  const { showSuccess, showError, showInfo } = useToast();

  // 設定値（getPreferences で取得）
  const [preferences, setPreferences] = useState<userApi.UserPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // 通知トグルの保存中フラグ（キー単位で二重操作を抑止）
  const [savingKey, setSavingKey] = useState<string | null>(null);

  // パスワード変更フォーム
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  useEffect(() => {
    const fetchPreferences = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await userApi.getPreferences();
        setPreferences(data);
      } catch (err) {
        console.error('Failed to fetch preferences:', err);
        setError(getErrorMessage(err) || '設定の読み込みに失敗しました');
      } finally {
        setIsLoading(false);
      }
    };
    fetchPreferences();
  }, []);

  // 通知トグルの切替（楽観的更新＋失敗時ロールバック）
  const handleToggle = async (key: 'notifications_enabled' | 'email_notifications') => {
    if (!preferences || savingKey) return;
    const previous = preferences;
    const nextValue = !preferences[key];
    setPreferences({ ...preferences, [key]: nextValue });
    setSavingKey(key);
    try {
      const updated = await userApi.updatePreferences({ [key]: nextValue });
      setPreferences(updated);
      showSuccess('設定を保存しました');
    } catch (err) {
      console.error('Failed to update preferences:', err);
      setPreferences(previous); // 楽観的更新の巻き戻し
      showError(getErrorMessage(err) || '設定の保存に失敗しました');
    } finally {
      setSavingKey(null);
    }
  };

  // 言語の変更
  const handleLanguageChange = async (language: string) => {
    if (!preferences || savingKey) return;
    const previous = preferences;
    setPreferences({ ...preferences, language });
    setSavingKey('language');
    try {
      const updated = await userApi.updatePreferences({ language });
      setPreferences(updated);
      showSuccess('設定を保存しました');
    } catch (err) {
      console.error('Failed to update language:', err);
      setPreferences(previous);
      showError(getErrorMessage(err) || '設定の保存に失敗しました');
    } finally {
      setSavingKey(null);
    }
  };

  // パスワード変更
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isChangingPassword) return;
    // クライアント側バリデーション
    if (newPassword !== confirmPassword) {
      showError('新しいパスワードと確認用パスワードが一致しません');
      return;
    }
    if (newPassword.length < 8) {
      showError('新しいパスワードは8文字以上で入力してください');
      return;
    }
    try {
      setIsChangingPassword(true);
      await userApi.changePassword(currentPassword, newPassword);
      showSuccess('パスワードを変更しました');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      console.error('Failed to change password:', err);
      showError(getErrorMessage(err) || 'パスワードの変更に失敗しました。現在のパスワードをご確認ください');
    } finally {
      setIsChangingPassword(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="flex justify-center items-center min-h-[400px]">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-muted">設定を読み込み中...</p>
          </div>
        </div>
      </div>
    );
  }

  // 再利用するトグルスイッチ
  const ToggleSwitch: React.FC<{ checked: boolean; disabled?: boolean; onChange: () => void }> = ({ checked, disabled, onChange }) => (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={onChange}
      className={`relative inline-flex h-7 w-12 flex-shrink-0 items-center rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${checked ? 'bg-primary' : 'bg-gray-300'}`}
    >
      <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-black mb-6">設定</h1>

      {error && (
        <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* 通知設定 */}
      {preferences && (
        <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 mb-6">
          <div className="p-6 border-b border-gray-100 flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined">notifications</span>
            </div>
            <h3 className="font-bold text-text-light">通知設定</h3>
          </div>
          <div className="p-6 flex items-center justify-between">
            <div className="flex-1 pr-4">
              <p className="font-bold text-text-light">アプリ内通知</p>
              <p className="text-sm text-text-muted">プランの更新やおすすめ情報をアプリ内で受け取る</p>
            </div>
            <ToggleSwitch
              checked={preferences.notifications_enabled}
              disabled={savingKey !== null}
              onChange={() => handleToggle('notifications_enabled')}
            />
          </div>
          <div className="p-6 border-t border-gray-100 flex items-center justify-between">
            <div className="flex-1 pr-4">
              <p className="font-bold text-text-light">メール通知</p>
              <p className="text-sm text-text-muted">お得な情報やお知らせをメールで受け取る</p>
            </div>
            <ToggleSwitch
              checked={preferences.email_notifications}
              disabled={savingKey !== null}
              onChange={() => handleToggle('email_notifications')}
            />
          </div>
        </div>
      )}

      {/* 言語と地域 */}
      {preferences && (
        <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 mb-6">
          <div className="p-6 border-b border-gray-100 flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined">language</span>
            </div>
            <h3 className="font-bold text-text-light">言語と地域</h3>
          </div>
          <div className="p-6">
            <label className="block text-text-muted text-sm font-bold mb-1">言語</label>
            <select
              value={preferences.language}
              disabled={savingKey !== null}
              onChange={(e) => handleLanguageChange(e.target.value)}
              className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 text-text-light font-medium focus:bg-white focus:ring-2 focus:ring-primary disabled:opacity-50"
            >
              <option value="ja">日本語</option>
              <option value="en">English</option>
            </select>
            <p className="mt-2 text-xs text-text-muted">設定値を保存します。アプリの表示言語の切替は今後対応予定です。</p>
          </div>
        </div>
      )}

      {/* プライバシーとセキュリティ */}
      <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 mb-6">
        <div className="p-6 border-b border-gray-100 flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined">lock</span>
          </div>
          <h3 className="font-bold text-text-light">プライバシーとセキュリティ</h3>
        </div>
        <form onSubmit={handleChangePassword} className="p-6 space-y-4">
          <p className="text-sm font-bold text-text-light">パスワードの変更</p>
          <div>
            <label className="block text-text-muted text-sm font-bold mb-1">現在のパスワード</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 text-text-light font-medium focus:bg-white focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label className="block text-text-muted text-sm font-bold mb-1">新しいパスワード</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 text-text-light font-medium focus:bg-white focus:ring-2 focus:ring-primary"
            />
            <p className="mt-1 text-xs text-text-muted">8文字以上で入力してください。</p>
          </div>
          <div>
            <label className="block text-text-muted text-sm font-bold mb-1">新しいパスワード（確認）</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              className="w-full p-3 rounded-xl bg-gray-50 border border-gray-200 text-text-light font-medium focus:bg-white focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            type="submit"
            disabled={isChangingPassword}
            className="bg-primary text-white px-6 py-3 rounded-full font-bold shadow-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {isChangingPassword ? '変更中...' : 'パスワードを変更'}
          </button>
        </form>
      </div>

      {/* お支払い方法（Stripe 未実装のため準備中） */}
      <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 mb-6">
        <button
          type="button"
          onClick={() => showInfo('お支払い機能は現在準備中です')}
          className="w-full p-6 hover:bg-gray-50 transition-colors flex items-center gap-4 group text-left"
        >
          <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-text-muted group-hover:bg-primary/10 group-hover:text-primary transition-colors">
            <span className="material-symbols-outlined">credit_card</span>
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-text-light">お支払い方法</h3>
            <p className="text-sm text-text-muted">クレジットカードの管理</p>
          </div>
          <span className="text-xs bg-gray-100 text-text-muted px-2 py-1 rounded-full font-bold">準備中</span>
        </button>
      </div>

      {/* ヘルプとサポート（お問い合わせページへ遷移） */}
      <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100">
        <button
          type="button"
          onClick={() => { window.location.hash = '#/contact'; }}
          className="w-full p-6 hover:bg-gray-50 transition-colors flex items-center gap-4 group text-left"
        >
          <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-text-muted group-hover:bg-primary/10 group-hover:text-primary transition-colors">
            <span className="material-symbols-outlined">help</span>
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-text-light">ヘルプとサポート</h3>
            <p className="text-sm text-text-muted">よくある質問、お問い合わせ</p>
          </div>
          <span className="material-symbols-outlined text-gray-300 group-hover:text-primary">chevron_right</span>
        </button>
      </div>
    </div>
  );
};