import sqlite3
from pathlib import Path
from config import logger
from typing import Dict
import json

class MemoryLogger:
    """
    MemoryLogger class to save the conversation and memory to the database.
    """
    def __init__(self):
        self._dblink: str = self._get_database_path()
        self._create_memory_table(self._dblink)

    @staticmethod
    def _get_database_path() -> str:
        """Return the path to the memory log database."""
        db_dir = Path(__file__).resolve().parents[2] / 'data' / 'database'
        if not db_dir.exists():
            db_dir.mkdir(parents=True)
            
        return db_dir / 'eva.db'

    @staticmethod
    def _create_memory_table(dblink: str) -> None:
        """ Create the memory table if it doesn't exist. """
        try:
            with sqlite3.connect(dblink) as conn:
                cursor = conn.cursor()
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
                conn.commit()
        
        except sqlite3.Error as e:
            logger.error(f"Error creating memory table: {e}")
        finally:
            conn.close()
        

    def save_memory_to_db(self, memory: Dict) -> None:
        """Save a single memory entry to the SQLite database."""
        try:
            with sqlite3.connect(self._dblink) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO memorylog (time, user_name, user_message, eva_message, observation, analysis, strategy, premeditation, action)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (memory["time"], memory["user_name"], memory["user_message"], memory["eva_message"], 
                    memory["observation"], memory["analysis"], memory["strategy"], memory["premeditation"], json.dumps(memory["action"])))
            conn.commit()
                
        except Exception as e:
            logger.error(f"Error: Failed to save memory to database: {str(e)}")
        finally:
            conn.close()  
            
        logger.info(f"Memory: Entry created at { memory['time'] }")