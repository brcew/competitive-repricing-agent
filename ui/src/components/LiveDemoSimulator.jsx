import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Pause, RotateCcw, CheckCircle, XCircle, Clock, Zap } from 'lucide-react';

// Simulated decision stream for demo
const demoDecisions = [
  {
    id: 1,
    time: 15,
    sku: 'LAP-0042',
    ourPrice: 1249.99,
    competitorPrice: 1199.99,
    action: 'MATCH',
    newPrice: 1199.99,
    margin: 14.2,
    passed: true,
    reasoning: 'Competitor undercut by $50. Matching to maintain competitiveness.'
  },
  {
    id: 2,
    time: 30,
    sku: 'MOU-0156',
    ourPrice: 45.99,
    competitorPrice: 42.99,
    action: 'UNDERCUT_50',
    newPrice: 42.49,
    margin: 13.8,
    passed: true,
    reasoning: 'Active price war detected. Undercutting by $0.50 to capture market share.'
  },
  {
    id: 3,
    time: 45,
    sku: 'KEY-0089',
    ourPrice: 89.99,
    competitorPrice: 79.99,
    action: 'HOLD',
    newPrice: null,
    margin: 11.3,
    passed: false,
    reasoning: '[OVERRIDDEN] LLM suggested MATCH at $79.99, but would violate 12% margin floor (11.3%). System enforced HOLD.'
  },
  {
    id: 4,
    time: 60,
    sku: 'MON-0234',
    ourPrice: 449.99,
    competitorPrice: 439.99,
    action: 'HOLD',
    newPrice: null,
    margin: 18.5,
    passed: true,
    reasoning: 'Price gap only 2.2% - below 5% threshold. Maintaining current price.'
  },
  {
    id: 5,
    time: 75,
    sku: 'HDD-0567',
    ourPrice: 129.99,
    competitorPrice: 124.99,
    action: 'MATCH',
    newPrice: 124.99,
    margin: 15.7,
    passed: true,
    reasoning: 'Competitor price drop detected. Matching to stay competitive.'
  },
  {
    id: 6,
    time: 90,
    sku: 'RAM-0891',
    ourPrice: 79.99,
    competitorPrice: 69.99,
    action: 'HOLD',
    newPrice: null,
    margin: 10.8,
    passed: false,
    reasoning: '[OVERRIDDEN] LLM suggested MATCH at $69.99, but margin check rejected (10.8% < 12%). Safety enforced HOLD.'
  }
];

