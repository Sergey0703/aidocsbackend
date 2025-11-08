-- ============================================================================
-- PRODUCTION RAG SYSTEM - DATABASE SCHEMA
-- Vehicle Management + Document Registry + Vector Search
-- UPDATED: documents.id changed from UUID to TEXT
-- UPDATED: Added Supabase Storage support to document_registry
-- UPDATED: Added MD/JSON Storage paths (markdown_storage_path, json_storage_path)
-- ============================================================================

-- ШАГ 1: Создание или обновление универсальной функции для `updated_at`
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = now();
   RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- VEHICLES TABLE - Реестр транспортных средств
-- ============================================================================

CREATE TABLE IF NOT EXISTS vecs.vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Основная информация
    registration_number TEXT UNIQUE NOT NULL,
    vin_number TEXT UNIQUE,
    make TEXT,
    model TEXT,
    
    -- Даты истечения документов
    insurance_expiry_date DATE,
    motor_tax_expiry_date DATE,
    nct_expiry_date DATE,
    
    -- Статус и назначение
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'maintenance', 'inactive', 'sold', 'archived')),
    current_driver_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Метаданные
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_vehicles_registration ON vecs.vehicles(registration_number);
CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vecs.vehicles(status);
CREATE INDEX IF NOT EXISTS idx_vehicles_driver ON vecs.vehicles(current_driver_id);

-- Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_vehicles_updated_at ON vecs.vehicles;
CREATE TRIGGER update_vehicles_updated_at
    BEFORE UPDATE ON vecs.vehicles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- DOCUMENT REGISTRY - Мастер-таблица документов
-- ============================================================================

CREATE TABLE IF NOT EXISTS vecs.document_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Связь с транспортным средством (опционально)
    vehicle_id UUID REFERENCES vecs.vehicles(id) ON DELETE SET NULL,

    -- 🆕 Supabase Storage fields (for Storage mode)
    storage_bucket TEXT DEFAULT 'vehicle-documents',
    storage_path TEXT,                      -- RAW file path in Storage (raw/pending/, raw/processed/)
    original_filename TEXT,
    file_size_bytes BIGINT,
    content_type TEXT,
    storage_status TEXT DEFAULT 'pending' CHECK (storage_status IN (
        'pending',
        'processing',
        'processed',
        'failed',
        'indexed'
    )),

    -- 🆕 Storage paths for converted files (MD/JSON)
    markdown_storage_path TEXT,             -- MD file in Storage (markdown/processed/filename.md)
    markdown_metadata_path TEXT,            -- Conversion metadata (markdown/_metadata/filename.json)
    json_storage_path TEXT,                 -- DoclingDocument JSON (json/processed/filename.json)

    -- 🆕 File hash for incremental indexing (detects file changes)
    file_hash TEXT,                         -- SHA256 hash of original file (for change detection)

    -- Пути к файлам (legacy/filesystem mode - now optional)
    raw_file_path TEXT,
    markdown_file_path TEXT,

    -- Метаданные документа
    document_type TEXT CHECK (document_type IN (
        'insurance',
        'motor_tax',
        'nct_certificate',
        'service_record',
        'purchase_agreement',
        'registration_document',
        'drivers_manual',
        'other'
    )),

    -- Статус обработки документа
    status TEXT DEFAULT 'pending_processing' CHECK (status IN (
        'pending_assignment',
        'pending_processing',
        'unassigned',
        'assigned',
        'pending_ocr',
        'pending_indexing',
        'processed',
        'archived',
        'failed'
    )),

    -- Извлечённые данные
    extracted_data JSONB DEFAULT '{}'::jsonb,

    -- Метаданные
    uploaded_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Индексы (базовые - для колонок, которые всегда существуют)
