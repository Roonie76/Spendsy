//No database needed
import React, { useState } from 'react';
import { 
  Home, ListFilter, Plus, ClipboardCheck, PieChart, Landmark, User, Wallet, LogOut, Menu, X, Calendar
} from 'lucide-react';
import { TABS } from '../../../../../../packages/shared/config/constants';

export const Navigation = ({ activeTab, setActiveTab, onSignOut }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  const navItems = [
    { id: TABS.HOME, icon: Home, label: "Home" },
    { id: TABS.HISTORY, icon: ListFilter, label: "History" },
    { id: TABS.ADD, icon: Plus, label: "Add New" },
    { id: TABS.AUDIT, icon: ClipboardCheck, label: "Tax Audit" },
    { id: TABS.STATS, icon: PieChart, label: "Stats" },
    { id: TABS.WEALTH, icon: Landmark, label: "Wealth" },
    { id: TABS.PLANNER, icon: Calendar, label: "Planner" },
    { id: TABS.PROFILE, icon: User, label: "Profile" }
  ];

  return (
    <>
      {/* =======================
          DESKTOP SIDEBAR 
      ======================== */}
      <nav className="hidden md:flex flex-col fixed left-4 top-4 bottom-4 w-20 hover:w-64 xl:w-24 xl:hover:w-64 bg-slate-900/60 backdrop-blur-xl border border-white/10 rounded-[2rem] items-center py-4 xl:py-6 z-50 shadow-2xl shadow-black/50 print:hidden transition-all duration-500 ease-in-out group overflow-hidden">
        
        {/* --- SECTION 1: TOP CONTENT (Logo + Nav Items) --- */}
        <div className="flex flex-col w-full gap-4 xl:gap-6 flex-1 min-h-0">
          
          {/* 1.1 LOGO SECTION (Sized exactly like Nav Items) */}
          <div className="shrink-0 mt-1 w-full px-2 xl:px-4">
             <div className="flex items-center p-2 xl:p-3 rounded-xl xl:rounded-2xl transition-all duration-300 shrink-0 overflow-hidden">
               
               {/* Icon Container - Matching Nav Item Size (w-6/w-8) */}
               <div className="w-6 h-6 xl:w-8 xl:h-8 bg-gradient-to-tr from-blue-600 to-cyan-500 rounded-lg xl:rounded-xl flex items-center justify-center shadow-lg shrink-0 mx-auto group-hover:mx-0 transition-all duration-500">
                  {/* Icon size adjusted to fit inside the smaller box */}
                  <Wallet className="w-3.5 h-3.5 xl:w-4.5 xl:h-4.5 text-white" />
               </div>

               {/* App Name */}
               <div className="opacity-0 w-0 group-hover:w-auto group-hover:opacity-100 group-hover:ml-3 transition-all duration-500 delay-75 whitespace-nowrap">
                  <h1 className="text-lg xl:text-xl font-black tracking-tight text-white">
                    Spendsy
                  </h1>
               </div>

             </div>
          </div>

          {/* 1.2 Navigation Items */}
          <div className="flex flex-col gap-1 xl:gap-3 w-full px-2 xl:px-4 pb-2 overflow-y-auto no-scrollbar">
            {navItems.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`group/btn relative flex items-center p-2 xl:p-3 rounded-xl xl:rounded-2xl transition-all duration-300 shrink-0 overflow-hidden ${
                  activeTab === tab.id
                    ? "bg-white/10 text-cyan-400"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }`}
              >
                {/* Icon Wrapper - w-6/w-8 (Same as Logo Container) */}
                <div className="w-6 h-6 xl:w-8 xl:h-8 flex items-center justify-center shrink-0 mx-auto group-hover:mx-0 transition-all duration-500">
                  <tab.icon className="w-5 h-5 xl:w-6 xl:h-6" />
                </div>
                
                {/* Text Label */}
                <span className="text-xs xl:text-sm font-semibold tracking-wide whitespace-nowrap opacity-0 w-0 group-hover:w-auto group-hover:opacity-100 group-hover:ml-3 transition-all duration-500 delay-75">
                  {tab.label}
                </span>

                {/* Active Indicator */}
                {activeTab === tab.id && (
                  <div className="absolute right-3 xl:right-4 w-1.5 h-1.5 bg-cyan-400 rounded-full shadow-[0_0_10px_cyan] opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* --- SECTION 2: BOTTOM CONTENT (Logout) --- */}
        <div className="shrink-0 w-full px-2 xl:px-4 mt-2">
          <button 
            onClick={onSignOut} 
            className="flex items-center w-full p-2 xl:p-4 rounded-xl xl:rounded-2xl text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-300 group/logout overflow-hidden"
          >
            <div className="w-6 h-6 xl:w-8 xl:h-8 flex items-center justify-center shrink-0 mx-auto group-hover:mx-0 transition-all duration-500">
              <LogOut className="w-5 h-5 xl:w-6 xl:h-6" />
            </div>
            <span className="text-xs xl:text-sm font-bold tracking-wide whitespace-nowrap opacity-0 w-0 group-hover:w-auto group-hover:opacity-100 group-hover:ml-3 transition-all duration-500 delay-75">
              Sign Out
            </span>
          </button>
        </div>

      </nav>

      {/* =======================
          MOBILE NAVIGATION (Unchanged)
      ======================== */}
      <div className="md:hidden print:hidden">
        {isMobileMenuOpen && (
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity duration-300"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}
        <div className={`fixed bottom-6 left-6 right-6 z-50 transition-all duration-300 transform ${
          isMobileMenuOpen ? 'translate-y-0 opacity-100' : 'translate-y-[120%] opacity-0 pointer-events-none'
        }`}>
          <div className="bg-[#0f0c29]/95 backdrop-blur-2xl border border-white/10 shadow-2xl shadow-black/50 rounded-[2rem] p-6">
            <div className="grid grid-cols-4 gap-4 mb-4">
              {navItems.map((t) => (
                <button 
                  key={t.id} 
                  onClick={() => {
                    setActiveTab(t.id);
                    setIsMobileMenuOpen(false);
                  }}
                  className="flex flex-col items-center gap-2"
                >
                  <div className={`p-4 rounded-2xl transition-all ${
                    activeTab === t.id 
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' 
                      : 'bg-white/5 text-slate-400'
                  }`}>
                    <t.icon className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-medium text-slate-400">{t.label}</span>
                </button>
              ))}
            </div>
            <button 
              onClick={onSignOut}
              className="w-full flex items-center justify-center gap-2 p-3 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20"
            >
              <LogOut className="w-4 h-4" />
              <span className="text-xs font-bold uppercase tracking-wider">Sign Out</span>
            </button>
          </div>
        </div>
        <div className="fixed bottom-6 right-6 z-50">
          <button 
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className={`w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 border border-white/10 ${
              isMobileMenuOpen 
                ? 'bg-slate-800 text-white rotate-90' 
                : 'bg-gradient-to-tr from-blue-600 to-cyan-500 text-white animate-bounce-slow'
            }`}
          >
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
        {!isMobileMenuOpen && (
           <div className="fixed bottom-6 left-6 z-40 bg-[#0f0c29]/90 backdrop-blur-xl border border-white/10 rounded-full py-2 px-4 flex items-center gap-3 shadow-lg">
             <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
             <span className="text-xs font-bold uppercase tracking-widest text-white/80">
               {navItems.find(n => n.id === activeTab)?.label}
             </span>
           </div>
        )}
      </div>
    </>
  );
};