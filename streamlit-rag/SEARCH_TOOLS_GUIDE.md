# Search Tools Guide

This guide explains the different search tools available in the RAG system and when to use each one.

## Overview

The system provides **two search tools** with different purposes:

1. **`simple_search.py`** - Fast CLI tool for quick searches
2. **`console_search.py`** - Interactive console with menu and multiple features

---

## 🚀 simple_search.py - Quick CLI Search

### Purpose
Fast, single-query command-line search tool for quick lookups and automation.

### Usage

```bash
# Basic search
python simple_search.py "your query"

# With options
python simple_search.py "John Nolan" --top-k 10 --threshold 0.3 --verbose

# Search for VRN
python simple_search.py "231-D-54321"

# Search for vehicle
python simple_search.py "FORD TRANSIT" --top-k 5
```

### Command-Line Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `query` | - | Required | Search query (positional argument) |
| `--top-k` | `-k` | 20 | Maximum number of results to return |
| `--threshold` | `-t` | 0.30 | Similarity threshold (0.0-1.0) |
| `--verbose` | `-v` | False | Show detailed processing information |

### Examples

#### 1. Quick VRN Lookup
```bash
python simple_search.py "231-D-54321"
```
**Output:**
```
🔍 Searching for: '231-D-54321'
✅ Found 1 results
⏱️  Search time: 0.946s

1. 📄 VCR.md
   Score: 0.6500 | Hybrid: 0.8873
   Preview: **A. Uimhir Chláraithe / Registration Number:** 231-D-54321...
```

#### 2. Person Search with Details
```bash
python simple_search.py "John Nolan" --verbose
```
**Output:**
```
🔧 Initializing system...
✅ Query validated
   Intent: person_search
   Confidence: 0.90
🔎 Extracting entities...
✅ Entity detected: 'John Nolan' (method: regex)
🔄 Generating query variants...

🔍 Searching for: 'John Nolan'
✅ Found 9 results
```

#### 3. Vehicle Make/Model Search
```bash
python simple_search.py "FORD TRANSIT" --top-k 5 --threshold 0.25
```

#### 4. Batch Processing (Automation)
```bash
# Search multiple VRNs from file
while read vrn; do
    echo "Searching: $vrn"
    python simple_search.py "$vrn" --top-k 3
    echo "---"
done < vehicle_list.txt
```

#### 5. Export Results to File
```bash
python simple_search.py "insurance documents" > search_results.txt
```

### When to Use simple_search.py

✅ **Use for:**
- Quick one-off searches
- Testing specific queries
- Automation scripts (CI/CD, cron jobs)
- Batch processing multiple queries
- Command-line workflows
- Performance benchmarking
- Debugging specific VRNs or names

❌ **Not ideal for:**
- Exploring the database interactively
- Trying multiple different searches
- Demonstrating the system to users
- Learning how the system works

---

## 🎯 console_search.py - Interactive Console

### Purpose
Feature-rich interactive console for exploration, demonstration, and learning.

### Usage

```bash
# Simply run the script
python console_search.py
```

The interactive menu will appear automatically.

### Menu Options

```
================================================================================
SEARCH OPTIONS
--------------------------------------------------------------------------------
1. Quick Search          - Search with automatic entity extraction
2. Advanced Search       - Search with custom parameters
3. File Name Search      - Search by document filename
4. Show Example Queries  - View example search queries
5. System Status         - Check system health and configuration
6. Help                  - Show help and tips
0. Exit                  - Quit the application
================================================================================
```

### Features

#### 1️⃣ Quick Search
- Automatic query validation
- Entity extraction
- Query rewriting
- Instant results

**Example Flow:**
```
Choose option: 1
Enter your search query: John Nolan

🔍 Processing query...
✅ Query validated (Intent: person_search)
🎯 Entity detected: 'John Nolan'

📊 RESULTS (9 found)
1. Training_Certificate_JohnNolan.pdf
2. Driver_License_JohnNolan.pdf
...
```

#### 2️⃣ Advanced Search
- Custom top_k parameter
- Custom similarity threshold
- Full control over search parameters

**Example Flow:**
```
Choose option: 2
Enter your search query: 231-D-54321
Number of results (default 20): 10
Similarity threshold (default 0.30): 0.25

🔍 Searching with custom parameters...
✅ Found 1 results
```

#### 3️⃣ File Name Search
- Search by exact or partial filename
- Useful for finding specific documents

