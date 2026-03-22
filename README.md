# Churn Prediction + Определение языка текста (ЛР №1–2)

Проект демонстрирует скелет AI-системы с архитектурой **Clean Architecture** и разделением на слои:

* `domain` — бизнес-сущности и интерфейсы (`IChurnModel`, `ILanguageDetector`, `IDataStorage`)
* `application` — use-case (отток, синхронизация данных `DataSyncService`)
* `infrastructure` — реализации (mock churn, детектор языка по корпусу, `S3Storage` / MinIO)
* `presentation` — CLI и фабрики (composition root)

**Лабораторная №2 (вариант 13):** корпус текстов для определения языка лежит в `data/corpus/`, версионируется через **DVC**; список языков **не зашит в код** — он выводится из подкаталогов корпуса.

**MinIO + DVC remote:** демо-датасет (`data/corpus`) пушится в бакет `datasets` через `dvc push`. Для **`dvc push` / `dvc pull`** учётные данные S3-remote заданы в **`.dvc/config.local`** (те же значения по умолчанию, что у MinIO в `docker-compose`). Для приложения **`S3Storage`** и **`lab_verify.py`** используется **`.env`** с переменными **`MINIO_*`** (ниже).

## Требования

* Python `>= 3.10` (рекомендуется 3.11+)
* Poetry (для установки зависимостей)
* Git, DVC с поддержкой S3 (`dvc[s3]`), Docker / Docker Compose (для MinIO)

Если Poetry не установлен:

```bash
pip install poetry
```

## Структура

```plaintext
docker-compose.yml          # MinIO + автосоздание бакета datasets (minio-init)
.env                        # MinIO для приложения (MINIO_*)
.dvc/config.local           # ключи для DVC remote (S3/MinIO)
scripts/                    # lab_check.bat, прочие .bat, *.py
data/
├── corpus.dvc
└── corpus/                 # подкаталоги = коды языков; внутри — *.txt
src/
├── domain/
│   ├── entities.py
│   └── interfaces.py       # IDataStorage, ILanguageDetector, …
├── application/
│   ├── services.py
│   └── data_sync_service.py
├── infrastructure/
│   ├── churn_model.py
│   ├── language_detector.py
│   ├── s3_storage.py
│   └── storage_settings.py
├── presentation/
│   ├── cli.py
│   ├── sync_cli.py
│   └── factories.py
tests/
pyproject.toml
README.md
```

## Установка зависимостей

```bash
cd E:\pythonProdgect\churn_prediction
poetry install
```

## Файл `.env` (MinIO)

В корне репозитория — файл **`.env`** (в Git не коммитится). Достаточно переменных для подключения к MinIO (их же использует `S3Storage` / проверка в `lab_verify.py`):

| Переменная | Назначение |
|------------|------------|
| `MINIO_ENDPOINT` | URL API MinIO, локально: `http://localhost:9000` |
| `MINIO_ACCESS_KEY` | Ключ доступа (в docker-compose: `minioadmin`) |
| `MINIO_SECRET_KEY` | Секретный ключ |
| `MINIO_BUCKET` | Имя бакета (`datasets`) |

`load_dotenv` читает `<корень проекта>/.env` (см. `storage_settings.py`).

