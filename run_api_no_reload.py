#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# run_api_no_reload.py - Run API without auto-reload for stable logging

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable auto-reload for stable logs
        log_level="info"
    )
