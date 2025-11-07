# Console Search Tools

This directory contains powerful console-based search tools for querying your vector database.

## 📦 Quick Setup

Before using the search tools, ensure your environment is set up:

```bash
# 1. Navigate to the project root
cd c:\Projects\aidocsbackend

# 2. Activate virtual environment (if you have one)
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# 3. Install dependencies (if not already installed)
pip install -r client_rag/requirements.txt

# 4. Verify .env file exists with required variables
# client_rag/.env should contain:
# - SUPABASE_CONNECTION_STRING
# - GEMINI_API_KEY
# - EMBED_MODEL
# - EMBED_DIM
```

**Note:** If dependencies are already installed in your main project, you can skip step 3.

---

## 🚀 Available Tools

### 1. Interactive Console Search (`console_search.py`)
Full-featured interactive menu-driven search application.

**Features:**
- 📊 Interactive menu interface
- 🔍 Quick search with automatic optimization
- ⚙️ Advanced search with custom parameters
- 📄 File name search
- 🏥 System health check
- 📚 Built-in examples and help

**Usage:**
```bash
# Navigate to client_rag directory
cd client_rag

# Run the interactive search
python console_search.py
```

**Menu Options:**
1. **Quick Search** - Best for most queries, uses automatic entity extraction and query optimization
2. **Advanced Search** - Fine-tune similarity threshold and result count
3. **File Name Search** - Direct filename lookup in database
4. **Show Example Queries** - View example search queries
5. **System Status** - Check system health and configuration
6. **Help** - Show help and tips

---

### 2. Simple Command-Line Search (`simple_search.py`)
Fast, lightweight command-line search for quick queries.

**Features:**
- 🚄 Fast startup and execution
- 🎯 Entity detection
- 🔄 Automatic query variant generation
- 📊 Clean, formatted output
- 🛠️ Customizable parameters

**Usage:**
```bash
# Basic search
python simple_search.py "John Nolan"

# Search with custom parameters
python simple_search.py "231-D-54321" --top-k 10 --threshold 0.3

# Verbose mode (shows more details)
python simple_search.py "insurance documents" --verbose

# Get help
python simple_search.py --help
```

**Command-Line Options:**
- `query` - Your search query (required)
- `-k, --top-k` - Maximum number of results (default: 20)
- `-t, --threshold` - Similarity threshold 0.0-1.0 (default: 0.30)
- `-v, --verbose` - Enable verbose output with detailed information

---

## 📋 Examples

### Example 1: Search for Person Documents
```bash
# Interactive mode
python console_search.py
# Select option 1 (Quick Search)
# Enter: John Nolan

# Command-line mode
python simple_search.py "John Nolan"
```

### Example 2: Search for Vehicle Registration Number
```bash
python simple_search.py "231-D-54321" --top-k 15
```

### Example 3: Search for Document Type
```bash
python simple_search.py "insurance documents" --threshold 0.25
```

### Example 4: Find Specific File
```bash
python console_search.py
# Select option 3 (File Name Search)
# Enter: Safe Administration
```

### Example 5: Advanced Search with Custom Parameters
```bash
python simple_search.py "NCT expiry" --top-k 30 --threshold 0.20 --verbose
```

---

## 🔧 How It Works

### Hybrid Search System
Both tools use the same powerful hybrid search system:

1. **Vector Search** 🔍
   - Semantic similarity using Gemini embeddings (768D)
   - Adaptive similarity thresholds
   - Smart content validation

2. **Database Search** 🗄️
   - Exact phrase matching
   - Flexible term search
   - High relevance scoring for exact matches

3. **Hybrid Fusion** 🔥
   - Intelligent result deduplication
   - Source-aware scoring
   - Entity-aware boosting

### Entity Extraction
Automatically detects:
- Person names (John Nolan, Breeda Daly, etc.)
- Vehicle Registration Numbers (VRNs)
- Document types

### Query Optimization
- Generates query variants for better recall
- Uses entity-specific search strategies
- Adaptive thresholds based on query type

