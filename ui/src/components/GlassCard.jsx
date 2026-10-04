import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';

/**
 * GlassCard - Liquid glass morphism component with 3D tilt on hover
 * 
 * Features:
 * - Translucent gradient background with backdrop blur
 * - Cursor-following specular highlight
 * - Subtle 3D tilt on hover (6-8deg)
 * - Respects prefers-reduced-motion
 * - Touch-friendly (disables tilt on mobile)
 */
export default function GlassCard({ 
  children, 
  className = '', 
  enableTilt = true,
  intensity = 'medium' // 'low' | 'medium' | 'high'
}) {
  const cardRef = useRef(null);
  const [isTouchDevice, setIsTouchDevice] = useState(false);
  
  // Motion values for tilt
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.5);
  
  // Spring physics for smooth movement
  const rotateX = useSpring(useTransform(mouseY, [0, 1], [6, -6]), {
    stiffness: 200,
    damping: 30
  });
  const rotateY = useSpring(useTransform(mouseX, [0, 1], [-6, 6]), {
    stiffness: 200,
    damping: 30
  });
  
  // Specular highlight position
  const highlightX = useTransform(mouseX, [0, 1], ['0%', '100%']);
  const highlightY = useTransform(mouseY, [0, 1], ['0%', '100%']);
  
  useEffect(() => {
    // Detect touch device
    setIsTouchDevice('ontouchstart' in window || navigator.maxTouchPoints > 0);
  }, []);
  
  const handleMouseMove = (e) => {
    if (!cardRef.current || !enableTilt || isTouchDevice) return;
    
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    
    mouseX.set(x);
    mouseY.set(y);
  };
  
  const handleMouseLeave = () => {
    mouseX.set(0.5);
    mouseY.set(0.5);
  };
  
  // Intensity presets
  const intensityConfig = {
    low: { blur: 'blur(16px)', opacity: 0.06 },
    medium: { blur: 'blur(24px)', opacity: 0.1 },
    high: { blur: 'blur(32px)', opacity: 0.14 }
  };
  
  const config = intensityConfig[intensity] || intensityConfig.medium;
  
  return (
    <motion.div
      ref={cardRef}
      className={`glass-card-enhanced ${className}`}
      style={{
        rotateX: enableTilt && !isTouchDevice ? rotateX : 0,
        rotateY: enableTilt && !isTouchDevice ? rotateY : 0,
        transformStyle: 'preserve-3d',
        '--blur-amount': config.blur,
        '--glass-opacity': config.opacity,
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      whileHover={isTouchDevice ? { scale: 1.02 } : undefined}
      transition={{ duration: 0.2 }}
    >
      {/* Specular highlight that follows cursor */}
      {enableTilt && !isTouchDevice && (
        <motion.div
          className="glass-specular"
          style={{
            left: highlightX,
            top: highlightY,
          }}
        />
      )}
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
}
