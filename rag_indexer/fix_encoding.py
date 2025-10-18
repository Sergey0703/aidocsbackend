#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для исправления кодировки файлов проекта RAG Indexer
Автоматически определяет и исправляет проблемы с кодировкой в Python файлах
"""

import os
import sys
import chardet
import shutil
from datetime import datetime


def detect_encoding(file_path):
    """
    Определить кодировку файла
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        str: Обнаруженная кодировка или None
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            if raw_data:
                result = chardet.detect(raw_data)
                return result.get('encoding')
    except Exception as e:
        print(f"Ошибка определения кодировки для {file_path}: {e}")
    return None


def read_file_with_encoding(file_path, encoding):
    """
    Прочитать файл с указанной кодировкой
    
    Args:
        file_path: Путь к файлу
        encoding: Кодировка для чтения
    
    Returns:
        str: Содержимое файла или None при ошибке
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        return None
    except Exception as e:
        print(f"Ошибка чтения файла {file_path}: {e}")
        return None


def clean_problematic_chars(content):
    """
    Очистить проблематичные символы из содержимого
    
    Args:
        content: Содержимое файла
    
    Returns:
        str: Очищенное содержимое
    """
    if not content:
        return content
    
    # Удалить null bytes и другие проблематичные символы
    content = content.replace('\u0000', '')
    content = content.replace('\x00', '')
    content = content.replace('\x95', '')  # Проблематичный байт из ошибки
    
    # Удалить другие управляющие символы, кроме переводов строк и табов
    cleaned_content = ''.join(char for char in content 
                            if ord(char) >= 32 or char in '\n\t\r')
    
    return cleaned_content


def fix_file_encoding(file_path, backup=True):
    """
    Исправить кодировку файла
    
    Args:
        file_path: Путь к файлу
        backup: Создать резервную копию перед исправлением
    
    Returns:
        bool: True если файл был исправлен
    """
    print(f"Обработка файла: {file_path}")
    
    # Создать резервную копию
    if backup:
        backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"  Создана резервная копия: {backup_path}")
        except Exception as e:
            print(f"  ПРЕДУПРЕЖДЕНИЕ: Не удалось создать резервную копию: {e}")
    
    # Определить текущую кодировку
    detected_encoding = detect_encoding(file_path)
    print(f"  Обнаруженная кодировка: {detected_encoding}")
    
    # Попробовать разные кодировки для чтения
    encodings_to_try = [
        detected_encoding,
        'utf-8',
        'utf-8-sig',  # UTF-8 с BOM
        'cp1252',     # Windows-1252
        'iso-8859-1', # Latin-1
        'cp1251',     # Windows-1251 (кириллица)
        'latin1'
    ]
    
    content = None
    used_encoding = None
    
    for encoding in encodings_to_try:
        if encoding:
            content = read_file_with_encoding(file_path, encoding)
            if content is not None:
                used_encoding = encoding
                print(f"  Успешно прочитан с кодировкой: {encoding}")
                break
    
    if content is None:
        print(f"  ОШИБКА: Не удалось прочитать файл ни с одной кодировкой")
        return False
    
    # Очистить проблематичные символы
    original_length = len(content)
    cleaned_content = clean_problematic_chars(content)
    
    if len(cleaned_content) != original_length:
        print(f"  Удалено {original_length - len(cleaned_content)} проблематичных символов")
    
    # Убедиться, что файл начинается с правильного shebang
    if file_path.endswith('.py'):
        lines = cleaned_content.split('\n')
        if lines and not lines[0].startswith('#!'):
            # Добавить shebang если его нет
            lines.insert(0, '#!/usr/bin/env python3')
            cleaned_content = '\n'.join(lines)
            print(f"  Добавлен shebang")
        
        # Убедиться, что есть объявление кодировки
        has_encoding_declaration = False
        for i, line in enumerate(lines[:3]):  # Проверить первые 3 строки
            if 'coding' in line and 'utf-8' in line:
                has_encoding_declaration = True
                break
        
        if not has_encoding_declaration:
            # Найти место для вставки объявления кодировки
            insert_pos = 1 if lines[0].startswith('#!') else 0
            encoding_line = '# -*- coding: utf-8 -*-'
            lines.insert(insert_pos, encoding_line)
            cleaned_content = '\n'.join(lines)
            print(f"  Добавлено объявление кодировки UTF-8")
    
    # Записать файл в UTF-8
    try:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(cleaned_content)
        print(f"  УСПЕХ: Файл сохранен в UTF-8")
        return True
    except Exception as e:
        print(f"  ОШИБКА: Не удалось сохранить файл: {e}")
        return False


def main():
    """Основная функция"""
    
    # Список файлов проекта для обработки
    project_files = [
        'indexer.py',
        'config.py',
        'database_manager.py',
        'embedding_processor.py',
        'batch_processor.py',
        'utils.py',
        'master_indexer.py',
        'file_utils.py',
        'ocr_processor.py',
        'doc_converter.py',
        'document_parsers.py',
        'loading_helpers.py',
        'enhanced_pdf_processor.py',
        'file_utils_core.py'
    ]
    
    print("=" * 60)
    print("УТИЛИТА ИСПРАВЛЕНИЯ КОДИРОВКИ RAG INDEXER")
    print("=" * 60)
    print(f"Проверка и исправление кодировки в {len(project_files)} файлах...")
    print()
    
    # Проверить, что chardet установлен
    try:
        import chardet
    except ImportError:
        print("ОШИБКА: Модуль chardet не установлен")
        print("Установите с помощью: pip install chardet")
        sys.exit(1)
    
    fixed_files = []
    missing_files = []
    failed_files = []
    
    for file_path in project_files:
        if not os.path.exists(file_path):
            print(f"Файл не найден: {file_path}")
            missing_files.append(file_path)
            continue
        
        try:
            if fix_file_encoding(file_path):
                fixed_files.append(file_path)
            else:
                failed_files.append(file_path)
        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА при обработке {file_path}: {e}")
            failed_files.append(file_path)
        
        print()  # Пустая строка между файлами
    
    # Итоговый отчет
    print("=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    print(f"Обработано файлов: {len(fixed_files)}")
    print(f"Не найдено файлов: {len(missing_files)}")
    print(f"Ошибок обработки: {len(failed_files)}")
    
    if fixed_files:
        print(f"\nУСПЕШНО ОБРАБОТАНО:")
        for file_path in fixed_files:
            print(f"  ✓ {file_path}")
    
    if missing_files:
        print(f"\nНЕ НАЙДЕНО:")
        for file_path in missing_files:
            print(f"  - {file_path}")
    
    if failed_files:
        print(f"\nОШИБКИ ОБРАБОТКИ:")
        for file_path in failed_files:
            print(f"  ✗ {file_path}")
    
    print(f"\nРезервные копии сохранены с расширением .backup_YYYYMMDD_HHMMSS")
    print(f"Если что-то пошло не так, можете восстановить файлы из резервных копий.")
    
    if fixed_files and not failed_files:
        print(f"\n🎉 ВСЕ ФАЙЛЫ УСПЕШНО ИСПРАВЛЕНЫ!")
        print(f"Теперь попробуйте запустить: python indexer.py")
    elif failed_files:
        print(f"\n⚠️  НЕКОТОРЫЕ ФАЙЛЫ НЕ УДАЛОСЬ ИСПРАВИТЬ")
        print(f"Проверьте ошибки выше и попробуйте исправить вручную")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