**Example Flow:**
```
Choose option: 3
Enter filename (or part of it): VCR
Enter number of results (default 10): 5

📄 Files matching 'VCR':
1. VCR.md
```

#### 4️⃣ Example Queries
Shows pre-configured example searches from the system:
- Person names (John Nolan, Breeda Daly, etc.)
- VRN patterns (191-D-12345, 231-D-54321)
- Document types (insurance, NCT, certifications)

#### 5️⃣ System Status
Comprehensive health check:
```
🏥 SYSTEM HEALTH CHECK
✅ Vector Search: Available
✅ Database Search: Available
✅ Hybrid Search: ENABLED
✅ Entity Extraction: 3 methods available (LLM, SpaCy, Regex)
✅ Query Rewriting: Available
```

#### 6️⃣ Help
Built-in help system with:
- Search tips
- Query syntax examples
- Performance guidelines
- Troubleshooting hints

### Example Session

```bash
$ python console_search.py

================================================================================
  VECTOR DATABASE CONSOLE SEARCH
  RAG System with Hybrid Search (Vector + Database)
================================================================================

🔧 Initializing configuration...
✅ Configuration loaded successfully
🔧 Initializing multi-strategy retriever...
✅ Retriever initialized successfully
🔧 Initializing query processors...
✅ Query processors initialized successfully

🏥 Running system health check...
✅ System health: ALL SYSTEMS OPERATIONAL

================================================================================
SEARCH OPTIONS
--------------------------------------------------------------------------------
1. Quick Search
2. Advanced Search
3. File Name Search
4. Show Example Queries
5. System Status
6. Help
0. Exit
================================================================================

Choose an option (0-6): 4

================================================================================
EXAMPLE QUERIES
--------------------------------------------------------------------------------
Try these example searches:

People:
  - John Nolan
  - tell me about John Nolan
  - show me John Nolan certifications
  - Breeda Daly
  - Bernie Loughnane

Vehicles:
  - 231-D-54321
  - FORD TRANSIT
  - vehicle registration

Documents:
  - insurance documents
  - NCT certificates
  - training records
================================================================================

Choose an option (0-6): 1

Enter your search query (or 'back' to return): John Nolan

🔍 Processing query: 'John Nolan'
✅ Query validated
   Intent: person_search
   Confidence: 0.90

🎯 Entity detected: 'John Nolan'
🔄 Generated 3 query variants

⏱️  Search time: 0.876s
📊 Found 9 results from 15 candidates
🔧 Methods: database_hybrid, vector_smart_threshold

================================================================================
RESULTS (showing top 9)
================================================================================

1. 📄 Training_Certificate_JohnNolan.pdf
   Score: 0.8750 | Source: database_hybrid
   Preview: Certificate of Training Completion...

2. 📄 Driver_License_JohnNolan.pdf
   Score: 0.8200 | Source: vector_smart_threshold
   Preview: Driver's License - John Nolan...

[... more results ...]

Choose an option (0-6): 0

👋 Thank you for using Vector Database Search!
Goodbye!
```

### When to Use console_search.py

✅ **Use for:**
- **Exploring the database** - trying different queries without restarting
- **Demonstrations** - showing the system to clients/stakeholders
- **Learning** - understanding how the system works
- **Training users** - teaching new team members
- **Complex debugging** - using multiple search types in sequence
- **Testing different parameters** - experimenting with thresholds
- **System diagnostics** - checking health and status

❌ **Not ideal for:**
- Automation (scripts, CI/CD)
- Single quick lookups
- Batch processing
- Programmatic access

---

## 📊 Comparison Table

| Feature | simple_search.py | console_search.py |
|---------|------------------|-------------------|
| **Interface** | Command-line arguments | Interactive menu |
| **Queries per session** | 1 | Unlimited |
| **Startup time** | Fast (~1s) | Slower (~3s initial) |
| **Health check** | ❌ No | ✅ Yes |
| **Examples** | ❌ No | ✅ Built-in |
| **Help** | `--help` flag | Interactive help menu |
| **Automation friendly** | ✅ Excellent | ❌ Not suitable |
| **Learning curve** | Low | Very low (guided) |
| **Debugging** | Good (--verbose) | Excellent (multiple tools) |
| **Batch processing** | ✅ Yes (loops) | ❌ No |
| **Export results** | ✅ Easy (redirect) | ⚠️ Manual copy |
| **Advanced options** | CLI flags | Interactive prompts |
| **Best for** | Automation & quick checks | Exploration & demos |

