import os
from config import logger
import asyncio
from typing_extensions import Dict, List, Optional
 
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from pathlib import Path

from client.data_manager import DataManager


class ConnectionManager:
    def __init__(self, stt_model: str, vision_model: str):
        self.app = FastAPI()
        self.data_manager = DataManager(stt_model, vision_model) 
        
        self.media_folder: str = "/media" # TODO: make this configurable
        self.client_id: Optional[str] = None
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Common CORS headers for file downloads
        self.cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept, Range, *",
            "Access-Control-Max-Age": "86400",  # 24 hours
        }
        
        self.setup_routes()

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()

        websocket.receive_limit = None
        websocket.send_limit = None
        self.active_connections[client_id] = websocket
        self.client_id = client_id # manage the client_id later
        
        initial_data = self.data_manager.get_session_data()
        await self.send_message(initial_data)

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_message(self, message: str, client_id: str = None):
        # manage the client id later.
        if client_id is None:
            client_id = self.client_id
        
        #logger.info(f"Sending message to client: {client_id} :: {message}")
        
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
        
    async def broadcast(self, message: str):
        for websocket in self.active_connections.values():
            await websocket.send_text(message)

            
    def setup_routes(self):
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await self.connect(websocket, client_id)
            await self.data_manager.start_queue()
            try:
                while True:
                    message = await websocket.receive_text()

                    response = await self.data_manager.process_message(message, client_id)

                    await self.send_message(response)
                    await asyncio.sleep(0.3)
                    
            except WebSocketDisconnect:
                self.disconnect(client_id)
            except Exception as e:
                raise Exception(f"Error handling connection: {str(e)}")
            finally:
                self.disconnect(client_id)
                await self.data_manager.stop()
        
        # @self.app.post("/upload/")
        # async def upload_file(file: UploadFile = File(...)):
        #     if is_valid(file.filename, [".jpg", ".jpeg"]):
        #         save_dir = "user_images"
        #     elif is_valid(file.filename, [".mp3"]):
        #         save_dir = "user_audio"
        #     else:
        #         raise HTTPException(status_code=400, detail="Invalid file type. Only .jpg, .jpeg, and .mp3 files are allowed.")

        #     file_path = os.path.join(self.media_folder, save_dir, file.filename)
            
        #     try:
        #         with open(file_path, "wb") as buffer:
        #             content = await file.read()
        #             buffer.write(content)
        #     except Exception as e:
        #         raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        #     return {"url": file_path}

        @self.app.get("/download/{file_type}/{filename}")
        async def download_file(file_type: str, filename: str, session_id: Optional[str] = None):
            """
            GET endpoint to serve audio and image files. This handles the actual file downloads.
            For browsers using CORS, the preflight OPTIONS request will be handled by options_download_file below.
            
            The relationship between this GET endpoint and the OPTIONS endpoint:
            - Modern browsers using CORS will first send an OPTIONS request (preflight) 
            - After receiving a successful response from OPTIONS, they'll send the actual GET request
            - Both endpoints use the same CORS headers from self.cors_headers
            """
            if file_type not in ["images", "audio"]:
                raise HTTPException(status_code=400, detail="Invalid file type.")
            
            if not session_id:
                logger.warning(f"File request without session ID for file: {filename} - this may cause caching issues")
                
            # Construct the path relative to the app root directory
            file_path = os.path.join(os.getcwd(), "app", "data", "media", file_type, filename)
                
            if not os.path.isfile(file_path):
                logger.error(f"File not found: {file_path}")
                raise HTTPException(status_code=404, detail=f"File: {filename} not found")

            try:
                # Use appropriate media type based on file_type
                media_type = "audio/mpeg" if file_type == "audio" else "image/jpeg"
                
                # Create a response with the file
                response = FileResponse(
                    file_path, 
                    filename=filename, 
                    media_type=media_type
                )
                
                # Add CORS headers from the common set
                for header, value in self.cors_headers.items():
                    response.headers[header] = value
                
                # Set caching headers based on session_id
                if session_id:
                    # Use cache control that allows caching but requires revalidation
                    response.headers["Cache-Control"] = "private, max-age=60, must-revalidate"
                    response.headers["Vary"] = "session_id"  # Vary on the session ID
                else:
                    # No caching if no session ID (to be safe)
                    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
                
                return response
            except Exception as e:
                logger.error(f"Error accessing file: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error accessing file: {str(e)}")

        @self.app.options("/download/{file_type}/{filename}")
        async def options_download_file(file_type: str, filename: str):
            """
            Handle CORS preflight requests for the download endpoint.

            1. Browsers send preflight OPTIONS requests before making cross-origin requests
            2. The preflight verifies that the server allows the actual request
            3. Without this endpoint, browsers would block cross-origin requests to our files
            
            We use the same CORS headers as the GET endpoint for consistency.
            The actual file download happens in the GET endpoint after this preflight check.
            """
            # Log the CORS preflight request
            logger.debug(f"Handling OPTIONS request for: /download/{file_type}/{filename}")
            
            # Use common CORS headers for the preflight response
            return JSONResponse(content={}, headers=self.cors_headers)

        @staticmethod
        def is_valid(filename: str, allowed_extensions: List[str]) -> bool:
            return any(filename.lower().endswith(ext) for ext in allowed_extensions)

    def get_message(self):
        return self.data_manager.get_first_data()

    def run_server(self):
        uvicorn.run(self.app, host="0.0.0.0", port=8080)

