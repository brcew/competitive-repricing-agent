import { useEffect, useRef, useState } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import { 
  Laptop, Smartphone, Tablet, Headphones, Watch, 
  Monitor, Keyboard, Mouse 
} from 'lucide-react';

/**
 * FloatingObjects - Animated product objects in 3 depth layers
 * 
 * Configuration object at top for easy tuning:
 * - Object count per layer
 * - Speed, opacity, blur per depth
 * - Motion ranges and parallax strength
 */

// === CONFIGURATION (TUNE HERE) ===
const CONFIG = {
  desktop: {
    far: { count: 5, opacity: 0.12, blur: 4, speed: 35, size: 60 },
    mid: { count: 4, opacity: 0.18, blur: 2, speed: 28, size: 80 },
    near: { count: 3, opacity: 0.25, blur: 0, speed: 20, size: 120 }
  },
  mobile: {
    far: { count: 2, opacity: 0.10, blur: 3, speed: 40, size: 50 },
    mid: { count: 2, opacity: 0.15, blur: 1, speed: 30, size: 70 },
    near: { count: 1, opacity: 0.20, blur: 0, speed: 25, size: 100 }
  },
  parallax: {
    near: 20,  // px shift for near layer
    mid: 12,   // px shift for mid layer
    far: 6     // px shift for far layer
  }
};

// Product icons with gradient colors
const PRODUCTS = [
  { Icon: Laptop, color: 'from-purple-500 to-pink-500' },
  { Icon: Smartphone, color: 'from-blue-500 to-cyan-500' },
  { Icon: Tablet, color: 'from-pink-500 to-orange-500' },
  { Icon: Headphones, color: 'from-purple-500 to-blue-500' },
  { Icon: Watch, color: 'from-orange-500 to-pink-500' },
  { Icon: Monitor, color: 'from-cyan-500 to-blue-500' },
  { Icon: Keyboard, color: 'from-purple-500 to-pink-500' },
  { Icon: Mouse, color: 'from-blue-500 to-purple-500' }
];

/**
 * Single floating object with drift + rotation + bobbing
 */
function FloatingObject({ 
  product, 
  depth, 
  index, 
  config,
  mouseX,
  mouseY,
  parallaxStrength 
}) {
  const { Icon, color } = product;
  const { opacity, blur, speed, size } = config;
  
  // Random starting position (avoid center top 30% for hero text)
  const startX = Math.random() * 80 + 10; // 10-90%
  const startY = Math.random() > 0.3 ? Math.random() * 100 : Math.random() * 30 + 40; // Avoid center top
  
  // Random animation parameters
  const driftX = (Math.random() - 0.5) * 100; // -50 to 50
  const driftY = -50 - Math.random() * 50; // -50 to -100 (upward)
  const rotateZ = (Math.random() - 0.5) * 360;
  const rotateX = (Math.random() - 0.5) * 30;
  const delay = Math.random() * speed;
  
  // Mouse parallax (spring-based smooth follow)
  const parallaxX = useSpring(
    useMotionValue(0),
    { stiffness: 50, damping: 20 }
  );
  const parallaxY = useSpring(
    useMotionValue(0),
    { stiffness: 50, damping: 20 }
  );
  
  useEffect(() => {
    parallaxX.set(mouseX.get() * parallaxStrength);
    parallaxY.set(mouseY.get() * parallaxStrength);
    
    const unsubscribeX = mouseX.on('change', (v) => parallaxX.set(v * parallaxStrength));
    const unsubscribeY = mouseY.on('change', (v) => parallaxY.set(v * parallaxStrength));
    
    return () => {
      unsubscribeX();
      unsubscribeY();
    };
  }, [mouseX, mouseY, parallaxX, parallaxY, parallaxStrength]);
  
  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{
        left: `${startX}%`,
        top: `${startY}%`,
        x: parallaxX,
        y: parallaxY,
        opacity,
        filter: `blur(${blur}px)`,
      }}
      animate={{
        x: [0, driftX, driftX * 0.5, 0],
        y: [0, driftY, driftY * 0.7, 0],
        rotateZ: [0, rotateZ, rotateZ * 0.5, 0],
        rotateX: [0, rotateX, -rotateX, 0],
        scale: [1, 1.1, 0.9, 1],
      }}
      transition={{
        duration: speed,
        delay,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    >
      {/* Soft glow behind object */}
      <div 
        className={`absolute inset-0 bg-gradient-to-br ${color} rounded-full blur-xl opacity-40`}
        style={{ 
          width: size * 1.5, 
          height: size * 1.5,
          transform: 'translate(-25%, -25%)'
        }}
      />
      
      {/* Product icon */}
      <Icon 
        size={size} 
        className={`bg-gradient-to-br ${color} bg-clip-text text-transparent`}
        strokeWidth={1.5}
      />
    </motion.div>
  );
}

