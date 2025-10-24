# Supabase Storage Migration Guide

This guide explains how to use the new Supabase Storage integration for document management in the RAG indexer.

## Overview

**Phase 1** migrates raw documents from local filesystem to Supabase Storage. This provides:

- ✅ Centralized document storage accessible from multiple API instances
- ✅ Automatic backups and versioning
- ✅ Document lifecycle tracking (pending → processing → processed/failed)
- ✅ Scalable architecture for production deployments

## Prerequisites

1. **Supabase Project** with:
   - Storage bucket created (`vehicle-documents`)
   - PostgreSQL database with `vecs` schema
   - Service role key with Storage access

2. **Python Dependencies**:
   ```bash
   pip install supabase
   ```

3. **Environment Variables** configured (see `.env.storage.example`)

## Setup Instructions

### Step 1: Create Supabase Storage Bucket

In your Supabase Dashboard:

1. Navigate to **Storage** → **Create new bucket**
2. Bucket name: `vehicle-documents`
3. Public bucket: **OFF** (keep private)
4. File size limit: 50 MB

### Step 2: Run Database Schema

Run the complete SQL script from README.md in Supabase SQL Editor:

**Important**: After running the schema, verify:

```sql
-- Check new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'document_registry'
  AND column_name IN ('storage_bucket', 'storage_path', 'storage_status');

-- Should return 3 rows
```

### Step 3: Configure Environment

Copy and customize the example environment file:

```bash
cp .env.storage.example .env
```

Edit `.env` and set:

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_CONNECTION_STRING=postgresql://postgres:...

# Optional (defaults shown)
SUPABASE_STORAGE_BUCKET=vehicle-documents
STORAGE_TEMP_DIR=/tmp/rag_storage_temp
```

### Step 4: Test the Workflow

Use the test script to verify everything works:

```bash
# Upload and process a test document
python scripts/test_storage_workflow.py /path/to/test.pdf
```

Expected output:
```
[STEP 1] Initializing managers...
[+] Managers initialized

[STEP 2] Uploading test document to Storage...
[+] Uploaded successfully

[STEP 3] Creating registry entry...
[+] Registry entry created

[STEP 4] Verifying document is pending...
[+] Document found in pending queue

[STEP 5] Processing document (conversion)...
[+] Conversion successful

[STEP 6] Verifying document was processed...
[+] Document successfully processed

TEST COMPLETED SUCCESSFULLY
```

## Usage Workflows

### Workflow 1: Upload Documents

Upload raw documents to Supabase Storage:

```bash
# Upload entire directory
python scripts/upload_documents.py --dir /path/to/documents

# Upload single file
python scripts/upload_documents.py --file document.pdf

# Upload with document type
python scripts/upload_documents.py --file insurance.pdf --document-type insurance

# Recursively upload subdirectories
python scripts/upload_documents.py --dir /path/to/docs --recursive

# Check pending uploads
python scripts/upload_documents.py --list-pending
```

This will:
1. Upload files to `raw/pending/` in Supabase Storage
2. Create registry entries with `storage_status='pending'`

### Workflow 2: Process Pending Documents

Convert uploaded documents to markdown:

```bash
# Process all pending documents
python process_documents_storage.py

# Process only first 10
python process_documents_storage.py --limit 10

# Enable OCR for images
python process_documents_storage.py --enable-ocr

# Dry run (preview without processing)
python process_documents_storage.py --dry-run
```

This will:
1. Download documents from Storage to temp directory
2. Convert using Docling
3. Save markdown to `MARKDOWN_OUTPUT_DIR`
4. Move raw files to `raw/processed/{year}/{month}/`
5. Update `storage_status='processed'`
6. Cleanup temp files

### Workflow 3: Index to Vector Database

After conversion, create embeddings:

```bash
# From project root
cd ..
python rag_indexer/indexer.py
```

This uses the existing indexing pipeline (unchanged).

## Document Lifecycle

Documents progress through these states:

```
1. Upload → raw/pending/          storage_status='pending'
2. Download to temp               storage_status='processing'
3. Convert with Docling
4a. Success → raw/processed/      storage_status='processed'
4b. Failure → raw/failed/         storage_status='failed'
```

### Checking Document Status

```sql
-- Count documents by status
SELECT storage_status, COUNT(*)
FROM vecs.document_registry
GROUP BY storage_status;

