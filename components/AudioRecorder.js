// Choose best MIME type for compatibility with backend
// Order of preference: audio/mp3 > audio/webm > audio/wav
let mimeType = 'audio/wav'; // Default fallback

// Avoid using MP3 as it's causing FFmpeg decoding issues
if (MediaRecorder.isTypeSupported('audio/webm')) {
  mimeType = 'audio/webm';
} else if (MediaRecorder.isTypeSupported('audio/ogg')) {
  mimeType = 'audio/ogg';
}

console.log(`Recording with MIME type: ${mimeType}, sample rate: 16000Hz, mono channel`); 

mediaRecorder.onstop = async () => {
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
    
    // Validate recording length
    if (recordingDuration < 0.5) {
      console.warn('Recording too short, ignoring');
      setRecordingError('Recording too short. Please hold for at least 0.5 seconds.');
      return;
    }
    
    // Process the audio blob to ensure it's in a format the backend can handle
    const processedBlob = await processAudioBlob(audioBlob, mimeType);
    
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

// Function to process audio blob to ensure compatibility with backend
const processAudioBlob = async (blob, originalMimeType) => {
  // For WAV and WebM, we can use as is since they are well supported
  if (originalMimeType === 'audio/wav' || originalMimeType === 'audio/webm') {
    return blob;
  }
  
  try {
    // If we have Web Audio API available, convert to WAV for better compatibility
    if (audioContextRef.current) {
      console.log('Converting audio to ensure format compatibility with backend');
      
      // Read the blob as an array buffer
      const arrayBuffer = await blob.arrayBuffer();
      
      // Decode the audio data
      const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);
      
      // Prepare for export as WAV
      const numberOfChannels = 1; // Mono
      const sampleRate = 16000; // 16kHz as required by backend
      const length = audioBuffer.length;
      
      // Create a new AudioBuffer with the correct specs
      const offlineContext = new OfflineAudioContext(numberOfChannels, length, sampleRate);
      const bufferSource = offlineContext.createBufferSource();
      bufferSource.buffer = audioBuffer;
      bufferSource.connect(offlineContext.destination);
      bufferSource.start(0);
      
      // Render to buffer
      const renderedBuffer = await offlineContext.startRendering();
      
      // Convert to WAV format
      const wavBlob = bufferToWav(renderedBuffer);
      console.log(`Converted audio to WAV: ${wavBlob.size} bytes`);
      
      return wavBlob;
    }
  } catch (error) {
    console.error('Error converting audio format:', error);
    // If conversion fails, return the original blob
  }
  
  return blob;
};

// Helper function to convert AudioBuffer to WAV Blob
const bufferToWav = (buffer) => {
  const numberOfChannels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const length = buffer.length;
  
  // Create the WAV file
  const wavDataView = createWaveFileData(buffer);
  
  // Create a Blob from the WAV DataView
  return new Blob([wavDataView], { type: 'audio/wav' });
};

// Function to create a WAV file from AudioBuffer data
const createWaveFileData = (audioBuffer) => {
  const numOfChannels = audioBuffer.numberOfChannels;
  const length = audioBuffer.length;
  const sampleRate = audioBuffer.sampleRate;
  const bitsPerSample = 16;
  const bytesPerSample = bitsPerSample / 8;
  const blockAlign = numOfChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = length * numOfChannels * bytesPerSample;
  
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  
  // Write WAV header
  // "RIFF" chunk descriptor
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true); // File size - 8
  writeString(view, 8, 'WAVE');
  
  // "fmt " sub-chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Sub-chunk size
  view.setUint16(20, 1, true); // Audio format (1 = PCM)
  view.setUint16(22, numOfChannels, true); // Number of channels
  view.setUint32(24, sampleRate, true); // Sample rate
  view.setUint32(28, byteRate, true); // Byte rate
  view.setUint16(32, blockAlign, true); // Block align
  view.setUint16(34, bitsPerSample, true); // Bits per sample
  
  // "data" sub-chunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataSize, true); // Sub-chunk size
  
  // Write audio data
  const channelData = [];
  for (let i = 0; i < numOfChannels; i++) {
    channelData.push(audioBuffer.getChannelData(i));
  }
  
  let offset = 44;
  for (let i = 0; i < length; i++) {
    for (let channel = 0; channel < numOfChannels; channel++) {
      const sample = Math.max(-1, Math.min(1, channelData[channel][i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      offset += bytesPerSample;
    }
  }
  
  return view;
};

// Helper to write string to DataView
const writeString = (view, offset, string) => {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}; 