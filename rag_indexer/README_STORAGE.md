# Supabase Storage Integration - Documentation Index

> **TL;DR**: Система теперь поддерживает хранение документов в Supabase Storage вместо локальной файловой системы. Это обеспечивает централизованное хранение, автоматические бэкапы и поддержку масштабирования.

---

## 🚀 Quick Links

| Если вы хотите... | Читайте это |
|-------------------|-------------|
| **Быстро начать работу (5 минут)** | [QUICKSTART_STORAGE.md](QUICKSTART_STORAGE.md) |
| **Понять архитектуру и детали** | [STORAGE_MIGRATION_GUIDE.md](STORAGE_MIGRATION_GUIDE.md) |
| **Развернуть в production** | [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) |
| **Узнать что изменилось в БД** | [SCHEMA_UPDATES.md](SCHEMA_UPDATES.md) |
| **Увидеть полный summary** | [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) |
| **Настроить environment** | [.env.storage.example](.env.storage.example) |
| **Посмотреть SQL схему** | [../README.md](../README.md) (строки 1-320) |

---

## 📚 Документация

### Для начинающих

1. **[QUICKSTART_STORAGE.md](QUICKSTART_STORAGE.md)** ⭐ START HERE
   - 5-минутная настройка
   - Простой workflow
   - Основные команды
   - Troubleshooting

### Для разработчиков

2. **[STORAGE_MIGRATION_GUIDE.md](STORAGE_MIGRATION_GUIDE.md)**
   - Полное руководство (2500+ слов)
   - Детальная архитектура
   - Все сценарии использования
   - Edge cases
   - API integration примеры
   - Performance tuning

3. **[SCHEMA_UPDATES.md](SCHEMA_UPDATES.md)**
   - Изменения в database schema
   - Новые поля и индексы
   - Backward compatibility
   - Migration options
   - Rollback инструкции

### Для DevOps

4. **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)**
   - Пошаговый чеклист развертывания
   - Pre-deployment checks
   - Testing procedures
   - Monitoring setup
   - Rollback plan

5. **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**
   - Обзор реализации
   - Все созданные файлы
   - Workflow сравнение
   - Quick reference

---

## 🗂️ Структура файлов

```
rag_indexer/
│
├── 📖 Documentation (you are here)
│   ├── README_STORAGE.md              ← Этот файл (index)
│   ├── QUICKSTART_STORAGE.md          ← Quick start (5 min)
│   ├── STORAGE_MIGRATION_GUIDE.md     ← Full guide
│   ├── DEPLOYMENT_CHECKLIST.md        ← Production deploy
│   ├── SCHEMA_UPDATES.md              ← DB changes
│   ├── IMPLEMENTATION_SUMMARY.md      ← Overview
│   └── .env.storage.example           ← Config template
│
├── 🔧 Core Modules
│   ├── storage/
│   │   ├── __init__.py
│   │   └── storage_manager.py         ← Upload/download/move
│   │
│   ├── chunking_vectors/
│   │   └── registry_manager.py        ← Updated with Storage methods
│   │
│   └── docling_processor/
│       ├── document_scanner.py        ← Updated with scan_storage()
│       └── document_converter.py      ← Updated with convert_from_storage()
│
├── 📜 Scripts
│   ├── process_documents_storage.py   ← Main processing script
│   └── scripts/
│       ├── upload_documents.py        ← Upload CLI tool
│       └── test_storage_workflow.py   ← End-to-end test
│
├── 🗄️ Database
│   └── ../README.md                   ← Complete SQL schema (single file)
│
└── 📋 Legacy (still works)
    ├── process_documents.py           ← Filesystem mode
    ├── indexer.py                     ← Unchanged
    └── pipeline.py                    ← Unchanged
```

---

## 🎯 Recommended Reading Order

### Scenario 1: Новый пользователь (чистая установка)

```
1. QUICKSTART_STORAGE.md (5 min)
   ↓
2. Run setup commands
   ↓
3. Test with test_storage_workflow.py
   ↓
4. [Optional] Read STORAGE_MIGRATION_GUIDE.md for details
```

### Scenario 2: Production deployment

```
1. QUICKSTART_STORAGE.md (понять workflow)
   ↓
2. SCHEMA_UPDATES.md (понять DB changes)
   ↓
3. DEPLOYMENT_CHECKLIST.md (follow step-by-step)
   ↓
4. STORAGE_MIGRATION_GUIDE.md (reference при проблемах)
```

### Scenario 3: Разработчик (нужно понять код)

```
1. IMPLEMENTATION_SUMMARY.md (overview)
   ↓
2. SCHEMA_UPDATES.md (DB structure)
   ↓
3. Read source code:
   - storage/storage_manager.py
   - registry_manager.py (new methods)
   - document_converter.py (Storage workflow)
   ↓
4. STORAGE_MIGRATION_GUIDE.md (deep dive)
```

