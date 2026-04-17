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

## Fresh clone: один проход “с нуля” до API

Ниже — минимальный сценарий для человека, который **только что** сделал `git clone` и хочет **поднять MinIO + DVC + обучить модель + запустить FastAPI**.

1) Создайте файл `.env` в корне репозитория (содержимое см. раздел **«`.env`»** ниже).

2) Установите зависимости и поднимите MinIO:

```bash
cd E:\pythonProdgect\churn_prediction
poetry install
docker compose up -d
```

3) Настройте DVC remotes/creds локально:
- для корпуса: команды из раздела **«DVC remote: переинициализация»** (remote `myremote`, бакет `datasets`);
- для модели: команды из раздела **«Лабораторная 3 → DVC remote для моделей»** (remote `models_storage`, бакет `models`).

4) Подготовьте корпус `data/corpus` (если `dvc pull` не подтянул данные):

```bash
poetry run python scripts/generate_corpus_data.py
```

5) Обучите модель и отправьте кэш DVC в MinIO **через DVC** (`dvc push` в remote `models_storage`; объекты попадают под префикс `dvc-store/` внутри бакета `models`, а не как отдельные ключи `*.onnx` в корне). Без локальных `models/*.onnx` / `classes.json` API при старте выполнит `dvc pull -r models_storage` по файлам `models/*.dvc`.

```bash
poetry run python scripts/train_model.py --corpus-root data/corpus --models-dir models
poetry run dvc status
```

6) Запустите API и сделайте REST‑запрос (примеры в разделе **«Лабораторная 3 → Проверка endpoint»**).

Примечание: если вы **не на Windows**, замените путь `E:\...` на путь вашего клона.

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

['remote "models_storage"']
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
['remote "models_storage"']
    url = s3://models/dvc-store
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
- поднимает MinIO и создаёт бакеты `datasets` и `models`;
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

### 1) MinIO + бакеты

```bash
cd E:\pythonProdgect\churn_prediction
docker compose up -d
```

В MinIO должны существовать бакеты:
- `datasets` (как раньше, для DVC корпуса)
- `models` (для DVC артефактов модели)

### 2) DVC remote для моделей (`models_storage`)

Один раз на машине (или после клона), настройте remote на бакет `models` и локальные креды (аналогично `myremote`):

```bash
poetry run dvc remote add models_storage s3://models/dvc-store
poetry run dvc remote modify models_storage endpointurl http://localhost:9000
poetry run dvc remote modify models_storage ssl_verify false
poetry run dvc remote modify models_storage access_key_id minioadmin --local
poetry run dvc remote modify models_storage secret_access_key minioadmin --local
poetry run dvc remote modify models_storage region us-east-1 --local
```

Примечание: файл `.dvc/config.local` игнорируется Git’ом (см. `.dvc/.gitignore`), поэтому **локальные креды** каждый разработчик настраивает у себя.

Если в методичке требуют `dvc remote add -d ...` (сделать `models_storage` default remote), выполните так, но имейте в виду:
это изменит default remote для **всех** последующих `dvc push/pull` в этом репозитории.
Вернуть обратно можно так:

```bash
poetry run dvc remote default myremote
```

### 3) Обучение + экспорт ONNX + `dvc add` + `dvc push`

Модель обучается строго по корпусу `data/corpus/<lang>/*.txt` и сохраняет:
- `models/language_detector.onnx`
- `models/classes.json`

```bash
cd E:\pythonProdgect\churn_prediction
poetry run python scripts/train_model.py --corpus-root data/corpus --models-dir models
```

Скрипт после обучения выполнит:
- `dvc add models/language_detector.onnx models/classes.json`
- `dvc push -r models_storage ...`

Проверка, что DVC видит новые/изменённые артефакты:

```bash
poetry run dvc status
```