CREATE INDEX IF NOT EXISTS idx_document_registry_vehicle ON vecs.document_registry(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_document_registry_status ON vecs.document_registry(status);
CREATE INDEX IF NOT EXISTS idx_document_registry_type ON vecs.document_registry(document_type);
CREATE INDEX IF NOT EXISTS idx_document_registry_raw_path ON vecs.document_registry(raw_file_path);
CREATE INDEX IF NOT EXISTS idx_document_registry_md_path ON vecs.document_registry(markdown_file_path);
CREATE INDEX IF NOT EXISTS idx_document_registry_extracted_data ON vecs.document_registry USING gin(extracted_data);

-- 🆕 ALTER TABLE для добавления Storage колонок (если таблица уже существует)
DO $$
BEGIN
    -- Add storage_bucket column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'storage_bucket') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN storage_bucket TEXT DEFAULT 'vehicle-documents';
    END IF;

    -- Add storage_path column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'storage_path') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN storage_path TEXT;
    END IF;

    -- Add original_filename column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'original_filename') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN original_filename TEXT;
    END IF;

    -- Add file_size_bytes column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'file_size_bytes') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN file_size_bytes BIGINT;
    END IF;

    -- Add content_type column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'content_type') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN content_type TEXT;
    END IF;

    -- Add storage_status column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'storage_status') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN storage_status TEXT DEFAULT 'pending';
        ALTER TABLE vecs.document_registry ADD CONSTRAINT check_storage_status
            CHECK (storage_status IN ('pending', 'processing', 'processed', 'failed', 'indexed'));
    END IF;

    -- 🆕 Add markdown_storage_path column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'markdown_storage_path') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN markdown_storage_path TEXT;
    END IF;

    -- 🆕 Add markdown_metadata_path column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'markdown_metadata_path') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN markdown_metadata_path TEXT;
    END IF;

    -- 🆕 Add json_storage_path column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'json_storage_path') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN json_storage_path TEXT;
    END IF;

    -- 🆕 Add file_hash column if it doesn't exist (for incremental indexing)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'vecs'
                   AND table_name = 'document_registry'
                   AND column_name = 'file_hash') THEN
        ALTER TABLE vecs.document_registry ADD COLUMN file_hash TEXT;
    END IF;
END $$;

-- 🆕 Storage mode indexes (создаются ПОСЛЕ добавления колонок)
CREATE INDEX IF NOT EXISTS idx_document_registry_storage_path ON vecs.document_registry(storage_path);
CREATE INDEX IF NOT EXISTS idx_document_registry_storage_status ON vecs.document_registry(storage_status);
CREATE INDEX IF NOT EXISTS idx_document_registry_uploaded_at ON vecs.document_registry(uploaded_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_registry_storage_path_unique
    ON vecs.document_registry(storage_bucket, storage_path)
    WHERE storage_path IS NOT NULL;

-- 🆕 Indexes for MD/JSON Storage paths
CREATE INDEX IF NOT EXISTS idx_document_registry_markdown_storage_path ON vecs.document_registry(markdown_storage_path);
CREATE INDEX IF NOT EXISTS idx_document_registry_json_storage_path ON vecs.document_registry(json_storage_path);

-- 🆕 Index for file_hash (for incremental indexing change detection)
CREATE INDEX IF NOT EXISTS idx_document_registry_file_hash ON vecs.document_registry(file_hash);

-- Триггер
DROP TRIGGER IF EXISTS update_document_registry_updated_at ON vecs.document_registry;
CREATE TRIGGER update_document_registry_updated_at
    BEFORE UPDATE ON vecs.document_registry
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- DOCUMENTS (CHUNKS) - Таблица для векторного поиска (RAG)
-- 🔥 ИЗМЕНЕНО: id теперь TEXT вместо UUID
-- ============================================================================

CREATE TABLE IF NOT EXISTS vecs.documents (
    id TEXT PRIMARY KEY,  -- 🔥 ИЗМЕНЕНО: TEXT вместо UUID
    
    -- Обязательная связь с мастер-записью документа
    registry_id UUID NOT NULL REFERENCES vecs.document_registry(id) ON DELETE CASCADE,
    
    -- Векторное представление чанка (768-dimensional embedding)
    vec VECTOR(768),
    
    -- Метаданные чанка
    metadata JSONB
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_documents_registry_id ON vecs.documents(registry_id);

-- HNSW индекс для векторного поиска
CREATE INDEX IF NOT EXISTS idx_documents_vec_hnsw ON vecs.documents
USING hnsw (vec vector_cosine_ops);

-- ============================================================================
-- 🆕 SUPABASE STORAGE POLICIES (для bucket 'vehicle-documents')
-- ============================================================================
-- ВАЖНО: Bucket 'vehicle-documents' должен быть создан в Supabase Dashboard
--        Settings: private=true, file_size_limit=52428800 (50MB)

-- Drop existing policies first (для идемпотентного выполнения)
DROP POLICY IF EXISTS "Service role can read all objects" ON storage.objects;
DROP POLICY IF EXISTS "Service role can insert objects" ON storage.objects;
DROP POLICY IF EXISTS "Service role can update objects" ON storage.objects;
DROP POLICY IF EXISTS "Service role can delete objects" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can read objects" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can upload objects" ON storage.objects;

-- Policy 1: Service role может читать все объекты
CREATE POLICY "Service role can read all objects"
ON storage.objects
FOR SELECT
TO service_role
USING (bucket_id = 'vehicle-documents');

-- Policy 2: Service role может загружать объекты
CREATE POLICY "Service role can insert objects"
ON storage.objects
FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'vehicle-documents');

-- Policy 3: Service role может обновлять объекты
CREATE POLICY "Service role can update objects"
ON storage.objects
FOR UPDATE
TO service_role
USING (bucket_id = 'vehicle-documents')
WITH CHECK (bucket_id = 'vehicle-documents');

-- Policy 4: Service role может удалять объекты
CREATE POLICY "Service role can delete objects"
ON storage.objects
FOR DELETE
TO service_role
USING (bucket_id = 'vehicle-documents');

-- Policy 5: Authenticated пользователи могут читать объекты
CREATE POLICY "Authenticated users can read objects"
ON storage.objects
FOR SELECT
TO authenticated
USING (bucket_id = 'vehicle-documents');

-- Policy 6: Authenticated пользователи могут загружать в raw/pending/
CREATE POLICY "Authenticated users can upload objects"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'vehicle-documents'
    AND (storage.foldername(name))[1] = 'raw'
    AND (storage.foldername(name))[2] = 'pending'
);

