# Состояние сессии перед перезагрузкой

**Дата:** 2025-10-23 15:30
**Проблема:** Логи поиска не появляются в консоли API после `Application startup complete.`

## Что было сделано в этой сессии

### 1. ✅ Исправлены скоры (РАБОТАЕТ)

**Файл:** `api/modules/search/routes/search.py` (строки 158-198)

**Что изменено:**
- API теперь приоритетно использует `llm_relevance_score` (0-10) вместо базового `similarity_score` (0.65)
- Конвертация: LLM score / 10.0 = display_score
- Результат: пользователь видит 100% вместо 65% для идеальных совпадений

**Статус:** ✅ Работает корректно

### 2. ❌ Попытка добавить детальное логирование (НЕ РАБОТАЕТ)

**Что пытались сделать:**
- Добавить подробные логи в `api/modules/search/routes/search.py`
- Настроить логгеры в `api/main.py`

**Проблема:**
- Логи НЕ появляются в консоли при поиске
- Фронтенд работает и получает результаты
- HTTP запросы доходят до API
- Но логи внутри search endpoint не выводятся

### 3. Откат изменений

Откатили файлы на коммит `9e520f7` (до "without logs"):
```bash
git checkout 9e520f7 -- api/main.py api/modules/search/routes/search.py
git restore --staged api/main.py api/modules/search/routes/search.py
```

**Результат:** Логи всё равно НЕ работают

## Текущее состояние файлов

### Git статус
```
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
	modified:   api/main.py
	modified:   api/modules/search/routes/search.py
```

### Коммиты (последние)
```
6a7d726 without logs  <-- HEAD
9e520f7 search UI     <-- откатились сюда
0838a78 search ok
0a8f400 search2
546fb4b search re ranking1
```

### Текущая версия api/main.py
- Базовая настройка logging.basicConfig
- БЕЗ дополнительных настроек логгеров
- БЕЗ force=True

### Текущая версия api/modules/search/routes/search.py
- Есть базовые логи: "SEARCH REQUEST", "STAGE 0", "STAGE 1", "STAGE 2"
- Используется `logger = logging.getLogger(__name__)`
- НО логи НЕ выводятся в консоль

## Вопрос без ответа

**Когда в последний раз логи работали?**
- До коммита "without logs"?
- Или они не работали уже давно?

Пользователь не помнит/не знает.

## Возможные причины проблемы

1. **Uvicorn перехватывает логи** - run_api.py использует `uvicorn.run()` с `reload=True`
2. **Logger не настроен** - `logging.getLogger(__name__)` в search.py не выводит в консоль
3. **Уровень логирования** - может быть установлен выше INFO
4. **Конфликт логгеров** - возможно где-то еще есть настройка логирования

## Что проверить после перезагрузки

1. **Проверить run_api.py** - как именно запускается uvicorn
2. **Добавить print() вместо logger** - чтобы понять доходит ли код до search endpoint
3. **Проверить переменные окружения** - может есть LOG_LEVEL или другие настройки
4. **Посмотреть uvicorn логи** - видны ли HTTP запросы "POST /api/search/ HTTP/1.1 200"

## Важные файлы

- `api/modules/search/routes/search.py` - основной search endpoint
- `api/main.py` - настройка FastAPI и logging
- `run_api.py` - запуск uvicorn
- `api/core/dependencies.py` - инициализация компонентов

## Созданные документы (можно удалить)

Эти файлы были созданы но не используются:
- `API_LOGGING_IMPROVED.md`
- `CHECK_LOGS_INSTRUCTIONS.md`
- `EXAMPLE_SEARCH_LOGS.txt`
- `HOW_TO_SEE_SEARCH_LOGS_RU.md`
- `run_api_no_reload.py`
- `show_api_logs.py`
- `test_detailed_logs.py`
- `SCORE_DISPLAY_IMPROVEMENT.md`
- `api_logs.txt`
- `test_api_score_fix.py`

## Следующие шаги (после перезагрузки)

1. Прочитать этот файл
2. Проверить `run_api.py` - как настроен uvicorn
3. Попробовать добавить `print()` в search endpoint чтобы убедиться что код выполняется
4. Проверить работает ли базовый logging в других частях API
5. Найти где раньше работали логи и как они были настроены

## Команда для восстановления контекста

После перезагрузки в новой сессии Claude Code скажите:

```
Прочитай файл SESSION_STATE_BEFORE_REBOOT.md - там описано где мы остановились.
Проблема: логи поиска не появляются в консоли API.
Нужно найти почему logger.info() в api/modules/search/routes/search.py не выводит в консоль.
```

## Background процессы (нужно убить перед перезагрузкой)

Есть несколько висящих background процессов. Не важно, после перезагрузки они сами завершатся.
