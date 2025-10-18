#!/bin/bash

echo "=== Ollama Status Check ==="
echo "Service status:"
systemctl status ollama --no-pager -l

echo -e "\nAPI response:"
curl -s http://localhost:11434/api/tags | jq '.' 2>/dev/null || curl -s http://localhost:11434/api/tags

echo -e "\nLoaded models:"
curl -s http://localhost:11434/api/tags | jq '.models[].name' 2>/dev/null || echo "Unable to parse models"

echo -e "\nSystem resources:"
echo "CPU: $(nproc) cores"
echo "RAM: $(free -h | awk '/^Mem:/{print $2}') total, $(free -h | awk '/^Mem:/{print $7}') available"
