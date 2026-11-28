# Проверка TaskFlow Performance

Проверка выполнена 28 ноября 2026 года на Windows, PowerShell и Docker Desktop с Linux Engine 29.5.3, WSL2 и cgroups v2. Compose использовал loopback-порты и отдельные базы, тома и сеть. Development-контейнеры оставались запущенными. Проверялись Docker Compose, реальные HTTP/SQL-запросы, Prometheus и Grafana, а также существующие тесты.

| Проверка | Фактический результат |
|---|---|
| Core и Full | Core стартовал с backend, PostgreSQL и одноразовыми миграциями. Full поднял Notification API, Worker, отдельную PostgreSQL, RabbitMQ, Outbox и Mailpit. |
| Изоляция | Сопоставлены результаты Compose config, сети и контейнеры. В `taskflow-performance-observe` присутствовали только контейнеры Performance и мониторинга. Development использует собственные порты и ресурсы. |
| LOW, MEDIUM, HIGH | Все три запустились. Docker inspect подтвердил CPU/RAM; HIGH backend получил 4 CPU и 2 GiB. HIGH стартовал с 2 backend workers и 3 Notification Worker. |
| HTTP и Connection Pool | Серия из 20 запросов с разными UUID дала +20 в counter и +20 в histogram count под одним `/api/v1/tasks/{id}`. Значения UUID отсутствовали в labels. Postgres pool capacity составила 15 с одним и 30 с двумя процессами. Принудительное завершение worker заменило процесс и восстановило capacity до 30, сохранив ранее накопленные HTTP counters. После перезапуска master первый 404-счётчик начинался с 0. |
| PostgreSQL | Оба экспортера отдали `pg_up=1`. `perf_monitor` состоит в `pg_monitor`, superuser отключён. `pg_stat_statements` установлен. Все 13 SQL-файлов выполнились с `ON_ERROR_STOP=1`, включая EXPLAIN для задач. |
| RabbitMQ и фоновые процессы | Prometheus наблюдал очереди основной, retry и DLQ, а также три отдельных Worker targets в HIGH. Дополнительный API smoke из 2 пользователей и 6 задач дал 8 полученных и обработанных событий, 8 broker confirmations и 8 принятых SMTP-писем. |
| Данные и очистка | DB и API smoke создали по 5 пользователей и 100 задач. Пользователь из DB mode авторизовался по настоящему API. Dry-run обнаружил у API-набора 105 Outbox событий, 105 уведомлений, 210 delivery rows и 105 писем. После Full cleanup Mailpit показал 0 писем, соседний DB dataset сохранился. Проверены JSON/CSV credentials и экспорт окружения. |
| Prometheus и Grafana | `promtool` принял конфигурацию и 15 правил. Проверены 5 с и 15 с. Grafana API обнаружил datasource и 7 dashboards. Через datasource получен backend P95 0,00475 с за двухминутное окно после smoke-запросов. Это квантиль по buckets, а не измерение отдельных запросов. Выражения всех панелей выполнились через Prometheus; две панели HTTP оставались без рядов (5xx и необработанные исключения). |
| cAdvisor | Получены ряды CPU, quota, throttling, memory usage/working set/limit, сеть, файловый I/O, last seen и OOM counter на этой установке Docker Desktop. OOM намеренно не провоцировался. Docker stats и Docker inspect проверены отдельно. |
| Опциональность | При отключённой инструментализации backend вернул 404 на `/metrics`. После остановки стека мониторинга API продолжил отвечать на `/health`. Во время остановки всего Performance Prometheus показывал backend DOWN, а Prometheus и Grafana проходили healthchecks. После перехода в Core backend вернулся в UP. |
| Существующие тесты | Notification Service: 17 passed. В отдельном `practice`: 24 passed, 3 UI setup errors с `AttributeError: Page.form_box`. Та же ошибка и тот же итог воспроизвелись с предыдущим backend image в отдельном Compose-проекте. |

В Chromium открыта панель Overview и подтверждён рендер графика P95. В LOW healthcheck прошёл с двумя SMTP threads и отдельными heartbeat-файлами. Dry-run xlarge рассчитал 1 000 000 задач. Попытка запуска xlarge без `--allow-large` и удаление данных из контейнера с development-настройками завершились до записи. Smoke-данные удалены. Полигон оставлен запущенным в Full MEDIUM с мониторингом.

