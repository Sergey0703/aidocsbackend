# Как проверить логи бэкенда

## Проблема
Вы запускали API (`python run_api.py`) и не видели детальные логи поиска.

## Решение
Я добавил подробное логирование на всех этапах поиска.

## Как проверить

### Вариант 1: Запустить API в консоли (рекомендуется)

```bash
# Остановите текущий API если он запущен
# Затем запустите заново:
python run_api.py
```

Вы увидите:
1. Логи инициализации
2. Затем при каждом поиске - детальные логи всех этапов

### Вариант 2: Тестовый запрос

В отдельной консоли запустите:
```bash
python test_detailed_logs.py
```

Затем посмотрите в окно где запущен API - там должны появиться детальные логи.

## Что вы увидите

```
================================================================================
SEARCH REQUEST: query='231-D-54321', top_k=10
================================================================================

STAGE 0: Query Preprocessing
----------------------------------------
[+] Query preprocessed: '231-D-54321' -> '231-D-54321'
    Method: PASS
    Time: 0.001s

STAGE 1: Multi-Strategy Retrieval
----------------------------------------
[+] Retrieved 6 candidates
    Methods: database_hybrid, vector_smart_threshold
    Time: 1.847s
    Result sources breakdown:
      - database_hybrid: 3 results
      - vector_smart_threshold: 3 results

STAGE 2: Hybrid Results Fusion + LLM Re-ranking
----------------------------------------
[+] Fused to 3 documents
    Fusion method: database_priority
    Time: 2.120s
    Top 3 results:
      [1] CVRT Pass Statement.md
          Base score: 0.650, LLM: 10.0, Match: exact_phrase
      [2] Vehicle Registration Certificate.md
          Base score: 0.650, LLM: 10.0, Match: exact_phrase
      [3] VCR.md
          Base score: 0.650, LLM: 10.0, Match: exact_phrase

STAGE 3: Format Response
----------------------------------------

================================================================================
SEARCH COMPLETED
================================================================================
Total Time: 3.289s
Results returned: 3
Time breakdown:
  - Preprocessing: 0.001s
  - Retrieval: 1.847s
  - Fusion: 2.120s
Final scores (what user sees):
  [1] CVRT Pass Statement.md: 100.0%
  [2] Vehicle Registration Certificate.md: 100.0%
  [3] VCR.md: 100.0%
================================================================================
```

## Детали логирования

### STAGE 0: Query Preprocessing
- Показывает оригинальный запрос
- Показывает обработанный запрос
- Показывает удаленные stop words (если есть)
- Показывает AI enhancement (если применялся)
- Время обработки

### STAGE 1: Retrieval
- Количество найденных кандидатов
- Использованные методы (database, vector)
- Разбивка по источникам
- Время поиска

### STAGE 2: Fusion + Re-ranking
- Метод fusion (database_priority, hybrid_weighted, etc.)
- Количество результатов после fusion
- Топ-3 результата с оценками:
  - Base score (базовый скор)
  - LLM score (оценка Gemini, 0-10)
  - Match type (exact_phrase, strong_match, etc.)
- Время fusion + LLM re-ranking

### STAGE 3: Format Response
- Финальное количество результатов
- Общее время выполнения
- Разбивка по времени на каждый этап
- **Финальные скоры что видит пользователь** (улучшенные!)

## Изменения в коде

### 1. `api/main.py`
```python
# Setup logging - Configure root logger to capture all backend logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    force=True
)

# Set log level for backend modules
logging.getLogger('retrieval').setLevel(logging.INFO)
logging.getLogger('query_processing').setLevel(logging.INFO)
logging.getLogger('api').setLevel(logging.INFO)
```

### 2. `api/modules/search/routes/search.py`
- Добавлено детальное логирование на каждом этапе
- Добавлена разбивка источников результатов
- Добавлен вывод топ-3 с LLM scores
- Добавлена таблица времени выполнения
- Добавлены финальные скоры для пользователя

## Если логи не появляются

1. Проверьте что API запущен в правильной консоли
2. Проверьте что уровень логирования INFO (не ERROR)
3. Перезапустите API:
   ```bash
   # Ctrl+C чтобы остановить
   python run_api.py
   ```
4. Отправьте тестовый запрос:
   ```bash
   python test_detailed_logs.py
   ```
5. Логи должны появиться немедленно в консоли API

## Примечание

Все изменения уже внесены в код. Вам нужно только:
1. Перезапустить API
2. Отправить любой поисковый запрос
3. Смотреть детальные логи в консоли

## Emoji удалены

Как вы просили, никаких emoji в логах нет - только ASCII символы:
- [+] успех
- [-] отфильтровано
- [!] предупреждение
- [*] информация
