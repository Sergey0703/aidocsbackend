# Deployment Checklist - Supabase Storage Mode

Используйте этот чеклист для развертывания Storage Mode после очистки базы данных.

## ✅ Pre-Deployment Checklist

### 1. Supabase Setup

- [ ] **Supabase проект создан**
  - [ ] Получен `SUPABASE_URL` (https://your-project.supabase.co)
  - [ ] Получен `SUPABASE_SERVICE_ROLE_KEY` (Settings → API)
  - [ ] Получен `SUPABASE_CONNECTION_STRING` (Settings → Database)

- [ ] **Storage bucket создан**
  - [ ] **Option A (Automatic)**: Run `python scripts/setup_storage.py` ✅
  - [ ] **Option B (Manual)**:
    - [ ] Bucket name: `vehicle-documents`
    - [ ] Privacy: Private ✓
    - [ ] File size limit: 50 MB (or custom)
  - [ ] Bucket visible в Storage dashboard

### 2. Database Setup

- [ ] **Очистка старой схемы (если нужно)**
  ```sql
  -- ВНИМАНИЕ: Это удалит ВСЕ данные!
  DROP SCHEMA IF EXISTS vecs CASCADE;
  CREATE SCHEMA vecs;
  ```

- [ ] **Запуск нового SQL скрипта**
  - [ ] Открыть [README.md](../README.md)
  - [ ] Скопировать весь SQL скрипт (строки 1-220+)
  - [ ] Вставить в Supabase SQL Editor
  - [ ] Запустить (Run)
  - [ ] Проверить: "Success. No rows returned"

- [ ] **Проверка таблиц**
  ```sql
  -- Должны вернуть данные:
  SELECT * FROM vecs.vehicles LIMIT 1;
  SELECT * FROM vecs.document_registry LIMIT 1;
  SELECT * FROM vecs.documents LIMIT 1;
  ```

- [ ] **Проверка Storage полей**
  ```sql
  -- Должны вернуть 6 строк:
  SELECT column_name FROM information_schema.columns
  WHERE table_name = 'document_registry'
    AND column_name IN ('storage_bucket', 'storage_path',
                        'storage_status', 'original_filename',
                        'file_size_bytes', 'content_type');
  ```

- [ ] **Проверка Storage policies**
  ```sql
  -- Должны вернуть 6 политик:
  SELECT COUNT(*) FROM pg_policies
  WHERE tablename = 'objects'
    AND schemaname = 'storage';
  ```

### 3. Python Environment

- [ ] **Зависимости установлены**
  ```bash
  pip install supabase  # Новая зависимость
  pip install -r requirements.txt  # Все остальные
  ```

- [ ] **Environment файл настроен**
  ```bash
  # В rag_indexer/
  cp .env.storage.example .env
  ```

- [ ] **Обязательные переменные заполнены**
  ```bash
  # Проверить в .env:
  SUPABASE_URL=https://...
  SUPABASE_SERVICE_ROLE_KEY=eyJ...
  SUPABASE_CONNECTION_STRING=postgresql://...
  GEMINI_API_KEY=AIza...
  ```

- [ ] **Опциональные переменные проверены**
  ```bash
  SUPABASE_STORAGE_BUCKET=vehicle-documents  ✓
  STORAGE_TEMP_DIR=/tmp/rag_storage_temp     ✓
  MARKDOWN_OUTPUT_DIR=./markdown_output      ✓
  ```

### 4. Testing

- [ ] **Модули импортируются без ошибок**
  ```bash
  python -c "from storage.storage_manager import SupabaseStorageManager; print('OK')"
  python -c "from chunking_vectors.registry_manager import DocumentRegistryManager; print('OK')"
  ```

- [ ] **Storage Manager инициализируется**
  ```bash
  python -c "
  from storage.storage_manager import SupabaseStorageManager
  sm = SupabaseStorageManager()
  print(f'Bucket: {sm.bucket_name}')
  "
  # Должно вывести: Bucket: vehicle-documents
  ```

- [ ] **Тест workflow выполнен**
  ```bash
  cd rag_indexer
  python scripts/test_storage_workflow.py /path/to/test.pdf
  # Должно вывести: TEST COMPLETED SUCCESSFULLY
  ```

## ✅ Deployment Steps

### Step 1: Upload Test Batch

- [ ] **Загрузить 3-5 тестовых документов**
  ```bash
  python scripts/upload_documents.py --dir /path/to/test/docs
  ```

- [ ] **Проверить в БД**
  ```sql
  SELECT id, original_filename, storage_status, uploaded_at
  FROM vecs.document_registry
  WHERE storage_status = 'pending'
  ORDER BY uploaded_at DESC
  LIMIT 5;
  ```

- [ ] **Проверить в Storage dashboard**
  - Storage → vehicle-documents → raw/pending/
  - Должны видеть загруженные файлы

### Step 2: Process Test Batch

- [ ] **Запустить обработку**
  ```bash
  python process_documents_storage.py --limit 5
  ```

- [ ] **Проверить результаты**
  ```sql
  SELECT storage_status, COUNT(*)
  FROM vecs.document_registry
  GROUP BY storage_status;

  -- Ожидаемый результат:
  -- processed: 5 (или меньше если были ошибки)
  -- failed: 0 (или кол-во неудачных)
  ```

- [ ] **Проверить markdown файлы созданы**
  ```bash
  ls -lh markdown_output/
  # Должны видеть .md файлы
  ```

- [ ] **Проверить файлы перемещены в Storage**
  - Storage → vehicle-documents → raw/processed/2025/01/
  - Должны видеть обработанные файлы

### Step 3: Index Test Batch

- [ ] **Запустить индексацию**
  ```bash
  cd ..  # Выйти из rag_indexer/
  python rag_indexer/indexer.py
  ```

- [ ] **Проверить embeddings созданы**
  ```sql
  SELECT COUNT(*) FROM vecs.documents;
  -- Должно быть > 0

  SELECT registry_id, COUNT(*) as chunks
  FROM vecs.documents
  GROUP BY registry_id;
  -- Каждый документ должен иметь несколько chunks
  ```

- [ ] **Проверить статус обновлен**
  ```sql
  SELECT status, storage_status, COUNT(*)
  FROM vecs.document_registry
  GROUP BY status, storage_status;
  ```

### Step 4: Test Search

- [ ] **Запустить quick search**
  ```bash
  cd streamlit-rag
  python scripts/quick_search.py
  # Изменить query в скрипте и запустить
  ```

- [ ] **Проверить результаты возвращаются**
  - Должны видеть chunks из загруженных документов
  - Similarity scores > 0.5

- [ ] **Запустить API (если нужно)**
  ```bash
  cd ..
  python run_api.py
  # API доступен на http://localhost:8000
  ```

- [ ] **Тестовый search через API**
  ```bash
  curl -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test query", "top_k": 5}'
  ```

### Step 5: Production Upload

- [ ] **Загрузить все документы**
  ```bash
  python scripts/upload_documents.py --dir /path/to/all/documents
  # Или по батчам:
  python scripts/upload_documents.py --dir /path/to/batch1
  python scripts/upload_documents.py --dir /path/to/batch2
  ```

- [ ] **Проверить количество**
  ```sql
  SELECT COUNT(*) FROM vecs.document_registry WHERE storage_status = 'pending';
  ```

- [ ] **Обработать все документы**
  ```bash
  python process_documents_storage.py
  # Может занять несколько часов для больших объемов
  ```

- [ ] **Мониторить прогресс**
  ```sql
  -- Выполнять каждые 5-10 минут:
  SELECT storage_status, COUNT(*)
  FROM vecs.document_registry
  GROUP BY storage_status;
  ```

- [ ] **Индексировать все документы**
  ```bash
  cd ..
  python rag_indexer/indexer.py
  ```

## ✅ Post-Deployment Verification

### Verify Counts

- [ ] **Все документы обработаны**
  ```sql
  SELECT
    COUNT(*) FILTER (WHERE storage_status = 'processed') as processed,
    COUNT(*) FILTER (WHERE storage_status = 'failed') as failed,
    COUNT(*) FILTER (WHERE storage_status = 'pending') as pending
  FROM vecs.document_registry;
  ```

- [ ] **Embeddings созданы для всех**
  ```sql
  SELECT
    dr.storage_status,
    COUNT(DISTINCT dr.id) as docs,
    COUNT(d.id) as chunks
  FROM vecs.document_registry dr
  LEFT JOIN vecs.documents d ON dr.id = d.registry_id
  GROUP BY dr.storage_status;
  ```

### Verify Storage

- [ ] **Проверить Storage usage**
  - Supabase Dashboard → Storage → vehicle-documents
  - Проверить размер: raw/pending/ (должно быть пусто)
  - Проверить размер: raw/processed/ (должны быть все файлы)
  - Проверить размер: raw/failed/ (проверить причины)

### Verify Search Quality

- [ ] **Тестовые queries работают**
  - Поиск по имени: "John Doe"
  - Поиск по VRN: "191-D-12345"
  - Поиск по дате: "expiry date"
  - Semantic search: "insurance documents"

- [ ] **Результаты релевантны**
  - Top-3 результата должны быть правильными
  - Similarity scores > 0.6 для прямых вопросов

## ✅ Monitoring Setup

### Daily Checks

- [ ] **Создать monitoring query**
  ```sql
  -- Сохранить как view:
  CREATE OR REPLACE VIEW vecs.storage_status_summary AS
  SELECT
    storage_status,
    COUNT(*) as count,
    SUM(file_size_bytes) / 1024 / 1024 as total_mb,
    MIN(uploaded_at) as oldest,
    MAX(uploaded_at) as newest
  FROM vecs.document_registry
  WHERE storage_path IS NOT NULL
  GROUP BY storage_status;
  ```

- [ ] **Проверять ежедневно**
  ```sql
  SELECT * FROM vecs.storage_status_summary;
  ```

### Alerts (Optional)

- [ ] **Настроить алерты для**:
  - Pending documents > 100 (очередь растет)
  - Failed documents > 10 (проблемы с conversion)
  - Storage usage > 80% (нужно больше места)

## ✅ Documentation

- [ ] **Команда обучена**
  - Показать workflow: upload → process → index
  - Показать как проверять статусы в БД
  - Показать Storage dashboard

- [ ] **Документация обновлена**
  - README.md актуален
  - .env.example актуален
  - Процедуры backup/restore задокументированы

## ✅ Backup & Recovery

- [ ] **Backup процедура настроена**
  ```bash
  # Database backup (автоматически в Supabase)
  # Storage backup (автоматически в Supabase)
  ```

- [ ] **Recovery процедура протестирована**
  - Restore database from backup
  - Verify Storage files accessible
  - Re-run indexing if needed

## 🎯 Success Criteria

Deployment считается успешным если:

- [x] Все тесты пройдены
- [x] Storage policies работают
- [x] Документы успешно обрабатываются
- [x] Embeddings создаются
- [x] Search возвращает релевантные результаты
- [x] Мониторинг настроен
- [x] Команда обучена

## 🐛 Rollback Plan

Если что-то пошло не так:

1. **Stop processing**
   ```bash
   # Ctrl+C в process_documents_storage.py
   ```

2. **Check logs**
   ```bash
   # Проверить failed_conversions/ для ошибок
   ls -lh failed_conversions/
   ```

3. **Fix issues**
   - Database connection problems → check .env
   - Storage upload fails → check policies
   - Conversion fails → check Docling setup

4. **Reset pending documents**
   ```sql
   UPDATE vecs.document_registry
   SET storage_status = 'pending'
   WHERE storage_status = 'processing';
   ```

5. **Retry**
   ```bash
   python process_documents_storage.py
   ```

---

**Last Updated**: 2025-01-23
**Version**: 1.0.0

Удачи с развертыванием! 🚀
