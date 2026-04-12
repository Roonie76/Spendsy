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
            <div className={`flex-1 min-w-0 relative z-10 ${isEditing ? 'w-full mb-2 sm:mb-0' : ''}`}>
                {isEditing ? (
                    <div className="space-y-2">
                        {!item.is_loan && (
                            <input 
                                className="bg-black/20 border border-white/20 rounded-xl px-4 py-2 text-white w-full outline-none focus:border-blue-500 font-medium transition-all"
                                value={tempName}
                                onChange={(e) => setTempName(e.target.value)}
                                placeholder="Name"
                            />
                        )}
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
            <div className={`shrink-0 flex flex-col items-end relative z-10 ${isEditing ? 'w-full' : 'text-right pl-4'}`}>
                {isEditing ? (
                    <div className="flex flex-col gap-3 w-full animate-in slide-in-from-top-1 duration-300">
                        {item.is_loan ? (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
                            <div className="space-y-3">
                              <select
                                  value={tempName}
                                  onChange={(e) => setTempName(e.target.value)}
                                  className="w-full bg-black/20 border border-white/20 rounded-xl px-4 py-2 text-white text-xs outline-none focus:border-blue-500 transition-all appearance-none"
                              >
                                {BANKS.map(bank => (
                                  <option key={bank} value={bank}>{bank}</option>
                                ))}
                                <option value="Other">Other</option>
                              </select>

                              <div className="space-y-1">
                                <div className="flex justify-between px-1">
                                  <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Balance</label>
                                  <span className="text-[10px] font-bold text-rose-300">₹{formatIndianCompact(tempValue)}</span>
                                </div>
                                <input 
                                    type="range"
                                    min="0"
                                    max="10000000"
                                    step="1000"
                                    className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-rose-500"
                                    value={tempValue}
                                    onChange={(e) => setTempValue(e.target.value)}
                                />
                              </div>
                            </div>

                            <div className="space-y-3">
                              <div className="space-y-1">
                                <div className="flex justify-between px-1">
                                  <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Interest Rate (%)</label>
                                  <span className="text-[10px] font-bold text-rose-300">{tempROI}%</span>
                                </div>
                                <input 
                                    type="range"
                                    min="1"
                                    max="30"
                                    step="0.1"
                                    className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-rose-500"
                                    value={tempROI}
                                    onChange={(e) => setTempROI(e.target.value)}
                                />
                              </div>

                              <input 
                                  type="number"
                                  className="bg-black/20 border border-white/20 rounded-xl px-4 py-2 text-white text-xs w-full outline-none focus:border-blue-500 transition-all"
                                  value={tempTenure}
                                  placeholder="Tenure (Months)"
                                  onChange={(e) => setTempTenure(e.target.value)}
                              />
                            </div>
                          </div>
                        ) : (
                          <div className="w-full">
                            <input 
                                type="number"
                                inputMode="decimal"
                                className="bg-black/20 border border-white/20 rounded-xl px-4 py-2 text-white w-full text-left outline-none focus:border-blue-500 transition-all"
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
                        )}
                        <div className="flex gap-2 justify-end w-full">
                            <button onClick={handleSave} className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-emerald-500/20 text-emerald-400 px-4 py-2 rounded-xl hover:bg-emerald-500/30 transition-all font-bold text-xs"><Check className="w-4 h-4" /> Save</button>
                            <button onClick={() => setIsEditing(false)} className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-rose-500/20 text-rose-400 px-4 py-2 rounded-xl hover:bg-rose-500/30 transition-all font-bold text-xs"><X className="w-4 h-4" /> Cancel</button>
                        </div>
                    </div>
                ) : (
                    <>
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
                    </>
                )}
            </div>
        </div>
    );
};

export default WealthItem;