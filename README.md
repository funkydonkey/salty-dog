# Salty Dog

Sailing charter trip companion — PWA на основе заметок Obsidian.

## Запуск

```bash
# зависимости (один раз)
uv sync

# .env уже настроен (VAULT_PATH, PORT)

# собрать content.json из vault
make build

# запустить сервер
make dev
```

Открыть http://localhost:8000

## Полезные команды

```bash
make test      # тесты
make test-cov  # тесты с покрытием
make build     # пересобрать content.json после правок в Obsidian
```

Подробности по структуре `_app.yaml`, шаблонам и добавлению заметок — см. [USAGE.md](USAGE.md).
