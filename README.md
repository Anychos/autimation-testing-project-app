# TaskFlow

TaskFlow — учебный менеджер личных задач и полигон для практики QA. Один аккаунт и одни и те же задачи доступны через веб-интерфейс, Android-клиент и REST API. Сервис уведомлений позволяет проверять асинхронное взаимодействие, а отдельное Performance-окружение — измерять поведение приложения под нагрузкой.

## Что есть в приложении

| Компонент | Возможности | Что можно практиковать |
|---|---|---|
| **Веб-приложение** · React, TypeScript, Vite | Регистрация, вход и выход, Dashboard, создание, редактирование и удаление задач. Поиск по заголовку, фильтр по статусу, сортировка, пагинация и счётчики. При подключённом сервисе — панель уведомлений. | Ручные проверки и Playwright. Для форм, задач и уведомлений предусмотрены `data-testid`. |
| **REST API** · FastAPI, SQLAlchemy, PostgreSQL, Alembic | Сессии, CSRF, CRUD задач и OpenAPI. У задачи есть заголовок, описание, статус `todo`, `in_progress` или `done` и необязательный срок. | API-контракты, валидация, доступ к чужим данным, сохранение изменений, поиск и пагинация. |
| **Notification Service** · FastAPI, Worker, PostgreSQL, RabbitMQ, Mailpit | Уведомления о регистрации и действиях с задачами. Счётчик непрочитанных, отметка прочитанности и удаление. Письма о регистрации, создании и завершении задачи. | Проверку событий, дедупликации, retry и DLQ, доставку писем и восстановление после сбоя брокера или SMTP. |
| **Android** · Kotlin, Jetpack Compose | Задачи и уведомления через API, демонстрационный режим без сервера, настройки подключения в debug. | Appium, навигацию, восстановление сессии, пагинацию и потерю сети. |
| **Performance и мониторинг** · Docker Compose, Prometheus, Grafana | Изолированные Core и Full, лимиты LOW / MEDIUM / HIGH, генератор данных, метрики приложения и семь дашбордов. | Load, Stress, Spike, Soak и Volume Testing. Анализ P95/P99, пула подключений, SQL-запросов, очередей и Outbox. |

## Быстрый запуск веб-приложения

Понадобятся Docker Desktop в режиме Linux containers, Docker Compose v2 и PowerShell. Команды выполняются из корня репозитория. Перед первым запуском создайте `.env` и задайте в нём локальный `POSTGRES_PASSWORD`.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Задайте локальный POSTGRES_PASSWORD в .env перед запуском.
docker compose up -d --build --wait
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/health
```

| Интерфейс | Адрес |
|---|---|
| Веб-приложение | [http://127.0.0.1:5173](http://127.0.0.1:5173) |
| Swagger TaskFlow | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| OpenAPI | [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) |

Backend применяет миграции Alembic при старте. `/health` проверяет соединение с PostgreSQL. Веб-интерфейс обращается к `/api/v1` через Vite proxy. Используйте один hostname для всех запросов сессии, поскольку `localhost` и `127.0.0.1` хранят разные cookie. Основная PostgreSQL доступна внутри Compose-сети. Команда `docker compose down` останавливает базовый стек и сохраняет данные в Docker volume.

### Тестовые аккаунты

Зарегистрируйтесь на `/register` и войдите на `/login` либо заполните development-базу учебными аккаунтами.

```powershell
docker compose exec backend python -m app.seed seed
```

| Email | Пароль |
|---|---|
| `user.a@example.com` | `Test12345!` |
| `user.b@example.com` | `Test12345!` |

У каждого аккаунта по пять задач, включая задачу с прошедшим сроком и задачу без срока. Повторный seed добавляет отсутствующие записи без дубликатов. Генерация доступна при `APP_ENV=development`. Прямая загрузка через seed не создаёт бизнес-событий.

Полный сброс **удаляет всех пользователей, задачи и сессии из основной локальной БД**, затем добавляет учебные аккаунты и задачи. База уведомлений, брокер и Mailpit обслуживаются по [инструкции Notification Service](notification-service/README.md#диагностика-и-обслуживание).

```powershell
docker compose exec backend python -m app.seed reset --confirm-local-reset
```

### Первый ручной сценарий

1. Войдите под первым аккаунтом и создайте задачу со сроком. Смените статус, очистите срок и обновите страницу. Проверьте, что изменения сохранились.
2. Проверьте поиск по части заголовка, фильтр по статусу и сортировку. Чтобы увидеть вторую страницу, уменьшите размер страницы или добавьте задачи.
3. Выйдите и войдите под вторым аккаунтом. Задача первого аккаунта должна отсутствовать в списке, а запрос по её UUID — возвращать HTTP 404.

## Запуск с уведомлениями

В этом режиме работают два Compose-проекта. Первый поднимает Notification API, Worker, отдельную PostgreSQL, RabbitMQ и Mailpit. Второй запускает веб-приложение, backend с прокси уведомлений и Outbox Publisher.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Test-Path notification-service/.env)) {
    Copy-Item notification-service/.env.example notification-service/.env
}
```

