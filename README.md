# TaskFlow

Локальный учебный менеджер личных задач для практики API- и UI-автоматизации. Python 3.12, FastAPI, PostgreSQL,
SQLAlchemy 2, Alembic; React + TypeScript + Vite. QA-автотестов в проекте нет.

## Запуск

Для запуска понадобятся Docker и Docker Compose. Скопируйте `.env.example` в `.env`
и задайте локальный `POSTGRES_PASSWORD`.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Миграции применяются backend автоматически перед запуском Uvicorn.
Swagger: http://localhost:8000/docs. Проверка БД: http://localhost:8000/health.

```powershell
curl.exe http://localhost:8000/health
docker compose exec backend alembic current
docker compose logs backend
docker compose down
```

`down` сохраняет данные в Docker volume. Пароли и локальный `.env` исключены из Git.

## Интерфейс и данные

Frontend: http://localhost:5173. Страницы: `/login`, `/register`, `/tasks`.
Frontend обращается к `/api/v1` через Vite proxy; cookie остаётся на том же origin.
Можно открывать приложение через `localhost` или `127.0.0.1`: оба Origin
разрешены по умолчанию. Это разные cookie hosts, поэтому вход выполняется
отдельно для каждого адреса. Используйте один адрес в рамках работы с сессией.

```powershell
docker compose exec backend python -m app.seed seed
```

| Пользователь | Email | Пароль |
|---|---|---|
| User A | user.a@test.local | Test12345! |
| User B | user.b@test.local | Test12345! |

У каждого по 5 задач, включая прошлую дату и задачу без даты.
Seed добавляет отсутствующих пользователей и задачи с постоянными UUID, не меняет
существующие записи и не создаёт дубликаты. Удалённые seed-задачи восстанавливаются.
Даты seed фиксированные, результат не зависит от дня запуска.

Полный сброс **всех** пользователей, задач и сессий этой локальной БД:

```powershell
docker compose exec backend python -m app.seed reset --confirm-local-reset
```

Обе команды разрешены только при `APP_ENV=development`. Reset выполняет очистку
и заполнение в одной транзакции; миграции сохраняются. HTTP API для сброса нет.

## Ручная проверка

1. Зарегистрируйтесь на `/register`, затем войдите на `/login`. Регистрация сама не авторизует.
2. Создайте задачу, отредактируйте её, очистите дату, смените статус, обновите страницу.
3. Проверьте поиск, фильтр, три сортировки, размер страницы и кнопки пагинации.
   Счётчики Total / In Progress / Completed отражают все задачи пользователя независимо от фильтров.
4. Удалите задачу через Confirm; Cancel должен сохранить запись.
5. Войдите другим пользователем: его список отделён от первого. Чужой UUID через API возвращает 404.
6. Нажмите Logout. Повторный запрос со старым cookie должен вернуть 401.
7. На ширине 375 px проверьте формы, фильтры, модальные окна и пагинацию.

### API и Swagger

Все пути задач: `/api/v1/tasks` и `/api/v1/tasks/{id}`.
Поддерживаются POST, GET списка/задачи, PATCH и DELETE; PUT отсутствует.
GET списка: `status`, `q`, `sort=created_desc|created_asc|due_date_asc`,
`page>=1`, `limit=1..50` (по умолчанию 10). Поиск — буквальная подстрока,
символы `%` и `_` не являются wildcards. При равенстве сортировка по UUID по возрастанию;
даты null в конце. Страница за пределами списка возвращает пустые items, pages=0 для пустой выборки.

