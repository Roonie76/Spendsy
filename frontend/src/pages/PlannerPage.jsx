import React, { useState, useEffect, useCallback, useMemo } from 'react';
import PlannerHeader from '../components/planner/PlannerHeader';
import PlanCard from '../components/planner/PlanCard';
import CreatePlanModal from '../components/planner/CreatePlanModal';
import PlanDetailsDrawer from '../components/planner/PlanDetailsDrawer';
import AIRecommendations from '../components/planner/AIRecommendations';
import ProTierFeatures from '../components/planner/ProTierFeatures';
import { Filter, Archive, Search } from 'lucide-react';
import { financeApi } from '../api';

export default function PlannerPage({ user, theme }) {
  const [plans, setPlans] = useState([]);
  const [filterType, setFilterType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const fetchPlans = useCallback(async () => {
    setIsLoading(true);
    try {
      const resp = await financeApi.plans();
      const data = resp?.data || resp;
      setPlans(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to fetch plans:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  const filteredPlans = plans.filter(p => {
    const matchesFilter = filterType === 'all' || p.source === filterType;
    const matchesSearch = p.title.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const handleCreatePlan = async (newPlan) => {
    try {
      await financeApi.addPlan(newPlan);
      fetchPlans();
      setIsModalOpen(false);
    } catch (err) {
      console.error("Failed to create plan:", err);
    }
  };

  const handleAdjustPlan = async (uid, adjustment) => {
    try {
      await financeApi.updatePlan(uid, adjustment);
      fetchPlans();
      setSelectedPlan(null);
    } catch (err) {
      console.error("Failed to update plan:", err);
    }
  };

  const handleDeletePlan = async (uid) => {
    try {
      await financeApi.deletePlan(uid);
      fetchPlans();
      setSelectedPlan(null);
    } catch (err) {
      console.error("Failed to delete plan:", err);
    }
  };

  const recommendations = useMemo(() => {
    const recs = [];
    const activePlans = plans.filter(p => p.status !== "completed" && p.status !== "cancelled");

    // Suggest increasing savings for plans behind schedule
    for (const p of activePlans) {
      if (p.deadline && p.target_amount && p.current_saved != null) {
        const remaining = Number(p.target_amount) - Number(p.current_saved || 0);
        const daysLeft = Math.max(1, Math.ceil((new Date(p.deadline) - new Date()) / 86400000));
        const neededDaily = remaining / daysLeft;
        const currentDaily = Number(p.daily_saving || 0);
        if (neededDaily > currentDaily * 1.2 && remaining > 0) {
          const extra = Math.ceil(neededDaily - currentDaily);
          recs.push({ text: `Increase daily saving on "${p.title}" by ₹${extra} to stay on track.`, planUid: p.uid });
        }
      }
    }

    // Suggest a new plan if fewer than 2 active
    if (activePlans.length < 2) {
      recs.push({ text: "You have capacity for a new savings plan. Consider starting an investment or emergency fund goal." });
    }

    return recs.length > 0 ? recs : [{ text: "All plans are on track. Keep it up!" }];
  }, [plans]);

  return (
    <div className="min-h-screen bg-[#060b15] pb-20 pt-24 px-4 md:px-8 lg:px-12 text-slate-200">
      <div className="mx-auto max-w-7xl">
        <PlannerHeader 
          totalPlans={plans.length} 
          monthlyCommitment={plans.reduce((acc, p) => acc + Number(p.monthly_saving), 0)}
          successRate={85}
          aiInfluenceScore={62}
          onCreateClick={() => setIsModalOpen(true)}
        />

        <div className="flex flex-col gap-8 lg:flex-row">
          <div className="flex-1">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <div className="flex gap-2 rounded-2xl bg-white/5 p-1 border border-white/5">
                {['all', 'ai', 'manual'].map(type => (
                  <button
                    key={type}
                    onClick={() => setFilterType(type)}
                    className={`px-4 py-2 text-xs font-bold rounded-xl transition-all ${filterType === type ? 'bg-white/10 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                  >
                    {type.toUpperCase()}
                  </button>
                ))}
              </div>
              
              <div className="relative w-full max-w-xs md:w-auto">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input 
                  type="text"
                  placeholder="Search plans..."
                  className="w-full rounded-2xl border border-white/10 bg-white/5 py-2 pl-10 pr-4 text-sm text-white outline-none focus:border-cyan-500 lg:w-64 placeholder:text-slate-600 shadow-inner"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {isLoading ? (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                {[1, 2, 3, 4].map(n => (
                  <div key={n} className="h-48 animate-pulse rounded-3xl bg-white/5 border border-white/10 shadow-lg" />
                ))}
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  {filteredPlans.map(plan => (
                    <PlanCard key={plan.id} plan={plan} onClick={setSelectedPlan} />
                  ))}
                </div>
                
                {filteredPlans.length === 0 && (
                  <div className="flex h-64 flex-col items-center justify-center rounded-3xl border border-dashed border-white/10 bg-white/[0.01]">
                    <p className="text-slate-500 font-medium">No plans found matching your criteria</p>
                  </div>
                )}

                <div className="mt-12">
                  <div className="mb-6 flex items-center gap-3 text-slate-500">
                    <Archive className="h-5 w-5" />
                    <h3 className="font-bold uppercase tracking-widest text-sm">Archived Plans</h3>
                  </div>
                  <div className="rounded-3xl border border-white/5 bg-white/[0.02] p-6 sm:p-12 text-center backdrop-blur-sm">
                    <p className="text-sm text-slate-600 font-medium">Your completed and cancelled plans will be safely stored here.</p>
                  </div>
                </div>
              </>
            )}
          </div>

          <aside className="w-full lg:w-80">
            <AIRecommendations
              recommendations={recommendations}
              onApply={(rec) => {
                if (rec.planUid) {
                  // Open the existing plan for adjustment
                  const plan = plans.find(p => p.uid === rec.planUid);
                  if (plan) setSelectedPlan(plan);
                } else {
                  // Open create modal for a new plan
                  setIsModalOpen(true);
                }
              }}
            />
            
            {/* Pro Tier Features Section */}
            <div className="mt-8">
              <ProTierFeatures 
                userTier={user?.tier || "free"}
                onSimulationSelect={(simType) => {
                  console.log("Simulation selected:", simType);
                  // TODO: Handle simulation selection - could open a modal or navigate
                }}
              />
            </div>
          </aside>
        </div>
      </div>

      <CreatePlanModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        onCreate={handleCreatePlan}
      />

      <PlanDetailsDrawer 
        plan={selectedPlan} 
        onClose={() => setSelectedPlan(null)} 
        onAdjust={handleAdjustPlan}
        onDelete={handleDeletePlan}
      />
    </div>
  );
}
