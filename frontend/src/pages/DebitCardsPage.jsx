import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  CreditCard as CardIcon, 
  Plus, 
  Trash2, 
  ChevronLeft, 
  ShieldCheck,
  Edit2
} from "lucide-react";
import { apiFetch } from "../api";

const DebitCardsPage = ({ 
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
    lastFour: "",
    cardHolder: "",
    expiry: ""
  });

  const fetchCards = async () => {
    try {
      setLoading(true);
      const data = await apiFetch(`${apiBaseUrl}/debit-cards`);
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
      lastFour: card.lastFour,
      cardHolder: card.cardHolder,
      expiry: card.expiry
    });
    setShowAddForm(true);
  };

  const handleAddCard = async (e) => {
    e.preventDefault();
    try {
      if (editingCardId) {
        await apiFetch(`${apiBaseUrl}/debit-cards/${editingCardId}`, {
          method: "PUT",
          body: JSON.stringify(formData)
        });
        showToast("Card updated successfully", "success");
      } else {
        await apiFetch(`${apiBaseUrl}/debit-cards`, {
          method: "POST",
          body: JSON.stringify(formData)
        });
        showToast("Card added successfully", "success");
      }
      setShowAddForm(false);
      setEditingCardId(null);
      setFormData({ bankName: "", lastFour: "", cardHolder: "", expiry: "" });
      fetchCards();
    } catch (error) {
      showToast(editingCardId ? "Update failed" : "Failed to add card", "error");
    }
  };

  const handleDeleteCard = (id) => {
    triggerConfirm("Delete this card?", async () => {
      try {
        await apiFetch(`${apiBaseUrl}/debit-cards/${id}`, { method: "DELETE" });
        showToast("Card deleted", "success");
        fetchCards();
      } catch (error) {
        showToast("Deletion failed", "error");
      }
    });
  };

  return (
    <div className="space-y-6 pb-28 animate-in slide-in-from-bottom-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-2">
        <button 
          onClick={onBack}
          className="p-2 bg-white/5 rounded-xl hover:bg-white/10 transition-colors"
        >
          <ChevronLeft className="w-5 h-5 text-white" />
        </button>
        <h1 className="text-xl font-bold text-white">Debit Cards</h1>
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
            className="w-full p-6 bg-gradient-to-br from-blue-600/20 to-indigo-600/20 border border-blue-500/30 rounded-[2rem] flex items-center justify-center gap-3 text-blue-400 font-bold"
          >
            <Plus className="w-5 h-5" />
            Add New Debit Card
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
               <h3 className="text-lg font-bold text-white">New Card Details</h3>
               <button onClick={() => setShowAddForm(false)} className="text-slate-500 hover:text-white text-sm">Cancel</button>
            </div>
            
            <form onSubmit={handleAddCard} className="space-y-4">
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Bank Name</label>
                <input 
                  type="text"
                  required
                  value={formData.bankName}
                  onChange={e => setFormData({...formData, bankName: e.target.value})}
                  placeholder="e.g. HDFC Bank"
                  className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-blue-500/50 transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Last 4 Digits</label>
                  <input 
                    type="text"
                    required
                    maxLength={4}
                    pattern="\d{4}"
                    value={formData.lastFour}
                    onChange={e => setFormData({...formData, lastFour: e.target.value.replace(/\D/g, '')})}
                    placeholder="1234"
                    className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-blue-500/50 transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Expiry (MM/YYYY)</label>
                  <input 
                    type="text"
                    required
                    maxLength={7}
                    placeholder="12/2028"
                    value={formData.expiry}
                    onChange={e => setFormData({...formData, expiry: e.target.value})}
                    className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-blue-500/50 transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-2">Card Holder Name</label>
                <input 
                  type="text"
                  required
                  value={formData.cardHolder}
                  onChange={e => setFormData({...formData, cardHolder: e.target.value})}
                  placeholder="John Doe"
                  className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white outline-none focus:border-blue-500/50 transition-colors"
                />
              </div>

              <button 
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white py-4 rounded-2xl font-bold shadow-lg shadow-blue-900/20 active:scale-95 transition-all mt-4"
              >
                Securely Save Card
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Cards List */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest px-2">Your Linked Cards</h3>
        
        {loading ? (
          <div className="py-12 flex justify-center">
            <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : cards.length === 0 ? (
          <div className="bg-white/5 border border-dashed border-white/10 p-12 rounded-[2.5rem] text-center">
            <CardIcon className="w-12 h-12 text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 text-sm">No debit cards found.<br/>Add one to start tracking.</p>
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
                className="group relative bg-gradient-to-br from-slate-900 to-slate-800 border border-white/10 p-6 rounded-[2.5rem] overflow-hidden"
              >
                {/* Visual Card Elements */}
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                   <ShieldCheck className="w-16 h-16 text-emerald-500" />
                </div>

                <div className="flex justify-between items-start mb-8 relative z-10">
                  <div>
                    <p className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-1">{card.bankName}</p>
                    <h4 className="text-lg font-bold text-white uppercase italic tracking-tighter italic">DEBIT</h4>
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => handleEditCard(card)}
                      className="p-3 bg-blue-500/10 text-blue-400 rounded-xl hover:bg-blue-500/20 transition-colors"
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

                <div className="flex items-center gap-4 mb-6 relative z-10">
                  <div className="flex gap-1.5 items-center">
                    {[1,2,3,4].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-600" />)}
                  </div>
                  <div className="flex gap-1.5 items-center">
                    {[1,2,3,4].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-600" />)}
                  </div>
                  <div className="flex gap-1.5 items-center">
                    {[1,2,3,4].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-600" />)}
                  </div>
                  <span className="text-xl font-mono text-white tracking-widest leading-none">{card.lastFour}</span>
                </div>

                <div className="flex justify-between items-end relative z-10">
                  <div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Card Holder</p>
                    <p className="text-sm font-bold text-white uppercase tracking-wider">{card.cardHolder}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Expires</p>
                    <p className="text-sm font-bold text-white font-mono">{card.expiry}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DebitCardsPage;
