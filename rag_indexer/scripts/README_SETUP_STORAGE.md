# setup_storage.py - Automatic Storage Setup

Автоматически создает и настраивает Supabase Storage bucket для RAG системы.

## Что делает скрипт

1. ✅ Проверяет подключение к Supabase
2. ✅ Создает bucket `vehicle-documents` (если не существует)
3. ✅ Настраивает параметры bucket:
   - Private (не публичный)
   - File size limit: 50 MB
   - Allowed MIME types: PDF, DOCX, PPTX
4. ✅ Создает структуру папок:
   - `raw/pending/`
   - `raw/processed/`
   - `raw/failed/`
5. ✅ Проверяет что всё работает:
   - Bucket exists
   - Can list files
   - Can upload/download/delete

## Использование

### Базовый запуск

```bash
# Убедитесь что .env настроен
python scripts/setup_storage.py

# Output:
# ============================================================
# SUPABASE STORAGE SETUP
# ============================================================
# [*] Connecting to Supabase...
# [+] Connected successfully
# [*] Creating bucket 'vehicle-documents'...
# [+] Bucket created successfully
# [*] Creating folder structure...
#     [+] Created: raw/pending/
#     [+] Created: raw/processed/
#     [+] Created: raw/failed/
# [*] Verifying Storage setup...
#     [✓] Bucket 'vehicle-documents' exists
#     [✓] Can list files in bucket
#     [✓] Folder structure exists
#     [✓] Upload/download/delete works
# [*] Verification Summary:
#     Checks passed: 4/4
#     [+] All checks passed! ✓
# ============================================================
# SETUP COMPLETE ✓
# ============================================================
```

### Опции

#### Только проверка (без создания)

```bash
python scripts/setup_storage.py --verify-only

# Проверяет существующую настройку без изменений
```

#### Кастомное имя bucket

```bash
python scripts/setup_storage.py --bucket-name my-custom-bucket

# По умолчанию: 'vehicle-documents'
```

#### Dry run (посмотреть что будет сделано)

```bash
python scripts/setup_storage.py --dry-run

# Output:
# ============================================================
# DRY RUN MODE
# ============================================================
# Would perform the following:
#   1. Connect to: https://your-project.supabase.co
#   2. Create bucket: 'vehicle-documents'
#   3. Settings:
#      - Public: No (private)
#      - File size limit: 50 MB
#      - Allowed types: PDF, DOCX, PPTX
#   4. Create folders:
#      - raw/pending/
#      - raw/processed/
#      - raw/failed/
#   5. Verify setup
```

## Требования

### Environment Variables

Должны быть установлены в `.env`:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Optional:
SUPABASE_STORAGE_BUCKET=vehicle-documents  # Default
```

### Python Dependencies

```bash
pip install supabase python-dotenv
```

## Проверки (Verification)

Скрипт выполняет 4 проверки:

1. **Bucket exists**: Bucket создан и виден
2. **Can list files**: Права на чтение работают
3. **Folder structure exists**: Папки созданы
4. **Upload/download/delete works**: Полный цикл работает

Если все 4 проверки пройдены → Setup успешен ✓

## Troubleshooting

### Error: "SUPABASE_URL not set"

**Решение:**
```bash
# Создайте .env файл
cp .env.storage.example .env

# Отредактируйте и добавьте:
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### Error: "Connection failed"

**Возможные причины:**
- Неверный URL или ключ
- Нет интернет соединения
- Проект Supabase не активен

**Решение:**
```bash
# Проверьте URL и ключ в Supabase Dashboard
# Settings → API
```

### Error: "Failed to create bucket"

**Если bucket уже существует:**
- Это нормально! Скрипт продолжит работу
- Output: "Bucket 'vehicle-documents' already exists (not an error)"

**Если реальная ошибка:**
- Проверьте permissions для service role key
- Убедитесь что Storage включен в проекте

### Warning: "Could not create folder"

**Не критично!** Папки создаются автоматически при первой загрузке файлов.

Скрипт пытается создать структуру заранее, но это опционально.

## Exit Codes

- `0` - Success (всё ОК)
- `1` - Error (что-то не получилось)

Используется в CI/CD скриптах:

```bash
#!/bin/bash
python scripts/setup_storage.py
if [ $? -eq 0 ]; then
    echo "Storage setup OK"
    # Continue with deployment
else
    echo "Storage setup FAILED"
    exit 1
fi
```

## Что делать после setup

```bash
# 1. Запустить SQL schema
# Copy entire SQL from ../README.md to Supabase SQL Editor

# 2. Загрузить тестовый документ
python scripts/upload_documents.py --file test.pdf

# 3. Обработать
python process_documents_storage.py --limit 1

# 4. Проверить
python scripts/test_storage_workflow.py test.pdf
```

## Integration with CI/CD

```yaml
# .github/workflows/deploy.yml
- name: Setup Supabase Storage
  run: |
    cd rag_indexer
    python scripts/setup_storage.py
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

## API

Можно использовать программно:

```python
from scripts.setup_storage import StorageSetup

setup = StorageSetup(
    supabase_url='https://...',
    supabase_key='eyJ...',
    bucket_name='vehicle-documents'
)

# Connect
if setup.connect():
    # Create bucket
    setup.create_bucket()

    # Create folders
    setup.create_folder_structure()

    # Verify
    if setup.verify_setup():
        print("All good!")
```

## Related Scripts

- `upload_documents.py` - Upload files to Storage
- `process_documents_storage.py` - Process uploaded files
- `test_storage_workflow.py` - End-to-end test

## Help

```bash
python scripts/setup_storage.py --help

# Shows all options and examples
```

---

**Рекомендация**: Запускайте этот скрипт **ОДИН РАЗ** при первоначальной настройке.

Повторный запуск безопасен (idempotent) - он просто проверит что всё на месте.