## Короткое сравнение накладных расходов

Один и тот же HIGH с двумя backend workers. Windows-клиент сделал по 12 прогревочных и 50 последовательных запросов `GET /api/v1/tasks` без cookie (401) на каждую конфигурацию.

| Метрики | Медиана | P95 клиента |
|---|---:|---:|
| Включены, серия 1 | 1,876 мс | 24,984 мс |
| Выключены | 2,242 мс | 20,404 мс |
| Включены, серия 2 | 1,855 мс | 19,678 мс |

Замеры включают HTTP-клиент, Windows loopback, Docker Desktop и обработку 401. Разброс на короткой серии не позволяет отделить цену инструментализации. Для сравнения под прикладной нагрузкой берите повторные серии с одним и тем же dataset, профилем и окном scrape.

## Файлы

**Добавлены**

- `.gitattributes` закрепляет LF для shell-скриптов Docker.
- `backend/app/` → `gunicorn_metrics.py`, `http_metrics.py`, `outbox_metrics.py`, `pool_metrics.py`.
- `notification-service/src/notification_service/` → `backlog_metrics.py`, `http_metrics.py`, `worker_metrics.py`.
- `performance/` → `.env.example`, `compose.yaml`, `full.yaml`, `initialize.ps1`, `start-backend.sh`, `postgres-init.sh`, `rabbitmq-plugins`, `cleanup.ps1`, `README.md`, `VERIFICATION.md`.
- `performance/profiles/` → `low.yaml`, `medium.yaml`, `high.yaml`.
- `performance/scripts/` → `dataset_store.py`, `seed_test_data.py`, `cleanup_test_data.py`, `inspect_environment.py`, `export_environment.py`. Пресеты лежат в `performance/datasets/presets.json`.
- `performance/sql/` → `active_connections.sql`, `blocking_queries.sql`, `cache_hit_ratio.sql`, `connection_usage.sql`, `database_locks.sql`, `database_size.sql`, `explain_tasks.sql`, `index_usage.sql`, `io_statistics.sql`, `long_running_transactions.sql`, `table_statistics.sql`, `top_slow_queries.sql`, `top_total_execution_time.sql`.
- `monitoring/` → `.env.example`, `compose.yaml`, `README.md`, `METRICS_REFERENCE.md`, `prometheus/prometheus.yml`, `prometheus/rules/taskflow.yml`.
- `monitoring/grafana/` → `provisioning/dashboards/taskflow.yaml`, `provisioning/datasources/prometheus.yaml`, `dashboards/docker.json`, `dashboards/http.json`, `dashboards/notifications.json`, `dashboards/outbox.json`, `dashboards/overview.json`, `dashboards/postgres.json`, `dashboards/rabbit.json`.

**Изменены**

- Корень → `.env.example`, `.gitignore`, `README.md`, `compose.yaml`.
- Backend → `requirements.txt`, `app/config.py`, `app/database.py`, `app/main.py`, `app/notification_proxy.py`, `app/outbox_publisher.py`.
- Notification Service → `pyproject.toml`, `requirements.lock`, `src/notification_service/settings.py`, `main.py`, `worker.py`, `email_delivery.py`, `health.py` в том же модуле.

## Границы проверки

Проверен короткий smoke. Заполнение xlarge и нагрузочные, soak и capacity-прогоны оставлены для самостоятельных экспериментов. В React Dashboard счётчики читаются из `pagination.total` нескольких запросов `/tasks`. Диагностический SQL повторяет эти запросы. Отдельного production dashboard endpoint для статистики нет. Grafana проверена через её API и datasource. SMTP acceptance означает ответ SMTP-сервера о принятии письма. OOM и счётчики рестартов имеют разные источники. Результат автоматизации UI блокируется существующим setup-багом для трёх тестов.

[Запуск, профили, данные и последовательность экспериментов](README.md) · [Мониторинг и интерфейсы](../monitoring/README.md) · [Метрики и их интерпретация](../monitoring/METRICS_REFERENCE.md)
