# Мониторинг TaskFlow Performance

```powershell
.\performance\initialize.ps1
docker compose -f monitoring/compose.yaml up -d --wait
docker compose -f monitoring/compose.yaml down
```

Сеть создаётся независимо от контейнеров приложения. Prometheus и Grafana стартуют при выключенном Performance. В Core недоступны Full targets. В Full список Worker строится через DNS, а при остановке всех Worker срабатывает отдельная проверка отсутствия цели. PostgreSQL exporter может отвечать сам и одновременно показывать `pg_up=0`. Включение метрик в Performance управляется `PERF_METRICS_ENABLED`.

Grafana доступна на http://127.0.0.1:3001. Начальные локальные данные для входа — `admin` / `taskflow-local-admin`. Переменные `GRAFANA_ADMIN_USER` и `GRAFANA_ADMIN_PASSWORD` применяются при первой инициализации тома. Datasource `taskflow-prom` и 7 dashboards появятся автоматически в папке TaskFlow Performance.

- **TaskFlow Performance Overview** — целевые сервисы, RPS, HTTP ошибки, P50/P90/P95/P99, in-flight запросы, CPU, память и backlog.
- **Backend HTTP** — HTTP endpoint, status и метод, фильтры сервиса и экземпляра, размеры тел, пул и таймаут.
- **PostgreSQL** — обе БД, подключения, cache hit, блокировки, транзакции, блоковые операции и статистика сканов.
- **Docker Resources** — Docker Compose project и контейнер, CPU, throttling, рабочий набор, сеть, диск и OOM.
- **RabbitMQ** — операции брокера, основная очередь, retry, DLQ, consumers, connections, channels и ресурсные alarms.
- **Notification Service** — consumer outcomes, lag, создание уведомлений, SMTP и pending email.
- **Transactional Outbox** — публикации, broker confirms, retries, ошибки, глубина, возраст и скорость уменьшения backlog.

Панели не подставляют нулевой ряд при отсутствии метрики. Гистограммы суммируют `rate(..._bucket)` по `le` перед расчётом квантиля, ошибки и HTTP throughput считаются по responses. Начальные нули у outcome counters означают запустившийся процесс с нулём наблюдений.

Настройки берутся из `monitoring/.env.example` как справочник. Для изменения скопируйте его в `monitoring/.env` и передайте `docker compose --env-file monitoring/.env -f monitoring/compose.yaml up -d --wait`. Поддерживаются scrape intervals `15s` (по умолчанию) и `5s`. Хранилище Prometheus ограничено `7d` и `2GB` через `PROMETHEUS_RETENTION_TIME` и `PROMETHEUS_RETENTION_SIZE`. Prometheus удаляет старые TSDB блоки по первому достигнутому ограничению; WAL и служебные файлы могут занимать дополнительное место. Grafana и Prometheus имеют отдельные именованные тома.

Роли обоих экспортеров — `perf_monitor` с PostgreSQL `pg_monitor`, без superuser. Метрики SQL-текста выключены. RabbitMQ использует агрегированный plugin endpoint плюс ограниченный `/metrics/detailed` для трёх семейств queue metrics в Performance vhost. Полные метрики всех объектов выключены.

## cAdvisor и Windows

```powershell
docker compose -f monitoring/compose.yaml --profile containers up -d --wait
docker stats --no-stream $(docker ps -q --filter "label=com.docker.compose.project=taskflow-performance")
python performance/scripts/inspect_environment.py
```

Опциональный cAdvisor работает в Linux VM Docker Desktop с привилегиями, host cgroups и монтированием файловой системы VM и `/var/run`, включая Docker socket. Read-only mount ограничивает запись в каталог, но даёт возможность обращаться к Docker daemon через socket. Включайте профиль только в доверенном локальном окружении. Docker API по TCP не публикуется. Prometheus сохраняет контейнерные ряды только для `taskflow-performance`. Доступность семейств зависит от версии Docker Desktop, cgroups и драйвера хранения. Docker stats даёт текущие CPU/RAM, сеть и Block I/O. Скрипт окружения добавляет RestartCount, OOMKilled и лимиты. Накопленные OOM events зависят от источника cAdvisor, а restart counter берётся только через Docker inspect.

## Учебные alerting rules

Состояние правил видно в Prometheus на http://127.0.0.1:19090/alerts. Пороги предварительные. Недоступность scrape/exporter и SQL backlog — 1 мин. HTTP 5xx — более 5% в течение 2 мин, backend P95 — более 500 мс в течение 2 мин, таймаут пула — ненулевой rate в течение минуты. PostgreSQL — более 80% лимита 2 мин. RabbitMQ и Outbox — рост более одной записи в секунду по пятиминутному окну 2 мин. DLQ — наличие сообщений 30 с. Outbox oldest — больше 60 с в течение 2 мин. SMTP lag P95 — выше 30 с в течение 2 мин. Память контейнера — рабочий набор выше 85% лимита в течение 2 мин. В Core optional targets DOWN ожидаемы. Alertmanager не требуется.

См. [справочник метрик](METRICS_REFERENCE.md) и [инструкции Performance](../performance/README.md).
