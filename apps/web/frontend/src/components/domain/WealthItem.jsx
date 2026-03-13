import React, { useState } from 'react';
import { Trash2, Building2, FileText, Pencil, Check, X } from 'lucide-react';
import { formatIndianCompact } from '../../../../../../packages/shared/utils/helpers';

const WealthItem = ({ item, onDelete, onUpdate }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [tempValue, setTempValue] = useState(item.amount);
    const [tempName, setTempName] = useState(item.title || item.name);

    const isAsset = item.type === 'asset';

    const handleSave = () => {
        onUpdate(item.id, { 
            title: tempName, 
            amount: parseFloat(tempValue) 
        });
        setIsEditing(false);
    };

    return (
        <div className="group flex items-center p-4 bg-white/5 backdrop-blur-md border border-white/10 rounded-3xl mb-3 transition-all hover:bg-white/10 relative overflow-hidden">
            {/* Icon */}
            <div className={`p-3.5 rounded-2xl mr-4 ${isAsset ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'} shadow-inner shrink-0 relative z-10`}>
                {isAsset ? <Building2 className="w-5 h-5" /> : <FileText className="w-5 h-5" />}
            </div>

            {/* Details or Edit Input */}
            <div className="flex-1 min-w-0 relative z-10">
                {isEditing ? (
                    <input 
                        className="bg-black/20 border border-white/20 rounded-lg px-2 py-1 text-white w-full outline-none focus:border-blue-500"
                        value={tempName}
                        onChange={(e) => setTempName(e.target.value)}
                    />
                ) : (
                    <>
                        <h4 className="font-semibold text-blue-50 truncate text-base md:text-lg">{item.title || item.name}</h4>
                        <p className="text-xs md:text-sm text-blue-300/70 mt-1 capitalize">{item.type}</p>
                    </>
                )}
            </div>

            {/* Actions & Amount */}
            <div className="text-right pl-4 shrink-0 flex flex-col items-end relative z-10">
                {isEditing ? (
                    <div className="flex flex-col items-end gap-2">
                        <input 
                            type="text"
                            inputMode="decimal"
                            className="bg-black/20 border border-white/20 rounded-lg px-2 py-1 text-white w-24 text-right outline-none"
                            value={tempValue}
                            onChange={(e) => {
                              const val = e.target.value;
                              if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) {
                                setTempValue(val);
                              }
                            }}
                        />
                        <div className="flex gap-2">
                            <button onClick={handleSave} className="p-1 text-emerald-400 hover:bg-emerald-400/10 rounded-full"><Check className="w-4 h-4" /></button>
                            <button onClick={() => setIsEditing(false)} className="p-1 text-rose-400 hover:bg-rose-400/10 rounded-full"><X className="w-4 h-4" /></button>
                        </div>
                    </div>
                ) : (
                    <>
                        <p className={`font-bold text-lg md:text-xl tracking-tight ${isAsset ? 'text-emerald-300' : 'text-rose-300'}`}>
                            {formatIndianCompact(item.amount)}
                        </p>
                        <div className="flex gap-1">
                            <button 
                                onClick={() => setIsEditing(true)} 
                                className="mt-1 p-2 text-slate-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-full transition-all"
                            >
                                <Pencil className="w-4 h-4" />
                            </button>
                            {onDelete && (
                                <button 
                                    onClick={() => onDelete(item.id)} 
                                    className="mt-1 p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-full transition-all active:scale-90"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default WealthItem;