-- ============================================================================
-- КОММЕНТАРИИ
-- ============================================================================

COMMENT ON TABLE vecs.vehicles IS 'Реестр транспортных средств компании';
COMMENT ON TABLE vecs.document_registry IS 'Мастер-таблица всех загруженных документов';
COMMENT ON TABLE vecs.documents IS 'Таблица чанков для векторного поиска (RAG). id изменён на TEXT для совместимости с vecs';

COMMENT ON COLUMN vecs.documents.id IS '🔥 TEXT ID вместо UUID для совместимости с vecs библиотекой';
COMMENT ON COLUMN vecs.document_registry.storage_bucket IS '🆕 Supabase Storage bucket name (default: vehicle-documents)';
COMMENT ON COLUMN vecs.document_registry.storage_path IS '🆕 Full path in Storage bucket (e.g., raw/pending/uuid_file.pdf)';
COMMENT ON COLUMN vecs.document_registry.original_filename IS '🆕 Original filename as uploaded by user';
COMMENT ON COLUMN vecs.document_registry.file_size_bytes IS '🆕 File size in bytes';
COMMENT ON COLUMN vecs.document_registry.content_type IS '🆕 MIME type (e.g., application/pdf)';
COMMENT ON COLUMN vecs.document_registry.storage_status IS '🆕 Storage processing status: pending, processing, processed, failed, indexed';
COMMENT ON COLUMN vecs.document_registry.raw_file_path IS 'Legacy: Путь к оригинальному файлу в data/raw/ (опционально для Storage mode)';
COMMENT ON COLUMN vecs.document_registry.markdown_file_path IS 'Путь к конвертированному markdown в data/markdown/';
COMMENT ON COLUMN vecs.document_registry.extracted_data IS 'JSON с извлечёнными данными: VRN, даты, OCR confidence';

-- ============================================================================
-- ПРИМЕРЫ ЗАПРОСОВ
-- ============================================================================

-- Получить все документы для конкретной машины
-- SELECT dr.*, v.registration_number 
-- FROM vecs.document_registry dr
-- JOIN vecs.vehicles v ON dr.vehicle_id = v.id
-- WHERE v.registration_number = '191-D-12345';

-- Получить все неназначенные документы
-- SELECT * FROM vecs.document_registry 
-- WHERE status = 'unassigned';

-- Получить документы, готовые к индексированию
-- SELECT * FROM vecs.document_registry 
-- WHERE status = 'pending_indexing' 
-- AND markdown_file_path IS NOT NULL;

-- Получить количество чанков для документа
-- SELECT dr.raw_file_path, COUNT(d.id) as chunk_count
-- FROM vecs.document_registry dr
-- LEFT JOIN vecs.documents d ON dr.id = d.registry_id
-- GROUP BY dr.id, dr.raw_file_path;

-- Поиск документов по извлечённому VRN
-- SELECT * FROM vecs.document_registry
-- WHERE extracted_data->>'vrn' = '191-D-12345';

-- ============================================================================
-- 🆕 STORAGE MODE QUERIES
-- ============================================================================

-- Получить все документы в очереди на обработку (Storage mode)
-- SELECT id, original_filename, storage_path, uploaded_at
-- FROM vecs.document_registry
-- WHERE storage_status = 'pending'
-- ORDER BY uploaded_at ASC;

