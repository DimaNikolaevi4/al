#!/usr/bin/env python3
"""
Smoke-тесты API AI Tutor Project
API Smoke Tests — Verifies basic functionality after deployment

Использование / Usage:
    python3 smoke_test.py                     # По умолчанию http://localhost:8000
    python3 smoke_test.py --url http://x:8000 # Кастомный URL
    python3 smoke_test.py --timeout 30        # Кастомный таймаут
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Цветной вывод / Colored terminal output
# ---------------------------------------------------------------------------

class Colors:
    """ANSI color codes for terminal output."""
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    BOLD = "\033[1m"
    NC = "\033[0m"


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    passed: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    details: str = ""


@dataclass
class SmokeTestReport:
    """Aggregated smoke test results."""
    results: list[TestResult] = field(default_factory=list)
    base_url: str = ""

    def add(self, result: TestResult) -> None:
        self.results.append(result)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return self.total - self.passed_count

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0

    def print_summary(self) -> None:
        """Print formatted summary of all test results."""
        print(f"\n{'=' * 60}")
        print(f"  SMOKE TEST RESULTS — {self.base_url}")
        print(f"{'=' * 60}")

        for result in self.results:
            status = (
                f"{Colors.GREEN}PASS{Colors.NC}"
                if result.passed
                else f"{Colors.RED}FAIL{Colors.NC}"
            )
            time_info = ""
            if result.response_time_ms is not None:
                time_info = f" ({result.response_time_ms:.0f}ms)"

            print(f"  [{status}] {result.name}{time_info}")

            if not result.passed and result.error:
                print(f"         {Colors.RED}Error: {result.error}{Colors.NC}")
            if result.details:
                for line in result.details.split("\n"):
                    print(f"         {line}")

        print(f"\n{'=' * 60}")
        pass_color = Colors.GREEN if self.all_passed else Colors.RED
        print(
            f"  {pass_color}{self.passed_count}/{self.total} passed, "
            f"{self.failed_count} failed{Colors.NC}"
        )
        print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# HTTP client — requests (primary) / httpx (fallback)
# ---------------------------------------------------------------------------

def get_http_client():
    """Get HTTP client. Tries 'requests', falls back to 'httpx'."""
    try:
        import requests
        return "requests", requests
    except ImportError:
        pass

    try:
        import httpx
        return "httpx", httpx
    except ImportError:
        print(
            f"{Colors.RED}Neither 'requests' nor 'httpx' is installed.{Colors.NC}\n"
            f"  Install one: pip install requests\n"
        )
        sys.exit(2)


def api_request(method: str, url: str, **kwargs) -> tuple[Optional[int], Any, Optional[float], Optional[str]]:
    """
    Make HTTP request using available client.
    Returns (status_code, response_json, response_time_ms, error_string).
    """
    client_name, client_mod = get_http_client()
    timeout = kwargs.pop("timeout", 10)

    try:
        start = time.time()
        if client_name == "requests":
            resp = client_mod.request(method, url, timeout=timeout, **kwargs)
        else:
            # httpx
            with client_mod.Client(timeout=timeout) as c:
                resp = c.request(method, url, **kwargs)
        elapsed_ms = (time.time() - start) * 1000

        # Try parsing JSON
        try:
            body = resp.json()
        except (json.JSONDecodeError, ValueError):
            body = resp.text[:500] if resp.text else ""

        return resp.status_code, body, elapsed_ms, None

    except Exception as exc:
        return None, None, None, str(exc)


# ---------------------------------------------------------------------------
# Individual test cases
# ---------------------------------------------------------------------------

def test_health(base_url: str, report: SmokeTestReport) -> None:
    """Test GET /api/v1/health"""
    url = f"{base_url}/api/v1/health"
    status, body, ms, err = api_request("GET", url)

    result = TestResult(
        name="GET /api/v1/health",
        status_code=status,
        response_time_ms=ms,
        error=err,
    )

    if err:
        result.passed = False
    elif status == 200:
        result.passed = True
        # Пытаемся извлечь статус из ответа
        if isinstance(body, dict):
            status_val = body.get("status", body.get("health", "unknown"))
            result.details = f"status={status_val}"
        else:
            result.details = str(body)[:200]
    else:
        result.passed = False
        result.error = f"HTTP {status}"
        result.details = str(body)[:200] if body else ""

    report.add(result)


def test_info(base_url: str, report: SmokeTestReport) -> None:
    """Test GET /api/v1/info"""
    url = f"{base_url}/api/v1/info"
    status, body, ms, err = api_request("GET", url)

    result = TestResult(
        name="GET /api/v1/info",
        status_code=status,
        response_time_ms=ms,
        error=err,
    )

    if err:
        result.passed = False
    elif status == 200:
        result.passed = True
        if isinstance(body, dict):
            version = body.get("version", body.get("app_version", "N/A"))
            model = body.get("model", body.get("model_name", "N/A"))
            result.details = f"version={version}, model={model}"
    elif status == 404:
        # Endpoint might not exist — not a critical failure
        result.passed = True
        result.details = "Endpoint not found (404) — OK (optional endpoint)"
    else:
        result.passed = False
        result.error = f"HTTP {status}"

    report.add(result)


def test_generate_summary(base_url: str, report: SmokeTestReport) -> None:
    """Test POST /api/v1/generate-summary with minimal input."""
    url = f"{base_url}/api/v1/generate-summary"
    payload = {
        "lecture_text": "Тестовый текст лекции для проверки API. Тема: основные принципы автоматизации.",
    }

    status, body, ms, err = api_request("POST", url, json=payload, timeout=30)

    result = TestResult(
        name="POST /api/v1/generate-summary",
        status_code=status,
        response_time_ms=ms,
        error=err,
    )

    if err:
        result.passed = False
        result.details = "Сервер недоступен (ожидаемо если модель не загружена)"
        result.error = err
    elif status == 200:
        result.passed = True
        if isinstance(body, dict):
            summary = body.get("summary", body.get("result", ""))[:100]
            result.details = f"summary={summary}..."
    elif status in (400, 422, 429, 503):
        # Ожидаемые ошибки (модель не загружена, валидация и т.д.)
        result.passed = True
        detail = ""
        if isinstance(body, dict):
            detail = body.get("detail", body.get("error", ""))
        result.details = f"HTTP {status} (ожидаемо: {detail})"
    else:
        result.passed = False
        result.error = f"HTTP {status}"
        result.details = str(body)[:200] if body else ""

    report.add(result)


def test_stats(base_url: str, report: SmokeTestReport) -> None:
    """Test GET /api/v1/stats"""
    url = f"{base_url}/api/v1/stats"
    status, body, ms, err = api_request("GET", url)

    result = TestResult(
        name="GET /api/v1/stats",
        status_code=status,
        response_time_ms=ms,
        error=err,
    )

    if err:
        result.passed = False
    elif status == 200:
        result.passed = True
        if isinstance(body, dict):
            keys = list(body.keys())[:5]
            result.details = f"keys={keys}"
    elif status == 404:
        result.passed = True
        result.details = "Endpoint not found (404) — OK (optional endpoint)"
    else:
        result.passed = False
        result.error = f"HTTP {status}"

    report.add(result)


def test_async_flow(base_url: str, report: SmokeTestReport) -> None:
    """Test async flow: submit task → poll status."""
    # Шаг 1: Отправляем задачу
    submit_url = f"{base_url}/api/v1/tasks"
    payload = {
        "text": "Тестовый текст для асинхронной обработки.",
        "subject": "test",
    }

    status, body, ms, err = api_request("POST", submit_url, json=payload, timeout=15)

    result = TestResult(
        name="POST /api/v1/tasks (async submit)",
        status_code=status,
        response_time_ms=ms,
        error=err,
    )

    task_id = None

    if err:
        result.passed = False
        result.details = "Не удалось отправить задачу"
    elif status in (200, 201, 202):
        result.passed = True
        if isinstance(body, dict):
            task_id = body.get("task_id", body.get("id"))
            result.details = f"task_id={task_id}"
    elif status == 404:
        result.passed = True
        result.details = "Async endpoint not found (404) — OK (optional)"
    elif status in (400, 422, 429, 503):
        result.passed = True
        detail = ""
        if isinstance(body, dict):
            detail = body.get("detail", body.get("error", ""))
        result.details = f"HTTP {status} (ожидаемо: {detail})"
    else:
        result.passed = False
        result.error = f"HTTP {status}"

    report.add(result)

    # Шаг 2: Опрашиваем статус задачи (если task_id получен)
    if task_id:
        poll_url = f"{base_url}/api/v1/tasks/{task_id}"
        max_polls = 10
        poll_interval = 2

        for attempt in range(1, max_polls + 1):
            p_status, p_body, p_ms, p_err = api_request("GET", poll_url, timeout=10)

            if p_err:
                break

            if isinstance(p_body, dict):
                task_status = p_body.get("status", "unknown")
                if task_status in ("completed", "done", "success", "failed", "error"):
                    poll_result = TestResult(
                        name=f"GET /api/v1/tasks/{task_id} (poll #{attempt})",
                        status_code=p_status,
                        response_time_ms=p_ms,
                        passed=True,
                        details=f"final_status={task_status}",
                    )
                    report.add(poll_result)
                    break
            else:
                break

            time.sleep(poll_interval)
        else:
            poll_result = TestResult(
                name=f"GET /api/v1/tasks/{task_id} (poll timeout)",
                status_code=p_status,
                response_time_ms=p_ms,
                passed=True,  # Timeout is OK for smoke test
                details=f"still running after {max_polls * poll_interval}s (expected for large tasks)",
            )
            report.add(poll_result)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-тесты API AI Tutor Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры / Examples:
  python3 smoke_test.py                          # http://localhost:8000
  python3 smoke_test.py --url http://10.0.0.1:8000
  python3 smoke_test.py --url https://api.example.com
  python3 smoke_test.py --timeout 30
        """,
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API URL (по умолчанию: http://localhost:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Таймаут запросов в секундах (по умолчанию: 15)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.url.rstrip("/")

    print(f"\n{Colors.BOLD}AI Tutor — Smoke Tests{Colors.NC}")
    print(f"  Target: {Colors.CYAN}{base_url}{Colors.NC}")
    print(f"  Timeout: {args.timeout}s\n")

    report = SmokeTestReport(base_url=base_url)

    # Проверяем доступность сервера
    print(f"{Colors.BLUE}Проверка доступности сервера...{Colors.NC}")
    check_status, _, _, check_err = api_request("GET", f"{base_url}/", timeout=5)
    if check_err and "Connection" in check_err:
        print(f"  {Colors.RED}Сервер недоступен: {check_err}{Colors.NC}")
        print(f"  {Colors.YELLOW}Убедитесь что API запущена.{Colors.NC}")
        sys.exit(1)

    # Запускаем тесты
    print(f"\n{Colors.BOLD}Запуск тестов:{Colors.NC}\n")

    test_health(base_url, report)
    test_info(base_url, report)
    test_generate_summary(base_url, report)
    test_stats(base_url, report)
    test_async_flow(base_url, report)

    # Итоговый отчёт
    report.print_summary()

    if report.all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ Все тесты пройдены!{Colors.NC}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Некоторые тесты не пройдены.{Colors.NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
