import { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * アプリ全体を囲むエラーバウンダリ。
 * 子コンポーネントのレンダリング中に例外が発生しても、画面全体が真っ白になるのを防ぎ、
 * フォールバックUI（再読み込み／トップへ戻る）を表示する。
 * ※React のエラーバウンダリはクラスコンポーネントでのみ実装可能。
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  // このプロジェクトには @types/react が無く基底クラスの props/state 型が解決されないため、
  // ここで明示的に宣言する（declare は型のみで実行コードには影響しない）。
  declare props: ErrorBoundaryProps;
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // 本番では監視サービス等へ送る想定。ここではコンソールに記録するに留める。
    console.error('ErrorBoundary caught an error:', error, info?.componentStack);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    // ハッシュルーターのためトップへ遷移してから再読み込みし、壊れた状態をリセットする
    window.location.hash = '#/';
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-background-light px-4 text-center">
          <span className="material-symbols-outlined text-6xl text-primary/40 mb-4">error</span>
          <h1 className="text-2xl font-bold text-text-light mb-2">問題が発生しました</h1>
          <p className="text-text-muted mb-8 max-w-md">
            画面の表示中に予期しないエラーが発生しました。ご迷惑をおかけします。
            ページを再読み込みするか、トップページからやり直してください。
          </p>
          <div className="flex gap-3">
            <button
              onClick={this.handleReload}
              className="bg-primary text-white px-6 py-3 rounded-full font-bold hover:opacity-90 transition-opacity"
            >
              再読み込み
            </button>
            <button
              onClick={this.handleGoHome}
              className="bg-white border border-gray-200 text-text-light px-6 py-3 rounded-full font-bold hover:bg-gray-50 transition-colors"
            >
              トップページへ
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
