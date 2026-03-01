import { useState, useEffect, useRef, useCallback } from 'react';
import lamejs from 'lamejs';

const AudioRecorder = ({ 
  onRecordingComplete, 
  disabled, 
  isEVATalking, 
  cutoffEVA,
  onRecordingStart,
  onRecordingEnd
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [hasPermission, setHasPermission] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioContextRef = useRef(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const actualDurationRef = useRef(0);
  const timerRef = useRef(null);
  const [recordingError, setRecordingError] = useState(null);
  
  // Check if we're on client-side
  useEffect(() => {
    setIsClient(true);
    
    // Initialize AudioContext if available
    if (typeof window !== 'undefined') {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioContextRef.current = new AudioContext({
          sampleRate: 16000 // Set initial sample rate to 16kHz to match backend
        });
      }
    }
    
    // Cleanup
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(console.error);
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);
  
  // Add keyboard event listener for space key
  useEffect(() => {
    if (!isClient) return;
    
    const handleKeyDown = (e) => {
      // Only trigger if space is pressed
      if (e.code === 'Space') {
        // Prevent default space behavior (scrolling)
        e.preventDefault();
        
        // If EVA is talking, stop it first
        if (isEVATalking && cutoffEVA) {
          cutoffEVA();
          return; // Don't start recording right away after stopping EVA
        }
        
        // If not already recording and not disabled, start recording
        if (!isRecording && !disabled) {
          startRecording();
        }
      }
    };
    
    const handleKeyUp = (e) => {
      // Only trigger if space is released and currently recording
      if (e.code === 'Space' && isRecording) {
        stopRecording();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [isClient, isRecording, disabled, isEVATalking]);
  
  // Reset recording duration when stopped
  useEffect(() => {
    if (!isRecording) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRecordingDuration(0);
    }
  }, [isRecording]);
  
  const startRecording = async () => {
    if (!isClient || disabled) return;
    
    // Reset any previous errors
    setRecordingError(null);
    
    // If EVA is talking, cut off the audio
    if (isEVATalking && cutoffEVA) {
      cutoffEVA();
    }
    
    try {
      // Get microphone permission with specific constraints for backend compatibility
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,           // Mono audio (required by backend)
          sampleRate: 16000,         // 16kHz sample rate (expected by backend)
          echoCancellation: true,    // Enable echo cancellation 
          noiseSuppression: true,    // Enable noise suppression
          autoGainControl: true      // Enable auto gain control
        } 
      });
      
      setHasPermission(true);
      
      // Choose best MIME type for compatibility with backend
      // Order of preference: audio/webm > audio/ogg > audio/wav
      let mimeType = 'audio/wav'; // Default fallback
      
      if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm';
      } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
        mimeType = 'audio/ogg';
      }
      
      console.log(`Recording with MIME type: ${mimeType}, sample rate: 16000Hz, mono channel`);
      
      // Create MediaRecorder with options
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 128000 // 128 kbps
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      // Handle data available event
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        } else {
          console.warn('Received empty audio chunk');
        }
      };
      
      // Handle recording error
      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        setRecordingError('Recording failed. Please try again.');
        stopRecording();
      };
      
      // Reset actual duration on start
      actualDurationRef.current = 0;
      
      // Handle recording stop
      mediaRecorder.onstop = async () => {
        // Call the onRecordingEnd callback if provided
        if (onRecordingEnd) {
          onRecordingEnd();
        }
        
        try {
          // Create a blob with the recorded audio
          if (audioChunksRef.current.length === 0) {
            console.warn('No audio chunks recorded');
            setRecordingError('No audio data recorded. Please try again.');
            return;
          }
          
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
          console.log(`Recording complete. Blob size: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
          
          // Stop all tracks to release microphone
          stream.getTracks().forEach(track => track.stop());
          
          // Validate audio blob
          if (!audioBlob || audioBlob.size < 100) {
            console.warn('Audio recording too small or invalid');
            setRecordingError('Recording too short or invalid. Please try again.');
            return;
          }
          
          // Validate recording length using the ref instead of state
          // This ensures we have the most up-to-date duration value
          console.log(`Actual recording duration: ${actualDurationRef.current.toFixed(1)}s`);
          if (actualDurationRef.current < 0.5) {
            console.warn('Recording too short, ignoring');
            setRecordingError('Recording too short. Please hold for at least 0.5 seconds.');
            return;
          }
          
          // Process the audio blob to ensure it's in a format the backend can handle
          const processedBlob = await processAudioBlob(audioBlob, mimeType);
          
          // Check if conversion failed
          if (!processedBlob) {
            console.error('Audio conversion failed, not sending to backend');
            setRecordingError('Audio processing failed. Please try again.');
            return;
          }
          
          // Send the processed audio to parent component
          if (onRecordingComplete) {
            onRecordingComplete(processedBlob);
          } else {
            console.error('No callback provided for recording completion');
          }
        } catch (error) {
          console.error('Error processing recording:', error);
          setRecordingError('Error processing recording. Please try again.');
        }
      };
      
      // Start recording with smaller timeslices for better chunks
      mediaRecorder.start(500);
      setIsRecording(true);
      
      // Call the onRecordingStart callback if provided
      if (onRecordingStart) {
        onRecordingStart();
      }
      
      // Start a timer to track recording duration
      let duration = 0;
      timerRef.current = setInterval(() => {
        duration += 0.1;
        actualDurationRef.current = duration; // Update the ref value directly
        setRecordingDuration(duration);
      }, 100);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      
      // Set permission denied state
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        setHasPermission(false);
        setRecordingError('Microphone access denied. Please enable microphone access in your browser settings.');
      } else {
        setRecordingError(`Microphone error: ${error.message}`);
      }
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      console.log('Stopping recording...');
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Clear the timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };
  
  // Function to process audio blob to ensure compatibility with backend
  const processAudioBlob = async (blob, originalMimeType) => {
    try {
      console.log(`Processing audio blob: size=${blob.size}, type=${originalMimeType}`);
      
      // Try to convert to MP3 using lamejs for better compatibility with FFmpeg
      try {
        const mp3Blob = await convertToMp3(blob);
        console.log(`Converted to MP3 using lamejs: size=${mp3Blob.size}`);
        return mp3Blob;
      } catch (conversionError) {
        console.error('Error converting audio format:', conversionError);
        
        // For debugging: try with original WebM data as a fallback
        console.warn('Falling back to original WebM audio format');
        
        // Check if the original format is already compatible with backend
        if (originalMimeType === 'audio/webm') {
          // If it's WebM, we'll try to send as WAV instead
          try {
            console.log('Attempting to convert WebM to WAV as a fallback');
            const wavBlob = await convertToWav(blob);
            return wavBlob;
          } catch (wavError) {
            console.error('Fallback WAV conversion also failed:', wavError);
            return null;
          }
        }
        
        // Since all conversions failed, we'll return null to indicate a failure
        return null;
      }
    } catch (error) {
      console.error('Error in audio processing:', error);
      return null;
    }
  };
  
  // Convert WebM to WAV as a fallback
  const convertToWav = async (audioBlob) => {
    return new Promise((resolve, reject) => {
      try {
        console.log('Converting audio to WAV format as fallback...');
        
        // Create an audio context
        const audioContext = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 16000 // Match the sample rate expected by the backend
        });
        
        // Read the original blob as an ArrayBuffer
        const reader = new FileReader();
        reader.onload = async () => {
          try {
            // Decode the audio data
            const audioData = await audioContext.decodeAudioData(reader.result);
            
            // Prepare for export as WAV
            const numberOfChannels = 1; // Mono
            const sampleRate = 16000; // 16kHz as required by backend
            const length = audioData.length;
            
            // Create a new AudioBuffer with the correct specs
            const offlineContext = new OfflineAudioContext(numberOfChannels, length, sampleRate);
            const bufferSource = offlineContext.createBufferSource();
            bufferSource.buffer = audioData;
            bufferSource.connect(offlineContext.destination);
            bufferSource.start(0);
            
            // Render to buffer
            const renderedBuffer = await offlineContext.startRendering();
            
            // Convert to WAV format
            const wavBlob = bufferToWav(renderedBuffer);
            console.log(`Converted audio to WAV: ${wavBlob.size} bytes`);
            
            // Clean up
            audioContext.close();
            
            resolve(wavBlob);
          } catch (decodingError) {
            console.error('Error decoding audio data for WAV conversion:', decodingError);
            reject(decodingError);
          }
        };
        
        reader.onerror = (error) => {
          console.error('Error reading audio blob for WAV conversion:', error);
          reject(error);
        };
        
        reader.readAsArrayBuffer(audioBlob);
      } catch (error) {
        console.error('Error in WAV conversion:', error);
        reject(error);
      }
    });
  };
  
  // Helper function to convert AudioBuffer to WAV Blob
  const bufferToWav = (buffer) => {
    const numberOfChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const length = buffer.length * numberOfChannels * 2;
    const arrayBuffer = new ArrayBuffer(44 + length);
    const view = new DataView(arrayBuffer);
    
    // Write WAV header
    // "RIFF" chunk descriptor
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + length, true);
    writeString(view, 8, 'WAVE');
    
    // "fmt " sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // subchunk1size
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * 2, true); // byte rate
    view.setUint16(32, numberOfChannels * 2, true); // block align
    view.setUint16(34, 16, true); // bits per sample
    
    // "data" sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, length, true);
    
    // Write audio data
    const offset = 44;
    for (let i = 0; i < buffer.numberOfChannels; i++) {
      const channelData = buffer.getChannelData(i);
      let pos = offset;
      
      for (let j = 0; j < channelData.length; j++, pos += 2) {
        const sample = Math.max(-1, Math.min(1, channelData[j]));
        view.setInt16(pos, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      }
    }
    
    return new Blob([view], { type: 'audio/wav' });
  };
  
  // Helper to write strings to the DataView
  const writeString = (view, offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };
  
  // Convert audio to MP3 format using lamejs
  const convertToMp3 = async (audioBlob) => {
    return new Promise((resolve, reject) => {
      try {
        console.log('Converting audio to MP3 format using lamejs...');
        
        // Create an audio context
        const audioContext = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 16000 // Match the sample rate expected by the backend
        });
        
        // Read the original blob as an ArrayBuffer
        const reader = new FileReader();
        reader.onload = async () => {
          try {
            // Decode the audio data
            const audioData = await audioContext.decodeAudioData(reader.result);
            
            // Prepare encoding parameters
            const sampleRate = 16000; // Force 16kHz for backend compatibility
            const channels = 1; // Mono audio (required by backend)
            const kbps = 128; // 128 kbps bitrate
            
            // Fix for "MPEGMode is not defined" error
            // Create the encoder directly without mode constants
            const mp3encoder = new lamejs.Mp3Encoder(channels, sampleRate, kbps);
            
            // Get audio PCM data
            const pcmData = audioData.getChannelData(0); // Get PCM data for the first channel
            
            // Convert Float32 [-1.0, 1.0] samples to Int16 [-32768, 32767]
            const samples = new Int16Array(pcmData.length);
            for (let i = 0; i < pcmData.length; i++) {
              samples[i] = Math.max(-1, Math.min(1, pcmData[i])) * 32767.5; // Scale and clamp
            }
            
            const data = [];
            const sampleBlockSize = 1152; // MP3 frame size for MPEG-1 Layer III
            
            // Encode the PCM data in chunks according to lamejs example
            for (let i = 0; i < samples.length; i += sampleBlockSize) {
              const chunk = samples.subarray(i, i + sampleBlockSize);
              const mp3buf = mp3encoder.encodeBuffer(chunk);
              if (mp3buf.length > 0) {
                data.push(mp3buf);
              }
            }
            
            // Finish encoding
            const mp3buf = mp3encoder.flush();
            if (mp3buf.length > 0) {
              data.push(mp3buf);
            }
            
            // Create the final MP3 Blob
            const mp3Blob = new Blob(data, { type: 'audio/mp3' });
            console.log(`MP3 encoding complete: size=${mp3Blob.size} bytes`);
            
            // Clean up
            audioContext.close();
            
            resolve(mp3Blob);
          } catch (decodingError) {
            console.error('Error decoding audio data:', decodingError);
            reject(decodingError);
          }
        };
        
        reader.onerror = (error) => {
          console.error('Error reading audio blob for MP3 conversion:', error);
          reject(error);
        };
        
        reader.readAsArrayBuffer(audioBlob);
      } catch (error) {
        console.error('Error in MP3 conversion:', error);
        reject(error);
      }
    });
  };
  
  // If we're on the server, render nothing
  if (!isClient) return null;
  
  // Format recording time as seconds
  const formatTime = (seconds) => {
    return seconds.toFixed(1) + 's';
  };
  
  // Get appropriate button label based on state
  const getButtonLabel = () => {
    if (isRecording) return `Recording ${formatTime(recordingDuration)}`;
    if (isEVATalking) return "Press space to stop";
    return "Hold space to speak";
  };
  
  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <div 
          className={`flex items-center justify-center space-x-2 px-5 py-3
            border border-opacity-25 backdrop-blur-sm rounded-full
            ${isRecording 
              ? 'bg-red-500 bg-opacity-15 border-red-400 shadow-sm shadow-red-900/10' 
              : isEVATalking 
                ? 'bg-blue-500 bg-opacity-15 border-red-400 shadow-sm shadow-red-900/10'
                : 'bg-blue-500 bg-opacity-10 border-blue-400 shadow-sm shadow-blue-900/10'
            } 
            transition-all duration-300
          `}
        >
          <div className={`w-6 h-6 mr-2 ${isRecording ? 'text-red-300' : isEVATalking ? 'text-red-300' : 'text-blue-300'}`}>
            {isRecording ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="animate-pulse">
                <path d="M8 5a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1H8Z" />
              </svg>
            ) : isEVATalking ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 18.75a.75.75 0 0 0 .75.75h.75a.75.75 0 0 0 .75-.75V6a.75.75 0 0 0-.75-.75h-.75A.75.75 0 0 0 6 6v12.75ZM16.5 18.75a.75.75 0 0 0 .75.75h.75a.75.75 0 0 0 .75-.75V6a.75.75 0 0 0-.75-.75h-.75a.75.75 0 0 0-.75.75v12.75Z" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
                <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
              </svg>
            )}
          </div>
          <span className={`text-base ${isRecording ? 'text-red-300' : isEVATalking ? 'text-red-300' : 'text-blue-300'}`}>
            {getButtonLabel()}
          </span>
        </div>
      </div>
      
      {recordingError && (
        <div className="text-red-400 text-xs mt-2 max-w-xs text-center">
          {recordingError}
        </div>
      )}
    </div>
  );
};

export default AudioRecorder; 