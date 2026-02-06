from pymongo import MongoClient
from typing import Dict, List, Any, Optional
from config import DATABASE_URL

class ConfigDatabase:
    def __init__(self, connection_string: str = DATABASE_URL, db_name: str = "reelnnback"):
        """Initialize MongoDB connection."""
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.config_collection = self.db["configs"]
        
        
        self.config_collection.create_index("key", unique=True)
    
    def upsert_config(self, key: str, value: Any, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Store or update configuration in MongoDB.
        
        Args:
            key: Unique identifier for the config
            value: Configuration value (can be any serializable type)
            description: Optional description of the configuration
            
        Returns:
            Dict with operation status
        """
        try:
            
            config_doc = {
                "key": key,
                "value": value,
            }
            
            if description:
                config_doc["description"] = description
            
            
            existing_config = self.config_collection.find_one({"key": key})
            
            if existing_config:
                
                result = self.config_collection.update_one(
                    {"key": key},
                    {"$set": config_doc}
                )
                
                return {
                    "status": "updated",
                    "key": key,
                    "modified_count": result.modified_count
                }
            else:
                
                result = self.config_collection.insert_one(config_doc)
                
                return {
                    "status": "inserted",
                    "key": key,
                    "inserted_id": str(result.inserted_id)
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_config(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration by key.
        
        Args:
            key: Configuration key to look up
            
        Returns:
            Configuration document or None if not found
        """
        try:
            config = self.config_collection.find_one({"key": key})
            if config:
                
                config["_id"] = str(config["_id"])
            return config
        except Exception as e:
            print(f"Error getting config: {str(e)}")
            return None
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get just the value of a configuration by its key.
        
        Args:
            key: Configuration key to look up
            default: Default value to return if config not found
            
        Returns:
            Configuration value or default if not found
        """
        config = self.get_config(key)
        if config and "value" in config:
            return config["value"]
        return default
    
    def delete_config(self, key: str) -> Dict[str, Any]:
        """
        Delete a configuration by its key.
        
        Args:
            key: Configuration key to delete
            
        Returns:
            Dict with operation status
        """
        try:
            result = self.config_collection.delete_one({"key": key})
            if result.deleted_count > 0:
                return {
                    "status": "success",
                    "message": f"Configuration with key '{key}' deleted",
                    "deleted_count": result.deleted_count
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"Configuration with key '{key}' not found"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def list_configs(self, filter_query: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        List configurations, optionally filtered.
        
        Args:
            filter_query: Optional MongoDB filter query
            
        Returns:
            List of configuration documents
        """
        try:
            cursor = self.config_collection.find(filter_query or {})
            configs = list(cursor)
            
            for config in configs:
                config["_id"] = str(config["_id"])
            return configs
        except Exception as e:
            print(f"Error listing configs: {str(e)}")
            return []
    
    def close(self):
        """Close the MongoDB connection."""
        self.client.close()

    
    
    def save_trending_config(self, movie_ids: List[int], show_ids: List[int]) -> Dict[str, Any]:
        """
        Save trending movie and show IDs.
        
        Args:
            movie_ids: List of trending movie IDs
            show_ids: List of trending show IDs
            
        Returns:
            Operation status
        """
        config_value = {
            "movie": movie_ids,
            "show": show_ids
        }
        return self.upsert_config(
            key="trending",
            value=config_value,
            description="IDs of trending movies and shows"
        )
    
    def get_trending_config(self) -> Dict[str, List[int]]:
        """
        Get trending movie and show IDs.
        
        Returns:
            Dict with 'movie' and 'show' keys containing lists of IDs
        """
        config = self.get_config_value("trending")
        if not config:
            return {"movie": [], "show": []}
        return config
