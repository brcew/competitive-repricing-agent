import { motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { recentDecisions } from '../data/mockData';

function DecisionRow({ decision, index }) {
  const isOverridden = decision.reasoning.startsWith('[OVERRIDDEN]');
  const isPassed = decision.marginCheck;
  
  const actionColors = {
    MATCH: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
    UNDERCUT_50: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
    HOLD: 'text-orange-400 bg-orange-400/10 border-orange-400/30'
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      className={`glass-card p-5 ${isOverridden ? 'border-red-500/40' : 'border-white/10'}`}
    >
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
        {/* SKU */}
        <div className="md:col-span-2">
          <div className="text-xs text-text-muted mb-1">SKU</div>
          <div className="font-mono font-bold text-accent-purple">{decision.sku}</div>
        </div>
        
        {/* Prices */}
        <div className="md:col-span-2">
          <div className="text-xs text-text-muted mb-1">Our Price</div>
          <div className="font-mono text-text-primary">${decision.ourPrice.toFixed(2)}</div>
        </div>
        
        <div className="md:col-span-2">
          <div className="text-xs text-text-muted mb-1">Competitor</div>
          <div className="font-mono text-text-primary">${decision.competitorPrice.toFixed(2)}</div>
        </div>
        
        {/* Action */}
        <div className="md:col-span-2">
          <div className="text-xs text-text-muted mb-1">Action</div>
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${actionColors[decision.action]}`}>
            {decision.action}
          </span>
        </div>
        
        {/* Margin Check */}
        <div className="md:col-span-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-xs text-text-muted mb-2">Safety</div>
            {isPassed ? (
              <CheckCircle className="w-6 h-6 text-green-400" />
            ) : (
              <XCircle className="w-6 h-6 text-red-400" />
            )}
          </div>
        </div>
        
        {/* Margin % */}
        <div className="md:col-span-1">
          <div className="text-xs text-text-muted mb-1">Margin</div>
          <div className={`font-mono font-bold ${decision.margin < 12 ? 'text-red-400' : 'text-green-400'}`}>
            {decision.margin.toFixed(1)}%
          </div>
        </div>
        
        {/* Reasoning */}
        <div className="md:col-span-12 mt-2">
          <div className="text-xs text-text-muted mb-1">Reasoning</div>
          <div className={`text-sm leading-relaxed ${isOverridden ? 'text-red-400' : 'text-text-primary/80'}`}>
            {isOverridden && <AlertTriangle className="inline w-4 h-4 mr-1" />}
            {decision.reasoning}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default function DecisionFeed() {
  return (
    <section className="mb-12">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="mb-6"
      >
        <h2 className="text-3xl font-bold text-gradient-purple mb-2">Live Decision Feed</h2>
        <p className="text-text-muted flex items-center gap-2">
          Recent pricing decisions with margin safety validation
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
            <XCircle className="w-3 h-3" />
            Override examples included
          </span>
        </p>
      </motion.div>
      
      <div className="space-y-4">
        {recentDecisions.map((decision, index) => (
          <DecisionRow key={decision.id} decision={decision} index={index} />
        ))}
      </div>
    </section>
  );
}
