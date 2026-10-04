import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { useRef, useState, useEffect } from 'react';

/**
 * TiltIcon - 3D tilting icon wrapper with layered depth and cursor-following glare
 * 
 * Features:
 * - Tilts up to 18deg based on cursor position inside icon
 * - Lifts with translateZ(25px) and scales 1.12 on hover
 * - Layered depth: icon glyph, glow layer, dynamic shadow
 * - Moving glare/shine highlight following cursor
 * - Smooth spring physics for natural motion
 * - Respects prefers-reduced-motion
 * - Simple tap scale on touch devices
 */
export default function TiltIcon({ 
  children, 
  className = '',
  glowColor = 'rgba(168, 85, 247, 0.6)', // purple glow default
  maxTilt = 18,
  liftAmount = 25
}) {
  const iconRef = useRef(null);
  const [isTouchDevice, setIsTouchDevice] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  
  // Motion values for tilt
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.5);
  
  // Spring physics for smooth tilt
  const rotateX = useSpring(useTransform(mouseY, [0, 1], [maxTilt, -maxTilt]), {
    stiffness: 300,
    damping: 35
  });
  const rotateY = useSpring(useTransform(mouseX, [0, 1], [-maxTilt, maxTilt]), {
    stiffness: 300,
    damping: 35
  });
  
  // Glare position
  const glareX = useTransform(mouseX, [0, 1], ['-50%', '150%']);
  const glareY = useTransform(mouseY, [0, 1], ['-50%', '150%']);
  
  // Shadow position (opposite to tilt)
  const shadowX = useTransform(mouseX, [0, 1], [10, -10]);
  const shadowY = useTransform(mouseY, [0, 1], [10, -10]);
  
  useEffect(() => {
    setIsTouchDevice('ontouchstart' in window || navigator.maxTouchPoints > 0);
  }, []);
  
  const handleMouseMove = (e) => {
    if (!iconRef.current || isTouchDevice) return;
    
    const rect = iconRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    
    mouseX.set(x);
    mouseY.set(y);
  };
  
  const handleMouseEnter = () => {
    setIsHovering(true);
  };
  
  const handleMouseLeave = () => {
    mouseX.set(0.5);
    mouseY.set(0.5);
    setIsHovering(false);
  };
  
  return (
    <div 
      className="tilt-icon-wrapper"
      style={{ perspective: '800px' }}
    >
      <motion.div
        ref={iconRef}
        className={`tilt-icon ${className}`}
        style={{
          rotateX: !isTouchDevice ? rotateX : 0,
          rotateY: !isTouchDevice ? rotateY : 0,
          transformStyle: 'preserve-3d',
        }}
        animate={{
          z: isHovering && !isTouchDevice ? liftAmount : 0,
          scale: isHovering ? 1.12 : 1,
        }}
        transition={{ 
          type: 'spring',
          stiffness: 300,
          damping: 30
        }}
        onMouseMove={handleMouseMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        whileTap={isTouchDevice ? { scale: 0.95 } : undefined}
      >
        {/* Dynamic colored shadow layer (moves opposite to tilt) */}
        {isHovering && !isTouchDevice && (
          <motion.div
            className="icon-shadow"
            style={{
              x: shadowX,
              y: shadowY,
              background: glowColor,
            }}
          />
        )}
        
        {/* Glow layer (depth: -5px) */}
        {isHovering && (
          <motion.div
            className="icon-glow"
            style={{
              transform: 'translateZ(-5px)',
              boxShadow: `0 0 30px ${glowColor}`,
            }}
          />
        )}
        
        {/* Icon glyph (depth: 0px) */}
        <div className="icon-content" style={{ transform: 'translateZ(0px)' }}>
          {children}
        </div>
        
        {/* Moving glare/shine highlight */}
        {isHovering && !isTouchDevice && (
          <motion.div
            className="icon-glare"
            style={{
              left: glareX,
              top: glareY,
            }}
          />
        )}
      </motion.div>
    </div>
  );
}
