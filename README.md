# Churn Prediction + Определение языка текста

Короткая инструкция по запуску и проверке проекта (ЛР №1–2) без скрытых шагов.

## Что нужно

- Windows
- Python `>= 3.10`
- Poetry
- Docker Desktop (Compose)
- Git

Если Poetry не установлен:

```bash
pip install poetry
```

## Быстрый старт (основной путь)

```bash
cd E:\pythonProdgect\churn_prediction
poetry install
docker compose up -d
poetry run dvc pull
poetry run pytest -q
poetry run python scripts/lab_verify.py
```

После этого можно проверять CLI:

```bash
poetry run python -m src.presentation.cli --client_id 123 --days_since_last_login 40 --total_spend 100.0 --support_tickets_count 6
poetry run python -m src.presentation.cli --text "The quick brown fox jumps over the lazy dog."
```

## Явные конфиги проекта

Для этого учебного проекта значения в `.env` и `.dvc/config.local` считаются несекретными и должны быть в документации.

### `.env`

Файл в корне проекта, используется приложением и `lab_verify.py`:

```env
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=datasets
```

### `.dvc/config.local`

Локальные креды для DVC remote:

```ini
['remote "myremote"']
    access_key_id = minioadmin
    secret_access_key = minioadmin
    region = us-east-1
```

### `.dvc/config`

Параметры remote (уже есть в репозитории):

```ini
[core]
    remote = myremote
['remote "myremote"']
    url = s3://datasets/dvc-store
    endpointurl = http://localhost:9000
    ssl_verify = false
```

## Полная ручная проверка (аналог `scripts/lab_check.bat`)

Если нужен прозрачный сценарий без `.bat`, выполните по порядку:

```bash
cd E:\pythonProdgect\churn_prediction
poetry install
docker compose up -d
poetry run dvc pull
poetry run python scripts/generate_corpus_data.py
poetry run dvc add data/corpus
poetry run dvc push
rmdir /s /q data\corpus
poetry run dvc pull
poetry run pytest -q
poetry run python scripts/lab_verify.py
```

Что это делает:
- поднимает MinIO и создаёт бакет `datasets`;
- подтягивает корпус из DVC (если уже есть в remote);
- при необходимости генерирует/обновляет корпус;
- отправляет версию корпуса в MinIO через DVC;
- удаляет локальный `data\corpus` и восстанавливает его из remote;
- запускает тесты и финальную проверку.

## DVC remote: переинициализация (если сломана настройка)

Раздел ниже нужен только если `myremote` отсутствует или настроен неверно:

```bash
poetry run dvc remote add -d myremote s3://datasets/dvc-store
poetry run dvc remote modify myremote endpointurl http://localhost:9000
poetry run dvc remote modify myremote ssl_verify false
poetry run dvc remote modify myremote access_key_id minioadmin --local
poetry run dvc remote modify myremote secret_access_key minioadmin --local
poetry run dvc remote modify myremote region us-east-1 --local
```

## Ежедневные команды

```bash
poetry run dvc pull
poetry run dvc add data/corpus
poetry run dvc push
poetry run pytest -q
poetry run python scripts/lab_verify.py
```

## Лабораторная 3: FastAPI + ONNX (определение языка)

### 1) Обучение + экспорт в ONNX

Модель обучается строго по корпусу `data/corpus/<lang>/*.txt` и сохраняет:
- `models/language_detector.onnx`
- `models/classes.json`

```bash
cd E:\pythonProdgect\churn_prediction
poetry run python scripts/train_model.py --corpus-root data/corpus --models-dir models
```

### 2) Загрузка модели в MinIO (бакет `models`)

Команда обучения `scripts/train_model.py` после сохранения автоматически загрузит:
- `language_detector.onnx`
- `classes.json`

в бакет `models` (по умолчанию) по ключам `language_detector.onnx` и `classes.json`.

Если бакет называется иначе, переопределите `MINIO_MODELS_BUCKET` в `.env`.

Важно: чтобы загрузка сработала, MinIO должен быть запущен:

```bash
cd E:\pythonProdgect\churn_prediction
docker compose up -d
```

### 3) Запуск API

```bash
cd E:\pythonProdgect\churn_prediction
poetry run uvicorn src.presentation.api:app --reload --port 8000
```

### 4) Проверка endpoint

PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/text/detect_language" -ContentType "application/json" -Body '{"text":"Hallo Welt"}'
```

Ожидаемый формат:

```json
{
  "language_code": "de",
  "confidence": 0.97
}
```

### 5) Если модели нет локально (скачивание из MinIO)

При старте API `src/presentation/dependencies.py` проверяет наличие:
- `models/language_detector.onnx`
- `models/classes.json`

Если файлов нет — скачивает их из MinIO/S3 по ключам:
- бакет `models` (по умолчанию; переопределяется переменной `MINIO_MODELS_BUCKET`)
- ключи:
  - `language_detector.onnx`
  - `classes.json`

Ключи можно переопределить env-переменными:
- `LANGUAGE_MODEL_ONNX_REMOTE_KEY`
- `LANGUAGE_MODEL_CLASSES_REMOTE_KEY`

Чтобы проверить fallback:

```bat
rmdir /s /q models
poetry run uvicorn src.presentation.api:app --reload --port 8000
```

### 6) Запуск автотестов

```bash
poetry run python -m pytest -q
```