Если вы хотите **зафиксировать метаданные** (`models/*.dvc`, `models/.gitignore`) в истории проекта — это уже шаг **Git** (не GitHub и не DVC): `git add ... && git commit ...`.
Для локальной работы и `dvc push` в MinIO это **не обязательно**.

Если нужно только локально обучить без DVC:

```bash
poetry run python scripts/train_model.py --corpus-root data/corpus --models-dir models --skip-dvc
```

### 4) Запуск API

```bash
cd E:\pythonProdgect\churn_prediction
poetry run uvicorn src.presentation.api:app --reload --port 8000
```

### 5) Проверка endpoint (REST)

PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/text/detect_language" -ContentType "application/json" -Body '{"text":"Hallo Welt"}'
```

`curl` (Git Bash / WSL):

```bash
curl -sS -X POST "http://localhost:8000/api/v1/text/detect_language" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Hallo Welt\"}"
```

`curl` (cmd.exe, перенос строки `^`):

```bat
curl -sS -X POST "http://localhost:8000/api/v1/text/detect_language" ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"Hallo Welt\"}"
```

Python `requests`:

```bash
poetry run python -c "import requests; print(requests.post('http://localhost:8000/api/v1/text/detect_language', json={'text':'Hallo Welt'}).json())"
```

Ожидаемый формат:

```json
{
  "language_code": "de",
  "confidence": 0.97
}
```

### 6) Если модели нет локально (восстановление при старте API)

При старте API `src/presentation/dependencies.py` проверяет наличие:
- `models/language_detector.onnx`
- `models/classes.json`

Если файлов нет — выполняется **`dvc pull -r models_storage`** для `models/language_detector.onnx.dvc` и `models/classes.json.dvc`. Это согласовано с remote `s3://models/dvc-store`: DVC хранит бинарники под префиксом `dvc-store/`, их нельзя корректно подтянуть «обычным» S3-скачиванием по имени файла из корня бакета.

Нужны: запущенный MinIO, секция `models_storage` в `.dvc/config.local`, и сами `*.dvc` после обучения (в репозитории или у вас локально).

Проверка вручную (удалить только бинарники и JSON, **не** удалять `models/*.dvc`):

PowerShell:

```powershell
Remove-Item -Force models\language_detector.onnx, models\classes.json -ErrorAction SilentlyContinue
poetry run uvicorn src.presentation.api:app --reload --port 8000
```

После старта файлы снова появятся в `models/` (проверьте `Get-ChildItem models`).

### 7) Запуск автотестов

```bash
poetry run python -m pytest -q
```

## Лабораторная 4 (вариант 13): асинхронное определение языка

Реализованы требования варианта:
- `POST /api/v1/text/detect_language_async` -> возвращает `{ "task_id": "..." }` (HTTP 202).
- `GET /api/v1/text/results/{task_id}` -> возвращает статус задачи и итог:
  `{ "status": "SUCCESS", "result": { "language_code": "en", "confidence": 0.99 } }`.

### Новые компоненты

- `src/presentation/celery_app.py` — настройка Celery + Redis broker/backend.
- `src/presentation/tasks.py` — Celery task `detect_language`.
- `Dockerfile.api` — контейнер FastAPI.
- `Dockerfile.worker` — контейнер Celery worker.
- `docker-compose.yml` — `api`, `worker`, `broker` (Redis), `minio`, `minio-mc`.

### Запуск всей системы

```bash
docker compose up -d --build
```

### Проверка API (вариант 13)

1) Создать задачу:

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/v1/text/detect_language_async" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Hallo Welt\"}"
```

Ответ:

```json
{"task_id":"<uuid>"}
```

2) Проверить результат:

```bash
curl -sS "http://127.0.0.1:8000/api/v1/text/results/<uuid>"
```

Сначала обычно:

```json
{"task_id":"<uuid>","status":"PENDING","result":null}
```

Потом:

```json
{"task_id":"<uuid>","status":"SUCCESS","result":{"language_code":"de","confidence":0.97}}
```
