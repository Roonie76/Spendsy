//No database needed
import React from 'react';
import { AlertTriangle, CheckCircle2, X } from 'lucide-react';
import { Wallet } from 'lucide-react';

export const Toast = ({ message, type, isVisible, onClose }) => {
  if (!isVisible) return null;
  const isError = type === 'error';
  return (
    <div className={`fixed bottom-6 left-1/2 transform -translate-x-1/2 z-[100] flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl border backdrop-blur-md animate-in slide-in-from-bottom-5 fade-in duration-300 ${
        isError ? 'bg-rose-500/90 border-rose-400 text-white' : 'bg-emerald-500/90 border-emerald-400 text-white'
    }`}>
       {isError ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle2 className="w-5 h-5" />}
       <span className="font-bold text-sm">{message}</span>
       <button onClick={onClose}><X className="w-4 h-4" /></button>
    </div>
  );
};

// Loading Screen Component
export const Loading = ({ message }) => (
  <div className="relative flex flex-col items-center justify-center min-h-screen bg-slate-950 overflow-hidden">
    
    {/* 1. Background Effects (Ambient Glows) */}
    <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0">
        {/* Main Blue Glow */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/20 rounded-full blur-[100px] animate-pulse" />
        {/* Secondary Cyan Glow (Replaced Purple) */}
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-600/10 rounded-full blur-[100px] animate-pulse delay-700" />
    </div>

    <div className="relative z-10 flex flex-col items-center">
      {/* 2. The Spinner Container */}
      <div className="relative w-24 h-24 mb-8">
        
        {/* Outer Ring (Primary Blue) */}
        <div className="absolute inset-0 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        
        {/* Inner Ring (Cyan/Sky - Replaced Purple) */}
        <div className="absolute inset-3 border-4 border-cyan-500/20 border-b-cyan-500 rounded-full animate-spin duration-[3s]" />
        
        {/* Center Icon (Pulsing) */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="bg-slate-900/50 backdrop-blur-sm p-3 rounded-full border border-white/10 shadow-[0_0_15px_rgba(59,130,246,0.5)] animate-pulse">
             <Wallet className="w-6 h-6 text-blue-400" />
          </div>
        </div>
      </div>

      {/* 3. Brand Text */}
      {/* Gradient now goes form Blue -> Cyan -> Blue */}
      <h1 className="text-2xl font-black tracking-[0.2em] bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-400 animate-gradient-x mb-4">
        Spendsy
      </h1>

      {/* 4. Loading Message Pill */}
      {message && (
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" />
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce delay-100" />
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce delay-200" />
          <span className="text-slate-400 text-xs font-medium ml-2">{message}</span>
        </div>
      )}
    </div>
  </div>
);

export const ErrorScreen = ({ error, onRetry }) => (
  <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-white p-6 text-center">
    <AlertTriangle className="w-16 h-16 text-rose-500 mb-4" />
    <h1 className="text-2xl font-bold mb-2">System Error</h1>
    <p className="text-slate-400 mb-6 max-w-xs mx-auto text-sm">
      {error || "Something went wrong while starting the app."}
    </p>
    <button
      onClick={onRetry}
      className="bg-blue-600 px-6 py-3 rounded-xl font-bold hover:bg-blue-500 transition"
    >
      Try Again
    </button>
  </div>
);

export const ConfirmationDialog = ({ isOpen, message, onConfirm, onCancel }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-[#0f0c29] border border-white/10 p-6 rounded-3xl shadow-2xl max-w-sm w-full transform scale-100 transition-all">
        <h3 className="text-lg font-bold text-white mb-2">Confirmation</h3>
        <p className="text-slate-300 mb-6 text-sm">{message}</p>
        <div className="flex gap-3 justify-end">
          <button 
            onClick={onCancel}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={onConfirm}
            className="px-5 py-2.5 rounded-xl text-sm font-bold bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-500/20 transition-all"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
};