---

## 💡 Quick Commands Reference

### Setup

```bash
# 1. Create .env file
cp .env.storage.example .env
# Edit: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_CONNECTION_STRING

# 2. Install dependency
pip install supabase

# 3. Create Storage bucket (automatic)
python scripts/setup_storage.py

# 4. Run SQL schema (copy from README.md to Supabase SQL Editor)
```

### Daily Usage

```bash
# Upload documents
python scripts/upload_documents.py --dir /path/to/documents

# Process pending
python process_documents_storage.py

# Index vectors
cd .. && python rag_indexer/indexer.py
```

### Monitoring

```sql
-- Check status
SELECT storage_status, COUNT(*)
FROM vecs.document_registry
WHERE storage_path IS NOT NULL
GROUP BY storage_status;

-- Pending queue
SELECT original_filename, uploaded_at
FROM vecs.document_registry
WHERE storage_status = 'pending'
ORDER BY uploaded_at ASC;
```

### Testing

```bash
# End-to-end test
python scripts/test_storage_workflow.py test.pdf

# Quick search test
cd ../rag_client && python scripts/quick_search.py
```

---

## 🆘 Getting Help

### Common Issues

| Error | Solution | Documentation |
|-------|----------|---------------|
| "SUPABASE_URL not set" | Check `.env` file | [QUICKSTART_STORAGE.md](QUICKSTART_STORAGE.md#troubleshooting) |
| "Bucket not found" | Create bucket in Dashboard | [QUICKSTART_STORAGE.md](QUICKSTART_STORAGE.md#1-create-storage-bucket) |
| Upload OK, download fails | Check Storage policies | [STORAGE_MIGRATION_GUIDE.md](STORAGE_MIGRATION_GUIDE.md#troubleshooting) |
| DB migration fails | Check schema compatibility | [SCHEMA_UPDATES.md](SCHEMA_UPDATES.md#migration-options) |

### Support Resources

1. **Troubleshooting Sections**:
   - [QUICKSTART_STORAGE.md#Troubleshooting](QUICKSTART_STORAGE.md)
   - [STORAGE_MIGRATION_GUIDE.md#Troubleshooting](STORAGE_MIGRATION_GUIDE.md)
   - [DEPLOYMENT_CHECKLIST.md#Rollback Plan](DEPLOYMENT_CHECKLIST.md)

2. **SQL Queries**:
   - [README.md](../README.md) - Lines 217-298 (query examples)
   - [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Monitoring queries

3. **Architecture Details**:
   - [STORAGE_MIGRATION_GUIDE.md#Architecture](STORAGE_MIGRATION_GUIDE.md)
   - [IMPLEMENTATION_SUMMARY.md#Workflow](IMPLEMENTATION_SUMMARY.md)

---

## 🎓 Key Concepts

### Storage Lifecycle

```
Upload → pending → processing → processed/failed → indexed
```

### Dual Mode Support

The system supports **both** modes simultaneously:
- **Filesystem mode**: Original (still works)
- **Storage mode**: New (recommended)

### Backward Compatibility

- Old code continues to work
- `raw_file_path` is now optional
- No breaking changes

---

## 📊 Feature Comparison

| Feature | Filesystem | Storage |
|---------|-----------|---------|
| **Multi-server** | ❌ | ✅ |
| **Auto backups** | ❌ | ✅ |
| **Status tracking** | Manual | ✅ Automatic |
| **CDN** | ❌ | ✅ |
| **Scalability** | Limited | ✅ Unlimited |
| **Cost** | Free | Free tier → Paid |
| **Setup time** | 0 min | 5 min |

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-23 | Initial Storage implementation |
| - | - | Added: storage_manager.py |
| - | - | Updated: registry_manager.py, document_scanner.py, document_converter.py |
| - | - | Database: Added Storage fields, indexes, policies |
| - | - | Documentation: 6 guides, 2500+ words |

---

## 🚀 What's Next?

### Optional Future Enhancements

- **Phase 2**: Store markdown/JSON in Storage (backups)
- **Phase 3**: Remove filesystem mode entirely
- **API Integration**: Add upload endpoint to FastAPI
- **Web UI**: Direct browser uploads to Storage
- **Monitoring Dashboard**: Real-time status tracking

### Current State

✅ **COMPLETE** - Phase 1: Raw documents in Storage
- All code implemented
- Fully tested
- Production ready
- 100% backward compatible

---

## 📞 Contact

For questions about this implementation:
- Check relevant documentation above
- Review SQL schema in [README.md](../README.md)
- Test with [test_storage_workflow.py](scripts/test_storage_workflow.py)

---

**Last Updated**: 2025-01-23
**Implementation Version**: 1.0.0
**Status**: ✅ Production Ready

**Recommended starting point**: [QUICKSTART_STORAGE.md](QUICKSTART_STORAGE.md) 🚀
