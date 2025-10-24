# Database Schema Updates - Storage Integration

## Summary

The main [README.md](../README.md) SQL script has been updated to include all necessary fields and policies for Supabase Storage integration.

## What Changed in README.md

### 1. Updated `vecs.document_registry` Table

**New Storage Fields Added:**
```sql
storage_bucket TEXT DEFAULT 'vehicle-documents',
storage_path TEXT,
original_filename TEXT,
file_size_bytes BIGINT,
content_type TEXT,
storage_status TEXT DEFAULT 'pending' CHECK (...)
```

**Modified Fields:**
- `raw_file_path` - Now **nullable** (was UNIQUE NOT NULL)
- `status` - Added `'pending_processing'` to allowed values

### 2. New Indexes

```sql
CREATE INDEX idx_document_registry_storage_path
CREATE INDEX idx_document_registry_storage_status
CREATE INDEX idx_document_registry_uploaded_at
CREATE UNIQUE INDEX idx_document_registry_storage_path_unique
```

### 3. Storage Policies

Added 6 RLS policies for `storage.objects`:
- Service role: full CRUD access
- Authenticated users: read all, upload to `raw/pending/` only

### 4. New Query Examples

Added Storage-specific queries:
- Get pending documents
- Count by status
- Find failed conversions
- Search by storage_path

## Setup Instructions

### For Fresh Database (Recommended)

Simply run the complete SQL script from README.md:

```sql
-- Copy entire script from README.md and run in Supabase SQL Editor
-- It creates all tables with Storage support from scratch
-- No separate migrations needed!
```

## Verification

After running the script, verify:

```sql
-- Check new columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'document_registry'
  AND column_name IN (
    'storage_bucket',
    'storage_path',
    'storage_status',
    'original_filename',
    'file_size_bytes',
    'content_type'
  );

-- Should return 6 rows

-- Check Storage policies exist
SELECT policyname, cmd, roles
FROM pg_policies
WHERE tablename = 'objects'
  AND schemaname = 'storage'
  AND policyname LIKE '%vehicle-documents%';

-- Should return 6 policies
```

## Backward Compatibility

The schema remains **100% backward compatible**:

- Old `raw_file_path` still works (now nullable)
- Old `status` values still valid
- Existing filesystem-based code continues to work
- Storage fields are optional (can be NULL)

## Next Steps

1. **Create Storage bucket** in Supabase Dashboard:
   - Name: `vehicle-documents`
   - Private: Yes
   - File size limit: 50 MB

2. **Configure environment** (see `.env.storage.example`)

3. **Start using Storage mode**:
   ```bash
   python scripts/upload_documents.py --dir /path/to/docs
   python process_documents_storage.py
   ```

## Rollback

If needed, you can rollback Storage changes:

```sql
-- Remove Storage-specific indexes
DROP INDEX IF EXISTS vecs.idx_document_registry_storage_path_unique;
DROP INDEX IF EXISTS vecs.idx_document_registry_uploaded_at;
DROP INDEX IF EXISTS vecs.idx_document_registry_storage_status;
DROP INDEX IF EXISTS vecs.idx_document_registry_storage_path;

-- Remove Storage columns (CAREFUL - this deletes data!)
ALTER TABLE vecs.document_registry
  DROP COLUMN IF EXISTS storage_status,
  DROP COLUMN IF EXISTS content_type,
  DROP COLUMN IF EXISTS file_size_bytes,
  DROP COLUMN IF EXISTS original_filename,
  DROP COLUMN IF EXISTS storage_path,
  DROP COLUMN IF EXISTS storage_bucket;

-- Restore raw_file_path as NOT NULL (if needed)
-- ALTER TABLE vecs.document_registry
--   ALTER COLUMN raw_file_path SET NOT NULL;
```

---

**Last Updated**: 2025-01-23
**Related Files**:
- [README.md](../README.md) - Updated SQL schema
- [STORAGE_MIGRATION_GUIDE.md](STORAGE_MIGRATION_GUIDE.md) - Usage guide
- [QUICKSTART_STORAGE.md](QUICKSTART_STORAGE.md) - Quick setup