/**
 * Layer of objects at a specific depth
 */
function ObjectLayer({ 
  depth, 
  config, 
  products, 
  mouseX, 
  mouseY, 
  parallaxStrength 
}) {
  // Generate random product selection for this layer
  const layerProducts = Array.from({ length: config.count }, (_, i) => {
    const randomProduct = products[Math.floor(Math.random() * products.length)];
    return { ...randomProduct, id: `${depth}-${i}` };
  });
  
  return (
    <div className={`absolute inset-0 z-${depth === 'far' ? '0' : depth === 'mid' ? '1' : '2'}`}>
      {layerProducts.map((product, index) => (
        <FloatingObject
          key={product.id}
          product={product}
          depth={depth}
          index={index}
          config={config}
          mouseX={mouseX}
          mouseY={mouseY}
          parallaxStrength={parallaxStrength}
        />
      ))}
    </div>
  );
}

/**
 * Main FloatingObjects component
 * Creates 3 depth layers with parallax mouse tracking
 */
export default function FloatingObjects() {
  const containerRef = useRef(null);
  const [isMobile, setIsMobile] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [isTabHidden, setIsTabHidden] = useState(false);
  
  // Mouse position for parallax (-1 to 1 normalized)
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  
  useEffect(() => {
    // Detect mobile
    setIsMobile(window.innerWidth < 768);
    
    // Detect reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);
    
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  useEffect(() => {
    // Mouse parallax tracking (desktop only)
    if (isMobile || reducedMotion) return;
    
    const handleMouseMove = (e) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1; // -1 to 1
      const y = (e.clientY / window.innerHeight) * 2 - 1;
      mouseX.set(x);
      mouseY.set(y);
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [isMobile, reducedMotion, mouseX, mouseY]);
  
  useEffect(() => {
    // Pause animations when tab is hidden
    const handleVisibilityChange = () => {
      setIsTabHidden(document.hidden);
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);
  
  // Don't render if reduced motion or hidden tab
  if (reducedMotion || isTabHidden) {
    return null;
  }
  
  const config = isMobile ? CONFIG.mobile : CONFIG.desktop;
  const parallax = CONFIG.parallax;
  
  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 overflow-hidden pointer-events-none"
      style={{ zIndex: 0 }}
    >
      {/* Far layer (smallest, slowest, most blur) */}
      <ObjectLayer 
        depth="far" 
        config={config.far} 
        products={PRODUCTS}
        mouseX={mouseX}
        mouseY={mouseY}
        parallaxStrength={isMobile ? 0 : parallax.far}
      />
      
      {/* Mid layer */}
      <ObjectLayer 
        depth="mid" 
        config={config.mid} 
        products={PRODUCTS}
        mouseX={mouseX}
        mouseY={mouseY}
        parallaxStrength={isMobile ? 0 : parallax.mid}
      />
      
      {/* Near layer (largest, fastest, sharpest) */}
      <ObjectLayer 
        depth="near" 
        config={config.near} 
        products={PRODUCTS}
        mouseX={mouseX}
        mouseY={mouseY}
        parallaxStrength={isMobile ? 0 : parallax.near}
      />
    </div>
  );
}
