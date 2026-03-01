import { useState, useEffect } from 'react';
import Head from 'next/head';
import dynamic from 'next/dynamic';

// Dynamically import client-side components with SSR disabled
const EVAResponse = dynamic(() => import('../components/EVAResponse'), { ssr: false });
const VideoCapture = dynamic(() => import('../components/VideoCapture'), { ssr: false });
const ConnectionStatus = dynamic(() => import('../components/ConnectionStatus'), { ssr: false });

export default function Home() {
  const [started, setStarted] = useState(false);
  const [query, setQuery] = useState('');
  const [isClient, setIsClient] = useState(false);
  const [showError, setShowError] = useState(false);
  const [error, setError] = useState('');
  const [browserCompatible, setBrowserCompatible] = useState(true);
  const [lastCaptureInfo, setLastCaptureInfo] = useState({ url: null, type: null, time: null });
  const [showCaptureInfo, setShowCaptureInfo] = useState(false);
  
  useEffect(() => {
    setIsClient(true);
    
    // Check browser compatibility
    if (typeof window !== 'undefined') {
      checkBrowserCompatibility();
    }
  }, [isClient]);
  
  // When a capture happens, show notification for a few seconds
  useEffect(() => {
    if (lastCaptureInfo.url) {
      setShowCaptureInfo(true);
      const timer = setTimeout(() => {
        setShowCaptureInfo(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [lastCaptureInfo]);
  
  const handleImageCaptured = (imageUrl, captureType) => {
    // Store the captured image info
    setLastCaptureInfo({
      url: imageUrl,
      type: captureType || 'observation',
      time: new Date().toLocaleTimeString()
    });
    
    console.log(`Image captured (${captureType}): ${imageUrl}`);
  };
  
  const checkBrowserCompatibility = () => {
    const incompatibilityReasons = [];
    
    // Check if MediaDevices API is supported
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      incompatibilityReasons.push('Media devices API not supported');
    }
    
    // Check if MediaRecorder API is supported
    if (typeof MediaRecorder === 'undefined') {
      incompatibilityReasons.push('MediaRecorder not supported');
    }
    
    // Check if Web Audio API is supported
    if (typeof AudioContext === 'undefined' && typeof webkitAudioContext === 'undefined') {
      incompatibilityReasons.push('Web Audio API not supported');
    }
    
    if (incompatibilityReasons.length > 0) {
      console.error('Browser compatibility issues:', incompatibilityReasons);
      setBrowserCompatible(false);
      showErrorNotification(`Your browser doesn't fully support EVA's features. Please try Chrome, Firefox, or Edge.`);
    }
  };
  
  const handleStart = () => {
    setStarted(true);
    console.log('Starting EVA conversation interface');
  };
  
  const handleNewQuery = (text) => {
    setQuery(text);
  };
  
  const handleReset = () => {
    setQuery('');
  };
  
  const showErrorNotification = (message) => {
    setError(message);
    setShowError(true);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
      setShowError(false);
    }, 5000);
  };
  
  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <Head>
        <title>EVA</title>
        <meta name="description" content="Enhanced Voice Assistant - EVA" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      {/* Connection Status - will be visible immediately */}
      {isClient && <ConnectionStatus />}
      
      {/* Image Capture Notification */}
      {isClient && showCaptureInfo && (
        <div className="fixed top-16 right-4 z-40 bg-indigo-900 bg-opacity-80 p-3 rounded-lg shadow-lg text-white text-sm flex items-start space-x-3 max-w-xs">
          <div className="flex-shrink-0 w-12 h-12 bg-black rounded overflow-hidden">
            {lastCaptureInfo.url && (
              <img 
                src={lastCaptureInfo.url} 
                alt="Captured" 
                className="w-full h-full object-cover" 
              />
            )}
          </div>
          <div>
            <div className="font-medium">{lastCaptureInfo.type === 'observation' ? 'Observation' : 'View'} Sent</div>
            <div className="text-xs text-indigo-200">
              Image captured and sent to EVA at {lastCaptureInfo.time}
            </div>
          </div>
        </div>
      )}
      
      <main className="flex-1 w-full container mx-auto px-4 sm:px-6 lg:px-8 flex flex-col items-center justify-center relative py-6">
        {/* Subtle background effects */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/3 left-1/4 w-96 h-96 rounded-full bg-blue-600 bg-opacity-5 opacity-40 blur-3xl"></div>
          <div className="absolute bottom-1/3 right-1/4 w-96 h-96 rounded-full bg-indigo-600 bg-opacity-5 opacity-40 blur-3xl"></div>
        </div>
        
        {!browserCompatible && (
          <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-700 rounded-lg text-center max-w-lg">
            <h3 className="text-red-300 text-base font-medium mb-1">Browser Compatibility Issue</h3>
            <p className="text-white text-sm">
              Your browser doesn't fully support all features needed for EVA.
              For the best experience, please use Chrome, Firefox, or Edge.
            </p>
          </div>
        )}
        
        {!started ? (
          <div className="relative z-10 text-center max-w-4xl mx-auto flex flex-col items-center">
            <div className="relative mb-8">
              {/* Subtle glow effect behind the text */}
              <div className="absolute -inset-1 bg-blue-500 opacity-10 blur-2xl rounded-lg"></div>
              
              <h2 className="relative text-[2.5rem] sm:text-5xl md:text-7xl font-bold leading-tight tracking-tight">
                <span className="inline-block bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-blue-400 animate-gradient whitespace-nowrap">
                  Enhanced Voice Assistant
                </span>
              </h2>
            </div>
            
            <p className="text-base md:text-xl text-gray-400 mb-16 tracking-wider">
              <span className="inline-block mx-2">EVA observes.</span>
              <span className="inline-block mx-2">EVA listens.</span>
              <span className="inline-block mx-2">EVA understands.</span>
            </p>
            
            <div className="flex flex-col items-center">
              <button 
                onClick={handleStart}
                className="group bg-blue-600 hover:bg-blue-600/90 text-white font-medium 
                         w-24 h-24 md:w-28 md:h-28 rounded-full transition-all duration-500 
                         shadow-lg hover:shadow-blue-500/40 flex items-center justify-center
                         border border-blue-400/30 relative overflow-hidden"
              >
                {/* Inner glow effect that appears on hover */}
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-400/20 to-blue-500/0 
                             opacity-0 group-hover:opacity-100 blur-sm transition-all duration-700"></div>
                
                {/* Outer ring that pulses on hover */}
                <div className="absolute -inset-1 bg-blue-400/10 rounded-full scale-0 
                             group-hover:scale-110 transition-all duration-700 opacity-0 
                             group-hover:opacity-100"></div>
                
                {/* Subtle animated border */}
                <div className="absolute inset-0 rounded-full border border-blue-400/20 
                             group-hover:border-blue-400/40 transition-all duration-500"></div>
                
                {/* Button text with its own animation */}
                <span className="relative text-xl md:text-2xl z-10 transition-transform duration-500 
                              group-hover:scale-110">Start</span>
              </button>
              
              <p className="mt-6 text-sm text-gray-500">
                Requires camera and microphone permissions
              </p>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-3xl relative z-10">
            {/* Video Capture - Now at the top with reduced margin */}
            <div className="mb-3">
              <VideoCapture onImageCaptured={handleImageCaptured} />
            </div>
            
            {/* EVA Response Section */}
            <div>
              <EVAResponse 
                query={query} 
                onNewQuery={handleNewQuery}
                onReset={handleReset}
              />
            </div>
          </div>
        )}
      </main>

      {/* Error Notification */}
      <div 
        className={`fixed top-5 right-5 max-w-sm bg-red-600 text-white py-3 px-5 rounded-lg shadow-lg transition-all duration-300 transform z-50 ${
          showError ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'
        }`}
      >
        {error}
      </div>
    </div>
  );
}