import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

from config import logger, eva_configuration
from eva.core.eva import EVA
from eva.client.data_manager import DataManager
from eva.senses.audio.transcriber import Transcriber
from eva.utils.vision.describer import Describer

MEDIA_ROOT = Path(__file__).parent / "data" / "media"
VALID_FILE_TYPES = {"images", "audio"}
MEDIA_TYPES = {"audio": "audio/mpeg", "images": "image/jpeg"}

logger.info("Initializing global models for Mobile server...")
stt_model_name = eva_configuration.get("STT_MODEL")
vision_model_name = eva_configuration.get("VISION_MODEL")
base_url = eva_configuration.get("BASE_URL")

GLOBAL_STT = Transcriber(stt_model_name)
GLOBAL_VISION = Describer(vision_model_name, base_url)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/download/{file_type}/{filename}")
async def download_file(file_type: str, filename: str, session_id: Optional[str] = None):
    """Serve audio and image files to the frontend."""
    if file_type not in VALID_FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file_type}.")

    if not session_id:
        logger.warning(f"File request without session ID for '{filename}' — may cause caching issues")

    file_path = MEDIA_ROOT / file_type / filename

    if not file_path.is_file():
        logger.error(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    response = FileResponse(file_path, filename=filename, media_type=MEDIA_TYPES[file_type])

    if session_id:
        response.headers["Cache-Control"] = "private, max-age=60, must-revalidate"
        response.headers["Vary"] = "session_id"
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

    return response


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    data_manager = DataManager(stt_model=GLOBAL_STT, vision_model=GLOBAL_VISION)
    await websocket.send_text(data_manager.get_session_data())
    await data_manager.start_queue()

    eva = EVA()
    eva_task = asyncio.create_task(eva.arun(websocket=websocket, data_manager=data_manager))

    try:
        while True:
            message = await websocket.receive_text()
            response = await data_manager.process_message(message, client_id)
            await websocket.send_text(response)

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        if not eva_task.done():
            eva_task.cancel()
        await data_manager.stop()


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
