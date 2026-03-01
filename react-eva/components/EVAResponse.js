import { useState, useEffect, useRef } from 'react';
import EVAAnimation from './EVAAnimation';
import AudioRecorder from './AudioRecorder';
import webSocketService from '../services/WebSocketService';
import config from '../config';

const EVAResponse = ({ query, onNewQuery, onReset }) => {
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isEVATalking, setIsEVATalking] = useState(false);
  const audioRef = useRef(null);
  const [isClient, setIsClient] = useState(false);
  const [htmlContent, setHtmlContent] = useState(null);
  const audioQueue = useRef([]);
  const [speechText, setSpeechText] = useState('');
  const [speechVisible, setSpeechVisible] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isWaitingForUserInput, setIsWaitingForUserInput] = useState(false);
  const lastAudioPlayedTime = useRef(null);
  const [userSpeaking, setUserSpeaking] = useState(false);
  
  // Get a single status label based on the current state
  const getStatusLabel = () => {
    if (isLoading) return { text: 'Processing', color: 'yellow' };
    if (isEVATalking) return { text: 'Speaking', color: 'blue' };
    if (userSpeaking) return { text: 'Listening', color: 'red' };
    if (isWaitingForUserInput) return { text: 'Ready', color: 'green' };
    return { text: 'Connecting', color: 'gray' };
  };
  
  // Debug log helper
  const debugLog = (message, type = 'info') => {
    if (config.debug.logAudioOperations) {
      console.log(`[EVA-${type}] ${message}`);
    }
  };
  
  // Helper function to extract filename from audio path
  const extractAudioFilename = (audioPath) => {
    if (!audioPath) return null;
    
    try {
      // Handle different formats of audio paths
      let filename = null;
      
      if (audioPath.includes('/download/audio/')) {
        // Extract from full URL
        const parts = audioPath.split('/download/audio/');
        filename = parts[1]?.split('?')[0];
      } else if (audioPath.includes('/audio/')) {
        // Extract from relative path with leading slash
        const parts = audioPath.split('/audio/');
        filename = parts[1]?.split('?')[0];
      } else if (audioPath.includes('audio/')) {
        // Extract from relative path without leading slash (like 'audio/filename.mp3')
        const parts = audioPath.split('audio/');
        filename = parts[1]?.split('?')[0];
      } else if (!audioPath.includes('/')) {
        // It might be just the filename
        filename = audioPath.split('?')[0];
      } else {
        // Fallback to last part of path
        const parts = audioPath.split('/');
        filename = parts[parts.length - 1].split('?')[0];
      }
      
      console.log(`Extracted filename: ${filename} from ${audioPath}`);
      return filename;
    } catch (e) {
      console.error('Error extracting filename:', e);
      return null;
    }
  };
  
  // Check if we're on the client side
  useEffect(() => {
    setIsClient(true);
    
    // Reset EVA talking state to ensure it's not incorrectly set to true on initialization
    setIsEVATalking(false);
    debugLog('Component mounted, reset EVA talking state to false');
    
    // Set up WebSocket connection when component mounts
    if (typeof window !== 'undefined') {
      // Track connection status
      webSocketService.setConnectionStatusCallback((status) => {
        setIsConnected(status === 'connected');
        
        // When connection is established, we're ready for user input
        if (status === 'connected') {
          setIsLoading(false);
          setIsWaitingForUserInput(true);
        }
      });
      
      // Establish connection
      webSocketService.connect().catch(error => {
        console.error('Failed to connect to WebSocket:', error);
        setResponse('Sorry, I encountered an error connecting to EVA. Please try again later.');
        setIsLoading(false);
      });
      
      // Set up message handler
      webSocketService.setMessageCallback(handleWebSocketMessage);
    }
    
    // Clean up when component unmounts
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }
      // Clear callback
      webSocketService.setMessageCallback(null);
      webSocketService.setConnectionStatusCallback(null);
    };
  }, []);

  useEffect(() => {
    if (query && !isLoading && !response && isConnected) {
      // Process the query via WebSocket
      sendQueryViaWebSocket(query);
    } else if (query && !isConnected) {
      // Show error if not connected
      setResponse('Waiting for connection to EVA server. Please wait...');
    }
  }, [query, isConnected]);
  
  // Effect to process the audio queue
  useEffect(() => {
    if (audioQueue.current.length > 0 && !isEVATalking && isClient) {
      if (config.debug.logAudioOperations) {
        console.log(`Audio queue has ${audioQueue.current.length} items and EVA is not talking. Playing next audio.`);
      }
      console.log('Detected: audioQueue has items, isEVATalking=false, isClient=true - will play next audio');
      const nextAudio = audioQueue.current.shift();
      
      // Use a short timeout to ensure React has time to update any state
      debugLog('Using setTimeout in queue processor to ensure state updates');
      setTimeout(() => {
        playAudio(nextAudio);
      }, 50);
    } else if (audioQueue.current.length > 0 && isEVATalking) {
      if (config.debug.logAudioOperations) {
        console.log(`Audio queue has ${audioQueue.current.length} items but EVA is currently talking.`);
      }
      console.log('Detected: audioQueue has items but isEVATalking=true - waiting for current audio to finish');
    } else if (audioQueue.current.length > 0 && !isClient) {
      console.log('Warning: audioQueue has items but isClient=false - cannot play audio yet');
    } else if (audioQueue.current.length === 0) {
      console.log('Audio queue is empty - nothing to play');
    }
  }, [isEVATalking, isClient, audioQueue.current.length]);
  
  // Effect to add a fallback mechanism for isEVATalking state
  // If talking state is stuck, this will reset it after 10 seconds of inactivity
  useEffect(() => {
    if (isEVATalking && lastAudioPlayedTime.current) {
      const timeSinceLastAudio = Date.now() - lastAudioPlayedTime.current;
      if (timeSinceLastAudio > 10000) { // 10 seconds
        debugLog(`Talking state appears stuck for ${timeSinceLastAudio}ms. Resetting to false.`, 'warning');
        setIsEVATalking(false);
      }
    }

    // Check every 2 seconds
    const intervalId = setInterval(() => {
      if (isEVATalking && audioRef.current) {
        // If there's an audio element but it's not actually playing, reset the state
        if (audioRef.current.paused || audioRef.current.ended) {
          debugLog('Audio is paused or ended but isEVATalking=true. Resetting state.', 'warning');
          setIsEVATalking(false);
        }
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [isEVATalking]);
  
  const handleWebSocketMessage = (message) => {
    if (!message) return;
    
    console.log('Processing message:', message);
    
    if (message.type === 'audio') {
      // Add audio to queue for processing
      const audioUrl = message.content;
      
      // Set speech text if provided (for captions)
      if (message.text) {
        console.log('Setting speech text from audio message:', message.text);
        setSpeechText(message.text);
        setResponse(message.text);
      }
      
      console.log('Queueing audio from:', audioUrl);
      
      // Extract filename for logging
      const filename = extractAudioFilename(audioUrl);
      
      // Add to audio queue
      audioQueue.current.push(audioUrl);
      
      // Log the current talking state
      console.log('Current EVA talking state:', isEVATalking);
      
      // If not currently talking, play the next audio
      if (!isEVATalking && isClient) {
        console.log('EVA not talking, playing next audio from queue');
        const nextAudio = audioQueue.current.shift();
        // Verify the nextAudio is valid before attempting to play
        if (nextAudio && typeof nextAudio === 'string' && nextAudio.trim() !== '') {
          debugLog('Using setTimeout to ensure state updates before playing audio');
          // Use a short timeout to ensure React has time to update the state
          setTimeout(() => {
            playAudio(nextAudio);
          }, 50);
        } else {
          console.warn('Invalid audio URL removed from queue', nextAudio);
          // Continue to the next item in queue if this one is invalid
          if (audioQueue.current.length > 0) {
            setTimeout(() => {
              const nextValidAudio = audioQueue.current.shift();
              if (nextValidAudio && typeof nextValidAudio === 'string' && nextValidAudio.trim() !== '') {
                playAudio(nextValidAudio);
              }
            }, 50);
          }
        }
      } else {
        console.log('EVA is already talking or not ready, audio added to queue for later playback');
      }
      
      setIsLoading(false);
    } 
    else if (message.type === 'html') {
      setHtmlContent(message.content);
      setIsLoading(false);
    }
    else if (message.type === 'over') {
      // Conversation turn is over, with new session ID
      if (message.content) {
        console.log('Received new session ID:', message.content);
        // Update our session ID
        webSocketService.sessionId = message.content;
      }
      setIsLoading(false);
      
      // If the backend sends 'over', it's waiting for the next user input
      setIsWaitingForUserInput(true);
    }
    else if (message.wait === true) {
      // Backend explicitly tells us it's waiting for user input
      console.log('EVA is waiting for user input');
      setIsWaitingForUserInput(true);
      setIsLoading(false);
    }
    else if (message.speech) {
      // Speech response from EVA
      console.log('Received speech response:', message.speech);
      setSpeechText(message.speech);
      setResponse(message.speech);
      setIsLoading(false);
    }
    else if (message.text) {
      // Text in the message (sometimes comes with audio)
      console.log('Received text in message:', message.text);
      setSpeechText(message.text);
      setResponse(message.text);
      setIsLoading(false);
    }
    else if (message.response) {
      // Legacy format (direct response text)
      console.log('Received response in message:', message.response);
      setResponse(message.response);
      setIsLoading(false);
    }
    else {
      console.log('Unhandled message type:', message);
    }
  };

  const sendQueryViaWebSocket = async (queryText) => {
    try {
      console.log('Sending query to WebSocket:', queryText);
      await webSocketService.sendMessage(queryText);
    } catch (error) {
      console.error('Error sending query via WebSocket:', error);
      setResponse('Sorry, I encountered an error while processing your request.');
      setIsLoading(false);
    }
  };

  // Function to handle audio recording
  const handleAudioRecorded = async (audioBlob) => {
    if (isLoading) return;
    
    // Mark that we're processing and not waiting for user input
    setIsWaitingForUserInput(false);
    setIsLoading(true);
    setUserSpeaking(false);
    
    // Clear previous response
    setResponse('');
    setSpeechText('');
    setHtmlContent(null);
    
    // Reset EVA talking state
    setIsEVATalking(false);
    
    // Clear audio queue
    audioQueue.current = [];
    
    try {
      console.log(`Received audio blob: size=${audioBlob.size}, type=${audioBlob.type}`);
      
      // Validate the audioBlob more thoroughly
      if (!audioBlob) {
        throw new Error('No audio data received');
      }
      
      if (audioBlob.size === 0) {
        throw new Error('Empty audio recording received');
      }
      
      if (audioBlob.size < 1000) {
        console.warn(`Audio recording is very small (${audioBlob.size} bytes), might be too short`);
        // Continue but warn the user
        setResponse('Processing your message... (Warning: short audio detected)');
      } else {
        // Set temporary response during processing
        setResponse('Processing your message...');
      }
      
      // Debug audio format info
      console.log('Audio format details:');
      console.log(`- Size: ${audioBlob.size} bytes`);
      console.log(`- MIME type: ${audioBlob.type}`);
      
      // Check compatibility with backend
      const isWebm = audioBlob.type.includes('webm');
      const isWav = audioBlob.type.includes('wav');
      
      if (!isWebm && !isWav) {
        console.log('Audio is not in WebM or WAV format, conversion will be needed');
      } else {
        console.log(`Audio is in ${isWebm ? 'WebM' : 'WAV'} format, should be compatible with backend`);
      }
      
      console.log('Sending audio to backend...');
      
      // Send audio via WebSocket, our updated service will handle conversion if needed
      try {
        await webSocketService.sendAudio(audioBlob);
        console.log('Audio sent successfully to WebSocket service');
      } catch (socketError) {
        console.error('WebSocket error sending audio:', socketError);
        throw new Error(`Communication error: ${socketError.message || 'Failed to send audio to server'}`);
      }
      
      console.log('Audio sent successfully, waiting for response...');
      // The response will come through the WebSocket message handler
      
      // Set a timeout to handle cases where server doesn't respond
      // This provides better UX than waiting indefinitely
      const messageTimeout = setTimeout(() => {
        if (isLoading) {
          console.warn('No response received from server after 15 seconds');
          setIsLoading(false);
          setResponse('The server is taking longer than expected to respond. Please try again or try a different message.');
        }
      }, 15000); // 15 second timeout
      
      // Clear timeout if component unmounts
      return () => clearTimeout(messageTimeout);
      
    } catch (error) {
      console.error('Error processing speech:', error);
      setIsLoading(false);
      
      // Provide a more specific error message based on the error type
      let errorMessage;
      
      if (!error) {
        errorMessage = 'An unknown error occurred while processing your speech.';
      } else if (error.name === 'NotAllowedError') {
        errorMessage = 'Microphone access is required. Please grant permission in your browser settings.';
      } else if (error.message?.includes('audio format')) {
        errorMessage = 'Your audio format is not supported. Please try again with a different device or browser.';
      } else if (error.message?.includes('convert')) {
        errorMessage = 'Could not process the audio data. Please try speaking more clearly or use a better microphone.';
      } else if (error.message?.includes('empty') || error.message?.includes('short')) {
        errorMessage = 'Your recording was too short or empty. Please hold the button and speak clearly.';
      } else if (error.message?.includes('connect') || error.message?.includes('Communication')) {
        errorMessage = 'Could not connect to the server. Please check your internet connection and try again.';
      } else {
        // Use the error message if available, otherwise a generic message
        errorMessage = `Error: ${error.message || 'Failed to process speech. Please try again.'}`;
      }
      
      setResponse(errorMessage);
    }
  };

  const playAudio = (audioUrl) => {
    if (!isClient || !audioUrl) {
      console.warn('Cannot play audio: isClient =', isClient, 'audioUrl =', audioUrl);
      // Even if we can't play, make sure we're not stuck in a talking state
      setIsEVATalking(false);
      return;
    }
    
    // Validate the audioUrl before proceeding
    if (typeof audioUrl !== 'string' || audioUrl.trim() === '') {
      console.error('Invalid audio URL provided:', audioUrl);
      setIsEVATalking(false);
      
      // Try the next audio in queue if available
      if (audioQueue.current.length > 0) {
        const nextAudio = audioQueue.current.shift();
        if (nextAudio && typeof nextAudio === 'string' && nextAudio.trim() !== '') {
          setTimeout(() => playAudio(nextAudio), 100);
        }
      }
      return;
    }
    
    // Update the last audio played timestamp
    lastAudioPlayedTime.current = Date.now();
    
    // Log the original URL for debugging
    console.log('Original audio URL:', audioUrl);
    
    // Set isEVATalking to true before starting to fetch/play
    setIsEVATalking(true);
    
    // Clean up any existing audio element to prevent conflicts
    if (audioRef.current) {
      debugLog('Cleaning up previous audio element before playing new audio');
      try {
        // Remove event listeners to prevent memory leaks
        const oldAudio = audioRef.current;
        const eventsToRemove = ['canplay', 'play', 'ended', 'error'];
        eventsToRemove.forEach(event => {
          oldAudio.removeEventListener(event, () => {});
        });
        
        // Stop playback and clear source
        oldAudio.pause();
        oldAudio.src = '';
        
        // Set to null to allow garbage collection
        audioRef.current = null;
      } catch (e) {
        debugLog(`Error cleaning up previous audio: ${e.message}`, 'error');
      }
    }
    
    // Extract session ID from URL if present for debugging
    let sessionId = null;
    try {
      const url = new URL(audioUrl);
      sessionId = url.searchParams.get('session_id');
      
      // If no session ID in URL, use the current session ID
      if (!sessionId) {
        sessionId = webSocketService.sessionId;
        
        // Add session ID to URL if not already present
        if (!audioUrl.includes('session_id=')) {
          audioUrl = `${audioUrl}${audioUrl.includes('?') ? '&' : '?'}session_id=${sessionId}`;
        }
      }
    } catch (e) {
      console.log('Could not parse URL for session ID:', e);
      sessionId = webSocketService.sessionId;
      
      // Handle the case where audioUrl is not a valid URL (might be a relative path)
      if (!audioUrl.includes('http://') && !audioUrl.includes('https://')) {
        // Check if this is a relative path like 'audio/filename.mp3'
        if (audioUrl.startsWith('audio/')) {
          const filename = audioUrl.split('audio/')[1]?.split('?')[0];
          if (filename) {
            console.log('Converting relative audio path to absolute URL:', filename);
            const baseUrl = config.api.baseUrl;
            audioUrl = `${baseUrl}/download/audio/${filename}?session_id=${sessionId}`;
          }
        }
      }
    }
    
    // Use the audioUrl as is, with session ID for cache busting
    const cacheBustUrl = audioUrl;
    
    console.log('Final audio URL to fetch:', cacheBustUrl);
    
    // Clear any currently playing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
    }
    
    console.log('Attempting to play audio from:', cacheBustUrl, sessionId ? `(Session: ${sessionId})` : '');
    
    // Skip audio playback if disabled in config
    if (!config.behavior.audioEnabled) {
      console.log('Audio playback disabled in config, skipping');
      setIsEVATalking(false);
      
      // Try the next audio in queue
      if (audioQueue.current.length > 0) {
        const nextAudio = audioQueue.current.shift();
        setTimeout(() => playAudio(nextAudio), 100);
      }
      return;
    }
    
    // First fetch the audio file
    console.log(`Fetching audio from: ${cacheBustUrl}`);
    fetch(cacheBustUrl, { 
      method: 'GET',
      headers: {
        'Accept': 'audio/mpeg, audio/*',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      },
      credentials: 'same-origin'
    })
      .then(response => {
        console.log(`Fetch response received - Status: ${response.status}, OK: ${response.ok}`);
        if (response.headers) {
          console.log(`Response headers:`, Object.fromEntries([...response.headers]));
        }
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.blob();
      })
      .then(blob => {
        console.log(`Blob received - Size: ${blob.size}, Type: ${blob.type}`);
        
        if (blob.size === 0) {
          throw new Error('Empty audio blob received');
        }
        
        // Create object URL from the blob
        const objectUrl = URL.createObjectURL(blob);
        
        // Log the successful fetch
        console.log('Successfully fetched audio and created object URL:', objectUrl);
        
        // Create new Audio element and play it from the object URL
        const audio = new Audio();
        audioRef.current = audio;
        
        // Set up event listeners before setting the source
        audio.addEventListener('canplay', () => {
          console.log('Audio can play event fired');
        });
        
        audio.addEventListener('play', () => {
          console.log('Audio playback started');
          setIsEVATalking(true);
          
          // Show captions if enabled in config
          if (config.behavior.captions && speechText) {
            setSpeechVisible(true);
          }
        });
        
        audio.addEventListener('ended', () => {
          console.log('Audio playback ended');
          setIsEVATalking(false);
          setSpeechVisible(false);
          
          // Revoke the object URL to avoid memory leaks
          URL.revokeObjectURL(objectUrl);
          
          // Play next audio in queue if available
          if (audioQueue.current.length > 0) {
            const nextAudio = audioQueue.current.shift();
            setTimeout(() => playAudio(nextAudio), 300);
          }
        });
        
        // Set up error handling
        audio.addEventListener('error', (err) => {
          const errorDetails = audio.error ? {
            code: audio.error.code,
            message: audio.error.message
          } : { message: 'Unknown audio error' };
          
          console.error('Audio playback error:', errorDetails);
          
          // Revoke the object URL to avoid memory leaks
          URL.revokeObjectURL(objectUrl);
          setIsEVATalking(false);
          
          // Try next audio in queue
          if (audioQueue.current.length > 0) {
            const nextAudio = audioQueue.current.shift();
            setTimeout(() => playAudio(nextAudio), 300);
          }
        });
        
        // Set audio properties
        audio.crossOrigin = "anonymous";
        audio.preload = "auto";
        audio.src = objectUrl;
        
        // Play the audio
        console.log('Attempting to play audio now...');
        const playPromise = audio.play();
        if (playPromise !== undefined) {
          playPromise
            .then(() => {
              console.log('Audio playback started successfully via Promise');
            })
            .catch(err => {
              console.error('Error starting audio playback:', err);
              
              // Clean up on error
              URL.revokeObjectURL(objectUrl);
              setIsEVATalking(false);
              
              // Try next audio in queue after error
              if (audioQueue.current.length > 0) {
                const nextAudio = audioQueue.current.shift();
                setTimeout(() => playAudio(nextAudio), 300);
              }
            });
        } else {
          console.error('Play promise is undefined, this might indicate browser autoplay restrictions');
        }
      })
      .catch(error => {
        console.error('Failed to fetch or process audio file:', error, cacheBustUrl);
        
        // Ensure isEVATalking is reset on error
        setIsEVATalking(false);
        
        // Try the next audio in case of error
        if (audioQueue.current.length > 0) {
          const nextAudio = audioQueue.current.shift();
          if (nextAudio && typeof nextAudio === 'string' && nextAudio.trim() !== '') {
            setTimeout(() => playAudio(nextAudio), 300);
          }
        }
      });
  };

  // Function to cut off EVA's speech
  const cutoffEVA = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsEVATalking(false);
    }
  };

  const handleReset = () => {
    cutoffEVA();
    setResponse('');
    setSpeechText('');
    setHtmlContent(null);
    setIsLoading(false);
    onReset();
  };

  // Function to handle when user starts speaking
  const handleUserSpeakingStart = () => {
    setUserSpeaking(true);
  };

  // Function to handle when user stops speaking
  const handleUserSpeakingEnd = () => {
    setUserSpeaking(false);
  };

  // Determine whether to show the space button - always show except during initial loading
  const showSpaceButton = !isLoading || (isWaitingForUserInput || isEVATalking);

  // Get current status
  const status = getStatusLabel();

  return (
    <div className="w-full">
      {/* Main UI Container - unified design for all states */}
      <div className="w-full p-4 transition-all duration-300">
        {/* Single Status indicator */}
        <div className="flex items-center justify-between mb-4">
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-sm font-medium bg-opacity-20 bg-${status.color}-500 text-${status.color}-300`}>
            {status.text === 'Ready' && (
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-ping mr-1.5"></span>
            )}
            {status.text}
          </span>
        </div>
        
        {/* Main content area with fixed height */}
        <div className="flex flex-col items-center min-h-[280px] relative">
          {/* Processing state with animation - circle only, no text */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center h-full">
              <EVAAnimation isActive={true} mode="processing" />
            </div>
          )}
          
          {/* Response content when available */}
          {(response || htmlContent) && !isLoading && (
            <div className="w-full mt-2 text-center px-4">
              {/* Show query if available */}
              {query && (
                <div className="mb-2">
                  <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-1">You</h3>
                  <p className="text-gray-300 text-sm">{query}</p>
                </div>
              )}
              
              {/* Show response - centered and higher up */}
              <div className="text-gray-200 mt-2">
                {htmlContent ? (
                  <div className="text-gray-200 overflow-auto max-h-96" dangerouslySetInnerHTML={{ __html: htmlContent }} />
                ) : (
                  <div>
                    <p className="text-gray-200 whitespace-pre-wrap text-center">{response}</p>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Waiting for input state */}
          {isWaitingForUserInput && !isLoading && !response && !htmlContent && (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="transform scale-75">
                <EVAAnimation isActive={false} />
              </div>
              <p className="text-gray-400 mt-2 text-sm">Press space to speak</p>
            </div>
          )}
          
          {/* Audio recorder - show in most states except during initial loading */}
          {showSpaceButton && (
            <div className="absolute bottom-2">
              <AudioRecorder 
                onRecordingComplete={handleAudioRecorded} 
                disabled={isLoading && !isEVATalking}
                isEVATalking={isEVATalking}
                cutoffEVA={cutoffEVA}
                onRecordingStart={handleUserSpeakingStart}
                onRecordingEnd={handleUserSpeakingEnd}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EVAResponse; 