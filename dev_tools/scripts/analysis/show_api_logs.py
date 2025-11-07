#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# show_api_logs.py - Extract and display API search logs

import subprocess
import sys

# Get output from background process
result = subprocess.run(
    ["bash", "-c", "tail -100 nul"],  # This won't work on Windows, need different approach
    capture_output=True,
    text=True
)

print("This script needs adjustment for Windows.")
print("Instead, please check the terminal window where you ran 'python run_api.py'")
print("You should see detailed logs there!")
