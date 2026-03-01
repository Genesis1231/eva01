import { useState, useRef, useEffect } from 'react';
import webSocketService from '../services/WebSocketService';
import config from '../config';

const VideoCapture = ({ onImageCaptured }) => {
  const [isClient, setIsClient] = useState(false);
  const [cameraStatus, setCameraStatus] = useState('initializing'); // 'initializing', 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  
  // Set isClient to true when component mounts
  useEffect(() => {
    setIsClient(true);
  }, []);
  
  // Start camera when component mounts on client side
  useEffect(() => {
    if (!isClient) return;
    
    // Try to start the camera after a short delay
    const timer = setTimeout(() => {
      initializeCamera();
    }, 1000);
    
    // Clean up function to run when component unmounts
    return () => {
      clearTimeout(timer);
      stopCamera();
    };
  }, [isClient]);

  // Set up handler for backend requests for images
  useEffect(() => {
    if (!isClient) return;
    
    console.log('Setting up image request handler in VideoCapture');
    
    // Create handler that will be called when backend requests an image
    const handleImageRequest = (requestType) => {
      console.log(`CRITICAL: Backend requested an image capture: ${requestType || 'frontImage'}`);
      
      if (cameraStatus === 'success' && !isCapturing) {
        // By default, send frontImage if not specified
        const isFrontImage = !requestType || requestType === 'frontImage';
        console.log(`CRITICAL: Camera available, capturing ${isFrontImage ? 'frontImage' : 'backImage'}`);
        captureAndSendImage(isFrontImage);
      } else if (cameraStatus === 'error') {
        // Try to send a fallback image if camera isn't available
        const isFrontImage = !requestType || requestType === 'frontImage';
        console.log(`CRITICAL: Camera unavailable, creating fallback ${isFrontImage ? 'frontImage' : 'backImage'}`);
        createFallbackImage(isFrontImage);
      } else {
        console.log(`CRITICAL: Cannot capture image - Camera status: ${cameraStatus}, isCapturing: ${isCapturing}`);
      }
    };
    
    // Register with WebSocket service
    webSocketService.setImageRequestCallback(handleImageRequest);
    console.log('CRITICAL: Image request handler registered with WebSocketService');
    
    return () => {
      // Clear the callback when component unmounts
      console.log('Clearing image request handler');
      webSocketService.setImageRequestCallback(null);
    };
  }, [isClient, cameraStatus, isCapturing]);
  
  // When camera becomes available, automatically send the first image
  // This avoids waiting for explicit request from backend
  useEffect(() => {
    // If camera just became ready, send an initial image
    if (cameraStatus === 'success' && !isCapturing) {
      console.log('Camera is now ready, sending initial image');
      // Short timeout to ensure everything is initialized
      setTimeout(() => {
        captureAndSendImage(true); // true = frontImage
      }, 1000);
    }
  }, [cameraStatus]);
  
  // Initialize the camera with a clean implementation
  const initializeCamera = async () => {
    try {
      // Request high-quality video
      const constraints = {
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      // Store the stream reference for cleanup
      streamRef.current = stream;
      
      // Set the video source
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        
        // Update status when video can play
        videoRef.current.onloadedmetadata = () => {
          setCameraStatus('success');
        };
      }
    } catch (error) {
      console.error('Camera initialization error:', error);
      setCameraStatus('error');
      setErrorMessage(error.message || 'Could not access camera');
      createFallbackImage();
    }
  };
  
  // Stop the camera and clean up resources
  const stopCamera = () => {
    if (streamRef.current) {
      const tracks = streamRef.current.getTracks();
      tracks.forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };
  
  // Capture an image from the video feed and send it via WebSocket
  const captureAndSendImage = (isFrontImage = true) => {
    if (!isClient || cameraStatus !== 'success' || !videoRef.current || !canvasRef.current) {
      console.error(`CRITICAL: Cannot capture image - prerequisites not met:
        - isClient: ${isClient}
        - cameraStatus: ${cameraStatus}
        - videoRef: ${videoRef.current ? 'available' : 'not available'}
        - canvasRef: ${canvasRef.current ? 'available' : 'not available'}`);
      return;
    }
    
    console.log('CRITICAL: Starting image capture process');
    setIsCapturing(true);
    
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      // Set canvas dimensions to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      // Draw the current video frame to the canvas
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Add timestamp to the image
      context.fillStyle = 'rgba(255, 255, 255, 0.7)';
      context.fillRect(10, 10, 200, 20);
      context.fillStyle = 'black';
      context.font = '12px Arial';
      const timestamp = new Date().toLocaleString();
      context.fillText(`Captured: ${timestamp}`, 15, 25);
      
      // Add a label for the image type
      const imageTypeLabel = isFrontImage ? 'Observation' : 'View';
      context.fillStyle = 'rgba(0, 0, 0, 0.5)';
      context.fillRect(canvas.width - 100, 10, 90, 20);
      context.fillStyle = 'white';
      context.textAlign = 'right';
      context.fillText(imageTypeLabel, canvas.width - 15, 25);
      context.textAlign = 'left';
      
      console.log('CRITICAL: Canvas image prepared, converting to blob');
      
      // Convert the canvas to a Blob
      canvas.toBlob((blob) => {
        // Send the image via WebSocket
        console.log(`CRITICAL: Canvas converted to blob: ${blob.size} bytes. Sending to WebSocketService.`);
        webSocketService.sendImage(blob, isFrontImage);
        
        // Notify any callback if provided
        if (onImageCaptured && typeof onImageCaptured === 'function') {
          // Create a URL from the blob for the image preview
          const imageUrl = URL.createObjectURL(blob);
          onImageCaptured(imageUrl, isFrontImage ? 'observation' : 'view');
        }
        
        // Reset capturing state after a short delay
        setTimeout(() => {
          setIsCapturing(false);
        }, 500);
      }, 'image/jpeg', config.behavior.imageQuality); // Use configured image quality
    } catch (error) {
      console.error('CRITICAL ERROR: Failed capturing image:', error);
      setIsCapturing(false);
    }
  };
  
  // Create a fallback image when camera is not available
  const createFallbackImage = (isFrontImage = true) => {
    if (!isClient || !canvasRef.current) {
      return;
    }
    
    try {
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      // Set canvas size
      canvas.width = 640;
      canvas.height = 480;
      
      // Create a simple fallback image
      context.fillStyle = '#f0f0f0';
      context.fillRect(0, 0, canvas.width, canvas.height);
      
      // Add text explaining the fallback
      context.fillStyle = '#333333';
      context.font = '24px Arial';
      context.textAlign = 'center';
      context.fillText('Camera not available', canvas.width / 2, canvas.height / 2 - 20);
      context.fillText(isFrontImage ? 'Using fallback front image' : 'Using fallback back image', canvas.width / 2, canvas.height / 2 + 20);
      
      // Add timestamp
      context.font = '12px Arial';
      context.textAlign = 'left';
      context.fillText(`Generated: ${new Date().toLocaleString()}`, 15, 25);
      
      // Add a label for the image type
      const imageTypeLabel = isFrontImage ? 'Observation' : 'View';
      context.fillStyle = 'rgba(0, 0, 0, 0.5)';
      context.fillRect(canvas.width - 100, 10, 90, 20);
      context.fillStyle = 'white';
      context.textAlign = 'right';
      context.fillText(imageTypeLabel, canvas.width - 15, 25);
      context.textAlign = 'left';
      
      // Convert to blob and send
      canvas.toBlob((blob) => {
        // Send the fallback image via WebSocket
        console.log(`Sending fallback ${isFrontImage ? 'frontImage' : 'backImage'} to backend`);
        webSocketService.sendImage(blob, isFrontImage);
        
        if (onImageCaptured && typeof onImageCaptured === 'function') {
          // Create a URL from the blob for the image preview
          const imageUrl = URL.createObjectURL(blob);
          onImageCaptured(imageUrl, isFrontImage ? 'observation' : 'view');
        }
      }, 'image/jpeg', config.behavior.imageQuality);
    } catch (error) {
      console.error('Error creating fallback image:', error);
    }
  };
  
  // Render the component
  return (
    <div className="relative">
      {/* Camera Status Indicator */}
      {cameraStatus === 'initializing' && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 text-white z-10">
          Initializing camera...
        </div>
      )}
      
      {cameraStatus === 'error' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-800 bg-opacity-75 text-white z-10 p-4">
          <p className="text-red-400 font-semibold">Camera Error</p>
          <p className="text-sm">{errorMessage}</p>
          <p className="text-xs mt-2">Using fallback images</p>
        </div>
      )}
      
      {/* Video element that shows the camera feed */}
      <video 
        ref={videoRef} 
        className={`w-full h-auto rounded-lg ${cameraStatus !== 'success' ? 'opacity-50' : ''}`} 
        autoPlay 
        playsInline 
        muted
      />
      
      {/* Hidden canvas used for capturing frames */}
      <canvas ref={canvasRef} className="hidden" />
      
      {/* Status indicator when capturing */}
      {isCapturing && (
        <div className="absolute top-2 right-2 bg-blue-500 text-white text-xs px-2 py-1 rounded">
          Capturing...
        </div>
      )}
    </div>
  );
};

export default VideoCapture; 