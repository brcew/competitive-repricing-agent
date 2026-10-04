import { motion } from 'framer-motion';
import { ArrowRight, Brain, Shield, Database } from 'lucide-react';
import GlassCard from './GlassCard';
import TiltIcon from './TiltIcon';

const nodes = [
  {
    id: 1,
    title: 'Orchestrator Agent',
    subtitle: 'llama-3.3-70b-versatile',
    details: 'Hourly • Watchlist Management',
    icon: Brain,
    color: 'from-purple-600 to-purple-800',
    glow: 'rgba(168, 85, 247, 0.7)'
  },
  {
    id: 2,
    title: 'Worker Agents',
    subtitle: 'llama-3.1-8b-instant',
    details: '15min/SKU • Pricing Decisions',
    icon: Brain,
    color: 'from-blue-600 to-blue-800',
    glow: 'rgba(59, 130, 246, 0.7)'
  },
  {
    id: 3,
    title: 'Margin Safety Checker',
    subtitle: 'Deterministic Python',
    details: '12% floor • Code enforced',
    icon: Shield,
    color: 'from-pink-600 to-pink-800',
    glow: 'rgba(236, 72, 153, 0.7)'
  },
  {
    id: 4,
    title: 'Execute or HOLD',
    subtitle: 'Database + Audit Trail',
    details: 'Decision logged & tracked',
    icon: Database,
    color: 'from-orange-600 to-orange-800',
    glow: 'rgba(249, 115, 22, 0.7)'
  }
];

function ArchitectureNode({ node, index }) {
  const Icon = node.icon;
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.15, duration: 0.5 }}
    >
      <GlassCard className="p-6 relative" intensity="medium">
        <TiltIcon glowColor={node.glow} maxTilt={15}>
          <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${node.color} flex items-center justify-center mb-4`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
        </TiltIcon>
        <h3 className="text-lg font-bold text-text-primary mb-1">{node.title}</h3>
        <p className="text-sm text-accent-purple font-mono mb-2">{node.subtitle}</p>
        <p className="text-xs text-text-muted">{node.details}</p>
      </GlassCard>
    </motion.div>
  );
}

function ConnectionArrow({ label, index }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.15 + 0.3, duration: 0.5 }}
      className="flex flex-col items-center justify-center"
    >
      <ArrowRight className="w-8 h-8 text-accent-purple animate-pulse" />
      <span className="text-xs text-text-muted mt-2 text-center max-w-[120px]">{label}</span>
    </motion.div>
  );
}

export default function ArchitectureDiagram() {
  return (
    <section className="mb-12">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="mb-6"
      >
        <h2 className="text-3xl font-bold text-gradient-purple mb-2">System Architecture</h2>
        <p className="text-text-muted">
          <span className="text-accent-pink font-semibold">LLM suggests</span> →{' '}
          <span className="text-accent-purple font-semibold">Code enforces</span>
        </p>
      </motion.div>
      
      <GlassCard className="p-8">
        {/* Desktop: Horizontal Flow */}
        <div className="hidden lg:grid lg:grid-cols-7 gap-4 items-center">
          <ArchitectureNode node={nodes[0]} index={0} />
          <ConnectionArrow label="Watchlist (max 15 SKUs)" index={0} />
          <ArchitectureNode node={nodes[1]} index={1} />
          <ConnectionArrow label="LLM suggests price" index={1} />
          <ArchitectureNode node={nodes[2]} index={2} />
          <ConnectionArrow label="Code enforces" index={2} />
          <ArchitectureNode node={nodes[3]} index={3} />
        </div>
        
        {/* Mobile/Tablet: Vertical Flow */}
        <div className="lg:hidden space-y-4">
          {nodes.map((node, index) => (
            <div key={node.id}>
              <ArchitectureNode node={node} index={index} />
              {index < nodes.length - 1 && (
                <div className="flex justify-center py-3">
                  <ArrowRight className="w-8 h-8 text-accent-purple rotate-90" />
                </div>
              )}
            </div>
          ))}
        </div>
      </GlassCard>
    </section>
  );
}
