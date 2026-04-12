// No database needed
import React from 'react';
import { UNITS } from '@shared/config/constants';

const UnitSelector = ({ currentUnit, onSelect, className = "" }) => (
    <div className={`flex bg-black/40 rounded-xl border border-white/10 p-1 ${className}`}>
        {UNITS.map(u => (
            <button 
                key={u.label} 
                type="button" 
                onClick={() => onSelect(u.value)} 
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-bold transition-all ${
                    currentUnit === u.value 
                        ? 'bg-white/20 text-white shadow-sm' 
                        : 'text-slate-500 hover:text-slate-300'
                }`}
            >
                {u.label}
            </button>
        ))}
    </div>
);

export default UnitSelector;