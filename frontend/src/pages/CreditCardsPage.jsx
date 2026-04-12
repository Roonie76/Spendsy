import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  CreditCard as CardIcon, 
  Plus, 
  Trash2, 
  ChevronLeft, 
  Zap,
  ShieldCheck,
  TrendingUp,
  Edit2
} from "lucide-react";
import { apiFetch } from "../api";
import { formatIndianCompact } from "@shared/utils/helpers";

const CreditCardsPage = ({ 
  apiBaseUrl, 
  showToast, 
  triggerConfirm, 
  onBack 
}) => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  
  // Form State
  const [formData, setFormData] = useState({
    bankName: "",
    cardHolder: "",
    lastFour: "",
    creditLimit: "",
    billingCycle: "1",
    dueDay: "20"
  });

  const fetchCards = async () => {
    try {
      setLoading(true);
      const data = await apiFetch(`${apiBaseUrl}/credit-cards`);
      setCards(data || []);
    } catch (error) {
      showToast("Failed to fetch cards", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCards();
  }, []);

  const [editingCardId, setEditingCardId] = useState(null);

  const handleEditCard = (card) => {
    setEditingCardId(card.id);
    setFormData({
      bankName: card.bankName,
      cardHolder: card.cardHolder,
      lastFour: card.lastFour,
      creditLimit: card.creditLimit,
      billingCycle: card.billingCycle,
      dueDay: card.dueDay
    });
    setShowAddForm(true);
  };

  const handleAddCard = async (e) => {
    e.preventDefault();
    try {
      if (editingCardId) {
        await apiFetch(`${apiBaseUrl}/credit-cards/${editingCardId}`, {
          method: "PUT",
          body: JSON.stringify(formData)
        });
        showToast("Credit card updated!", "success");
      } else {
        await apiFetch(`${apiBaseUrl}/credit-cards`, {
          method: "POST",
          body: JSON.stringify(formData)
        });
        showToast("Credit card added!", "success");
      }
      setShowAddForm(false);
      setEditingCardId(null);
      setFormData({ 
        bankName: "", 
        cardHolder: "", 
        lastFour: "", 
        creditLimit: "", 
        billingCycle: "1", 
        dueDay: "20" 
      });
      fetchCards();
    } catch (error) {
      showToast(editingCardId ? "Update failed" : "Failed to add card", "error");
    }
  };

  const handleDeleteCard = (id) => {
    triggerConfirm("Delete this credit card?", async () => {
      try {
        await apiFetch(`${apiBaseUrl}/credit-cards/${id}`, { method: "DELETE" });
        showToast("Credit card deleted", "success");
        fetchCards();
      } catch (error) {
        showToast("Deletion failed", "error");
      }
    });
  };

  const totalLimit = cards.reduce((acc, c) => acc + parseFloat(c.creditLimit || 0), 0);

  return (
    <div className="space-y-6 pb-28 animate-in slide-in-from-bottom-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="p-2 bg-white/5 rounded-xl hover:bg-white/10 transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-white" />
          </button>
          <h1 className="text-xl font-bold text-white">Credit Cards</h1>
        </div>
        {!loading && cards.length > 0 && (
          <div className="text-right">
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Total Limit</p>
            <p className="text-lg font-black text-emerald-400">{formatIndianCompact(totalLimit)}</p>
          </div>
        )}
      </div>

      {/* Add Card Button / Form Toggle */}
      <AnimatePresence mode="wait">
        {!showAddForm ? (
          <motion.button
            key="add-btn"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowAddForm(true)}
            className="w-full p-6 bg-gradient-to-br from-purple-600/20 to-pink-600/20 border border-purple-500/30 rounded-[2rem] flex items-center justify-center gap-3 text-purple-400 font-bold"
          >
            <Plus className="w-5 h-5" />
            Add New Credit Card
          </motion.button>
        ) : (
          <motion.div 
            key="add-form"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white/5 backdrop-blur-xl p-6 rounded-[2.5rem] border border-white/10 shadow-2xl"
          >
            <div className="flex justify-between items-center mb-6">
               <h3 className="text-lg font-bold text-white">Credit Card Setup</h3>
               <button onClick={() => setShowAddForm(false)} className="text-slate-500 hover:text-white text-sm">Cancel</button>
            </div>
            
            <form onSubmit={handleAddCard} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Bank Name</label>
                  <input 
                    type="text"
                    required
                    value={formData.bankName}
                    onChange={e => setFormData({...formData, bankName: e.target.value})}
                    placeholder="SBI / ICICI"
                    className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-purple-500/50 transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Last 4 Digits</label>
                  <input 
                    type="text"
                    required
                    maxLength={4}
                    pattern="\d{4}"
                    value={formData.lastFour}
                    onChange={e => setFormData({...formData, lastFour: e.target.value.replace(/\D/g, '')})}
                    placeholder="4444"
                    className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-purple-500/50 transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Credit Limit</label>
                <input 
                  type="number"
                  required
                  value={formData.creditLimit}
                  onChange={e => setFormData({...formData, creditLimit: e.target.value})}
                  placeholder="e.g. 150000"
                  className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-purple-500/50 transition-colors font-bold"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Bill Cycle (Day)</label>
                  <input 
                    type="number"
                    min="1" max="31"
                    required
                    value={formData.billingCycle}
                    onChange={e => setFormData({...formData, billingCycle: e.target.value})}
                    className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-purple-500/50 transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Due Day</label>
                  <input 
                    type="number"
                    min="1" max="31"
                    required
                    value={formData.dueDay}
                    onChange={e => setFormData({...formData, dueDay: e.target.value})}
                    className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-purple-500/50 transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Card Holder</label>
                <input 
                  type="text"
                  required
                  value={formData.cardHolder}
                  onChange={e => setFormData({...formData, cardHolder: e.target.value})}
                  placeholder="ROHIN VENGATESH"
                  className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-purple-500/50 transition-colors"
                />
              </div>

              <button 
                type="submit"
                className="w-full bg-purple-600 hover:bg-purple-500 text-white py-4 rounded-2xl font-bold shadow-lg shadow-purple-900/20 active:scale-95 transition-all mt-4"
              >
                Save Credit Card
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Cards List */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest px-2">Credit Portfolio</h3>
        
        {loading ? (
          <div className="py-12 flex justify-center">
            <div className="w-8 h-8 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
          </div>
        ) : cards.length === 0 ? (
          <div className="bg-white/5 border border-dashed border-white/10 p-12 rounded-[2.5rem] text-center">
            <CardIcon className="w-12 h-12 text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 text-sm">No credit cards linked.<br/>Add your cards to manage limits.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {cards.map((card, idx) => (
              <motion.div 
                key={card.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                layout
                className="group relative bg-gradient-to-br from-slate-900 via-indigo-950/20 to-slate-900 border border-white/10 p-6 rounded-[2.5rem] overflow-hidden"
              >
                {/* Visual Card Elements */}
                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                   <TrendingUp className="w-24 h-24 text-purple-500" />
                </div>

                <div className="flex justify-between items-start mb-8 relative z-10">
                  <div className="flex items-center gap-3">
                    <div className="p-3 bg-white/5 rounded-2xl">
                      <Zap className="w-5 h-5 text-yellow-500 fill-yellow-500/20" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-1">{card.bankName}</p>
                      <h4 className="text-lg font-black text-white italic tracking-tighter">PLATINUM</h4>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => handleEditCard(card)}
                      className="p-3 bg-purple-500/10 text-purple-400 rounded-xl hover:bg-purple-500/20 transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => handleDeleteCard(card.id)}
                      className="p-3 bg-rose-500/10 text-rose-500 rounded-xl hover:bg-rose-500/20 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-4 mb-8 relative z-10">
                  <div className="flex gap-1.5 items-center">
                    <div className="w-2.5 h-1.5 rounded-sm bg-yellow-500/50" />
                    {[1,2,3].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-600" />)}
                  </div>
                  <div className="flex gap-1.5 items-center">
                    {[1,2,3,4].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-600" />)}
                  </div>
                  <div className="flex gap-1.5 items-center">
                    {[1,2,3,4].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-600" />)}
                  </div>
                  <span className="text-xl font-mono text-white tracking-widest leading-none">{card.lastFour}</span>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-6 relative z-10">
                   <div className="p-4 bg-white/5 rounded-2xl border border-white/5">
                      <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Total Limit</p>
                      <p className="text-lg font-black text-emerald-400 truncate">{formatIndianCompact(card.creditLimit)}</p>
                   </div>
                   <div className="p-4 bg-white/5 rounded-2xl border border-white/5">
                      <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Due Cycle</p>
                      <p className="text-lg font-black text-white">{card.billingCycle} / {card.dueDay}</p>
                   </div>
                </div>

                <div className="flex justify-between items-center relative z-10 pt-2 border-t border-white/5">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-500" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Active Protection</span>
                  </div>
                  <p className="text-xs font-bold text-white uppercase opacity-60 tracking-widest">{card.cardHolder}</p>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CreditCardsPage;
