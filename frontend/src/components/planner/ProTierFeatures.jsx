import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, Zap, DollarSign, Home, ChevronDown } from "lucide-react";

/**
 * ProTierFeatures - Shows Pro-tier exclusive simulation tools
 * @param {string} userTier - User's subscription tier
 * @param {function} onSimulationSelect - Callback when user selects a simulation
 */
export function ProTierFeatures({ userTier = "free", onSimulationSelect }) {
  const [expandedSimulation, setExpandedSimulation] = useState(null);

  const simulations = [
    {
      id: "loan_repayment",
      title: "Loan Repayment Optimizer",
      icon: Home,
      description: "Optimize your loan payoff strategy",
      features: [
        "Calculate extra payment impact",
        "Compare debt snowball vs debt avalanche",
        "Analyze loan consolidation savings",
        "Find optimal payoff timeline"
      ],
      benefits: "Save months and thousands in interest",
      color: "bg-blue-900/30",
      borderColor: "border-blue-700",
      accentColor: "text-blue-400"
    },
    {
      id: "tax_efficient_investment",
      title: "Tax-Efficient Investment Planner",
      icon: TrendingUp,
      description: "Plan investments with tax optimization",
      features: [
        "Smart allocation by risk profile",
        "Old vs New regime comparison",
        "SIP growth projections (post-tax)",
        "Tax benefit estimation"
      ],
      benefits: "Maximize after-tax wealth",
      color: "bg-green-900/30",
      borderColor: "border-green-700",
      accentColor: "text-green-400"
    },
    {
      id: "tax_whatif",
      title: "Tax What-If Scenarios",
      icon: Zap,
      description: "Run custom tax planning scenarios",
      features: [
        "Investment scenario analysis",
        "Tax liability simulation",
        "Regime comparison with changes",
        "Estimated annual tax savings"
      ],
      benefits: "Plan tax moves before they happen",
      color: "bg-amber-900/30",
      borderColor: "border-amber-700",
      accentColor: "text-amber-400"
    },
    {
      id: "multi_loan_strategy",
      title: "Multi-Loan Strategy Analysis",
      icon: DollarSign,
      description: "Manage multiple loans efficiently",
      features: [
        "Payoff sequence recommendations",
        "Proportional vs threshold strategies",
        "Total payoff timeline",
        "Interest savings calculation"
      ],
      benefits: "Stay debt-free faster",
      color: "bg-purple-900/30",
      borderColor: "border-purple-700",
      accentColor: "text-purple-400"
    }
  ];

  if (userTier === "free") {
    return (
      <motion.div
        className="rounded-lg border border-amber-700 bg-amber-900/20 p-6"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Zap size={24} className="text-amber-400" />
            <h3 className="text-xl font-bold text-amber-100">Pro-Tier Simulations</h3>
          </div>
          <p className="text-amber-200/70">
            Unlock advanced financial simulations to optimize your loans, investments, and tax strategy.
          </p>
          <button className="w-full px-4 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-semibold transition-colors">
            Upgrade to Pro
          </button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div className="space-y-4">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <Zap className="text-amber-400" />
          Pro Tier Simulations
        </h2>
        <p className="text-slate-400 mt-2">Run advanced financial scenarios to optimize your money</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {simulations.map((sim) => {
          const Icon = sim.icon;
          const isExpanded = expandedSimulation === sim.id;

          return (
            <motion.div
              key={sim.id}
              className={`rounded-lg border ${sim.borderColor} ${sim.color} p-4 cursor-pointer transition-all`}
              onClick={() => setExpandedSimulation(isExpanded ? null : sim.id)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1">
                  <div className={`p-2 rounded-lg bg-slate-900/50`}>
                    <Icon size={20} className={sim.accentColor} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-100">{sim.title}</h3>
                    <p className="text-sm text-slate-400 mt-1">{sim.description}</p>
                  </div>
                </div>
                <motion.div
                  animate={{ rotate: isExpanded ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ChevronDown size={20} className="text-slate-400" />
                </motion.div>
              </div>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="mt-4 pt-4 border-t border-slate-700/50"
                  >
                    <div className="space-y-3">
                      <div>
                        <h4 className="text-sm font-semibold text-slate-200 mb-2">Features:</h4>
                        <ul className="space-y-1">
                          {sim.features.map((feature, idx) => (
                            <li key={idx} className="text-sm text-slate-400 flex items-center gap-2">
                              <span className={`w-1.5 h-1.5 rounded-full ${sim.accentColor}`}></span>
                              {feature}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className="bg-slate-900/50 rounded p-2 mt-3">
                        <p className={`text-sm font-medium italic ${sim.accentColor}`}>
                          💡 {sim.benefits}
                        </p>
                      </div>
                      <button
                        onClick={() => onSimulationSelect && onSimulationSelect(sim.id)}
                        className={`w-full mt-3 px-3 py-2 rounded font-semibold text-white transition-colors ${
                          sim.color.replace("/30", "/60").replace("900", "700")
                        }`}
                      >
                        Run Simulation
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>

      <div className="mt-6 bg-slate-900/50 rounded-lg border border-slate-700 p-4">
        <p className="text-sm text-slate-400">
          💡 <span className="text-slate-300 font-semibold">Pro Tip:</span> Run TORA simulations to get AI-powered recommendations combined with these analysis tools.
        </p>
      </div>
    </motion.div>
  );
}

export default ProTierFeatures;
