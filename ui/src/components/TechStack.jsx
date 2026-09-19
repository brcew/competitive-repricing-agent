import { motion } from 'framer-motion';
import { 
  Code2, Zap, Brain, Database, Server, 
  FileText, CheckSquare, Container, Workflow 
} from 'lucide-react';

const iconMap = {
  Code2, Zap, Brain, Database, Server,
  FileText, CheckSquare, Container, Workflow,
  BrainCircuit: Brain
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
        className="glass-card p-8"
      >
        <div className="flex flex-wrap gap-3">
          {techStack.map((tech, index) => {
            const Icon = iconMap[tech.icon];
            return (
              <motion.div
                key={tech.name}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05, duration: 0.3 }}
                className="glass-card-hover px-4 py-3 flex items-center gap-3"
              >
                <Icon className={`w-5 h-5 ${tech.color}`} />
                <span className="text-sm font-medium text-text-primary">{tech.name}</span>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </section>
  );
}
