import { motion } from 'framer-motion';
import { Zap, Clock, AlertCircle } from 'lucide-react';

export default function DemoModeInfo() {
  return (
    <section className="mb-12">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="mb-6"
      >
        <h2 className="text-3xl font-bold text-gradient-purple mb-2">Demo Mode</h2>
        <p className="text-text-muted">
          Compressed timing for rapid system demonstration (60× faster than production)
        </p>
      </motion.div>
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.6 }}
        className="glass-card p-8"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Production Mode */}
          <div className="glass-card p-6 border-2 border-accent-purple/30">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
                <Clock className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-text-primary">Production Mode</h3>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-text-muted">Worker Agents</span>
                <span className="text-lg font-bold text-accent-purple font-mono">15 minutes</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-text-muted">Orchestrator Agent</span>
                <span className="text-lg font-bold text-accent-purple font-mono">60 minutes</span>
              </div>
              <div className="mt-4 pt-4 border-t border-white/10">
                <p className="text-xs text-text-muted">
                  Standard timing for real-world deployment. Full cycle takes ~1 hour to complete.
                </p>
              </div>
            </div>
          </div>

          {/* Demo Mode */}
          <div className="glass-card p-6 border-2 border-green-400/30 relative overflow-hidden">
            <div className="absolute top-2 right-2">
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/20 border border-green-500/30 text-green-400 text-xs font-bold">
                <Zap className="w-3 h-3" />
                60× FASTER
              </span>
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-green-600 to-green-800 flex items-center justify-center">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-text-primary">Demo Mode</h3>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-text-muted">Worker Agents</span>
                <span className="text-lg font-bold text-green-400 font-mono">15 seconds</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-text-muted">Orchestrator Agent</span>
                <span className="text-lg font-bold text-green-400 font-mono">60 seconds</span>
              </div>
              <div className="mt-4 pt-4 border-t border-white/10">
                <p className="text-xs text-text-muted">
                  Accelerated timing for demonstrations. Full system cycle completes in ~5-10 minutes.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* How to Enable */}
        <div className="mt-8 glass-card p-6 border border-accent-orange/30">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-accent-orange mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="text-sm font-bold text-text-primary mb-2">How to Enable Demo Mode</h4>
              <div className="space-y-2 text-xs font-mono text-text-muted">
                <div className="glass-card p-3 border border-white/10">
                  <span className="text-accent-purple">Method 1:</span> python run_demo.py
                </div>
                <div className="glass-card p-3 border border-white/10">
                  <span className="text-accent-purple">Method 2:</span> DEMO_MODE=true python main.py
                </div>
                <div className="glass-card p-3 border border-white/10">
                  <span className="text-accent-purple">Method 3:</span> Add <span className="text-accent-pink">DEMO_MODE=true</span> to .env file
                </div>
              </div>
              <p className="text-xs text-text-muted mt-3">
                All safety checks remain active in demo mode (margin floor, budget guard, rate limits).
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