---

## 🎯 Search Tips

### For Best Results:
- **Person Queries**: Use full names
  - ✅ "John Nolan"
  - ✅ "tell me about John Nolan"
  - ✅ "John Nolan certifications"

- **Vehicle Queries**: Use VRN format
  - ✅ "231-D-54321"
  - ✅ "vehicle 231-D-54321"

- **Document Type Queries**: Use specific terms
  - ✅ "insurance documents"
  - ✅ "NCT records"
  - ✅ "service history"

### Adjusting Parameters:
- **Lower threshold** (0.20-0.25) → More results, broader recall
- **Higher threshold** (0.35-0.40) → Fewer results, higher precision
- **Higher top-k** (30-50) → More results to choose from

---

## ⚙️ Configuration

Both tools use the same configuration from [config/settings.py](config/settings.py) and [.env](.env):

### Key Settings:
```bash
# .env file
SUPABASE_CONNECTION_STRING="postgresql://..."
GEMINI_API_KEY="your-api-key"
EMBED_MODEL="text-embedding-004"
EMBED_DIM="768"
```

### Hybrid Search Configuration:
See [config/settings.py](config/settings.py) for detailed configuration:
- `enable_hybrid_search` - Enable/disable hybrid search
- `enable_vector_search` - Enable/disable vector search
- `enable_database_search` - Enable/disable database search
- Similarity thresholds, top-k limits, fusion weights, etc.

---

## 🏥 System Health Check

### Using Interactive Tool:
```bash
python console_search.py
# Select option 5 (System Status)
```

### What It Checks:
- ✅ Database connection
- ✅ Vector retriever availability
- ✅ Database retriever availability
- ✅ Configuration validity
- ✅ Hybrid search status
- ✅ API keys and credentials

---

## 🐛 Troubleshooting

### Common Issues:

**1. Import Errors**
```bash
# Make sure you're in the client_rag directory
cd client_rag
python console_search.py
```

**2. Database Connection Errors**
- Check `.env` file has correct `SUPABASE_CONNECTION_STRING`
- Verify database is accessible
- Run health check to diagnose

**3. No Results Found**
- Try lowering similarity threshold: `--threshold 0.20`
- Try increasing top-k: `--top-k 50`
- Use verbose mode to see what's happening: `--verbose`
- Check if documents are indexed in database

**4. Slow Performance**
- First search is slower (initializing models)
- Subsequent searches are faster (cached)
- Large top-k values take longer

**5. API Errors**
- Check `GEMINI_API_KEY` in `.env`
- Verify API quota/rate limits
- Check internet connection

---

## 📊 Understanding Results

### Result Fields:
- **Filename** - Document filename
- **Score** - Similarity score (0.0-1.0)
- **Hybrid Score** - Combined hybrid score (if available)
- **Source** - Search method used (vector, database, etc.)
- **Match Type** - Type of match (exact_phrase, flexible_terms, etc.)
- **Preview** - Content preview
- **Chunk** - Chunk index in document

### Score Interpretation:
- **0.80-1.00** - Excellent match, highly relevant
- **0.60-0.79** - Good match, likely relevant
- **0.40-0.59** - Moderate match, may be relevant
- **0.20-0.39** - Weak match, possibly relevant
- **0.00-0.19** - Very weak match, unlikely relevant

---

## 📚 Additional Resources

- **Main Documentation**: [README.md](../README.md)
- **Project Overview**: [CLAUDE.md](../CLAUDE.md)
- **Configuration Guide**: [config/settings.py](config/settings.py)
- **API Reference**: [api/](api/)

---

## 🤝 Need Help?

1. Run the help command:
   ```bash
   python simple_search.py --help
   ```

2. Use the interactive help:
   ```bash
   python console_search.py
   # Select option 6 (Help)
   ```

3. Check system status:
   ```bash
   python console_search.py
   # Select option 5 (System Status)
   ```

4. Review the logs and error messages - they usually contain helpful information!

---

**Happy Searching! 🚀**
