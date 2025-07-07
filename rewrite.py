import os

def export_directory_structure(start_path, output_file="output.txt"):
    excluded_files = {'my_account.session', 'my_account.session-journal', '__*', 'poetry.lock', 'pyproject.toml', 'pytest.ini', 'requirements.txt', 'rewrite.py'}
    
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for root, dirs, files in os.walk(start_path):
            # Исключаем ненужные папки (изменяем список dirs "на лету")
            dirs[:] = [d for d in dirs if d not in ('voice_messages', 'venv', '__pycache__', '.git', 'tests')]
            
            # Записываем текущую директорию
            out_file.write(f"=== ДИРЕКТОРИЯ: {root} ===\n\n")
            
            # Записываем все файлы в директории и их содержимое
            for file in files:
                if file in excluded_files:
                    continue  # Пропускаем исключенные файлы
                    
                file_path = os.path.join(root, file)
                out_file.write(f"📄 ФАЙЛ: {file_path}\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        out_file.write("🔹 СОДЕРЖИМОЕ:\n")
                        out_file.write(f.read() + "\n")
                except UnicodeDecodeError:
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            out_file.write("🔹 СОДЕРЖИМОЕ (бинарное или неизвестная кодировка):\n")
                            out_file.write(f.read() + "\n")
                    except Exception as e:
                        out_file.write(f"❌ Ошибка чтения файла: {e}\n")
                except Exception as e:
                    out_file.write(f"❌ Ошибка: {e}\n")
                
                out_file.write("\n" + "-" * 50 + "\n\n")  # Разделитель

if __name__ == "__main__":
    target_directory = input("Введите путь к папке: ")
    output_filename = input("Введите имя выходного файла (по умолчанию output.txt): ") or "output.txt"
    export_directory_structure(target_directory, output_filename)
    print(f"✅ Готово! Результат сохранён в {output_filename}")