---

## 🎯 Decision Guide

### "Which tool should I use?"

```
START
  ↓
Do you need to automate/script searches?
  ├── YES → Use simple_search.py
  │   └── Example: Batch processing VRNs from file
  │
  └── NO → Continue
      ↓
  Do you want to try multiple different searches?
      ├── YES → Use console_search.py
      │   └── Example: Exploring what's in the database
      │
      └── NO → Continue
          ↓
      Is this a one-time quick lookup?
          ├── YES → Use simple_search.py
          │   └── Example: "What's in this VRN?"
          │
          └── NO → Use console_search.py
              └── Example: Demonstrating to client
```

---

## 💡 Pro Tips

### For simple_search.py

1. **Use verbose mode for debugging:**
   ```bash
   python simple_search.py "query" --verbose
   ```

2. **Export to file for analysis:**
   ```bash
   python simple_search.py "query" > results.txt
   ```

3. **Combine with other tools:**
   ```bash
   # Find and count results
   python simple_search.py "John Nolan" | grep -c "📄"

   # Search and email results
   python simple_search.py "urgent" | mail -s "Search Results" admin@company.com
   ```

4. **Lower threshold for broader results:**
   ```bash
   python simple_search.py "vague query" --threshold 0.2
   ```

### For console_search.py

1. **Start with System Status (option 5)** to verify everything works

2. **Use Example Queries (option 4)** to learn query patterns

3. **Try Quick Search first**, then Advanced if you need customization

4. **Use File Name Search** when you know part of the filename

5. **Keep the console running** for multiple searches - no need to restart

---

## 🚨 Troubleshooting

### simple_search.py

**Problem:** "No results found" for valid query
```bash
# Try lowering threshold
python simple_search.py "query" --threshold 0.2

# Try verbose to see what's happening
python simple_search.py "query" --verbose
```

**Problem:** Too many irrelevant results
```bash
# Raise threshold
python simple_search.py "query" --threshold 0.4

# Reduce number of results
python simple_search.py "query" --top-k 5
```

### console_search.py

**Problem:** Script hangs on startup
- Check database connection in `.env`
- Verify `SUPABASE_CONNECTION_STRING` is correct

**Problem:** "Import error"
- Ensure you're in the `streamlit-rag/` directory
- Check virtual environment is activated

---

## 🔧 Advanced Usage

### Creating Aliases (for faster access)

**Bash/Linux:**
```bash
# Add to ~/.bashrc or ~/.zshrc
alias qsearch='python /path/to/simple_search.py'
alias isearch='python /path/to/console_search.py'

# Then use:
qsearch "231-D-54321"
isearch
```

**Windows PowerShell:**
```powershell
# Add to $PROFILE
function qsearch { python C:\path\to\simple_search.py $args }
function isearch { python C:\path\to\console_search.py }

# Then use:
qsearch "231-D-54321"
isearch
```

### Integration Examples

#### 1. Scheduled Daily Reports
```bash
#!/bin/bash
# daily_search_report.sh

echo "Daily Search Report - $(date)" > report.txt
echo "======================================" >> report.txt

python simple_search.py "expiring insurance" >> report.txt
python simple_search.py "expiring NCT" >> report.txt

mail -s "Daily Report" admin@company.com < report.txt
```

#### 2. API Integration
```python
import subprocess
import json

def search_vrn(vrn):
    result = subprocess.run(
        ['python', 'simple_search.py', vrn],
        capture_output=True,
        text=True
    )
    return result.stdout

# Use in your API
vrn_data = search_vrn("231-D-54321")
```

---

## 📚 Related Documentation

- **[README.md](../README.md)** - Main project documentation
- **[FIX_WARNINGS.md](FIX_WARNINGS.md)** - Troubleshooting guide
- **[config/settings.py](config/settings.py)** - Configuration options
- **[CLAUDE.md](../CLAUDE.md)** - Detailed architecture guide

---

## 🤝 Support

If you encounter issues:

1. Check **System Status** in `console_search.py` (option 5)
2. Review **[FIX_WARNINGS.md](FIX_WARNINGS.md)**
3. Run with `--verbose` flag for details
4. Check logs in the console output

---

**Last Updated:** 2025-10-18
**Version:** 1.0
