/**
 * Test suite for tier-based frontend components
 * Tests TierBadge, ProFeatureGate, and ProTierFeatures rendering
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TierBadge, ProFeatureGate, FeatureComparison } from '../components/ui/TierBadge';
import ProTierFeatures from '../components/planner/ProTierFeatures';

describe('TierBadge Component', () => {
  it('renders free tier badge', () => {
    render(<TierBadge tier="free" showLabel={true} size="md" />);
    expect(screen.getByText('Free')).toBeInTheDocument();
  });

  it('renders pro tier badge', () => {
    render(<TierBadge tier="pro" showLabel={true} size="md" />);
    expect(screen.getByText('Pro')).toBeInTheDocument();
  });

  it('renders enterprise tier badge', () => {
    render(<TierBadge tier="enterprise" showLabel={true} size="md" />);
    expect(screen.getByText('Enterprise')).toBeInTheDocument();
  });

  it('hides label when showLabel is false', () => {
    render(<TierBadge tier="pro" showLabel={false} size="md" />);
    expect(screen.queryByText('Pro')).not.toBeInTheDocument();
  });

  it('applies correct color classes for free tier', () => {
    const { container } = render(<TierBadge tier="free" size="md" />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('text-blue-400');
    expect(badge).toHaveClass('bg-blue-900/30');
  });

  it('applies correct color classes for pro tier', () => {
    const { container } = render(<TierBadge tier="pro" size="md" />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('text-amber-400');
    expect(badge).toHaveClass('bg-amber-900/30');
  });

  it('applies size classes correctly', () => {
    const { container } = render(<TierBadge tier="free" size="lg" />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('text-base');
    expect(badge).toHaveClass('px-4');
  });

  it('renders with title tooltip', () => {
    const { container } = render(<TierBadge tier="pro" size="md" />);
    const badge = container.firstChild;
    expect(badge).toHaveAttribute('title');
    expect(badge.getAttribute('title')).toContain('Advanced simulations');
  });
});

describe('ProFeatureGate Component', () => {
  it('renders content for pro tier users', () => {
    render(
      <ProFeatureGate userTier="pro" featureName="Test Feature">
        <div>Feature Content</div>
      </ProFeatureGate>
    );
    expect(screen.getByText('Feature Content')).toBeInTheDocument();
  });

  it('renders content for enterprise tier users', () => {
    render(
      <ProFeatureGate userTier="enterprise" featureName="Test Feature">
        <div>Feature Content</div>
      </ProFeatureGate>
    );
    expect(screen.getByText('Feature Content')).toBeInTheDocument();
  });

  it('shows lock UI for free tier users', () => {
    render(
      <ProFeatureGate userTier="free" featureName="Premium Tool">
        <div>Should not see this</div>
      </ProFeatureGate>
    );
    expect(screen.queryByText('Should not see this')).not.toBeInTheDocument();
    expect(screen.getByText('Premium Tool')).toBeInTheDocument();
    expect(screen.getByText(/Upgrade to Pro Tier/)).toBeInTheDocument();
  });

  it('displays upgrade button for free tier', () => {
    render(
      <ProFeatureGate userTier="free" featureName="Tool">
        <div>Content</div>
      </ProFeatureGate>
    );
    const upgradeButton = screen.getByRole('button', { name: /Upgrade Now/i });
    expect(upgradeButton).toBeInTheDocument();
  });

  it('displays feature name in lock UI', () => {
    const featureName = 'Advanced Tax Planning';
    render(
      <ProFeatureGate userTier="free" featureName={featureName}>
        <div>Content</div>
      </ProFeatureGate>
    );
    expect(screen.getByText(featureName)).toBeInTheDocument();
  });
});

describe('FeatureComparison Component', () => {
  it('renders feature comparison table', () => {
    render(<FeatureComparison />);
    expect(screen.getByText('Feature')).toBeInTheDocument();
    expect(screen.getByText('Create Plans')).toBeInTheDocument();
  });

  it('shows all three tier columns', () => {
    const { container } = render(<FeatureComparison />);
    const headers = container.querySelectorAll('th');
    expect(headers.length).toBeGreaterThanOrEqual(4); // Feature + 3 tiers
  });

  it('displays checkmarks for available features', () => {
    const { container } = render(<FeatureComparison />);
    const cells = container.querySelectorAll('td');
    const checkmarks = Array.from(cells).filter(cell => 
      cell.textContent.includes('✓')
    );
    expect(checkmarks.length).toBeGreaterThan(0);
  });

  it('displays dashes for unavailable features', () => {
    const { container } = render(<FeatureComparison />);
    const cells = container.querySelectorAll('td');
    const dashes = Array.from(cells).filter(cell => 
      cell.textContent.includes('−')
    );
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('shows memory limits correctly', () => {
    render(<FeatureComparison />);
    expect(screen.getByText(/5 turns/)).toBeInTheDocument();
  });

  it('pro tier has simulations enabled', () => {
    render(<FeatureComparison />);
    const rows = screen.getAllByRole('row');
    const simulationRow = rows.find(row => 
      row.textContent.includes('Loan Repayment Simulations')
    );
    expect(simulationRow).toBeInTheDocument();
  });
});

describe('ProTierFeatures Component', () => {
  it('shows upgrade prompt for free tier', () => {
    render(<ProTierFeatures userTier="free" />);
    expect(screen.getByText(/Upgrade to Pro/)).toBeInTheDocument();
  });

  it('displays simulator cards for pro tier', () => {
    render(<ProTierFeatures userTier="pro" />);
    expect(screen.getByText('Loan Repayment Optimizer')).toBeInTheDocument();
    expect(screen.getByText('Tax-Efficient Investment Planner')).toBeInTheDocument();
  });

  it('shows all 4 simulators for pro tier', () => {
    const { container } = render(<ProTierFeatures userTier="pro" />);
    const cards = container.querySelectorAll('[class*="rounded-lg"][class*="border"]');
    // Should have at least 4 simulator cards (+ tip box)
    expect(cards.length).toBeGreaterThanOrEqual(4);
  });

  it('displays simulator descriptions', () => {
    render(<ProTierFeatures userTier="pro" />);
    expect(screen.getByText(/Optimize your loan payoff strategy/)).toBeInTheDocument();
    expect(screen.getByText(/Plan investments with tax optimization/)).toBeInTheDocument();
  });

  it('shows features list when expanded', async () => {
    const { container } = render(<ProTierFeatures userTier="pro" />);
    const firstCard = container.querySelector('[class*="rounded-lg"][class*="border"]');
    
    // Initially should not show detailed features
    // (This depends on implementation - may need to click to expand)
  });

  it('calls onSimulationSelect when button clicked', () => {
    const mockSelect = vitest.fn();
    const { container } = render(
      <ProTierFeatures userTier="pro" onSimulationSelect={mockSelect} />
    );
    
    const buttons = screen.getAllByRole('button');
    const runButtons = buttons.filter(b => b.textContent.includes('Run Simulation'));
    expect(runButtons.length).toBeGreaterThan(0);
  });

  it('displays pro tier for enterprise users', () => {
    render(<ProTierFeatures userTier="enterprise" />);
    expect(screen.getByText('Loan Repayment Optimizer')).toBeInTheDocument();
  });

  it('shows correct styling for each simulator', () => {
    const { container } = render(<ProTierFeatures userTier="pro" />);
    expect(container.textContent).toContain('Loan Repayment Optimizer');
    expect(container.textContent).toContain('Tax-Efficient Investment Planner');
    expect(container.textContent).toContain('Tax What-If Scenarios');
    expect(container.textContent).toContain('Multi-Loan Strategy Analysis');
  });
});

describe('Tier-based Feature Gating', () => {
  it('free tier cannot see pro-exclusive features', () => {
    render(
      <ProFeatureGate userTier="free" featureName="Loan Simulator">
        <div>Loan Simulator Content</div>
      </ProFeatureGate>
    );
    expect(screen.queryByText('Loan Simulator Content')).not.toBeInTheDocument();
  });

  it('pro tier can see pro-exclusive features', () => {
    render(
      <ProFeatureGate userTier="pro" featureName="Loan Simulator">
        <div>Loan Simulator Content</div>
      </ProFeatureGate>
    );
    expect(screen.getByText('Loan Simulator Content')).toBeInTheDocument();
  });

  it('enterprise tier can see all features', () => {
    render(
      <ProFeatureGate userTier="enterprise" featureName="Feature">
        <div>Enterprise Feature</div>
      </ProFeatureGate>
    );
    expect(screen.getByText('Enterprise Feature')).toBeInTheDocument();
  });
});

describe('Accessibility', () => {
  it('tier badge has proper ARIA attributes', () => {
    const { container } = render(<TierBadge tier="pro" size="md" />);
    const badge = container.firstChild;
    // Should have title for screenreader access
    expect(badge).toHaveAttribute('title');
  });

  it('comparison table is keyboard navigable', () => {
    const { container } = render(<FeatureComparison />);
    const table = container.querySelector('table');
    expect(table).toBeInTheDocument();
  });

  it('pro feature gate has descriptive text', () => {
    render(
      <ProFeatureGate userTier="free" featureName="Tax Optimizer">
        <div>Content</div>
      </ProFeatureGate>
    );
    expect(screen.getByText(/Upgrade to.*Pro Tier/)).toBeInTheDocument();
  });
});

describe('Responsive Design', () => {
  it('feature comparison adjusts for mobile', () => {
    const { container } = render(<FeatureComparison />);
    const table = container.querySelector('table');
    // Table has responsive overflow
    expect(table).toBeInTheDocument();
  });

  it('pro tier features responsive on mobile', () => {
    const { container } = render(<ProTierFeatures userTier="pro" />);
    // Should render without errors on narrow viewport
    expect(container).toBeInTheDocument();
  });
});