-- Find failed documents
SELECT original_filename, storage_path, status
FROM vecs.document_registry
WHERE storage_status = 'failed'
ORDER BY uploaded_at DESC;

-- Find documents ready for indexing
SELECT original_filename, markdown_file_path
FROM vecs.document_registry
WHERE storage_status = 'processed'
  AND status != 'indexed';
```

## Storage Structure

Files are organized in the `vehicle-documents` bucket:

```
vehicle-documents/
├── raw/
│   ├── pending/                    # New uploads awaiting processing
│   │   └── {uuid}_{filename}.pdf
│   ├── processed/                  # Successfully converted
│   │   └── 2025/01/
│   │       └── {uuid}_{filename}.pdf
│   └── failed/                     # Conversion failures
│       └── {uuid}_{filename}.pdf
```

## Troubleshooting

### Issue: "SUPABASE_URL not set"

**Solution**: Ensure `.env` file exists and contains:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### Issue: "Bucket 'vehicle-documents' not found"

**Solution**: Create bucket in Supabase Dashboard or change bucket name in `.env`:
```bash
SUPABASE_STORAGE_BUCKET=your-bucket-name
```

### Issue: Upload succeeds but download fails

**Solution**: Check RLS policies allow service_role to read:
```sql
-- Verify policies exist
SELECT * FROM pg_policies
WHERE tablename = 'objects'
  AND schemaname = 'storage';
```

### Issue: Documents stuck in "processing" status

**Solution**: Reset status manually:
```sql
UPDATE vecs.document_registry
SET storage_status = 'pending'
WHERE storage_status = 'processing';
```

Then re-run `process_documents_storage.py`.

### Issue: Temp files not cleaned up

**Solution**: Manually clean temp directory:
```bash
rm -rf /tmp/rag_storage_temp/*
```

Or set different temp dir in `.env`:
```bash
STORAGE_TEMP_DIR=/custom/temp/path
```

## API Integration (Future)

The Storage workflow can be integrated with FastAPI for web uploads:

```python
from fastapi import UploadFile
from storage.storage_manager import SupabaseStorageManager

@app.post("/upload-document")
async def upload_document(file: UploadFile):
    storage_manager = SupabaseStorageManager()

    # Upload to Storage
    result = storage_manager.upload_document(
        file=await file.read(),
        original_filename=file.filename
    )

    # Create registry entry
    registry_id = registry_manager.create_entry_from_storage(...)

    return {"document_id": registry_id, "status": "pending"}
```

## Performance Tips

1. **Batch Processing**: Process documents in batches during off-peak hours
2. **Rate Limiting**: Gemini API is rate-limited to 10 req/s by default
3. **Temp Directory**: Use fast local disk (SSD) for `STORAGE_TEMP_DIR`
4. **Cleanup**: Run cleanup script weekly to remove old temp files

## Comparison: Storage vs Filesystem

| Feature | Local Filesystem | Supabase Storage |
|---------|------------------|------------------|
| **Scalability** | Single server only | Multiple servers |
| **Backups** | Manual setup | Automatic |
| **Access Control** | OS-level | RLS policies |
| **CDN** | None | Built-in |
| **Cost** | Free (local disk) | Free tier → Paid |
| **Monitoring** | Custom scripts | Dashboard |
| **Versioning** | Manual | Built-in |

## Migration Checklist

- [ ] Create Supabase Storage bucket
- [ ] Run database migrations (001, 002)
- [ ] Update `.env` with Storage credentials
- [ ] Test workflow with sample document
- [ ] Upload existing documents (optional)
- [ ] Update deployment scripts/CI to use Storage mode
- [ ] Monitor first batch processing
- [ ] Clean up old local files (after verification)

## Next Steps

After completing Phase 1 (raw documents in Storage):

- **Phase 2** (optional): Store markdown/JSON in Storage for backups
- **Phase 3** (optional): Remove local filesystem mode entirely
- **API Integration**: Add upload endpoint to FastAPI backend

## Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Review migration SQL scripts for schema details
3. Check logs in `failed_conversions/` directory
4. Query `document_registry` table for status tracking

---

**Last Updated**: 2025-01-23
**Version**: 1.0.0 (Phase 1 - Raw Documents)
