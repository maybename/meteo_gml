import os, config

for file in os.listdir('/'):
    if (file.endswith('.log') or file.endswith('.txt')) and not file == config.data_file:
        try:
            os.remove(file)
            print(f"Removed {file}")
        except Exception as e:
            print(f"Error removing {file}: {e}")