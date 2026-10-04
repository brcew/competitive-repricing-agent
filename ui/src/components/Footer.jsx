import { Github, Linkedin, Mail } from 'lucide-react';
import GlassCard from './GlassCard';
import TiltIcon from './TiltIcon';

export default function Footer() {
  return (
    <footer className="border-t border-white/10 py-8 mt-16">
      <GlassCard className="rounded-none rounded-t-2xl">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-6">
              <a 
                href="https://github.com/brcew" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-text-muted hover:text-accent-purple transition-colors"
              >
                <TiltIcon glowColor="rgba(168, 85, 247, 0.6)">
                  <Github className="w-5 h-5" />
                </TiltIcon>
                <span className="text-sm">GitHub</span>
              </a>
              <a 
                href="https://www.linkedin.com/in/brcew/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-text-muted hover:text-accent-purple transition-colors"
              >
                <TiltIcon glowColor="rgba(236, 72, 153, 0.6)">
                  <Linkedin className="w-5 h-5" />
                </TiltIcon>
                <span className="text-sm">LinkedIn</span>
              </a>
              <a 
                href="mailto:urs.shahulsk@gmail.com" 
                className="flex items-center gap-2 text-text-muted hover:text-accent-purple transition-colors"
              >
                <TiltIcon glowColor="rgba(249, 115, 22, 0.6)">
                  <Mail className="w-5 h-5" />
                </TiltIcon>
                <span className="text-sm">Contact</span>
              </a>
            </div>
            
            <div className="text-center md:text-right">
              <p className="text-sm text-text-muted">
                Portfolio Project • <span className="text-accent-purple font-semibold">Shahul Hussain</span>
              </p>
              <p className="text-xs text-text-muted/70 mt-1">
                Graduate School Applications • 2029 Intake
              </p>
            </div>
          </div>
          
          <div className="mt-6 pt-6 border-t border-white/10 text-center">
            <p className="text-xs text-text-muted/60">
              Demonstrates cost-aware AI architecture and production-grade safety engineering.
              <br />
              All test data is simulated. System designed for portfolio evaluation.
            </p>
          </div>
        </div>
      </GlassCard>
    </footer>
  );
}
