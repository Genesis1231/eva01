import sqlite3
from config import logger
from pathlib import Path
from typing import Dict

class IDManager:
    """ Manage the ID of the EVA """
    
    def __init__(self):
        self._db_path = self._get_database_path()
        self._pid_list, self._void_list, self._id_list = self.initialize_database()
    
    def get_pid_list(self) -> Dict:
        """ Get the pid list """
        return self._pid_list
            
    def get_void_list(self) -> Dict:
        """ Get the void list """
        return self._void_list
    
    def is_empty(self) -> bool:
        """ Check if the ID manager is empty """
        return len(self._id_list) == 0
    
    def initialize_database(self):
        """ Initialize the database and create the voice id table """
        
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
            cursor = conn.cursor()

            try:
                cursor.execute('SELECT user_name, void, pid FROM ids;')
                rows = cursor.fetchall()
                
                # Create main mapping and reverse mappings
                pid_list = {row["pid"]: row["user_name"] for row in rows if row["pid"]}
                void_list = {row["void"]: row["user_name"] for row in rows if row["void"]}
                id_list = {row["user_name"]: {"void": row["void"], "pid": row["pid"]} for row in rows}
                return pid_list, void_list, id_list

            except sqlite3.Error as e:
                # If table doesn't exist, create it and return an empty list
                logger.error(f"Failed to initialize ID manager: {str(e)}")
                return {}, {}, {}
    
    def _get_database_path(self) -> Path:
        """Return the path to the memory log database and create it if it doesn't exist."""
        path = Path(__file__).resolve().parents[1] / 'data' / 'database' / 'eva.db'
        
        # Check if the database file exists, if not, create an empty database
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
            with sqlite3.connect(path) as conn:
                self._create_table(conn)
            logger.info("Created new empty eva.db database")
        
        return path
    
    def _create_table(self, conn)-> None:    
        """ Create a new id table """
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                void TEXT,
                pid TEXT
            )
        ''')
        conn.commit()
        logger.info("ID table created successfully")

    def add_user(self, user_name: str, void: str = None, pid: str = None) -> bool:
        """ Add a new user with optional void and pid"""
        # Check for unique void and pid
        if void and void in self._void_list:
            logger.warning(f"Voice ID {void} already exists")
            return False
            
        if pid and pid in self._pid_list:
            logger.warning(f"Picture ID {pid} already exists")
            return False
            
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ids (user_name, void, pid)
                    VALUES (?, ?, ?)
                ''', (user_name, void, pid))
                conn.commit()
                
                # Update internal dictionaries
                if user_name not in self._id_list:
                    self._id_list[user_name] = {"void": void, "pid": pid}
                if void:
                    self._void_list[void] = user_name
                if pid:
                    self._pid_list[pid] = user_name
                    
                logger.info(f"Successfully added user {user_name}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to add user {user_name}: {str(e)}")
            return False

    def update_user(self, user_name: str, void: str = None, pid: str = None) -> bool:
        """ Update an existing user's void or pid"""
        
        # Check if user exists
        if user_name not in self._id_list:
            logger.warning(f"User {user_name} does not exist")
            return False
        
        # Check for unique void and pid
        if void and void in self._void_list and self._void_list[void] != user_name:
            logger.warning(f"Voice ID {void} already exists for another user")
            return False
        
        if pid and pid in self._pid_list and self._pid_list[pid] != user_name:
            logger.warning(f"Picture ID {pid} already exists for another user")
            return False
        
        # Get current IDs
        current_void = self._id_list[user_name]["void"]
        current_pid = self._id_list[user_name]["pid"]
        
        # Only update if there's a change
        new_void = void if void else current_void
        new_pid = pid if pid else current_pid
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ids 
                    SET void = ?, pid = ?
                    WHERE user_name = ?
                ''', (new_void, new_pid, user_name))
                conn.commit()
                
                # Update internal dictionaries
                if current_void and void and current_void != void:
                    del self._void_list[current_void]  # Remove old void
                if void:
                    self._void_list[void] = user_name  # Add new void
                
                if current_pid and pid and current_pid != pid:
                    del self._pid_list[current_pid]  # Remove old pid
                if pid:
                    self._pid_list[pid] = user_name  # Add new pid
                
                self._id_list[user_name] = {"void": new_void, "pid": new_pid}
                
                logger.info(f"Successfully updated user {user_name}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to update user {user_name}: {str(e)}")
            return False



id_manager = IDManager()
