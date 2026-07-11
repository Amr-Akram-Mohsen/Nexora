# app/domains/interaction/service/insights/learning_memory.py
import os
import json
import logging
import shutil
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MEMORY_FILE_PATH = os.path.join("instance", "content_intelligence_memory.json")

def load_json_file(file_path, default_factory=list):
    """
    Loads JSON data from file_path, creating the directory and file with default_factory() if it doesn't exist.
    If the JSON is malformed, it makes a copy of the corrupted file and overwrites it with default_factory()
    to recover gracefully.
    """
    if not os.path.exists(file_path):
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            default_data = default_factory()
            save_json_file(file_path, default_data)
            return default_data
        except Exception as e:
            logger.exception(f"Failed to initialize file: {file_path}")
            raise e

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON in file {file_path}: {e}")
        # Recover gracefully: rename/backup malformed file and overwrite with default
        timestamp = int(datetime.now(timezone.utc).timestamp())
        backup_path = f"{file_path}.corrupt.{timestamp}"
        try:
            shutil.copy2(file_path, backup_path)
            logger.warning(f"Backed up corrupted file to {backup_path}")
        except Exception as backup_err:
            logger.error(f"Failed to backup corrupted file: {backup_err}")
            
        try:
            default_data = default_factory()
            save_json_file(file_path, default_data)
            return default_data
        except Exception as write_err:
            logger.exception(f"Failed to write recovery default data: {file_path}")
            raise write_err
    except Exception as e:
        logger.exception(f"Failed to read file: {file_path}")
        raise e

def save_json_file(file_path, data):
    """
    Saves data to a JSON file atomically using a temporary file.
    Does not silently swallow exceptions.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        temp_path = f"{file_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, file_path)
    except Exception as e:
        logger.exception(f"Failed to save JSON to file: {file_path}")
        raise e

def load_memory_layer():
    """
    Loads the memory layer from MEMORY_FILE_PATH, recovering from corruption.
    Returns a list of memory records for backward compatibility.
    Converts list-only structures (v1) to versioned structures (v2) on read.
    """
    def get_seed_data():
        return {
            "version": 2,
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "description": "Nexora content intelligence memory layer seed data"
            },
            "records": [
                {"entity": "Smartwatches", "platform": "youtube", "intent": "comparison", "outcome": "success", "impact_score": 0.85, "version": 1},
                {"entity": "Laptops", "platform": "blog", "intent": "buying-guide", "outcome": "success", "impact_score": 0.78, "version": 1},
                {"entity": "Perfumes", "platform": "pinterest", "intent": "gift-ideas", "outcome": "failure", "impact_score": 0.32, "version": 1},
                {"entity": "Bags", "platform": "pinterest", "intent": "gift-ideas", "outcome": "success", "impact_score": 0.82, "version": 1},
                {"entity": "Electronics", "platform": "blog", "intent": "buying-guide", "outcome": "failure", "impact_score": 0.28, "version": 1}
            ]
        }

    raw_data = load_json_file(MEMORY_FILE_PATH, default_factory=get_seed_data)
    
    # If raw_data is a list, migrate to dict structure
    if isinstance(raw_data, list):
        logger.warning("Migrating old list-based memory to versioned dict structure.")
        migrated_data = {
            "version": 2,
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "description": "Migrated from legacy list-based structure"
            },
            "records": []
        }
        for product in raw_data:
            if isinstance(product, dict):
                if "version" not in product:
                    product["version"] = 1
                migrated_data["records"].append(product)
        try:
            save_json_file(MEMORY_FILE_PATH, migrated_data)
        except Exception as e:
            logger.exception("Failed to write migrated memory file")
        return migrated_data["records"]

    # If it's a dict, make sure records is returned
    if isinstance(raw_data, dict):
        records = raw_data.get("records", [])
        # Ensure records are dicts and have versions
        for product in records:
            if isinstance(product, dict) and "version" not in product:
                product["version"] = 1
        return records

    return []

def save_memory_layer(data):
    """
    Wraps a list of memory records in a versioned envelope and saves it to MEMORY_FILE_PATH.
    Does not silently swallow exceptions.
    """
    if not isinstance(data, list):
        raise TypeError("save_memory_layer expects a list of records")
        
    wrapped_data = {
        "version": 2,
        "metadata": {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "description": "Nexora content intelligence memory layer"
        },
        "records": data
    }
    save_json_file(MEMORY_FILE_PATH, wrapped_data)
