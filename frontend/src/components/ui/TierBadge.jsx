import React from "react";
import { Crown, Zap, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

/**
 * TierBadge - Displays user's subscription tier with visual styling
 * @param {string} tier - "free", "pro", or "enterprise"
 * @param {boolean} showLabel - Show text label alongside icon
 * @param {string} size - "sm", "md", "lg"
 */
export function TierBadge({ tier = "free", showLabel = true, size = "md" }) {
  const tierConfig = {
    free: {
      icon: Zap,
      label: "Free",
      color: "text-blue-400",
      bgColor: "bg-blue-900/30",
      borderColor: "border-blue-700",
      displayName: "Free Tier",
      description: "Basic financial planning"
    },
    pro: {
      icon: Crown,
      label: "Pro",
      color: "text-amber-400",
      bgColor: "bg-amber-900/30",
      borderColor: "border-amber-700",
      displayName: "Pro Tier",
      description: "Advanced simulations & tax optimization"
    },
    enterprise: {
      icon: Sparkles,
      label: "Enterprise",
      color: "text-purple-400",
      bgColor: "bg-purple-900/30",
      borderColor: "border-purple-700",
      displayName: "Enterprise Tier",
      description: "Unlimited features & priority support"
    }
  };

  const config = tierConfig[tier] || tierConfig.free;
  const IconComponent = config.icon;

  const sizeClasses = {
    sm: "px-2 py-1 text-xs gap-1",
    md: "px-3 py-2 text-sm gap-2",
    lg: "px-4 py-3 text-base gap-2"
  };

  const iconSizes = {
    sm: 14,
    md: 16,
    lg: 20
  };

  return (
    <motion.div
      className={`inline-flex items-center rounded-lg border ${config.bgColor} ${config.borderColor} ${sizeClasses[size]}`}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.98 }}
      title={config.description}
    >
      <IconComponent size={iconSizes[size]} className={config.color} />
      {showLabel && <span className={`font-semibold ${config.color}`}>{config.label}</span>}
    </motion.div>
  );
}

/**
 * ProFeatureGate - Conditionally render Pro-tier features with lock UI
 * @param {string} userTier - User's subscription tier
 * @param {React.ReactNode} children - Content to show for Pro users
 * @param {string} featureName - Name of the feature being gated
 */
export function ProFeatureGate({ userTier = "free", children, featureName = "Feature" }) {
  if (userTier === "pro" || userTier === "enterprise") {
    return <>{children}</>;
  }

  return (
    <motion.div
      className="relative rounded-lg border border-amber-700/50 bg-amber-900/20 p-6 text-center"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="space-y-3">
        <div className="flex justify-center">
          <Crown size={32} className="text-amber-400 opacity-60" />
        </div>
        <div>
          <h3 className="font-semibold text-amber-100">{featureName}</h3>
          <p className="text-sm text-amber-200/70 mt-1">
            Upgrade to <span className="font-semibold">Pro Tier</span> to unlock this feature
          </p>
        </div>
        <button className="mt-4 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-semibold transition-colors">
          Upgrade Now
        </button>
      </div>
    </motion.div>
  );
}

/**
 * FeatureComparison - Compare tiers side-by-side
 */
export function FeatureComparison() {
  const features = [
    { name: "Create Plans", free: true, pro: true, enterprise: true },
    { name: "Adjust Plans", free: true, pro: true, enterprise: true },
    { name: "Tax Regime Comparison", free: true, pro: true, enterprise: true },
    { name: "Loan Repayment Simulations", free: false, pro: true, enterprise: true },
    { name: "Tax-Efficient Investment Planning", free: false, pro: true, enterprise: true },
    { name: "Autonomous Actions", free: false, pro: true, enterprise: true },
    { name: "Conversation Memory", free: "5 turns", pro: true, enterprise: true },
    { name: "What-if Tax Scenarios", free: false, pro: true, enterprise: true },
    { name: "Multi-Loan Strategy Analysis", free: false, pro: true, enterprise: true },
    { name: "Priority Support", free: false, pro: false, enterprise: true },
  ];

  return (
    <motion.div className="w-full overflow-x-auto rounded-lg border border-slate-700 bg-slate-900/50">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700 bg-slate-800/50">
            <th className="px-4 py-3 text-left font-semibold">Feature</th>
            <th className="px-4 py-3 text-center font-semibold">
              <TierBadge tier="free" showLabel={true} size="sm" />
            </th>
            <th className="px-4 py-3 text-center font-semibold">
              <TierBadge tier="pro" showLabel={true} size="sm" />
            </th>
            <th className="px-4 py-3 text-center font-semibold">
              <TierBadge tier="enterprise" showLabel={true} size="sm" />
            </th>
          </tr>
        </thead>
        <tbody>
          {features.map((feature, idx) => (
            <tr key={idx} className="border-b border-slate-700/50">
              <td className="px-4 py-3 font-medium text-slate-200">{feature.name}</td>
              <td className="px-4 py-3 text-center">
                {feature.free === true ? (
                  <span className="text-green-400">✓</span>
                ) : feature.free === false ? (
                  <span className="text-slate-500">−</span>
                ) : (
                  <span className="text-blue-400 text-xs">{feature.free}</span>
                )}
              </td>
              <td className="px-4 py-3 text-center">
                {feature.pro === true ? (
                  <span className="text-green-400">✓</span>
                ) : (
                  <span className="text-slate-500">−</span>
                )}
              </td>
              <td className="px-4 py-3 text-center">
                {feature.enterprise === true ? (
                  <span className="text-green-400">✓</span>
                ) : (
                  <span className="text-slate-500">−</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
}

export default TierBadge;