**DVC** не читает `.env` автоматически: ключи для remote лежат в **`.dvc/config.local`** (`access_key_id`, `secret_access_key`, `region`). При смене логина/пароля MinIO обновите их командой [`dvc remote modify`](https://dvc.org/doc/command-reference/remote/modify) с флагом **`--local`** или задайте переменные окружения **`AWS_ACCESS_KEY_ID`** / **`AWS_SECRET_ACCESS_KEY`** (и при необходимости **`AWS_DEFAULT_REGION`**).

---

## Настройка, запуск и проверка

Нужны **Windows** (сценарии `.bat`), **Python** 3.10+, **Poetry**, **Git**, **Docker** с Compose, файл **`.env`** в корне (таблица выше).

| Шаг | Действие |
|-----|----------|
| 1 | Клонировать или распаковать репозиторий. |
| 2 | В корне: `poetry install` |
| 3 | Создать **`.env`** с переменными `MINIO_*` (см. таблицу). |
| 4 | Запустить проверку (см. ниже «Как запустить `.bat`»). |

## DVC: remote на MinIO и данные

Локальный кэш артефактов: `.dvc/cache` (каталог **не коммитится** в Git — см. корневой `.gitignore`).

В репозитории уже задан default-remote **`myremote`** на `s3://datasets/dvc-store` с `endpointurl=http://localhost:9000` и `ssl_verify=false` (файл `.dvc/config`). Учётные данные для MinIO по умолчанию — в **`.dvc/config.local`** (не дублируйте секреты в `.dvc/config`). При необходимости пересоздайте remote вручную:

```bash
dvc remote add -d myremote s3://datasets/dvc-store
dvc remote modify myremote endpointurl http://localhost:9000
dvc remote modify myremote ssl_verify false
dvc remote modify myremote access_key_id minioadmin --local
dvc remote modify myremote secret_access_key minioadmin --local
dvc remote modify myremote region us-east-1 --local
```

### Как запустить `lab_check.bat`

* **Проводник:** откройте папку `scripts`, дважды щёлкните по **`lab_check.bat`** (рабочая папка должна быть корнем проекта — скрипт сам делает `cd` в родительский каталог).
* **Командная строка / PowerShell:** перейдите в корень репозитория и выполните:
  ```bat
  scripts\lab_check.bat
  ```
  или полный путь, например: `E:\pythonProdgect\churn_prediction\scripts\lab_check.bat`

### Что делает `lab_check.bat` (кратко)

1. Поднимает **Docker Compose** (MinIO + автосоздание бакета `datasets`).
2. Ждёт **10 секунд**, затем **`dvc pull`** (если в remote уже есть корпус после чужого `dvc push`, данные подтянутся).
3. Если корпуса нет — **генерирует** демо-корпус (`lab_ensure_corpus` → `generate_corpus_data.py`).
4. **`dvc add data/corpus`** и **`dvc push`** — фиксация и отправка в MinIO.
5. **Демонстрация DVC:** удаляется локальный каталог **`data\corpus`**, затем **`dvc pull`** из MinIO (без запасного `dvc checkout` из локального кэша). Если **`dvc push`** на шаге 4 не удался, сценарий завершается с ошибкой.
6. **`pytest -q`** (требуется **100%** покрытие `src`).
7. **`lab_verify.py`**: `.env`, доступ к MinIO, структура `data/corpus`, детектор языка, команды DVC.

В конце должно появиться сообщение **«Проверка завершена успешно»**.

**Если что-то упало:** проверьте Docker, свободен ли порт **9000**, верны ли **`MINIO_*`** и содержимое **`.dvc/config.local`**, совпадает ли оно с учётной записью MinIO.

---

## MinIO вручную (без bat)

После **`.env`** можно поднять только контейнеры:

```bash
docker compose up -d
```

Сервис **`minio-init`** создаёт бакет **`datasets`**. Консоль: [http://localhost:9001](http://localhost:9001), логин/пароль: `minioadmin` / `minioadmin`.

## DVC: remote на MinIO и данные

Локальный кэш артефактов: `.dvc/cache` (каталог **не коммитится** в Git — см. корневой `.gitignore`).

В репозитории уже задан default-remote **`myremote`** на `s3://datasets/dvc-store` с `endpointurl=http://localhost:9000` и `ssl_verify=false` (файл `.dvc/config`). Учётные данные для MinIO по умолчанию — в **`.dvc/config.local`** (не дублируйте секреты в `.dvc/config`). При необходимости пересоздайте remote вручную:

```bash
dvc remote add -d myremote s3://datasets/dvc-store
dvc remote modify myremote endpointurl http://localhost:9000
dvc remote modify myremote ssl_verify false
dvc remote modify myremote access_key_id minioadmin --local
dvc remote modify myremote secret_access_key minioadmin --local
dvc remote modify myremote region us-east-1 --local
```

Далее:

```bash
dvc add data/corpus
dvc push
```

### Скачать данные после клона

```bash
dvc pull
```

### Первичная фиксация корпуса в DVC (если ещё не сделано)

```bash
dvc init
dvc add data/corpus
git add .dvc data/corpus.dvc data/.gitignore
git commit -m "Track language corpus with DVC"
```

### Добавить новый язык

1. Создайте каталог с **ISO-подобным** кодом языка, например `data/corpus/it/`.
2. Положите в него несколько файлов `*.txt` с текстами на этом языке.
3. Зафиксируйте новую версию корпуса:

```bash
dvc add data/corpus
git add data/corpus.dvc data/.gitignore
git commit -m "Add Italian corpus"
```

Модель `CorpusLanguageDetector` при следующем запуске подхватит новый язык автоматически (список читается с диска).

### Переключение версий корпуса (Git + DVC)

1. Найдите нужный коммит, где зафиксирована версия `data/corpus.dvc`:

```bash
git log --oneline -- data/corpus.dvc
```

2. Переключитесь на него и подтяните данные:

```bash
git checkout <commit>
dvc checkout data/corpus
# или, если настроен remote и нужно скачать бинарники:
dvc pull
```

3. Убедитесь, что в `data/corpus/` только языки этой версии, и при необходимости перезапустите CLI/тесты.

## Скрипты (`scripts/`)

| Файл | Назначение |
|------|------------|
| **`lab_check.bat`** | Основной сценарий: Docker, DVC (pull → генерация при отсутствии → add/push → удаление `data\corpus` → pull из MinIO), pytest, `lab_verify.py` |

Запуск — см. раздел **«Как запустить `lab_check.bat`»** выше. Дополнительные пошаговые **`.bat`** перечислены в **`scripts/README.md`**. Вручную без bat: `poetry run python scripts/generate_corpus_data.py`, `poetry run python scripts/lab_verify.py`.

## CLI: как проверить, что система работает

После успешного **`lab_check.bat`** (или когда корпус уже лежит в `data/corpus/`).

### Прогноз оттока (ЛР №1)

```bash
poetry run python -m src.presentation.cli --client_id 123 ^
  --days_since_last_login 40 ^
  --total_spend 100.0 ^
  --support_tickets_count 6
```

**Признак успеха:** в консоли есть `Client ID:`, `Risk:`, `Score:`, блок `Recommendation:`.

### Определение языка (ЛР №2)

```bash
poetry run python -m src.presentation.cli --text "The quick brown fox jumps over the lazy dog."
```

**Признак успеха:** строка `Detected language:` с кодом языка и `Available languages:` — список кодов из подкаталогов `data/corpus/`.

### Дополнительно

Корпус целиком версионируется через **DVC**. **`sync_cli`** (`python -m src.presentation.sync_cli`) и **`DataSyncService`** — опциональная демонстрация `IDataStorage` для одного файла.

## Тесты

```bash
poetry run pytest -q
```

Покрытие `src`: **100%** (`--cov-fail-under=100`).

## Полезные команды DVC

| Команда | Назначение |
|--------|------------|
| `dvc add data/corpus` | Зафиксировать новую версию каталога корпуса |
| `dvc push` | Отправить кэш на удалённое хранилище |
| `dvc pull` | Загрузить данные с remote в локальный кэш и рабочую копию |

### Пример вывода CLI (отток)

```text
Client ID: 123
Risk: HIGH
Score: 0.8

Recommendation:
- Offer discount
- Contact support team
```
