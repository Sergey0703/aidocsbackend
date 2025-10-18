#!/usr/bin/env python3
"""
Performance monitoring script for RAG indexing
"""

import psutil
import time
import requests
import json
import os
from datetime import datetime

def get_ollama_stats():
    """Get Ollama performance statistics"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return f"🟢 Online ({len(models)} models loaded)"
        else:
            return f"🔴 Error (HTTP {response.status_code})"
    except:
        return "🔴 Offline"

def get_gpu_stats():
    """Get GPU statistics if available"""
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            gpu_util, mem_used, mem_total, temp = result.stdout.strip().split(', ')
            return f"🎮 GPU: {gpu_util}% util, {mem_used}MB/{mem_total}MB, {temp}°C"
        else:
            return "🎮 GPU: Not available"
    except:
        return "🎮 GPU: Not available"

def monitor_system():
    """Monitor system performance during indexing"""
    print("=== RAG Indexing Performance Monitor ===")
    print("Press Ctrl+C to stop monitoring\n")
    
    try:
        while True:
            # Clear screen
            os.system('clear' if os.name == 'posix' else 'cls')
            
            # System stats
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            
            # Network stats
            net_io = psutil.net_io_counters()
            
            # Process stats
            indexer_processes = [p for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']) 
                               if 'python' in p.info['name'] and any(cmd for cmd in p.cmdline() if 'indexer' in cmd)]
            
            # Display
            print(f"📊 Performance Monitor - {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 60)
            print(f"🖥️  CPU Usage: {cpu_percent}%")
            print(f"🧠 Memory: {memory.percent}% ({memory.available/1024**3:.1f}GB available)")
            print(f"💾 Disk I/O: R:{disk_io.read_bytes/1024**3:.2f}GB W:{disk_io.write_bytes/1024**3:.2f}GB")
            print(f"🌐 Network: ↓{net_io.bytes_recv/1024**2:.0f}MB ↑{net_io.bytes_sent/1024**2:.0f}MB")
            print(f"🤖 Ollama: {get_ollama_stats()}")
            print(f"{get_gpu_stats()}")
            
            if indexer_processes:
                print(f"\n🔍 Indexer Processes:")
                for p in indexer_processes:
                    print(f"   PID {p.info['pid']}: CPU {p.info['cpu_percent']:.1f}%, RAM {p.info['memory_percent']:.1f}%")
            
            print("=" * 60)
            print("💡 Optimization Tips:")
            if cpu_percent > 95:
                print("⚠️  Very high CPU usage - consider reducing batch size")
            elif cpu_percent > 80:
                print("ℹ️  High CPU usage - normal for indexing")
            
            if memory.percent > 90:
                print("⚠️  Very high memory usage - consider reducing workers")
            elif memory.percent > 75:
                print("ℹ️  High memory usage - normal for large datasets")
            
            if not indexer_processes:
                print("ℹ️  No indexer processes detected")
            
            print("\n⏱️  Updating in 5 seconds...")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped.")

if __name__ == "__main__":
    monitor_system()