В обоих файлах задайте локальные пароли соответствующих PostgreSQL. Согласуйте `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`, `RABBITMQ_EXCHANGE`, `RABBITMQ_QUEUE` и `INTERNAL_SERVICE_TOKEN` (от 16 символов). В корневом `.env` установите `NOTIFICATIONS_ENABLED=true`.

```powershell
.\notification-service\scripts\ensure_network.ps1
docker compose --env-file notification-service/.env -f notification-service/compose.yaml up -d --build --wait
docker compose -f compose.yaml -f compose.notifications.yaml up -d --build --wait
```

| Интерфейс | Адрес по умолчанию |
|---|---|
| Notification Swagger | [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs) |
| RabbitMQ Management | [http://127.0.0.1:15672](http://127.0.0.1:15672) |
| Mailpit | [http://127.0.0.1:8025](http://127.0.0.1:8025) |

Зарегистрируйте нового пользователя, войдите и создайте задачу. Проверьте уведомления в Dashboard и письма в Mailpit. Transactional Outbox сохраняет событие в транзакции с бизнес-изменением. Publisher отправляет событие в RabbitMQ, Worker сохраняет уведомление и обрабатывает доставку письма. Это асинхронный процесс, поэтому уведомление может появиться позже HTTP-ответа.

```powershell
docker compose -f compose.yaml -f compose.notifications.yaml down
docker compose --env-file notification-service/.env -f notification-service/compose.yaml down
```

Настройки портов, независимый запуск, примеры событий и сценарии сбоев описаны в [README Notification Service](notification-service/README.md) и [контрактах событий](notification-service/contracts/README.md). При смене паролей на существующих томах синхронизируйте значения в `.env` с учётными записями внутри PostgreSQL и RabbitMQ.

## Android

Откройте `mobile-android/` в Android Studio. Для сборки нужны JDK 17 и SDK из [инструкции Android](mobile-android/README.md#сборка-и-установка). Запустите эмулятор или подключите устройство с USB-отладкой. Команды предполагают, что `adb` доступен в `PATH`.

```powershell
Push-Location mobile-android
.\gradlew.bat assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.taskflow.app/.MainActivity
Pop-Location
```

- **Real mode.** Запустите TaskFlow через базовый Compose. Эмулятор обращается к `http://10.0.2.2:8000/`. Для USB-устройства выполните `adb reverse tcp:8000 tcp:8000` и задайте в **Connection settings** URL `http://127.0.0.1:8000/`. **Allowed authentication origin** должен совпадать со значением из `ALLOWED_ORIGINS` backend.
- **Demo mode.** Включите его в **Connection settings**. Вход — `demo@taskflow.local` / `taskflow-demo`. Данные хранятся в памяти до завершения процесса или переключения в Real mode.
- **Appium.** Пакет `com.taskflow.app`, Activity `com.taskflow.app.MainActivity`. Capabilities см. в [README Android](mobile-android/README.md#appium), идентификаторы элементов — в [TEST_LOCATORS.md](mobile-android/TEST_LOCATORS.md).

## Performance и мониторинг

Для нагрузочных экспериментов используется отдельный Compose-проект `taskflow-performance` с собственными портами, сетью и томами. **Core** запускает API и PostgreSQL. **Full** добавляет Notification API, Worker, отдельную БД уведомлений, Outbox Publisher, RabbitMQ и Mailpit.

Запуск **Core / MEDIUM** и независимого стека мониторинга:

```powershell
.\performance\initialize.ps1
$Perf = @('--env-file', 'performance/.env.example', '-f', 'performance/compose.yaml')
$Medium = @('-f', 'performance/profiles/medium.yaml')
docker compose @Perf @Medium up -d --build --wait
docker compose -f monitoring/compose.yaml up -d --wait
```

Запуск **Full / MEDIUM** с теми же переменными PowerShell:

```powershell
$Full = @('-f', 'performance/full.yaml', '--profile', 'full')
docker compose @Perf @Full @Medium up -d --build --wait
```

| Интерфейс | Адрес |
|---|---|
| Performance Swagger | [http://127.0.0.1:8100/docs](http://127.0.0.1:8100/docs) |
| Full Notification Swagger | [http://127.0.0.1:8101/docs](http://127.0.0.1:8101/docs) |
| Full RabbitMQ Management | [http://127.0.0.1:25672](http://127.0.0.1:25672) |
| Full Mailpit | [http://127.0.0.1:8026](http://127.0.0.1:8026) |
| Prometheus | [http://127.0.0.1:19090](http://127.0.0.1:19090) |
| Grafana | [http://127.0.0.1:3001](http://127.0.0.1:3001) |

Grafana автоматически получает datasource и семь дашбордов. Начальные локальные данные для входа — `admin` / `taskflow-local-admin`. Для метрик контейнеров запустите мониторинг с профилем `containers`.

```powershell
docker compose @Perf exec -T backend python /performance/scripts/seed_test_data.py --dataset smoke --mode db
```

Smoke-набор содержит 5 пользователей и 100 задач. **DB mode** подходит для массового наполнения и диагностики SQL. **API mode** проходит через регистрацию и REST API, поэтому в Full создаёт события. Скрипты экспортируют тестовые учётные данные, сохраняют параметры эксперимента и очищают отдельные наборы.

Профили, переключение режимов, остановка и сценарии экспериментов описаны в [Performance README](performance/README.md). Метрики и проверку стека см. в [руководстве по мониторингу](monitoring/README.md), [справочнике метрик](monitoring/METRICS_REFERENCE.md) и [отчёте о проверках](performance/VERIFICATION.md).

## Как работать с REST API

Все бизнес-маршруты начинаются с `/api/v1`. Откройте [Swagger](http://127.0.0.1:8000/docs) или используйте клиент с поддержкой cookie.

| Группа | Маршруты |
|---|---|
| Авторизация | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `GET /auth/csrf`, `POST /auth/logout` |
| Задачи | `GET /tasks`, `POST /tasks`, `GET /tasks/{id}`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}` |
| Уведомления | `GET /notifications`, `GET /notifications/unread-count`, действия с отдельными уведомлениями и `POST /notifications/read-all` |

1. Для регистрации и входа нужен разрешённый `Origin`, например `http://127.0.0.1:8000`. В Postman и curl укажите его явно.
2. После входа сохраните `taskflow_session`. Браузер отправляет HttpOnly-cookie автоматически, для внешнего клиента нужен cookie jar.
3. Получите `csrf_token` из `GET /api/v1/auth/csrf`. Передавайте его в `X-CSRF-Token` при изменении задач, уведомлений и выходе. В Swagger используйте **Authorize → APIKeyHeader**.

Список задач принимает `q`, `status`, `sort=created_desc|created_asc|due_date_asc`, `page` и `limit` (1–50, по умолчанию 10). Поиск ищет буквальную подстроку в заголовке. Для очистки срока в PATCH отправьте `"due_date": null`. Чужая задача возвращает 404. Счётчики Dashboard учитывают все задачи аккаунта независимо от текущего фильтра.

Пример входа и создания задачи в PowerShell после запуска seed:

```powershell
$Api = 'http://127.0.0.1:8000/api/v1'
$Login = @{ email = 'user.a@example.com'; password = 'Test12345!' } | ConvertTo-Json
Invoke-RestMethod "$Api/auth/login" -Method Post -ContentType 'application/json' -Body $Login `
    -Headers @{ Origin = 'http://127.0.0.1:8000' } -SessionVariable TaskFlowSession
$Csrf = (Invoke-RestMethod "$Api/auth/csrf" -WebSession $TaskFlowSession).csrf_token
$Task = @{ title = 'Проверить создание задачи'; status = 'todo' } | ConvertTo-Json
Invoke-RestMethod "$Api/tasks" -Method Post -WebSession $TaskFlowSession `
    -Headers @{ 'X-CSRF-Token' = $Csrf } -ContentType 'application/json; charset=utf-8' -Body $Task
```

## Структура и диагностика

| Путь | Содержимое |
|---|---|
| `backend/` | FastAPI, SQLAlchemy, Alembic, CLI seed/reset, Outbox Publisher |
| `frontend/` | Веб-интерфейс React и прокси Vite |
| `notification-service/` | Notification API и Worker, миграции, контракты и тесты |
| `mobile-android/` | Android-клиент, Gradle Wrapper, JVM-тесты и локаторы Appium |
| `performance/` | Изолированный Compose, профили, datasets и диагностический SQL |
| `monitoring/` | Prometheus, Grafana, PostgreSQL exporters и cAdvisor |
| `compose.yaml`, `compose.notifications.yaml` | Базовый стек и подключение уведомлений |

```powershell
docker compose logs --tail 100 backend frontend
docker compose exec backend alembic current
docker compose exec frontend npm run build
```

В корневом `.env.example` описаны параметры основной БД, время жизни сессии и допустимые Origin. У Notification Service, Performance и мониторинга свои файлы-примеры. Локальные `.env` и `performance/artifacts/` исключены из Git. API/UI-автотесты основного приложения находятся в отдельном проекте `practice`. Тесты Notification Service и Android входят в этот репозиторий.
