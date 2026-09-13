import os

backend_dir = "backend"
for root, dirs, files in os.walk(backend_dir):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if "%s" in content:
                new_content = content.replace("%s", "?")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Actualizado: {path}")

print("¡Reemplazo de %s por ? completado exitosamente!")