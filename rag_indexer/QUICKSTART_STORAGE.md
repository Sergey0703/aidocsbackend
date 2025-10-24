# Quick Start: Supabase Storage Mode

Fast setup guide for using Supabase Storage instead of local filesystem.

## 🚀 Quick Setup (5 minutes)

### 1. Configure Environment

```bash
# Copy example
cp .env.storage.example .env

# Edit .env and set these 3 required variables:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_CONNECTION_STRING=postgresql://postgres:...
```

### 2. Create Storage Bucket

**Option A: Automatic (Recommended)**
```bash
python scripts/setup_storage.py

# Should output: "SETUP COMPLETE ✓"
```

**Option B: Manual (via Dashboard)**
- **Storage** → **New bucket**
- Name: `vehicle-documents`
- Private: ✓
- Click **Create**

### 3. Run Database Schema

Copy **entire** SQL script from [../README.md](../README.md) and run in **Supabase SQL Editor**.

This single script creates:
- ✅ Tables (vehicles, document_registry, documents)
- ✅ Storage fields and indexes
- ✅ Storage policies
- ✅ Everything needed - no separate migrations!

### 4. Test It Works

```bash
# Upload a test PDF
python scripts/upload_documents.py --file test.pdf

# Process it
python process_documents_storage.py --limit 1

# Should see: "PROCESSING COMPLETE" ✓
```

## 📋 Daily Workflow

### Step 1: Upload Documents

```bash
# Upload from directory
python scripts/upload_documents.py --dir /path/to/documents

# Or upload single file
python scripts/upload_documents.py --file document.pdf
```

### Step 2: Convert to Markdown

```bash
# Process all pending
python process_documents_storage.py

# Or process with limit
python process_documents_storage.py --limit 10
```

### Step 3: Create Embeddings

```bash
# Run indexer (from project root)
cd ..
python rag_indexer/indexer.py
```

Done! Documents are now searchable via API.

## 🔍 Check Status

```sql
-- See pending documents
SELECT COUNT(*) FROM vecs.document_registry WHERE storage_status = 'pending';

-- See processed documents
SELECT COUNT(*) FROM vecs.document_registry WHERE storage_status = 'processed';

-- See failed documents
SELECT original_filename, status
FROM vecs.document_registry
WHERE storage_status = 'failed';
```

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| "SUPABASE_URL not set" | Check `.env` file exists and has correct values |
| "Bucket not found" | Create `vehicle-documents` bucket in Supabase Dashboard |
| Upload works but download fails | Check Storage policies were applied (script 001) |
| No pending documents | Run `upload_documents.py` first |

## 📁 File Structure

After setup, you'll have:

```
rag_indexer/
├── storage/
│   ├── storage_manager.py      ✓ New: Handles Storage uploads/downloads
│   └── __init__.py             ✓ New
├── scripts/
│   ├── upload_documents.py     ✓ New: Upload files to Storage
│   └── test_storage_workflow.py ✓ New: Test end-to-end
├── migrations/
│   ├── 001_storage_bucket_policies.sql ✓ New
│   └── 002_document_registry_storage_fields.sql ✓ New
├── process_documents_storage.py ✓ New: Main processing script
├── .env.storage.example        ✓ New: Environment template
└── STORAGE_MIGRATION_GUIDE.md  📖 Full documentation
```

## 🎯 What Changed?

**Before (Filesystem Mode)**:
```
Raw docs → Local folder → Docling → Markdown → Indexer
```

**After (Storage Mode)**:
```
Upload → Supabase Storage → Download → Docling → Markdown → Indexer
                ↓
         Database tracking (pending/processed/failed)
```

**Benefits**:
- ✅ Multi-server access to same documents
- ✅ Automatic backups
- ✅ Document lifecycle tracking
- ✅ Production-ready scaling

## 📚 Full Documentation

For detailed info, see: **[STORAGE_MIGRATION_GUIDE.md](STORAGE_MIGRATION_GUIDE.md)**

- Architecture details
- API integration examples
- Performance tuning
- Troubleshooting guide

---

**Ready to Go?** Start with Step 1 above! 🚀
