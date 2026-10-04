import { Github, Linkedin } from 'lucide-react';
import GlassCard from './GlassCard';
import TiltIcon from './TiltIcon';

export default function TopBar() {
  return (
    <div className="fixed top-0 left-0 right-0 z-50 border-b border-white/10">
      <GlassCard className="rounded-none rounded-b-2xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <TiltIcon glowColor="rgba(168, 85, 247, 0.7)">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent-purple to-accent-pink flex items-center justify-center">
                <span className="text-xl font-bold">CP</span>
              </div>
            </TiltIcon>
            <div>
              <h1 className="text-lg font-bold text-gradient-purple">
                Competitive Pricing Multi-Agent System
              </h1>
              <p className="text-xs text-text-muted">Two-Tier AI Architecture with Deterministic Safety • Shahul Hussain</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <a 
              href="https://github.com/brcew" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 glass-card-hover text-sm font-medium"
            >
              <TiltIcon glowColor="rgba(168, 85, 247, 0.6)">
                <Github className="w-4 h-4" />
              </TiltIcon>
              View on GitHub
            </a>
            <TiltIcon glowColor="rgba(236, 72, 153, 0.6)">
              <a 
                href="https://www.linkedin.com/in/brcew/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-text-muted hover:text-accent-purple transition-colors"
              >
                <Linkedin className="w-5 h-5" />
              </a>
            </TiltIcon>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