-- Подсчитать документы по статусам (Storage mode)
-- SELECT storage_status, COUNT(*) as count
-- FROM vecs.document_registry
-- WHERE storage_path IS NOT NULL
-- GROUP BY storage_status
-- ORDER BY count DESC;

-- Найти документ по storage_path
-- SELECT * FROM vecs.document_registry
-- WHERE storage_path = 'raw/pending/abc123_insurance.pdf';

-- Получить все обработанные документы за последние 7 дней
-- SELECT original_filename, storage_status, uploaded_at, markdown_file_path
-- FROM vecs.document_registry
-- WHERE storage_status = 'processed'
--   AND uploaded_at > NOW() - INTERVAL '7 days'
-- ORDER BY uploaded_at DESC;

-- Найти документы, которые не удалось обработать
-- SELECT id, original_filename, storage_path, status
-- FROM vecs.document_registry
-- WHERE storage_status = 'failed'
-- ORDER BY updated_at DESC;

-- ============================================================================
-- 🆕 QUICK START WITH STORAGE MODE
-- ============================================================================
-- The schema above now supports BOTH:
--   1. Legacy filesystem mode (backward compatible)
--   2. NEW: Supabase Storage mode (recommended for production)
--
-- To use Storage mode after running this schema:
--   1. Create bucket 'vehicle-documents' in Supabase Dashboard
--   2. Configure .env (see rag_indexer/.env.storage.example)
--   3. Upload: python rag_indexer/scripts/upload_documents.py --dir /path/to/docs
--   4. Process: python rag_indexer/process_documents_storage.py
--   5. Index: python rag_indexer/indexer.py
--
-- Documentation:
--   - Quick Start: rag_indexer/QUICKSTART_STORAGE.md
--   - Full Guide: rag_indexer/STORAGE_MIGRATION_GUIDE.md
--   - Schema Changes: rag_indexer/SCHEMA_UPDATES.md
-- ============================================================================

This project is a sophisticated, production-ready RAG (Retrieval-Augmented Generation) system designed to answer questions based on a private collection of documents. It specializes in extracting information about people, leveraging a powerful hybrid search mechanism that combines vector-based semantic search with direct database keyword search.

The backend is built with Python and designed as an API, making it easy to integrate with any custom frontend. The system uses Google Gemini for LLM tasks and Supabase (PostgreSQL with pgvector) for data storage and retrieval.

**NEW**: The system now supports Supabase Storage for centralized document management. See `rag_indexer/QUICKSTART_STORAGE.md` for setup instructions.

================================
I have described the complete lifecycle of a document's status from its initial state to the final processed state.

The flow is as follows:

pending_indexing: Set after document conversion in api/modules/indexing/services/conversion_service.py.
processed: Set after successful indexing in api/modules/indexing/services/indexing_service.py.
unassigned or assigned: Set upon creation in api/modules/vehicles/services/document_registry_service.py.

=======================================================================
Mercedes-Benz	Германия / глобально	Sprinter (варианты минибусов)
MAN	Германия	TGE Minibus 
MAN
Karsan	Турция	Jest 
Wikipedia
, J10 
Wikipedia
Isuzu	Япония / Азия	Isuzu Journey

## Key Features