В Swagger сначала выполните `/auth/register` или `/auth/login`.
Origin браузера `http://localhost:8000` разрешён по умолчанию.
Для curl/httpx/Postman отправляйте `Origin: http://localhost:8000` явно
при регистрации/входе: отсутствие Origin также даёт 403.
Cookie `taskflow_session` браузер отправляет автоматически; HttpOnly cookie
нельзя вручную установить из Swagger Authorize. Во внешнем клиенте используйте cookie jar.
Получите `csrf_token` через `/auth/csrf`, вставьте его в **Authorize → APIKeyHeader**.
Он нужен для POST задач, PATCH, DELETE и logout. После нового входа получите новый токен.
Если вы вошли через frontend на localhost, cookie доступен и Swagger на localhost:8000.

Пример регистрации в PowerShell:

```powershell
$body = @{email='new@test.local'; password='Test12345!'} | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/auth/register -Method Post `
  -Headers @{Origin='http://localhost:8000'} -ContentType application/json -Body $body
```

Ошибки имеют вид `{"error":{"code":"...","message":"...","details":[]}}`.
422 содержит loc/msg/type для полей; исходный пароль не включается в ответ.
Неизменяемые и неизвестные поля запрещены. Пустой PATCH запрещён;
null допустим только для due_date. Description по умолчанию — пустая строка.
Требования к title применяются после trim, описание не обрезается.
Проверка email синтаксическая, без DNS; `.local` поддержан для учебных данных.

## Конфигурация и устройство

Backend: `backend/app/` — конфигурация, ORM-модели, схемы Pydantic,
security, auth/tasks роутеры, общие обработчики ошибок и CLI seed/reset.
Миграции: `backend/migrations/`. Frontend: `frontend/src/`.
Пароли хешируются Argon2, случайные сессионные токены хранятся в БД в виде SHA-256,
CSRF привязан к серверной сессии. В браузере токены не записываются в localStorage.
Сессии живут `SESSION_HOURS` (по умолчанию 24 часа); истёкшие сессии удаляются при входе.
Cookie: HttpOnly, SameSite=Lax, Path=/; для HTTPS задайте `COOKIE_SECURE=true`.
`ALLOWED_ORIGINS` — список точных origin через запятую.
Порты приложений доступны только через loopback, PostgreSQL наружу не публикуется.
Реальные пароли БД задавайте только в `.env`. При изменении пароля существующего
PostgreSQL volume пароль в самой БД автоматически не изменяется.

```powershell
docker compose exec backend alembic current
docker compose exec backend alembic check
docker compose exec frontend npm run build
docker compose logs --tail 100 backend frontend
```

`/health` проверяет реальное соединение с PostgreSQL. При остановке backend
соединения пула закрываются. Сервер пишет технические исключения в логи,
клиент получает нейтральную ошибку 500 без stack trace.

Для разработки frontend вне Docker: Node.js 22.12+, `cd frontend`, `npm ci`, `npm run dev`.
Vite по умолчанию проксирует на localhost:8000; внутри Docker использует `API_PROXY_TARGET`.
Для backend нужен Python 3.12+ и PostgreSQL: установите `backend/requirements.txt`,
экспортируйте переменные из `.env`, задайте `DB_HOST`, выполните из `backend/`
`alembic upgrade head`, затем `uvicorn app.main:app --reload`.

Проект намеренно не содержит pytest/Playwright-тестов и тестового фреймворка.

## Проверки реализации (17.11.2026)

Docker Compose: все три сервиса healthy. TypeScript и production-сборка Vite
успешны; `alembic current` — `0001`, `alembic check` не находит расхождений.
Живыми HTTP-запросами проверены регистрация, вход, CRUD задач, поиск, пагинация,
очистка даты, изоляция пользователей, Origin/CSRF, недопустимые поля,
повторный email, logout и повторная отправка старого cookie.
Сессия и задачи сохраняются при перезапуске backend. Повторный seed оставляет
по 5 задач; reset в production отклонён.
В Chrome визуально проверены регистрация и список задач при viewport 375 px,
вход и список задач на desktop; на мобильных страницах нет горизонтального переполнения.
Полный сценарий взаимодействия с UI кликами остаётся для ручной проверки по списку выше.
