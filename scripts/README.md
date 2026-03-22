# Скрипты

Все **`.bat`** сами переходят в корень репозитория (`cd /d "%~dp0.."`). Запуск основного сценария — см. корневой **`README.md`**, разделы «Настройка, запуск и проверка» и «Как запустить `lab_check.bat`».

## Главный сценарий

**`lab_check.bat`** — Docker, DVC (pull → при отсутствии корпуса генерация → add/push → удаление `data\corpus` → pull из MinIO), pytest, `lab_verify.py`.

## Python

| Файл | Назначение |
|------|------------|
| `generate_corpus_data.py` | Генерация `data/corpus/<язык>/*.txt` |
| `lab_verify.py` | Проверки: `.env`, MinIO, корпус, детектор языка, DVC |

## Пошаговые `.bat`

| Файл | Действие |
|------|----------|
| `lab_docker_up.bat` | `docker compose up -d` |
| `lab_generate_corpus.bat` | только генерация корпуса |
| `lab_ensure_corpus.bat` | корпус есть? иначе генерация |
| `lab_dvc_push_corpus.bat` | `dvc add` + `dvc push` |
| `lab_dvc_pull_corpus.bat` | `dvc pull` |
| `lab_dvc_checkout_corpus.bat` | `dvc checkout data/corpus.dvc` |
| `lab_dvc_status.bat` | `dvc status` |
| `lab_git_log_corpus_dvc.bat` | `git log` по `data/corpus.dvc` |
| `lab_run_tests.bat` | `pytest -q` |
| `lab_verify.bat` | только `lab_verify.py` |

Их можно запускать так же, как **`lab_check.bat`**: из папки `scripts` двойным щелчком или из корня проекта командой `scripts\имя_файла.bat`.
