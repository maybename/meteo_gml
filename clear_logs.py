import os
to_remove: list[str] = []

for file in os.listdir('/'):
    if (file.endswith('.log') or file.endswith('.txt')):
        to_remove.append(file)

print("going to remove:\n")
print('\n'.join(to_remove))
if not input("Do you want to continue? (y/N)") == "y":
    exit()

for file in to_remove:
    try:
        os.remove(file)
        print(f"Removed {file}")
    except Exception as e:
        print(f"Error removing {file}: {e}")