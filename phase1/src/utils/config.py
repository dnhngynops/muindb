"""
Configuration settings for the Billboard Music Database project.

This module contains all configuration settings, constants, and environment variables.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    database_path: str
    backup_enabled: bool = True
    backup_retention_days: int = 30
    batch_size: int = 1000
    connection_timeout: int = 30


@dataclass
class DataSourceConfig:
    """Data source configuration settings."""
    billboard_api_url: str = "https://api.billboard.com/api/v1/charts/hot-100"
    json_data_path: str = "data/raw/billboard_hot100_all.json"
    download_timeout: int = 300
    retry_attempts: int = 3
    retry_delay: int = 5


@dataclass
class ProcessingConfig:
    """Data processing configuration settings."""
    enable_data_cleaning: bool = True
    enable_normalization: bool = True
    enable_statistics: bool = True
    parallel_processing: bool = True
    max_workers: int = 4


class Config:
    """Main configuration class."""
    
    def __init__(self):
        """Initialize configuration with default values."""
        self.project_root = self._get_project_root()
        self.database = self._get_database_config()
        self.data_source = self._get_data_source_config()
        self.processing = self._get_processing_config()
        self.logging = self._get_logging_config()
    
    def _get_project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent
    
    def _get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        database_path = os.getenv(
            'BILLBOARD_DB_PATH',
            str(self.project_root / 'data' / 'music_database.db')
        )
        
        return DatabaseConfig(
            database_path=database_path,
            backup_enabled=os.getenv('BILLBOARD_DB_BACKUP', 'true').lower() == 'true',
            backup_retention_days=int(os.getenv('BILLBOARD_DB_BACKUP_DAYS', '30')),
            batch_size=int(os.getenv('BILLBOARD_DB_BATCH_SIZE', '1000')),
            connection_timeout=int(os.getenv('BILLBOARD_DB_TIMEOUT', '30'))
        )
    
    def _get_data_source_config(self) -> DataSourceConfig:
        """Get data source configuration."""
        return DataSourceConfig(
            billboard_api_url=os.getenv(
                'BILLBOARD_API_URL',
                'https://api.billboard.com/api/v1/charts/hot-100'
            ),
            json_data_path=os.getenv(
                'BILLBOARD_JSON_PATH',
                str(self.project_root / 'data' / 'raw' / 'billboard_hot100_all.json')
            ),
            download_timeout=int(os.getenv('BILLBOARD_DOWNLOAD_TIMEOUT', '300')),
            retry_attempts=int(os.getenv('BILLBOARD_RETRY_ATTEMPTS', '3')),
            retry_delay=int(os.getenv('BILLBOARD_RETRY_DELAY', '5'))
        )
    
    def _get_processing_config(self) -> ProcessingConfig:
        """Get processing configuration."""
        return ProcessingConfig(
            enable_data_cleaning=os.getenv('BILLBOARD_ENABLE_CLEANING', 'true').lower() == 'true',
            enable_normalization=os.getenv('BILLBOARD_ENABLE_NORMALIZATION', 'true').lower() == 'true',
            enable_statistics=os.getenv('BILLBOARD_ENABLE_STATISTICS', 'true').lower() == 'true',
            parallel_processing=os.getenv('BILLBOARD_PARALLEL_PROCESSING', 'true').lower() == 'true',
            max_workers=int(os.getenv('BILLBOARD_MAX_WORKERS', '4'))
        )
    
    def _get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            'level': os.getenv('BILLBOARD_LOG_LEVEL', 'INFO').upper(),
            'format': os.getenv(
                'BILLBOARD_LOG_FORMAT',
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ),
            'file': os.getenv(
                'BILLBOARD_LOG_FILE',
                str(self.project_root / 'logs' / 'billboard_database.log')
            ),
            'max_size': int(os.getenv('BILLBOARD_LOG_MAX_SIZE', '10485760')),  # 10MB
            'backup_count': int(os.getenv('BILLBOARD_LOG_BACKUP_COUNT', '5'))
        }
    
    def get_database_path(self) -> str:
        """Get the full database path."""
        return self.database.database_path
    
    def get_json_data_path(self) -> str:
        """Get the full JSON data file path."""
        return self.data_source.json_data_path
    
    def get_log_file_path(self) -> str:
        """Get the full log file path."""
        return self.logging['file']
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.project_root / 'data',
            self.project_root / 'data' / 'raw',
            self.project_root / 'logs',
            Path(self.database.database_path).parent
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'project_root': str(self.project_root),
            'database': {
                'database_path': self.database.database_path,
                'backup_enabled': self.database.backup_enabled,
                'backup_retention_days': self.database.backup_retention_days,
                'batch_size': self.database.batch_size,
                'connection_timeout': self.database.connection_timeout
            },
            'data_source': {
                'billboard_api_url': self.data_source.billboard_api_url,
                'json_data_path': self.data_source.json_data_path,
                'download_timeout': self.data_source.download_timeout,
                'retry_attempts': self.data_source.retry_attempts,
                'retry_delay': self.data_source.retry_delay
            },
            'processing': {
                'enable_data_cleaning': self.processing.enable_data_cleaning,
                'enable_normalization': self.processing.enable_normalization,
                'enable_statistics': self.processing.enable_statistics,
                'parallel_processing': self.processing.parallel_processing,
                'max_workers': self.processing.max_workers
            },
            'logging': self.logging
        }


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def reload_config():
    """Reload the configuration from environment variables."""
    global config
    config = Config()


# Constants
class Constants:
    """Project constants."""
    
    # Chart positions
    CHART_SIZE = 100
    TOP_10 = 10
    TOP_40 = 40
    
    # Date formats
    DATE_FORMAT = '%Y-%m-%d'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # File extensions
    JSON_EXTENSION = '.json'
    DB_EXTENSION = '.db'
    LOG_EXTENSION = '.log'
    
    # Database table names
    BILLBOARD_ENTRIES_TABLE = 'billboard_entries'
    CHART_SUMMARIES_TABLE = 'chart_summaries'
    ARTIST_STATS_TABLE = 'artist_stats'
    SONG_STATS_TABLE = 'song_stats'
    
    # Data validation
    MIN_YEAR = 1958  # Billboard Hot 100 started in 1958
    MAX_YEAR = 2030  # Reasonable future limit
    MIN_POSITION = 1
    MAX_POSITION = 100
    MIN_WEEKS_ON_CHART = 1
    MAX_WEEKS_ON_CHART = 1000  # Reasonable upper limit
    
    # Error messages
    INVALID_DATE_FORMAT = "Invalid date format. Expected YYYY-MM-DD"
    INVALID_POSITION = f"Invalid position. Must be between {MIN_POSITION} and {MAX_POSITION}"
    INVALID_YEAR = f"Invalid year. Must be between {MIN_YEAR} and {MAX_YEAR}"
    INVALID_WEEKS = f"Invalid weeks on chart. Must be between {MIN_WEEKS_ON_CHART} and {MAX_WEEKS_ON_CHART}"


# Environment variable names
class EnvVars:
    """Environment variable names."""
    
    # Database
    BILLBOARD_DB_PATH = 'BILLBOARD_DB_PATH'
    BILLBOARD_DB_BACKUP = 'BILLBOARD_DB_BACKUP'
    BILLBOARD_DB_BACKUP_DAYS = 'BILLBOARD_DB_BACKUP_DAYS'
    BILLBOARD_DB_BATCH_SIZE = 'BILLBOARD_DB_BATCH_SIZE'
    BILLBOARD_DB_TIMEOUT = 'BILLBOARD_DB_TIMEOUT'
    
    # Data source
    BILLBOARD_API_URL = 'BILLBOARD_API_URL'
    BILLBOARD_JSON_PATH = 'BILLBOARD_JSON_PATH'
    BILLBOARD_DOWNLOAD_TIMEOUT = 'BILLBOARD_DOWNLOAD_TIMEOUT'
    BILLBOARD_RETRY_ATTEMPTS = 'BILLBOARD_RETRY_ATTEMPTS'
    BILLBOARD_RETRY_DELAY = 'BILLBOARD_RETRY_DELAY'
    
    # Processing
    BILLBOARD_ENABLE_CLEANING = 'BILLBOARD_ENABLE_CLEANING'
    BILLBOARD_ENABLE_NORMALIZATION = 'BILLBOARD_ENABLE_NORMALIZATION'
    BILLBOARD_ENABLE_STATISTICS = 'BILLBOARD_ENABLE_STATISTICS'
    BILLBOARD_PARALLEL_PROCESSING = 'BILLBOARD_PARALLEL_PROCESSING'
    BILLBOARD_MAX_WORKERS = 'BILLBOARD_MAX_WORKERS'
    
    # Logging
    BILLBOARD_LOG_LEVEL = 'BILLBOARD_LOG_LEVEL'
    BILLBOARD_LOG_FORMAT = 'BILLBOARD_LOG_FORMAT'
    BILLBOARD_LOG_FILE = 'BILLBOARD_LOG_FILE'
    BILLBOARD_LOG_MAX_SIZE = 'BILLBOARD_LOG_MAX_SIZE'
    BILLBOARD_LOG_BACKUP_COUNT = 'BILLBOARD_LOG_BACKUP_COUNT'
