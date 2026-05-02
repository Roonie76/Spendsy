import React, { useState } from 'react';
import { Trash2, Building2, FileText, Pencil, Check, X } from 'lucide-react';
import { formatIndianCompact } from '@shared/utils/helpers';
import { BANKS } from '@shared/config/constants';

const WealthItem = ({ item, onDelete, onUpdate }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [tempValue, setTempValue] = useState(item.amount);
    const [tempName, setTempName] = useState(item.is_loan ? item.loan_details?.bank_name : (item.title || item.name));
    const [tempROI, setTempROI] = useState(item.loan_details?.roi || 10);
    const [tempTenure, setTempTenure] = useState(item.loan_details?.tenure || 12);

    const isAsset = item.type === 'asset';

    const handleSave = () => {
        onUpdate(item.id, { 
            title: tempName, 
            amount: parseFloat(tempValue),
            interest_rate: parseFloat(tempROI),
            tenure: parseInt(tempTenure)
        });
        setIsEditing(false);
    };

    return (
        <div className={`group flex ${isEditing ? 'flex-col sm:flex-row sm:items-center' : 'items-center'} p-4 bg-white/5 backdrop-blur-md border border-white/10 rounded-3xl mb-3 transition-all hover:bg-white/10 relative overflow-hidden`}>
            {/* Icon */}
            <div className={`p-3.5 rounded-2xl mr-4 ${isAsset ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'} shadow-inner shrink-0 relative z-10`}>
                {isAsset ? <Building2 className="w-5 h-5" /> : <FileText className="w-5 h-5" />}
            </div>

            {/* Details or Edit Input */}
            <div className={`flex-1 min-w-0 relative z-10 ${isEditing ? 'w-full mb-4 sm:mb-0' : ''}`}>
                {isEditing ? (
                    <div className="space-y-4 w-full">
                        {item.is_loan ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                                <div className="space-y-3">
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Bank Name</label>
                                        <select
                                            value={tempName}
                                            onChange={(e) => setTempName(e.target.value)}
                                            className="w-full bg-black/30 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm outline-none focus:border-blue-500 transition-all appearance-none"
                                        >
                                            {BANKS.map(bank => (
                                                <option key={bank} value={bank} className="bg-slate-900">{bank}</option>
                                            ))}
                                            <option value="Other" className="bg-slate-900">Other</option>
                                        </select>
                                    </div>

                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Remaining Balance (₹)</label>
                                        <input 
                                            type="number"
                                            className="bg-black/30 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm w-full outline-none focus:border-blue-500 transition-all"
                                            value={tempValue}
                                            onChange={(e) => setTempValue(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Interest Rate (%)</label>
                                        <input 
                                            type="number"
                                            step="0.1"
                                            className="bg-black/30 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm w-full outline-none focus:border-blue-500 transition-all"
                                            value={tempROI}
                                            onChange={(e) => setTempROI(e.target.value)}
                                        />
                                    </div>

                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Tenure (Months)</label>
                                        <input 
                                            type="number"
                                            className="bg-black/30 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm w-full outline-none focus:border-blue-500 transition-all"
                                            value={tempTenure}
                                            onChange={(e) => setTempTenure(e.target.value)}
                                        />
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Name</label>
                                    <input 
                                        className="bg-black/30 border border-white/10 rounded-2xl px-4 py-3 text-white w-full outline-none focus:border-blue-500 font-medium transition-all"
                                        value={tempName}
                                        onChange={(e) => setTempName(e.target.value)}
                                        placeholder="Name"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Amount (₹)</label>
                                    <input 
                                        type="number"
                                        inputMode="decimal"
                                        className="bg-black/30 border border-white/10 rounded-2xl px-4 py-3 text-white w-full text-left outline-none focus:border-blue-500 transition-all"
                                        value={tempValue}
                                        placeholder="Amount"
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) {
                                                setTempValue(val);
                                            }
                                        }}
                                    />
                                </div>
                            </div>
                        )}
                        <div className="flex gap-2 justify-end pt-2">
                            <button onClick={() => setIsEditing(false)} className="flex items-center gap-2 bg-white/5 text-slate-400 px-5 py-2.5 rounded-xl hover:bg-white/10 transition-all font-bold text-xs"><X className="w-4 h-4" /> Cancel</button>
                            <button onClick={handleSave} className="flex items-center gap-2 bg-blue-600/20 text-blue-400 border border-blue-500/20 px-6 py-2.5 rounded-xl hover:bg-blue-600/30 transition-all font-bold text-xs"><Check className="w-4 h-4" /> Save Changes</button>
                        </div>
                    </div>
                ) : (
                    <>
                        <div className="flex items-center gap-2">
                            <h4 className="font-semibold text-blue-50 truncate text-base md:text-lg">{item.title || item.name}</h4>
                            {item.is_loan && (
                                <span className="bg-rose-500/20 text-rose-400 text-[10px] font-bold px-1.5 py-0.5 rounded border border-rose-500/20 uppercase">
                                    Loan
                                </span>
                            )}
                        </div>
                        <p className="text-xs md:text-sm text-blue-300/70 mt-2 capitalize shadow-sm">
                            {item.is_loan ? `${item.loan_details?.bank_name} • ${item.loan_details?.roi}% Interest Rate` : item.type}
                        </p>
                    </>
                )}
            </div>

            {/* Actions & Amount */}
            {!isEditing && (
                <div className="shrink-0 flex flex-col items-end text-right pl-4 relative z-10">
                    <p className={`font-bold text-lg md:text-xl tracking-tight ${isAsset ? 'text-emerald-300' : 'text-rose-300'}`}>
                        {formatIndianCompact(item.amount)}
                    </p>
                    <div className="flex gap-1 justify-end">
                        <button 
                            onClick={() => setIsEditing(true)} 
                            className="mt-1 p-2 text-slate-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-full transition-all"
                        >
                            <Pencil className="w-4 h-4" />
                        </button>
                        {onDelete && (
                            <button 
                                onClick={() => onDelete(item)} 
                                className="mt-1 p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-full transition-all active:scale-90"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default WealthItem;