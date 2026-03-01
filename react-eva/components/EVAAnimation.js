import { useEffect, useState } from 'react';

const EVAAnimation = ({ isActive, mode = 'default' }) => {
  const totalBars = 12;
  const [isClient, setIsClient] = useState(false);
  const [barHeights, setBarHeights] = useState([]);
  
  // Set up client-side detection
  useEffect(() => {
    setIsClient(true);
    
    // Generate random heights for static bars
    const heights = Array(totalBars).fill().map(() => 
      Math.floor(Math.random() * 6) + 3
    );
    setBarHeights(heights);
  }, []);
  
  // For processing mode, only show the breathing circle
  if (mode === 'processing' && isClient) {
    return (
      <div className="relative w-full max-w-xs mx-auto h-20 flex items-center justify-center">
        <div className="absolute w-20 h-20 rounded-full bg-blue-400 opacity-15 blur-md animate-pulse scale-110"></div>
      </div>
    );
  }
  
  return (
    <div className="relative w-full max-w-xs mx-auto h-20 flex items-center justify-center">
      {/* Central circle glow effect */}
      <div className={`absolute w-16 h-16 rounded-full
        ${isActive && isClient ? 'bg-blue-400 opacity-15' : 'bg-blue-300 opacity-10'} 
        blur-md transition-all duration-500
        ${isActive && isClient ? 'scale-110' : 'scale-100'}`}>
      </div>
      
      {/* Waveform visualization */}
      <div className="flex items-center justify-center h-12 gap-[3px] z-10">
        {[...Array(totalBars)].map((_, index) => (
          <div 
            key={index}
            className={`w-1 rounded-full transition-all duration-300
              ${isActive && isClient 
                ? 'bg-blue-400 bg-opacity-70 animate-wave' 
                : 'bg-blue-300 bg-opacity-40'}`}
            style={{
              height: isActive && isClient 
                ? undefined 
                : `${barHeights[index] || 3}px`,
              animationDelay: `${index * 70}ms`
            }}
          />
        ))}
      </div>
    </div>
  );
};

// Define the custom animation
const styles = `
  @keyframes wave {
    0% { height: 3px; }
    50% { height: 25px; }
    100% { height: 5px; }
  }
  
  .animate-wave {
    animation: wave 1.5s ease-in-out infinite;
  }
`;

// Add the styles to the document
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}

export default EVAAnimation; 