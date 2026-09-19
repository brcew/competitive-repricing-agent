import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { costComparisonData } from '../data/mockData';

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-card p-3 border border-white/20">
        <p className="text-sm font-bold text-text-primary mb-2">{payload[0].payload.period}</p>
        <p className="text-xs text-accent-purple">
          Two-Tier: ${payload[0].value.toFixed(4)}
        </p>
        <p className="text-xs text-accent-pink">
          Single Model: ${payload[1].value.toFixed(4)}
        </p>
        <p className="text-xs text-green-400 mt-1 font-bold">
          Savings: ${(payload[1].value - payload[0].value).toFixed(4)} (60%)
        </p>
      </div>
    );
  }
  return null;
};

export default function CostChart() {
  return (
    <section className="mb-12">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="mb-6"
      >
        <h2 className="text-3xl font-bold text-gradient-purple mb-2">Cost Comparison</h2>
        <p className="text-text-muted">
          Two-tier architecture achieves{' '}
          <span className="text-green-400 font-bold">60% cost savings</span>{' '}
          vs single large model approach
        </p>
      </motion.div>
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.6 }}
        className="glass-card p-8"
      >
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={costComparisonData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff20" />
            <XAxis 
              dataKey="period" 
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              wrapperStyle={{ color: '#f5f3ff', fontSize: '14px' }}
              iconType="circle"
            />
            <Bar 
              dataKey="twoTier" 
              name="Two-Tier Approach" 
              fill="#a855f7" 
              radius={[8, 8, 0, 0]}
            />
            <Bar 
              dataKey="singleModel" 
              name="Single Large Model" 
              fill="#ec4899" 
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          <div className="glass-card p-4 text-center">
            <div className="text-2xl font-bold text-accent-purple mb-1">$0.0032</div>
            <div className="text-xs text-text-muted">Daily Cost (Two-Tier)</div>
          </div>
          <div className="glass-card p-4 text-center">
            <div className="text-2xl font-bold text-accent-pink mb-1">$0.0078</div>
            <div className="text-xs text-text-muted">Daily Cost (Single Model)</div>
          </div>
          <div className="glass-card p-4 text-center border-2 border-green-400/30">
            <div className="text-2xl font-bold text-green-400 mb-1">59.5%</div>
            <div className="text-xs text-text-muted">Cost Reduction</div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
