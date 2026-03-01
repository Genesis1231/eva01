import { useState, useEffect } from 'react';
import webSocketService from '../services/WebSocketService';

const ConnectionStatus = () => {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [showStatus, setShowStatus] = useState(true);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  useEffect(() => {
    // Set up connection status callback
    webSocketService.setConnectionStatusCallback((status, data) => {
      setConnectionStatus(status);
      if (status === 'reconnecting' && data) {
        setReconnectAttempt(data);
      }
      
      // Auto-hide the connected status after 5 seconds
      if (status === 'connected') {
        const timer = setTimeout(() => {
          setShowStatus(false);
        }, 5000);
        return () => clearTimeout(timer);
      } else {
        setShowStatus(true);
      }
    });
    
    // Try to connect immediately
    webSocketService.connect().catch(err => {
      console.error('Initial connection failed:', err);
    });
    
    // Clean up
    return () => {
      webSocketService.setConnectionStatusCallback(null);
    };
  }, []);
  
  // Determine background color based on status
  const getBackgroundColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-blue-500';
      case 'reconnecting':
        return 'bg-yellow-500';
      case 'error':
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };
  
  // Get status message
  const getStatusMessage = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected to EVA';
      case 'connecting':
        return 'Connecting to EVA...';
      case 'reconnecting':
        return `Reconnecting to EVA (Attempt ${reconnectAttempt})...`;
      case 'failed':
        return 'Connection failed. Please refresh the page.';
      case 'error':
        return 'Connection error. Please check your network.';
      default:
        return 'Disconnected from EVA';
    }
  };
  
  // Don't render anything if status is hidden
  if (!showStatus && connectionStatus === 'connected') {
    return null;
  }
  
  return (
    <div 
      className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-full shadow-lg 
                 text-white text-sm font-medium transition-all duration-300 
                 flex items-center space-x-2 ${getBackgroundColor()}`}
    >
      {/* Status indicator dot */}
      <div className={`h-2 w-2 rounded-full ${
        connectionStatus === 'connecting' || connectionStatus === 'reconnecting' 
          ? 'animate-pulse bg-white' 
          : 'bg-white'
      }`}></div>
      
      {/* Status message */}
      <span>{getStatusMessage()}</span>
      
      {/* Close button - only show for connected status */}
      {connectionStatus === 'connected' && (
        <button 
          onClick={() => setShowStatus(false)}
          className="ml-2 text-white hover:text-gray-200 focus:outline-none"
          aria-label="Dismiss"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      )}
      
      {/* Manual connect button for failed/error states */}
      {(connectionStatus === 'failed' || connectionStatus === 'error' || connectionStatus === 'disconnected') && (
        <button 
          onClick={() => webSocketService.connect()}
          className="ml-2 bg-white bg-opacity-20 hover:bg-opacity-30 px-2 py-1 rounded text-xs"
        >
          Retry
        </button>
      )}
    </div>
  );
};

export default ConnectionStatus; 