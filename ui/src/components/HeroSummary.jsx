import { TrendingDown, CheckCircle, Shield, Package } from 'lucide-react';
import { motion } from 'framer-motion';
import { stats } from '../data/mockData';

const iconMap = {
  TrendingDown,
  CheckCircle,
  Shield,
  Package
};

function StatCard({ stat, index }) {
  const Icon = iconMap[stat.icon];
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      className="glass-card-hover p-6"
    >
      <div className="flex items-start justify-between mb-4">
        <Icon className={`w-8 h-8 ${stat.color}`} />
      </div>
      <div className={`text-4xl font-bold mb-2 ${stat.color} glow-purple`}>
        {stat.value}
      </div>
      <div className="text-sm font-medium text-text-primary mb-1">
        {stat.label}
      </div>
      <div className="text-xs text-text-muted">
        {stat.description}
      </div>
    </motion.div>
  );
}

export default function HeroSummary() {
  return (
    <section className="mb-12">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="mb-8 text-center"
      >
        <p className="text-xl md:text-2xl text-text-primary/90 max-w-4xl mx-auto leading-relaxed">
          Two-tier AI agents that reprice against competitors — with{' '}
          <span className="text-gradient-purple font-bold">hard-coded financial safety limits</span>{' '}
          the LLM can never override.
        </p>
      </motion.div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <StatCard key={stat.label} stat={stat} index={index} />
        ))}
      </div>
    </section>
  );
}
