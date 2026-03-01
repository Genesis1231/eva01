import sys
from pathlib import Path
import sqlite3
import logging
logging.disable(logging.WARNING)

def create_directories():
    """Create necessary directories for EVA"""
    app_dir = Path(__file__).resolve() / 'app' / 'data'
    
    # Create data directories
    directories = [
        app_dir / 'database',
        app_dir / 'voids',
        app_dir / 'pids',
    ]
    
    try:    
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Directory setup error: {e}")
        sys.exit(1)

def setup_database():
    """Initialize the SQLite database with required tables"""
    try:
        db_path = Path(__file__).resolve() / 'app' / 'data' / 'database' / 'eva.db'
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create memory log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memorylog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT NOT NULL,
                    user_name TEXT,
                    user_message TEXT,
                    eva_message TEXT,
                    observation TEXT,
                    analysis TEXT,
                    strategy TEXT,
                    premeditation TEXT,
                    action TEXT
                )
            ''')
            
            # Create voice ID table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    void TEXT,
                    pid TEXT,
                    user_name TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            logging.info("Database tables created successfully")
            
    except sqlite3.Error as e:
        logging.error(f"Database setup error: {e}")
        sys.exit(1)
        
def test_modules():
    """Test importing the modules"""
    try:
        from app.core import eva
        from app.tools import ToolManager
        from app.utils.agent import ChatAgent
        from app.utils.extension import Window, MidjourneyServer
        from app.utils.memory import Memory
        from app.utils.stt import PCListener
        from app.utils.stt.model_fasterwhisper import FWTranscriber
        from app.utils.stt.model_whisper import WhisperTranscriber
        from app.utils.stt.model_groq import GroqTranscriber
        from app.utils.tts import Speaker
        from app.utils.tts.model_elevenlabs import ElevenLabsSpeaker
        from app.utils.tts.model_coqui import CoquiSpeaker
        from app.utils.tts.model_openai import OpenAISpeaker
        from app.utils.vision import Watcher
        from app.utils.vision.model_groq import GroqVision
        from app.utils.vision.model_openai import OpenAIVision
        from app.utils.vision.model_ollama import OllamaVision
        
    except ImportError as e:
        logging.error(f"MODULES NOT INSTALLED! {e}")
        sys.exit(1)

if __name__ == "__main__":
    logging.info("Starting EVA setup...")

    create_directories()
    setup_database()
    test_modules()
    
    logging.info("EVA setup completed successfully")
