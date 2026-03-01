# EVA React Web Interface

A React-based web interface for EVA that allows for voice and video interaction.

## Features

- Modern, responsive web interface for EVA
- Webcam integration for visual input
- Microphone recording for voice commands
- Real-time voice feedback using Web Speech API
- Visual animation when EVA is talking
- Space key hold-to-talk functionality
- Automatic periodic image capture (every 10 seconds)
- WebSocket connection with automatic reconnection handling
- Error notifications for better user experience

## Requirements

- Node.js (v14 or later)
- EVA backend server running on port 8080

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open your browser to http://localhost:3000

## How to Use

1. Click the "Start Conversation with EVA" button to initialize the interface.
2. Allow browser permissions for camera and microphone when prompted.
3. EVA will initiate the conversation.
4. To speak to EVA:
   - Hold down the spacebar while speaking
   - Or press and hold the "Speak" button
   - Release when done speaking
5. If EVA is speaking when you start talking, it will stop to listen to you.
6. The camera is always on, providing visual context to EVA automatically.

## Configuration

The WebSocket URL is automatically determined based on your current protocol (HTTP/HTTPS):
- For HTTP: `ws://hostname:8080`
- For HTTPS: `wss://hostname:8080`

You can modify these settings in `pages/index.js` if your EVA backend is running on a different address.

## Features and Fixes

- Fixed WebSocket reconnection handling with automatic retries
- Improved error handling throughout the application
- Added user notifications for connection issues and errors
- Fixed spacebar hold-to-talk functionality to prevent duplicate recordings
- Added automatic image capture on a regular interval
- Fixed dependency arrays in React hooks to prevent memory leaks
- Improved resource cleanup for media streams
- Added promise-based API for WebSocket communication
- Improved WebRTC security by implementing proper error handling

## Building for Production

```bash
npm run build
npm start
```

## License

ISC 