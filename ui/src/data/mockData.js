// Realistic mock data based on actual project architecture

export const stats = [
  {
    label: 'Cost Savings',
    value: '60%',
    description: 'vs single large model',
    icon: 'TrendingDown',
    color: 'text-green-400'
  },
  {
    label: 'Tests Passing',
    value: '107',
    description: '$0 test cost',
    icon: 'CheckCircle',
    color: 'text-accent-purple'
  },
  {
    label: 'Margin Floor',
    value: '12%',
    description: 'never violated',
    icon: 'Shield',
    color: 'text-accent-pink'
  },
  {
    label: 'SKUs Monitored',
    value: '800',
    description: '15 active watchlist',
    icon: 'Package',
    color: 'text-accent-orange'
  }
];

export const recentDecisions = [
  {
    id: 1,
    sku: 'LAP-0042',
    ourPrice: 1249.99,
    competitorPrice: 1199.99,
    action: 'MATCH',
    marginCheck: true,
    newPrice: 1199.99,
    margin: 14.2,
    reasoning: 'Competitor undercut by $50. Matching to maintain competitiveness while preserving 14.2% margin.'
  },
  {
    id: 2,
    sku: 'MOU-0156',
    ourPrice: 45.99,
    competitorPrice: 42.99,
    action: 'UNDERCUT_50',
    marginCheck: true,
    newPrice: 42.49,
    margin: 13.8,
    reasoning: 'Active price war detected. Undercutting by $0.50 to capture market share.'
  },
  {
    id: 3,
    sku: 'KEY-0089',
    ourPrice: 89.99,
    competitorPrice: 79.99,
    action: 'HOLD',
    marginCheck: false,
    newPrice: null,
    margin: 11.3,
    reasoning: '[OVERRIDDEN] LLM suggested MATCH at $79.99, but would violate 12% margin floor (calculated 11.3%). System enforced HOLD.'
  },
  {
    id: 4,
    sku: 'MON-0234',
    ourPrice: 449.99,
    competitorPrice: 439.99,
    action: 'HOLD',
    marginCheck: true,
    newPrice: null,
    margin: 18.5,
    reasoning: 'Price gap only 2.2% - below 5% threshold. Maintaining current price with healthy margin.'
  },
  {
    id: 5,
    sku: 'HDD-0567',
    ourPrice: 129.99,
    competitorPrice: 124.99,
    action: 'MATCH',
    marginCheck: true,
    newPrice: 124.99,
    margin: 15.7,
    reasoning: 'Competitor price drop detected. Matching to stay competitive with 15.7% margin maintained.'
  },
  {
    id: 6,
    sku: 'RAM-0891',
    ourPrice: 79.99,
    competitorPrice: 69.99,
    action: 'HOLD',
    marginCheck: false,
    newPrice: null,
    margin: 10.8,
    reasoning: '[OVERRIDDEN] LLM suggested MATCH at $69.99, but margin check rejected (would be 10.8% < 12% floor). Safety mechanism prevented unprofitable decision.'
  }
];

export const costComparisonData = [
  { period: 'Daily', twoTier: 0.0032, singleModel: 0.0078 },
  { period: 'Weekly', twoTier: 0.0224, singleModel: 0.0546 },
  { period: 'Monthly', twoTier: 0.096, singleModel: 0.234 },
  { period: 'Yearly', twoTier: 1.16, singleModel: 2.85 }
];

export const architectureFlow = {
  nodes: [
    {
      id: 'orchestrator',
      label: 'Orchestrator Agent',
      sublabel: 'llama-3.3-70b-versatile',
      description: 'Hourly • Watchlist Management',
      type: 'large'
    },
    {
      id: 'worker',
      label: 'Worker Agents',
      sublabel: 'llama-3.1-8b-instant',
      description: '15min/SKU • Pricing Decisions',
      type: 'small'
    },
    {
      id: 'safety',
      label: 'Margin Safety Checker',
      sublabel: 'Deterministic Python',
      description: '12% floor • Code enforced',
      type: 'safety'
    },
    {
      id: 'execute',
      label: 'Execute or HOLD',
      sublabel: 'Database + Audit Trail',
      description: 'Decision logged & tracked',
      type: 'result'
    }
  ],
  connections: [
    { from: 'orchestrator', to: 'worker', label: 'Watchlist (max 15 SKUs)' },
    { from: 'worker', to: 'safety', label: 'LLM suggests price' },
    { from: 'safety', to: 'execute', label: 'Code enforces constraints' }
  ]
};

export const techStack = [
  { name: 'Python 3.11', icon: 'Code2' },
  { name: 'Groq API', icon: 'Zap' },
  { name: 'Llama 3.1 8B', icon: 'Brain' },
  { name: 'Llama 3.3 70B', icon: 'BrainCircuit' },
  { name: 'SQLAlchemy', icon: 'Database' },
  { name: 'PostgreSQL', icon: 'Server' },
  { name: 'structlog', icon: 'FileText' },
  { name: 'pytest (107 tests)', icon: 'CheckSquare' },
  { name: 'Docker', icon: 'Container' },
  { name: 'asyncio', icon: 'Workflow' }
];

export const systemMetrics = {
  budgetUsed: 8420,
  budgetLimit: 14400,
  watchlistSize: 15,
  watchlistCap: 15,
  dailyCost: 0.0032,
  monthlyCost: 0.096,
  savingsPercent: 59.49,
  testsRun: 107,
  testCost: 0,
  marginViolations: 0,
  totalDecisions: 1847
};
