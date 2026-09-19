import { useEffect } from 'react';
import TopBar from './components/TopBar';
import HeroSummary from './components/HeroSummary';
import ArchitectureDiagram from './components/ArchitectureDiagram';
import DemoModeInfo from './components/DemoModeInfo';
import LiveDemoSimulator from './components/LiveDemoSimulator';
import DecisionFeed from './components/DecisionFeed';
import CostChart from './components/CostChart';
import TechStack from './components/TechStack';
import Footer from './components/Footer';

function BackgroundBlobs() {
  return (
    <>
      <div 
        className="blob-bg w-[500px] h-[500px] bg-accent-purple/30 top-[10%] left-[-10%]"
        style={{ animation: 'float 20s infinite ease-in-out' }}
      />
      <div 
        className="blob-bg w-[400px] h-[400px] bg-accent-pink/30 top-[50%] right-[-5%]"
        style={{ animation: 'float 20s infinite ease-in-out 5s' }}
      />
      <div 
        className="blob-bg w-[350px] h-[350px] bg-accent-orange/30 bottom-[10%] left-[40%]"
        style={{ animation: 'float 20s infinite ease-in-out 10s' }}
      />
    </>
  );
}

export default function App() {
  useEffect(() => {
    // Add floating animation keyframes
    const style = document.createElement('style');
    style.textContent = `
      @keyframes float {
        0%, 100% {
          transform: translate(0, 0) scale(1);
        }
        33% {
          transform: translate(50px, -50px) scale(1.1);
        }
        66% {
          transform: translate(-30px, 30px) scale(0.9);
        }
      }
    `;
    document.head.appendChild(style);
    
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  return (
    <div className="min-h-screen relative overflow-x-hidden">
      <BackgroundBlobs />
      
      <TopBar />
      
      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-32 pb-16">
        <HeroSummary />
        <ArchitectureDiagram />
        <DemoModeInfo />
        <LiveDemoSimulator />
        <DecisionFeed />
        <CostChart />
        <TechStack />
      </main>
      
      <Footer />
    </div>
  );
}