function DecisionCard({ decision }) {
  const isOverridden = decision.reasoning.startsWith('[OVERRIDDEN]');
  
  const actionColors = {
    MATCH: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
    UNDERCUT_50: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
    HOLD: 'text-orange-400 bg-orange-400/10 border-orange-400/30'
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 20, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className={`glass-card p-4 mb-3 ${isOverridden ? 'border-red-500/50' : 'border-white/10'}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className="font-mono font-bold text-accent-purple">{decision.sku}</span>
          <span className={`px-2 py-1 rounded-full text-xs font-bold border ${actionColors[decision.action]}`}>
            {decision.action}
          </span>
          {decision.passed ? (
            <CheckCircle className="w-5 h-5 text-green-400" />
          ) : (
            <XCircle className="w-5 h-5 text-red-400" />
          )}
        </div>
        <span className="text-xs text-text-muted font-mono">{decision.time}s</span>
      </div>
      
      <div className="grid grid-cols-3 gap-3 mb-2 text-sm">
        <div>
          <span className="text-text-muted text-xs">Our Price</span>
          <div className="font-mono text-text-primary">${decision.ourPrice.toFixed(2)}</div>
        </div>
        <div>
          <span className="text-text-muted text-xs">Competitor</span>
          <div className="font-mono text-text-primary">${decision.competitorPrice.toFixed(2)}</div>
        </div>
        <div>
          <span className="text-text-muted text-xs">Margin</span>
          <div className={`font-mono font-bold ${decision.margin < 12 ? 'text-red-400' : 'text-green-400'}`}>
            {decision.margin.toFixed(1)}%
          </div>
        </div>
      </div>
      
      <p className={`text-xs ${isOverridden ? 'text-red-400' : 'text-text-muted'}`}>
        {decision.reasoning}
      </p>
    </motion.div>
  );
}

export default function LiveDemoSimulator() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [visibleDecisions, setVisibleDecisions] = useState([]);
  const [orchestratorRun, setOrchestratorRun] = useState(false);

  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setCurrentTime(prev => {
        const newTime = prev + 1;
        
        // Check if orchestrator should run (every 60 seconds)
        if (newTime % 60 === 0) {
          setOrchestratorRun(true);
          setTimeout(() => setOrchestratorRun(false), 3000);
        }
        
        // Check for new decisions
        const newDecision = demoDecisions.find(d => d.time === newTime);
        if (newDecision) {
          setVisibleDecisions(prev => [newDecision, ...prev].slice(0, 4)); // Keep last 4
        }
        
        // Reset after 90 seconds (or loop)
        if (newTime >= 90) {
          return 0;
        }
        
        return newTime;
      });
    }, 1000); // Real-time seconds

    return () => clearInterval(interval);
  }, [isRunning]);

  const handleStart = () => {
    setIsRunning(true);
  };

  const handlePause = () => {
    setIsRunning(false);
  };

  const handleReset = () => {
    setIsRunning(false);
    setCurrentTime(0);
    setVisibleDecisions([]);
    setOrchestratorRun(false);
  };

  return (
    <section className="mb-12">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="mb-6"
      >
        <h2 className="text-3xl font-bold text-gradient-purple mb-2">Live Demo Simulator</h2>
        <p className="text-text-muted flex items-center gap-2">
          Experience the system in action with accelerated demo mode timing
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/10 border border-green-500/30 text-green-400 text-xs font-bold">
            <Zap className="w-3 h-3" />
            60× FASTER
          </span>
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Control Panel */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="glass-card p-6"
        >
          <h3 className="text-xl font-bold text-text-primary mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-accent-purple" />
            Demo Controls
          </h3>

          {/* Timer Display */}
          <div className="glass-card p-6 mb-6 text-center border-2 border-accent-purple/30">
            <div className="text-5xl font-mono font-bold text-accent-purple mb-2">
              {Math.floor(currentTime / 60)}:{String(currentTime % 60).padStart(2, '0')}
            </div>
            <div className="text-sm text-text-muted">
              {isRunning ? 'Demo Running...' : 'Demo Paused'}
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex gap-3 mb-6">
            {!isRunning ? (
              <button
                onClick={handleStart}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 text-white font-semibold transition-all hover:scale-105"
              >
                <Play className="w-5 h-5" />
                Start Demo
              </button>
            ) : (
              <button
                onClick={handlePause}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-500 hover:to-orange-600 text-white font-semibold transition-all hover:scale-105"
              >
                <Pause className="w-5 h-5" />
                Pause
              </button>
            )}
            
            <button
              onClick={handleReset}
              className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg glass-card-hover font-semibold"
            >
              <RotateCcw className="w-5 h-5" />
              Reset
            </button>
          </div>

          {/* Status Indicators */}
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 glass-card border border-white/10">
              <span className="text-sm text-text-muted">Worker Interval</span>
              <span className="text-sm font-mono font-bold text-green-400">15 seconds</span>
            </div>
            <div className="flex items-center justify-between p-3 glass-card border border-white/10">
              <span className="text-sm text-text-muted">Orchestrator Interval</span>
              <span className="text-sm font-mono font-bold text-purple-400">60 seconds</span>
            </div>
            <div className="flex items-center justify-between p-3 glass-card border border-white/10">
              <span className="text-sm text-text-muted">Next Worker Run</span>
              <span className="text-sm font-mono font-bold text-text-primary">
                {isRunning ? `${15 - (currentTime % 15)}s` : '--'}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 glass-card border border-white/10">
              <span className="text-sm text-text-muted">Next Orchestrator</span>
              <span className="text-sm font-mono font-bold text-text-primary">
                {isRunning ? `${60 - (currentTime % 60)}s` : '--'}
              </span>
            </div>
          </div>

          {/* Orchestrator Alert */}
          <AnimatePresence>
            {orchestratorRun && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mt-4 p-4 rounded-lg bg-purple-600/20 border-2 border-purple-500/50 text-center"
              >
                <div className="text-purple-400 font-bold mb-1">🎯 Orchestrator Running</div>
                <div className="text-xs text-text-muted">Analyzing watchlist and market conditions...</div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Live Decision Feed */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="glass-card p-6"
        >
          <h3 className="text-xl font-bold text-text-primary mb-4">Live Decision Stream</h3>
          
          {visibleDecisions.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <Clock className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>Click "Start Demo" to see live pricing decisions</p>
            </div>
          ) : (
            <div className="space-y-3">
              <AnimatePresence mode="popLayout">
                {visibleDecisions.map((decision) => (
                  <DecisionCard key={`${decision.id}-${decision.time}`} decision={decision} />
                ))}
              </AnimatePresence>
            </div>
          )}

          {/* Stats Counter */}
          {isRunning && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-4 grid grid-cols-3 gap-3 text-center"
            >
              <div className="glass-card p-3">
                <div className="text-2xl font-bold text-accent-purple">{visibleDecisions.length}</div>
                <div className="text-xs text-text-muted">Decisions</div>
              </div>
              <div className="glass-card p-3">
                <div className="text-2xl font-bold text-green-400">
                  {visibleDecisions.filter(d => d.passed).length}
                </div>
                <div className="text-xs text-text-muted">Passed</div>
              </div>
              <div className="glass-card p-3">
                <div className="text-2xl font-bold text-red-400">
                  {visibleDecisions.filter(d => !d.passed).length}
                </div>
                <div className="text-xs text-text-muted">Overridden</div>
              </div>
            </motion.div>
          )}
        </motion.div>
      </div>

      {/* Instructions */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5, duration: 0.6 }}
        className="mt-6 glass-card p-6 border border-accent-orange/30"
      >
        <h4 className="text-sm font-bold text-text-primary mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-accent-orange" />
          How to Run Real Demo Mode
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="glass-card p-3 border border-white/10">
            <div className="text-accent-purple font-bold mb-1">Method 1: Quick Start</div>
            <div className="text-text-muted">python run_demo.py</div>
          </div>
          <div className="glass-card p-3 border border-white/10">
            <div className="text-accent-purple font-bold mb-1">Method 2: Environment</div>
            <div className="text-text-muted">set DEMO_MODE=true & python main.py</div>
          </div>
          <div className="glass-card p-3 border border-white/10">
            <div className="text-accent-purple font-bold mb-1">Method 3: Config File</div>
            <div className="text-text-muted">Add DEMO_MODE=true to .env</div>
          </div>
        </div>
        <p className="text-xs text-text-muted mt-3 text-center">
          This web simulator shows accelerated visualization. For actual system demo, use the commands above.
        </p>
      </motion.div>
    </section>
  );
}
