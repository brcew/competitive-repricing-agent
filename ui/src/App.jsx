import TopBar from './components/TopBar';
import HeroSummary from './components/HeroSummary';
import ArchitectureDiagram from './components/ArchitectureDiagram';
import DemoModeInfo from './components/DemoModeInfo';
import LiveDemoSimulator from './components/LiveDemoSimulator';
import DecisionFeed from './components/DecisionFeed';
import CostChart from './components/CostChart';
import TechStack from './components/TechStack';
import Footer from './components/Footer';
import FloatingObjects from './components/FloatingObjects';

function BackgroundBlobs() {
  return (
    <>
      {/* Smaller blobs positioned at edges only */}
      <div 
        className="blob-bg w-[300px] h-[300px] bg-accent-purple/30 top-[5%] left-[-8%]"
        style={{ animationDelay: '0s' }}
      />
      <div 
        className="blob-bg w-[250px] h-[250px] bg-accent-pink/30 top-[60%] right-[-5%]"
        style={{ animationDelay: '5s' }}
      />
      <div 
        className="blob-bg w-[200px] h-[200px] bg-accent-orange/30 bottom-[8%] left-[5%]"
        style={{ animationDelay: '10s' }}
      />
    </>
  );
}

export default function App() {
  // Liquid morph animation is now in index.css

  return (
    <div className="min-h-screen relative overflow-x-hidden">
      {/* Floating product objects (behind everything) */}
      <FloatingObjects />
      
      {/* Liquid morphing blobs */}
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
