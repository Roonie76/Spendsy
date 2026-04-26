import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#060b15] flex items-center justify-center p-6 text-center">
          <div className="max-w-md w-full bg-white/5 border border-white/10 p-8 rounded-[2.5rem] backdrop-blur-xl">
            <div className="w-16 h-16 bg-rose-500/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-rose-500" />
            </div>
            <h1 className="text-2xl font-black text-white mb-2">Something went wrong</h1>
            <p className="text-slate-400 text-sm mb-8">
              Spendsy encountered an unexpected error. Don't worry, your data is safe.
            </p>
            <button
              onClick={this.handleReset}
              className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-black rounded-2xl transition-all shadow-lg flex items-center justify-center gap-3"
            >
              <RefreshCw className="w-4 h-4" />
              Reload Application
            </button>
            {process.env.NODE_ENV === "development" && (
              <div className="mt-8 text-left p-4 bg-black/40 rounded-xl overflow-auto max-h-40">
                <p className="text-[10px] font-mono text-rose-300 break-all">
                  {this.state.error?.toString()}
                </p>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
