import { motion } from 'framer-motion';
import { 
  Code2, Zap, Brain, Database, Server, 
  FileText, CheckSquare, Container, Workflow 
} from 'lucide-react';
import GlassCard from './GlassCard';
import TiltIcon from './TiltIcon';

const iconMap = {
  Code2, Zap, Brain, Database, Server,
  FileText, CheckSquare, Container, Workflow,
  BrainCircuit: Brain
};

// Glow colors for each tech
const glowMap = {
  Code2: 'rgba(96, 165, 250, 0.6)',
  Zap: 'rgba(250, 204, 21, 0.6)',
  Brain: 'rgba(168, 85, 247, 0.6)',
  BrainCircuit: 'rgba(236, 72, 153, 0.6)',
  Database: 'rgba(34, 197, 94, 0.6)',
  Server: 'rgba(34, 211, 238, 0.6)',
  FileText: 'rgba(249, 115, 22, 0.6)',
  CheckSquare: 'rgba(34, 197, 94, 0.6)',
  Container: 'rgba(96, 165, 250, 0.6)',
  Workflow: 'rgba(168, 85, 247, 0.6)',
};

const techStack = [
  { name: 'Python 3.11', icon: 'Code2', color: 'text-blue-400' },
  { name: 'Groq API', icon: 'Zap', color: 'text-yellow-400' },
  { name: 'Llama 3.1 8B', icon: 'Brain', color: 'text-purple-400' },
  { name: 'Llama 3.3 70B', icon: 'BrainCircuit', color: 'text-pink-400' },
  { name: 'SQLAlchemy', icon: 'Database', color: 'text-green-400' },
  { name: 'PostgreSQL', icon: 'Server', color: 'text-cyan-400' },
  { name: 'structlog', icon: 'FileText', color: 'text-orange-400' },
  { name: 'pytest (107 tests)', icon: 'CheckSquare', color: 'text-green-400' },
  { name: 'Docker', icon: 'Container', color: 'text-blue-400' },
  { name: 'asyncio', icon: 'Workflow', color: 'text-purple-400' }
];

export default function TechStack() {
  return (
    <section className="mb-12">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="mb-6"
      >
        <h2 className="text-3xl font-bold text-gradient-purple mb-2">Tech Stack</h2>
        <p className="text-text-muted">Production-grade tools for cost-efficient AI systems</p>
      </motion.div>
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.6 }}
      >
        <GlassCard className="p-8">
          <div className="flex flex-wrap gap-3">
            {techStack.map((tech, index) => {
              const Icon = iconMap[tech.icon];
              const glowColor = glowMap[tech.icon];
              return (
                <motion.div
                  key={tech.name}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.05, duration: 0.3 }}
                >
                  <GlassCard className="px-4 py-3 flex items-center gap-3" intensity="low">
                    <TiltIcon glowColor={glowColor} maxTilt={15}>
                      <Icon className={`w-5 h-5 ${tech.color}`} />
                    </TiltIcon>
                    <span className="text-sm font-medium text-text-primary">{tech.name}</span>
                  </GlassCard>
                </motion.div>
              );
            })}
          </div>
        </GlassCard>
      </motion.div>
    </section>
  );
}
