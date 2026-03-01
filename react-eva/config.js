/**
 * EVA App Configuration
 * Central configuration file for the EVA React application
 */

// Environment variables with fallbacks
const getEnvVar = (key, fallback) => {
  if (typeof window !== 'undefined') {
    return process.env[key] || fallback;
  }
  return fallback;
};

const config = {
  // WebSocket settings
  websocket: {
    // WebSocket base URL, defaults to localhost in development
    baseUrl: getEnvVar('NEXT_PUBLIC_EVA_WS_URL', 'ws://localhost:8080'),
    
    // WebSocket reconnection settings
    reconnectInterval: 3000, // ms between reconnection attempts
    reconnectAttempts: 5,    // max number of reconnection attempts
  },
  
  // API settings
  api: {
    // API base URL, defaults to localhost in development
    baseUrl: getEnvVar('NEXT_PUBLIC_EVA_API_URL', 'http://localhost:8080'),
    
    // Download path for resources
    downloadPath: '/download',
  },
  
  // Application behavior settings
  behavior: {
    // Image capture settings
    imageQuality: 0.92,  // JPEG quality for captured images (0-1)
    
    // Audio settings
    audioEnabled: true,  // Whether audio responses are enabled
    
    // Text-to-speech settings
    ttsEnabled: true,    // Whether text-to-speech is enabled
    
    // Accessibility settings
    captions: true,      // Whether to show captions for audio responses
  },
  
  // Application information
  app: {
    name: getEnvVar('NEXT_PUBLIC_APP_NAME', 'EVA Voice Assistant'),
    version: '1.0.0',
  },
  
  // Debug settings
  debug: {
    // Enable verbose logging in development mode
    verbose: process.env.NODE_ENV === 'development',
    logWebSocketMessages: process.env.NODE_ENV === 'development',
    
    // Audio debugging
    logAudioOperations: true, // Log all audio operations (loads, plays, errors)
    showAudioUrls: true,      // Log the exact URLs being used for audio
    
    // Force show all debug during development
    showAllDebug: process.env.NODE_ENV === 'development',
    
    // Master switch for debug panel
    enabled: process.env.NODE_ENV === 'development'
  }
};

export default config; 