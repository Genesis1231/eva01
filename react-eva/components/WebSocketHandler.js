import { useState, useEffect, useCallback, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';

const WebSocketHandler = ({ url, onOpen, onMessage, onClose, onError }) => {
  const [socket, setSocket] = useState(null);
  const [clientId, setClientId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;
  
  const connectWebSocket = useCallback(() => {
    if (!clientId || typeof window === 'undefined') return;
    
    // Clear any existing socket
    if (socket) {
      socket.close();
    }
    
    try {
      const ws = new WebSocket(`${url}/ws/${clientId}`);
      
      ws.onopen = (event) => {
        setConnected(true);
        reconnectAttemptsRef.current = 0;
        if (onOpen) onOpen(event);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // If we receive a session ID, store it
          if (data.session_id && data.type === 'receive_start') {
            setSessionId(data.session_id);
          }
          
          if (onMessage) onMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      ws.onclose = (event) => {
        setConnected(false);
        if (onClose) onClose(event);
        
        // Attempt to reconnect unless max attempts reached
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          console.log(`WebSocket closed. Attempting to reconnect (${reconnectAttemptsRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connectWebSocket();
          }, RECONNECT_DELAY);
        } else {
          console.error('Max reconnection attempts reached. Please reload the page.');
        }
      };
      
      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        if (onError) onError(event);
      };
      
      setSocket(ws);
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      if (onError) onError(error);
    }
  }, [url, clientId, onOpen, onMessage, onClose, onError, socket]);
  
  // Initialize WebSocket connection
  useEffect(() => {
    // Skip on server-side
    if (typeof window === 'undefined') return;
    
    // Generate a unique client ID if none exists
    if (!clientId) {
      setClientId(uuidv4());
    } else if (!socket || (socket && socket.readyState !== 1 && socket.readyState !== 0)) {
      connectWebSocket();
    }
    
    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      if (socket && socket.readyState === 1) { // WebSocket.OPEN = 1
        socket.close();
      }
    };
  }, [clientId, socket, connectWebSocket]);
  
  // Function to send audio data
  const sendAudio = useCallback((audioBlob) => {
    if (!socket || !socket.readyState || socket.readyState !== 1 || !sessionId) {
      console.error('Cannot send audio: WebSocket not connected or no session ID');
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onloadend = () => {
        try {
          const base64data = reader.result.split(',')[1];
          
          const message = {
            session_id: sessionId,
            type: 'audio',
            content: base64data
          };
          
          socket.send(JSON.stringify(message));
          resolve();
        } catch (error) {
          console.error('Error processing audio data:', error);
          reject(error);
        }
      };
      
      reader.onerror = (error) => {
        console.error('Error reading audio file:', error);
        reject(error);
      };
      
      reader.readAsDataURL(audioBlob);
    });
  }, [socket, sessionId]);
  
  // Function to send image data
  const sendImage = useCallback((imageBlob, type = 'frontImage') => {
    if (!socket || !socket.readyState || socket.readyState !== 1 || !sessionId) {
      console.error('Cannot send image: WebSocket not connected or no session ID');
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onloadend = () => {
        try {
          const base64data = reader.result.split(',')[1];
          
          const message = {
            session_id: sessionId,
            type: type,
            content: base64data
          };
          
          socket.send(JSON.stringify(message));
          resolve();
        } catch (error) {
          console.error('Error processing image data:', error);
          reject(error);
        }
      };
      
      reader.onerror = (error) => {
        console.error('Error reading image file:', error);
        reject(error);
      };
      
      reader.readAsDataURL(imageBlob);
    });
  }, [socket, sessionId]);
  
  // Function to signal the end of data transmission
  const sendOver = useCallback(() => {
    if (!socket || !socket.readyState || socket.readyState !== 1 || !sessionId) {
      console.error('Cannot send "over" signal: WebSocket not connected or no session ID');
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    return new Promise((resolve, reject) => {
      try {
        const message = {
          session_id: sessionId,
          type: 'over',
          content: 'completed'
        };
        
        socket.send(JSON.stringify(message));
        resolve();
      } catch (error) {
        console.error('Error sending over signal:', error);
        reject(error);
      }
    });
  }, [socket, sessionId]);
  
  return {
    connected,
    sessionId,
    clientId,
    sendAudio,
    sendImage,
    sendOver
  };
};

export default WebSocketHandler; 