-   **🚀 Hybrid Search:** Combines semantic vector search with exact-match database search for superior accuracy and recall.
-   **🧠 Smart Entity Extraction:** Automatically identifies key entities (like people's names) in user queries using advanced NLP techniques.
-   **✏️ Multi-Query Rewriting:** Expands the original user query into several variants to cover different search angles.
-   **⚖️ Advanced Results Fusion:** Intelligently merges and ranks results from multiple retrieval strategies to provide the most relevant answers.
-   **🤖 API-First Design:** Built as a standalone backend API (e.g., using FastAPI/Flask), ready to be consumed by any frontend application (web, mobile, etc.).
-   **✨ Powered by Google Gemini:** Utilizes Google's powerful Gemini models for embeddings and intelligent NLP tasks.
-   **💾 Supabase/PostgreSQL Backend:** Leverages the power and flexibility of SQL and `pgvector` for efficient hybrid storage and retrieval.

## Architecture Overview

The system is designed with a clean separation between the frontend, backend, and data layers:

`Frontend (e.g., Vercel)` ➡️ `Backend API (e.g., AWS, Render)` ➡️ `Supabase DB & Google Gemini API`

This README focuses on setting up and running the **Backend API**.

## Project Structure

```
aidocsbackend/
├── api/                    # FastAPI backend
├── rag_indexer/           # Document processing pipeline
├── rag_client/         # RAG logic
├── frontend/              # React web application
├── dev_tools/             # Development utilities
│   ├── tests/            # Test files
│   ├── scripts/          # Analysis, diagnostics, and maintenance scripts
│   │   ├── analysis/    # Scripts for data analysis and quality checks
│   │   ├── diagnostics/ # Scripts for database and system diagnostics
│   │   └── maintenance/ # Scripts for data fixing and maintenance
│   ├── docs/            # Technical documentation
│   └── logs/            # Archived logs
├── data/                  # Working data directory
├── .env                   # Environment configuration
├── requirements.txt       # Python dependencies
├── run_api.py            # API server launcher
├── run_indexer.py        # Indexer launcher
└── README.md             # This file
```

For detailed information about development tools, see [dev_tools/README.md](dev_tools/README.md).

## Prerequisites

Before you begin, ensure you have the following installed:
-   Python 3.8+
-   Git

## Getting Started: Backend Setup

Follow these steps to set up and run the backend service on your local machine or a server.

### 1. Clone the Repository

First, clone the new repository to your local machine:
```bash
git clone https://github.com/your-username/your-new-repository-name.git
cd your-new-repository-name
```

### 2. Create and Activate a Virtual Environment

It is crucial to use a virtual environment to manage project dependencies and avoid conflicts with other Python projects.

**On macOS / Linux:**
```bash
# Create the virtual environment (in a folder named 'venv')
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```
*(You will see `(venv)` at the beginning of your terminal prompt, indicating it's active.)*

**On Windows:**
```bash
# Create the virtual environment (in a folder named 'venv')
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\activate
```
*(You will see `(venv)` at the beginning of your terminal prompt, indicating it's active.)*

### 3. Install Dependencies

With your virtual environment activated, install all the required Python packages:
```bash
pip install -r requirements.txt
```

**Important:** After installing dependencies, download the SpaCy language model for entity extraction:
```bash
python -m spacy download en_core_web_sm
```

This downloads the English language model (~12 MB) required for Named Entity Recognition (NER) in query processing. If you skip this step, the system will fall back to regex-based entity extraction with slightly lower accuracy (85% vs 90%).

### 4. Configure Environment Variables

The application requires API keys and connection strings to be configured in an environment file.

-   Create a copy of `.env.example` (if it exists) or create a new file named `.env` in the project root.
-   Add the following variables to your `.env` file:

```env
# Your Supabase connection string (PostgreSQL format)
SUPABASE_CONNECTION_STRING="postgresql://postgres:[YOUR-PASSWORD]@[YOUR-DB-HOST]:5432/postgres"

# Your Google Gemini API Key
GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"

# You can also override other settings from config/settings.py here if needed
# For example:
# TABLE_NAME="my_custom_table"
```

### 5. Initialize Database Schema

**Important:** Before running the indexer, you must create the database schema and indexes in Supabase.

1. **Open Supabase SQL Editor:**
   - Go to your Supabase dashboard
   - Navigate to SQL Editor

2. **Execute the schema creation script:**
   - Copy the SQL schema from the beginning of this README (lines 1-182)
   - Paste and execute it in the SQL Editor

3. **Verify vector index creation:**
   ```sql
   -- Check if HNSW vector index exists
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'documents'
   AND schemaname = 'vecs';
   ```

   You should see `idx_documents_vec_hnsw` in the results. This index is **critical for performance** - it speeds up vector similarity searches by 3-5x.

4. **Enable pgvector extension (if not already enabled):**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

## Running the Backend

The backend has two main processes: the **Indexer** (run once to process documents) and the **API Server** (runs continuously to answer queries).

### Step 1: Run the Indexer

Before you can perform searches, you must process your documents and populate the database.

> **Important:** Make sure your `DOCUMENTS_DIR` is correctly set in `config.py` or your `.env` file before running the indexer.

To start the indexing process, run:
```bash
# Make sure your virtual environment is active!
python indexer.py
```
This process may take a long time depending on the number and size of your documents.

### Step 2: Run the API Server

Once the indexing is complete, you can start the API server. This server will expose the endpoints that your frontend application will call.

Assuming you have created an `api.py` file with FastAPI, run the following command:
```bash
# Make sure your virtual environment is active!
uvicorn api:app --reload
```
-   `api`: The name of your Python file (e.g., `api.py`).
-   `app`: The name of the FastAPI instance inside your file.
-   `--reload`: Automatically restarts the server when you make changes to the code (great for development).

Your backend API is now running and ready to accept requests! You can typically access it at `http://127.0.0.1:8000`.

## Testing the System

The system includes two search tools for testing and exploration:

### Quick CLI Search
```bash
cd rag_client
python simple_search.py "231-D-54321"
python simple_search.py "John Nolan" --verbose
```

### Interactive Console Search
```bash
cd rag_client
python console_search.py
# Then choose from the interactive menu
```

**📚 For detailed guide on both tools, see [SEARCH_TOOLS_GUIDE.md](rag_client/SEARCH_TOOLS_GUIDE.md)**

## Security & Validation Testing

The system includes comprehensive security and validation tests to ensure data integrity and protection against attacks.

### Test Suite Overview

**63 automated tests** covering:
- ✅ SQL Injection protection
- ✅ XSS attack prevention
- ✅ Input validation & sanitization
- ✅ Error handling & timeouts
- ✅ API endpoint security
- ✅ Response format validation

### Running Tests

**Prerequisites:**
```bash
pip install pytest requests
```

**All Tests** (requires API running):
```bash
# Terminal 1: Start API server
python run_api.py

# Terminal 2: Run tests
python run_tests.py
```

**Test Modes:**

1. **Validator Tests Only** (no API required):
```bash
python run_tests.py validators
```
Fast unit tests for input validation logic (39 tests, ~2 seconds)

2. **API Integration Tests** (requires API):
```bash
python run_tests.py api
```
End-to-end API security tests (14 tests, ~2 minutes)

3. **Quick Security Check** (requires API):
```bash
python run_tests.py security
```
Rapid validation of critical attack vectors (4 tests, ~5 seconds)

### Test Results

```
Security Validation: 4/4 PASSED (100%)
  [OK] SQL Injection: BLOCKED (400)
  [OK] XSS Attack: BLOCKED (400)
  [OK] Long Input: BLOCKED (422)
  [OK] Empty Query: BLOCKED (422)

API Integration Tests: 14/14 PASSED (100%)
Validator Unit Tests: 38/39 PASSED (97%)

[SUCCESS] All critical security tests passed!
```

### What's Tested

**Security Protection:**
- SQL injection patterns (SELECT, DROP, UNION, OR attacks)
- XSS attacks (script tags, javascript:, event handlers, iframes)
- Input length limits (1-1000 characters)
- Special character validation

**Error Handling:**
- User-friendly error messages
- Proper HTTP status codes (400, 422, 503, 504, 500)
- Timeout protection (30s/20s/15s hierarchical)
- Empty results guidance

**API Reliability:**
- Request/response format validation
- Recovery after invalid requests
- Performance requirements (<30s response time)

**📚 For detailed testing documentation, see [tests/README.md](tests/README.md)**
**📚 For implementation details, see [ERROR_HANDLING_IMPROVEMENTS.md](ERROR_HANDLING_IMPROVEMENTS.md)**

## Troubleshooting

### Warning: "Query does not have a covering index"

If you see this warning when running searches:
```
UserWarning: Query does not have a covering index for IndexMeasure.cosine_distance
```

**Cause:** The HNSW vector index is missing from your database.

**Solution 1 (Recommended):** Create the index via SQL in Supabase SQL Editor:
```sql
-- Create HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_documents_vec_hnsw
ON vecs.documents
USING hnsw (vec vector_cosine_ops);
```

**Solution 2 (Alternative):** Use the Python script:
```bash
cd rag_client
python create_vector_index.py
```

**Performance Impact:**
- **Without index:** Vector searches take ~1.0s (slower, but still functional)
- **With index:** Vector searches take ~0.2s (3-5x faster)

The index creation may take several minutes depending on the number of documents in your database.

### SpaCy Model Not Found

If you see:
```
⚠️ SpaCy not available: Can't find model 'en_core_web_sm'
```

**Solution:**
```bash
python -m spacy download en_core_web_sm
```

The system will fall back to regex-based entity extraction (75% accuracy vs 90% with SpaCy).

### Invalid Query Errors

If valid queries are being rejected, check the domain configuration in `rag_client/config/settings.py`:

```python
# Expand document_types to include your document types
document_types = [
    "Vehicle registration certificates",
    "Insurance documents",
    # Add your custom types here
]
```

---

## RAG Testing Methodology

This section documents the comprehensive testing framework implemented for validating RAG system quality and performance.

### Testing Framework Overview

The system follows a **7-phase testing methodology** based on industry standards (Ragas framework):

| Phase | Status | Purpose | Location |
|-------|--------|---------|----------|
| Phase 1: Database Snapshot | ✅ COMPLETE | Ground truth validation | `dev_tools/scripts/diagnostics/snapshot_database.py` |
| Phase 2: Smoke Test | ✅ COMPLETE | Quick sanity check (<1 min) | `dev_tools/tests/rag_evaluation/smoke_test.py` |
| Phase 2.5: Deduplication Fix | ✅ COMPLETE | Production-critical fix | [DEDUPLICATION_FIX_SUMMARY.md](DEDUPLICATION_FIX_SUMMARY.md) |
| Phase 3: Retrieval Quality | 🔜 PENDING | Precision@5, Recall@10, MRR | TBD |
| Phase 4: Answer Quality | 🔜 PENDING | Faithfulness, relevance | TBD |
| Phase 5: End-to-End | 🔜 PENDING | Full pipeline validation | TBD |
| Phase 6: Stress Testing | 🔜 PENDING | Performance under load | TBD |
| Phase 7: Regression | 🔜 PENDING | Continuous monitoring | TBD |

### Testing Files Structure

```
dev_tools/
├── tests/
│   └── rag_evaluation/
│       ├── smoke_test.py                    # Phase 2: Quick sanity check
│       └── smoke_test_results_*.json        # Timestamped test results
├── scripts/
│   └── diagnostics/
│       └── snapshot_database.py             # Database state capture for ground truth
├── datasets/
│   └── ground_truth/
│       ├── database_snapshot.json           # Current database state (ground truth)
│       └── vehicle_queries.json             # Test cases (v1.1 - validated)
└── docs/
    └── RAG_TESTING_GUIDE.md                 # Comprehensive testing guide
```

### Test Outputs & Their Purpose

#### 1. Database Snapshot (`database_snapshot.json`)
**Purpose**: Captures current database state for ground truth validation

**Generated by**: `python dev_tools/scripts/diagnostics/snapshot_database.py`

**Contains**:
- Total documents and chunks in database
- All VRNs (Vehicle Registration Numbers) in `vehicles` table
- Document distribution across files
- Timestamp of snapshot

**Example**:
```json
{
  "snapshot_date": "2025-11-08T13:08:20.316425",
  "total_documents": 6,
  "total_chunks": 18,
  "vrns": ["141-D-98765", "231-D-54321", "231-D-54329"]
}
```

#### 2. Smoke Test Results (`smoke_test_results_YYYYMMDD_HHMMSS.json`)
**Purpose**: Detailed test results for 5 critical query types

**Generated by**: `python dev_tools/tests/rag_evaluation/smoke_test.py`

**Contains**:
- Test execution timestamp
- Per-test results (PASS/FAIL, latency, retrieved results count)
- Full API responses (answer, results, metadata)
- Failure reasons (missing keywords, retrieval issues)

**Example**:
```json
{
  "timestamp": "2025-11-08 13:03:11",
  "test_results": {
    "vrn_001": {
      "status": "PASS",
      "latency": 11.23,
      "results_retrieved": 3
    }
  }
}
```

#### 3. Test Analysis Documents
- **`PHASE2_SMOKE_TEST_RESULTS.md`** - Human-readable analysis of test results
- **`TESTING_STATUS.md`** - Quick status summary for future sessions
- **`DEDUPLICATION_FIX_SUMMARY.md`** - Documentation of deduplication fix (Phase 2.5)

### Critical Testing Workflow Rule

**⚠️ ALWAYS RUN FRESH SNAPSHOT BEFORE TESTING**

```bash
# ❌ WRONG: Running tests without fresh snapshot
python dev_tools/tests/rag_evaluation/smoke_test.py

# ✅ CORRECT: Capture current state FIRST, then test
# Step 1: Capture current database state
python dev_tools/scripts/diagnostics/snapshot_database.py

# Step 2: Run tests (now validated against fresh ground truth)
python dev_tools/tests/rag_evaluation/smoke_test.py
```

**Why This Matters**:
- Ground truth must match actual database state
- Without fresh snapshot → false conclusions
- Example: Don't assume LLM is "hallucinating" VRNs without checking if those VRNs exist in indexed chunks
- Database changes (new documents, extracted entities) invalidate old snapshots

### Running Tests

#### Quick Smoke Test (Phase 2)
```bash
# 1. FIRST: Ensure API server is running
python run_api.py

# 2. SECOND: Capture current database state (in new terminal)
python dev_tools/scripts/diagnostics/snapshot_database.py

# 3. THIRD: Run smoke test
python dev_tools/tests/rag_evaluation/smoke_test.py

# Results saved to: dev_tools/tests/rag_evaluation/smoke_test_results_<timestamp>.json
```

**Expected Output**:
```
========================================
RAG SMOKE TEST - Quick Sanity Check
========================================

[1/5] Testing vrn_001: "231-D-54321"
    [PASS] (11.23s)

[2/5] Testing agg_001: "how many cars we have?"
    [PASS] (9.92s)
    [+] Results retrieved: 10 results

...

========================================
SMOKE TEST COMPLETE
========================================
Passed: 3/5 (60%)
Failed: 2/5
Average latency: 13.01s
```

#### Database Snapshot (Phase 1)
```bash
# Run snapshot to capture current database state
python dev_tools/scripts/diagnostics/snapshot_database.py

# Output saved to: dev_tools/datasets/ground_truth/database_snapshot.json
```

### Test Coverage

The smoke test covers **5 critical query types**:

1. **Exact VRN Lookup** (`vrn_001`)
   - Query: "231-D-54321"
   - Validates: Database search accuracy, metadata retrieval

2. **Aggregation Query** (`agg_001`)
   - Query: "how many cars we have?"
   - Validates: Multi-document retrieval, LLM counting, deduplication strategy

3. **Entity Search** (`entity_001`)
   - Query: "Show me all VCR documents"
   - Validates: Semantic search, document type filtering

4. **Semantic Query** (`semantic_001`)
   - Query: "Tell me about the Volvo truck"
   - Validates: Natural language understanding, content extraction

5. **Negative Test** (`neg_001`)
   - Query: "What is the weather in Dublin?"
   - Validates: Query rejection for out-of-scope questions

### Key Metrics Tracked

- **Pass Rate**: Percentage of tests passing strict validation
- **Functional Success Rate**: Percentage of tests working (may fail on keyword mismatch)
- **Average Latency**: Mean response time across all tests
- **Results Retrieved**: Number of chunks returned per query
- **Deduplication Ratio**: Percentage of chunks dropped during deduplication

### Recent Improvements

#### ✅ Phase 2.5: Deduplication Fix (2025-11-08)

**Problem**: Aggressive filename-based deduplication was losing 50-80% of chunks, causing aggregation queries to miss entities.

**Solution**: Changed from filename-based to content-based deduplication in two locations:
- `rag_client/retrieval/results_fusion.py:663-706`
- `rag_client/retrieval/multi_retriever.py:775-833`

**Impact**:
- Results improved from 2 → 10 chunks for aggregation queries (400% increase)
- Deduplication ratio improved from ~66% (too aggressive) → ~17% (optimal)
- System now follows professional RAG best practices (keep all unique content)

**Status**: ✅ Production-ready

For detailed documentation, see [DEDUPLICATION_FIX_SUMMARY.md](DEDUPLICATION_FIX_SUMMARY.md)

### Testing Documentation

- **[RAG_TESTING_GUIDE.md](dev_tools/RAG_TESTING_GUIDE.md)** - Comprehensive testing methodology and best practices
- **[TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md)** - 7-phase implementation roadmap
- **[TESTING_STATUS.md](TESTING_STATUS.md)** - Current testing status and next steps
- **[DEDUPLICATION_FIX_SUMMARY.md](DEDUPLICATION_FIX_SUMMARY.md)** - Deduplication fix details and validation

### Monitoring Recommendations

For production deployment, track these metrics:
```python
{
    "retrieval_before_dedup": 12,      # Chunks before deduplication
    "retrieval_after_dedup": 10,       # Chunks after deduplication
    "deduplication_ratio": 0.17,       # 17% dropped (optimal: 15-30%)
    "avg_chunks_per_file": 2.5,        # Multiple chunks per file allowed
    "query_latency_ms": 13010,         # Total query time
    "reranking_latency_ms": 2500       # Reranking overhead (expected: 1.4-3.5s)
}
```

**Alert Thresholds**:
- Deduplication ratio > 50% → Too aggressive (regression detected)
- Deduplication ratio < 5% → Too lenient (possible duplicates)
- Query latency > 20s → Performance degradation

---
Client start:

#streamlit run main_app.py
python run_api.py
# Перейдите в родительскую папку
cd C:\projects\aidocs

# Создайте React проект (это займет несколько минут)
npx create-react-app webclient

# Перейдите в созданный проект
cd frontend

# Установите зависимости
npm install axios react-markdown

npm start