# project/run_api.py
# Script to run the FastAPI server

import uvicorn
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",  # Импорт из api/main.py
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )