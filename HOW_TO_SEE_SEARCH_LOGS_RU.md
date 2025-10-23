# Как увидеть логи поиска (РЕШЕНИЕ)

## Проблема

Вы видите только логи инициализации API, но не видите детальные логи при поиске.

## Причина

Когда вы делаете поиск через фронтенд, логи появляются **В КОНСОЛИ ГДЕ ЗАПУЩЕН API**, но их может быть не видно из-за автоматических перезагрузок watchfiles.

## РЕШЕНИЕ

### Шаг 1: Остановите текущий API

В консоли где запущен API, нажмите:
```
Ctrl+C
```

### Шаг 2: Запустите API БЕЗ auto-reload

Вместо `python run_api.py` используйте:
```bash
python run_api_no_reload.py
```

Этот скрипт запускает API **без автоматической перезагрузки**, что позволяет видеть все логи четко.

### Шаг 3: Дождитесь инициализации

Вы увидите:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
2025-10-23 15:XX:XX,XXX - INFO - api.main - 🚀 Starting Document Intelligence Platform API...
...
INFO:     Application startup complete.
```

### Шаг 4: Сделайте поиск

Откройте фронтенд в браузере и выполните любой поиск (например, "231-D-54321").

### Шаг 5: НЕМЕДЛЕННО вернитесь к консоли API

В консоли ВЫ УВИДИТЕ детальные логи:

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

INFO:     192.168.1.100:54321 - "POST /api/search/ HTTP/1.1" 200 OK
```

## Что вы увидите

### STAGE 0: Query Preprocessing
- Оригинальный запрос
- Обработанный запрос
- Метод обработки (PASS, CLEANED, AI_ENHANCED, REJECTED)
- Удаленные stop words (если есть)
- Время обработки

### STAGE 1: Multi-Strategy Retrieval
- Количество найденных кандидатов
- Использованные методы (database_hybrid, vector_smart_threshold)
- Разбивка по источникам (сколько от database, сколько от vector)
- Время поиска

### STAGE 2: Hybrid Results Fusion + LLM Re-ranking
- Метод fusion (database_priority, hybrid_weighted, etc.)
- Количество результатов после deduplic ation и fusion
- Топ-3 результата с детальными скорами:
  - **Base score**: базовый скор (0.65 для database)
  - **LLM score**: оценка Gemini 0-10 (например, 10.0)
  - **Match type**: тип совпадения (exact_phrase, strong_match, etc.)
- Время fusion + re-ranking

### STAGE 3: Format Response
- Финальное количество результатов
- Общее время выполнения
- Разбивка времени по этапам
- **Финальные скоры что видит пользователь** (улучшенные!)
  - Например: 100.0% вместо 65.0%

## Важные детали

### 1. Логи появляются В РЕАЛЬНОМ ВРЕМЕНИ

Когда пользователь делает поиск в браузере → логи СРАЗУ появляются в консоли API.

### 2. Каждый поиск = новый блок логов

Каждый запрос начинается с:
```
================================================================================
SEARCH REQUEST: query='...'
================================================================================
```

### 3. Emoji заменены на ASCII

Все символы ASCII:
- [+] - успех/завершение
- [-] - отфильтровано
- [!] - предупреждение
- [*] - информация

## Альтернативный способ (если не хотите останавливать API)

Если у вас уже запущен API с reload, просто подождите 30 секунд чтобы watchfiles успокоился, затем сделайте поиск и СРАЗУ смотрите в консоль.

## Если СОВСЕМ не видите логов

1. **Проверьте что смотрите в правильное окно консоли**
   - Там где вы запустили `python run_api_no_reload.py`

2. **Проверьте что запрос дошел до API**
   - Откройте браузер DevTools (F12)
   - Вкладка Network
   - Ищите POST запрос на `/api/search/`
   - Проверьте что Status = 200

3. **Проверьте что API не упал**
   - В консоли должно быть "Application startup complete"
   - Попробуйте: `curl http://localhost:8000/health`

## Тестовый запрос через curl

Если хотите быстро протестировать логи БЕЗ фронтенда:

```bash
curl -X POST "http://localhost:8000/api/search/" \
     -H "Content-Type: application/json" \
     -d "{\"query\": \"test\", \"top_k\": 3}"
```

Сразу после выполнения команды смотрите в консоль API - там будут все логи!

## Резюме

```
┌─────────────────────────────────────┐
│ 1. Остановите API (Ctrl+C)         │
│ 2. Запустите run_api_no_reload.py  │
│ 3. Дождитесь "startup complete"     │
│ 4. Сделайте поиск                    │
│ 5. СМОТРИТЕ В КОНСОЛЬ API            │
└─────────────────────────────────────┘
```

**Логи НЕ появляются здесь в чате - они в ВАШЕЙ консоли!**

## Статус

- ✅ Код логирования добавлен и работает
- ✅ Все этапы логируются детально
- ✅ Финальные скоры показываются корректно (100% вместо 65%)
- ✅ Создан скрипт без reload для стабильных логов
- ✅ Без emoji (только ASCII)

Теперь когда вы запустите API и сделаете поиск, вы увидите все детали процесса!
