#!/usr/bin/env python3
"""
Проверка лабораторной «определение языка + DVC + MinIO»:
.env, доступ к бакету (как у S3Storage), корпус, CorpusLanguageDetector, DVC.

Запуск (из корня репозитория):
  poetry run python scripts/lab_verify.py

Или: scripts\\lab_verify.bat
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv


def _dvc_run(*args: str, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    """DVC из того же venv, что и текущий интерпретатор (надёжно под poetry run)."""
    return subprocess.run(
        [sys.executable, "-m", "dvc", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _ok(msg: str) -> None:
    print(f"  OK: {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL: {msg}")


def check_env_file() -> bool:
    print("[1] Файл .env в корне репозитория")
    p = _REPO_ROOT / ".env"
    if not p.is_file():
        _fail(f"нет файла {p}")
        return False
    _ok(".env найден")
    return True


def check_minio_s3() -> bool:
    print("[2] MinIO: бакет из .env (тот же endpoint, что использует DVC/S3Storage)")
    load_dotenv(dotenv_path=_REPO_ROOT / ".env")
    try:
        import boto3  # noqa: PLC0415
        from src.infrastructure.storage_settings import load_storage_settings  # noqa: PLC0415
    except ImportError as e:
        _fail(f"импорт: {e}")
        return False

    s = load_storage_settings()
    try:
        client = boto3.client(
            "s3",
            endpoint_url=s.endpoint_url,
            aws_access_key_id=s.access_key,
            aws_secret_access_key=s.secret_key,
        )
        client.head_bucket(Bucket=s.bucket)
    except Exception as e:  # noqa: BLE001
        _fail(f"MinIO/S3: {e}")
        return False
    _ok(f"бакет «{s.bucket}» доступен ({s.endpoint_url})")
    return True


def check_corpus_layout() -> bool:
    print("[3] Структура data/corpus (папки языков и .txt)")
    root = _REPO_ROOT / "data" / "corpus"
    if not root.is_dir():
        _fail(f"нет каталога {root}")
        return False
    required = {"en", "fr", "de", "es"}
    found = {p.name for p in root.iterdir() if p.is_dir()}
    if not required <= found:
        _fail(f"ожидались папки {required}, есть {found}")
        return False
    for lang in sorted(required):
        txts = list((root / lang).glob("*.txt"))
        if len(txts) < 3:
            _fail(f"в {lang}/ меньше 3 файлов .txt")
            return False
    _ok("en/fr/de/es и по >=3 .txt")
    return True


def check_language_detector() -> bool:
    print("[4] Детектор языка (короткие фразы)")
    try:
        from src.presentation.factories import create_language_detector  # noqa: PLC0415
    except ImportError as e:
        _fail(str(e))
        return False

    # Те же фразы, что в tests/test_language_detector.py (устойчивые к корпусу после generate_corpus_data).
    samples = [
        ("en", "The quick brown fox jumps over the lazy dog and visits museums in London."),
        ("fr", "Le petit-déjeuner avec une baguette et de la confiture est très typique en France."),
        ("de", "Der schnelle braune Fuchs springt über den faulen Hund und fährt mit der Bahn."),
        ("es", "El zorro marrón salta sobre el perro y el desayuno incluye pan tostado."),
    ]
    det = create_language_detector()
    for expected, text in samples:
        got = det.detect(text)
        if got != expected:
            _fail(f"ожидался {expected}, получен {got} для фразы …{text[:40]}…")
            return False
    _ok("en / fr / de / es распознаны")
    return True


def check_dvc_metadata() -> bool:
    print("[5] DVC: data/corpus.dvc и remote")
    dvc_file = _REPO_ROOT / "data" / "corpus.dvc"
    if not dvc_file.is_file():
        _fail("нет data/corpus.dvc (запустите scripts\\lab_dvc_push_corpus.bat или: poetry run dvc add data/corpus)")
        return False
    _ok("data/corpus.dvc найден")
    try:
        out = _dvc_run("remote", "list", timeout=30.0)
        if out.returncode != 0:
            _fail(f"dvc remote list: {out.stderr or out.stdout}")
            return False
        if "myremote" not in out.stdout and "datasets" not in out.stdout:
            _fail(f"неожиданный вывод dvc remote list:\n{out.stdout}")
            return False
    except subprocess.TimeoutExpired:
        _fail("таймаут dvc remote list")
        return False
    _ok("dvc remote list выполнен")
    return True


def check_dvc_status() -> bool:
    print("[6] dvc status (версионирование рабочей копии)")
    try:
        out = _dvc_run("status", timeout=60.0)
        if out.returncode != 0:
            _fail(out.stderr or out.stdout or "dvc status")
            return False
        tail = (out.stdout or "").strip()
        if tail:
            print(tail)
        _ok("dvc status выполнен")
        return True
    except subprocess.TimeoutExpired:
        _fail("таймаут dvc status")
        return False


def main() -> int:
    print("=" * 60)
    print("ЛР: корпус для определения языка — проверка (MinIO + DVC + модель)")
    print("=" * 60)

    steps = [
        check_env_file,
        check_minio_s3,
        check_corpus_layout,
        check_language_detector,
        check_dvc_metadata,
        check_dvc_status,
    ]
    for fn in steps:
        if not fn():
            print()
            print("Итог: проверка НЕ пройдена.")
            return 1
        print()

    print("Итог: все проверки пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
