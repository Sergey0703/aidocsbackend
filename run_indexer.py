#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper to run indexer with UTF-8 output"""

import sys
import io

# Force UTF-8 for stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add rag_indexer to path
sys.path.insert(0, 'rag_indexer')

# Import and run indexer
if __name__ == "__main__":
    import indexer
