# Churn Prediction (Mock) - Лабораторная работа №1

Проект демонстрирует скелет AI-системы с архитектурой **Clean Architecture** и разделением на слои:

* `domain` - бизнес-сущности и интерфейсы
* `application` - use-case (логика сценария)
* `infrastructure` - реализации интерфейсов (mock-модель)
* `presentation` - CLI для запуска прогнозов

На этом этапе используется **Mock-реализация** модели (без реального ML).

## Требования

* Python `>= 3.10` (рекомендуется 3.11+)
* Poetry (для установки зависимостей)

Если Poetry не установлен, установите его (пример):

```bash
pip install poetry
```

## Структура

```plaintext
src/
├── domain/
│   ├── entities.py
│   └── interfaces.py
├── application/
│   └── services.py
├── infrastructure/
│   └── churn_model.py
├── presentation/
│   └── cli.py
tests/
pyproject.toml
README.md
```

## Установка зависимостей

1. Перейдите в корень проекта (где лежит `pyproject.toml`):

```bash
cd E:\pythonProdgect\churn_prediction
```

2. Установите зависимости через Poetry:

```bash
poetry install
```

## Проверка лабораторной (что должно работать)

### 1) Запуск CLI

Запустите CLI-приложение (пример из задания):

```bash
poetry run python -m src.presentation.cli --client_id 123 \
  --days_since_last_login 40 \
  --total_spend 100.0 \
  --support_tickets_count 6
```

Ожидаемый вывод (пример):

```text
Client ID: 123
Risk: HIGH
Score: 0.8

Recommendation:
- Offer discount
- Contact support team
```

### 2) Запуск тестов (pytest)

Запустите тесты:

```bash
poetry run pytest -q
```

