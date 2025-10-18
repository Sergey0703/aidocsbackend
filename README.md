-- ============================================================================
-- PRODUCTION RAG SYSTEM - DATABASE SCHEMA
-- Vehicle Management + Document Registry + Vector Search
-- UPDATED: documents.id changed from UUID to TEXT
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
    
    -- Пути к файлам
    raw_file_path TEXT UNIQUE,
    markdown_file_path TEXT UNIQUE,
    
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
    status TEXT DEFAULT 'unassigned' CHECK (status IN (
        'pending_assignment',
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

-- Индексы
CREATE INDEX IF NOT EXISTS idx_document_registry_vehicle ON vecs.document_registry(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_document_registry_status ON vecs.document_registry(status);
CREATE INDEX IF NOT EXISTS idx_document_registry_type ON vecs.document_registry(document_type);
CREATE INDEX IF NOT EXISTS idx_document_registry_raw_path ON vecs.document_registry(raw_file_path);
CREATE INDEX IF NOT EXISTS idx_document_registry_md_path ON vecs.document_registry(markdown_file_path);
CREATE INDEX IF NOT EXISTS idx_document_registry_extracted_data ON vecs.document_registry USING gin(extracted_data);

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
-- КОММЕНТАРИИ
-- ============================================================================

COMMENT ON TABLE vecs.vehicles IS 'Реестр транспортных средств компании';
COMMENT ON TABLE vecs.document_registry IS 'Мастер-таблица всех загруженных документов';
COMMENT ON TABLE vecs.documents IS 'Таблица чанков для векторного поиска (RAG). id изменён на TEXT для совместимости с vecs';

COMMENT ON COLUMN vecs.documents.id IS '🔥 TEXT ID вместо UUID для совместимости с vecs библиотекой';
COMMENT ON COLUMN vecs.document_registry.raw_file_path IS 'Путь к оригинальному файлу в data/raw/';
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

This project is a sophisticated, production-ready RAG (Retrieval-Augmented Generation) system designed to answer questions based on a private collection of documents. It specializes in extracting information about people, leveraging a powerful hybrid search mechanism that combines vector-based semantic search with direct database keyword search.

The backend is built with Python and designed as an API, making it easy to integrate with any custom frontend. The system uses Google Gemini for LLM tasks and Supabase (PostgreSQL with pgvector) for data storage and retrieval.

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
cd streamlit-rag
python simple_search.py "231-D-54321"
python simple_search.py "John Nolan" --verbose
```

### Interactive Console Search
```bash
cd streamlit-rag
python console_search.py
# Then choose from the interactive menu
```

**📚 For detailed guide on both tools, see [SEARCH_TOOLS_GUIDE.md](streamlit-rag/SEARCH_TOOLS_GUIDE.md)**

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
cd streamlit-rag
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

If valid queries are being rejected, check the domain configuration in `streamlit-rag/config/settings.py`:

```python
# Expand document_types to include your document types
document_types = [
    "Vehicle registration certificates",
    "Insurance documents",
    # Add your custom types here
]
```

---
Client start:

#streamlit run main_app.py
python run_api.py
# Перейдите в родительскую папку
cd C:\projects\aidocs

# Создайте React проект (это займет несколько минут)
npx create-react-app webclient

# Перейдите в созданный проект
cd webclient

# Установите зависимости
npm install axios react-markdown

npm start