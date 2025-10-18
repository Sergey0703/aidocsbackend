from pypdf import PdfReader

# Укажите точный путь к вашему PDF файлу
file_path = './data/BD.pdf' # <--- ЗАМЕНИТЕ НА ИМЯ ВАШЕГО ФАЙЛА

print(f"Attempting to read text from: {file_path}")

try:
    reader = PdfReader(file_path)
    print(f"Successfully opened PDF. Number of pages: {len(reader.pages)}")
    
    full_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            print(f"--- Text from Page {i+1} ---")
            print(text)
            print("----------------------")
            full_text += text
        else:
            print(f"--- No text found on Page {i+1} ---")

    if not full_text:
        print("\nRESULT: No text could be extracted from this PDF file. It is likely an image-based or scanned document.")
    else:
        print("\nRESULT: Text was successfully extracted.")

except Exception as e:
    print(f"\nAn error occurred: {e}")
