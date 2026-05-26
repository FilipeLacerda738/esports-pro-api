import sys
from loguru import logger

logger.remove()


logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)


logger.add(
    "logs/api_{time:YYYY-MM-DD}.log", 
    rotation="10 MB",               
    retention="14 days",              
    level="INFO",                    
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)