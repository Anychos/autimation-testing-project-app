# TaskFlow Android

Нативный клиент TaskFlow для Android 8.0+ и практики мобильной автоматизации. Экраны написаны на Kotlin, Jetpack Compose и Material 3. Интерфейс на английском.

## Сборка и установка

Понадобятся Android Studio Narwhal 3 Feature Drop (2025.1.3) или новее, JDK 17, Android SDK Platform 36.1, Build-Tools 36.0.0 и Platform-Tools. Для эмулятора установите Android Emulator и образ Android 35, например AOSP x86_64 на Windows x64. Gradle Wrapper загрузит Gradle 8.13, а первая сборка также загрузит зависимости.

[Совместимость Android Studio и Android Gradle Plugin](https://developer.android.com/build/releases/about-agp)

1. В Android Studio выберите **File → Open** и откройте папку `mobile-android`. При первом открытии IDE может показать **Trust Project**. После подтверждения дождитесь Gradle Sync. При необходимости укажите SDK и JDK 17 в настройках Gradle.
2. В **Tools → Device Manager → Create virtual device** выберите Pixel 6, образ API 35 и запустите AVD. Убедитесь, что устройство появилось в `adb devices`.
3. Выполните следующие команды в PowerShell из корня TaskFlow.

```powershell
Set-Location .\mobile-android
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:JAVA_HOME = 'C:\Program Files\Microsoft\jdk-17.0.20.8-hotspot' # Укажите путь своего JDK 17
$env:Path = "$env:ANDROID_HOME\platform-tools;$env:Path"

.\gradlew.bat assembleDebug
adb devices
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.taskflow.app/.MainActivity
```

При нескольких устройствах добавьте к командам `adb -s <serial>`. В Linux для сборки выполните `./gradlew assembleDebug` или `sh ./gradlew assembleDebug`. Для сборки сервер запускать не требуется.

## Real mode

Режим по умолчанию. Запустите существующий TaskFlow из корня основного проекта.

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

На эмуляторе откройте TaskFlow. Приложение по умолчанию обращается к `http://10.0.2.2:8000/`. Зарегистрируйте тестового пользователя или войдите под существующим. На экране входа и Dashboard шестерёнка **Connection settings** открывает настройки debug. Выключите **Demo mode**, если он активен, задайте **API base URL** и **Allowed authentication origin**, затем нажмите **Save**. Origin должен в точности совпадать с одним из значений `ALLOWED_ORIGINS` на сервере. По умолчанию используется `http://localhost:5173`. Это значение HTTP-заголовка, фактические сетевые запросы отправляются на API base URL.

В текущем Compose порт 8000 опубликован на loopback компьютера. Для физического устройства с USB-отладкой выполните `adb reverse tcp:8000 tcp:8000` и задайте Base URL `http://127.0.0.1:8000/` в приложении. Если у вашего API уже есть сетевой адрес, используйте его. Для HTTPS-сервера нужен сертификат, которому доверяет Android.

Интеграция уведомлений включается существующим Compose overlay. Публикацию событий о задачах выполняет `outbox-publisher`. Клиент использует тот же Base URL, что и для задач. Если интеграция выключена или прокси получает ошибку от Notification Service, экран уведомлений показывает ошибку с возможностью повторить загрузку. Dashboard продолжает загружать задачи. Порядок запуска сервисов и настройки интеграции приведены в [README Notification Service](../notification-service/README.md).

## Demo mode

Откройте **Connection settings**, включите **Demo mode** и сохраните. Войдите под `demo@taskflow.local` с паролем `taskflow-demo` или зарегистрируйте демонстрационного пользователя. Баннер **Demo mode** отображается на каждом экране. Данные и авторизация Demo живут в памяти приложения и сбрасываются при завершении процесса либо при переключении в Real mode. Сам режим сохранится после перезапуска. Переключение режима или настроек подключения завершает локальную сессию. Сетевая ошибка в Real mode сохраняет Real mode.

## REST API

Все маршруты ниже начинаются с `/api/v1`. Полная серверная схема доступна по `http://localhost:8000/openapi.json`, Swagger UI по `http://localhost:8000/docs`.

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/auth/register`, `/auth/login` | Регистрация и вход по email и паролю |
| GET | `/auth/me`, `/auth/csrf` | Проверка сохранённой сессии и получение CSRF-токена |
| POST | `/auth/logout` | Удаление сессии на сервере |
| GET | `/tasks` | Список с `q`, `status`, `sort`, `page` и `limit` |
| POST | `/tasks` | Создание задачи |
| GET, PATCH, DELETE | `/tasks/{id}` | Просмотр, изменение и удаление задачи |
| GET | `/notifications` | Список уведомлений с `page` |
| GET | `/notifications/unread-count` | Число непрочитанных |
| PATCH | `/notifications/{id}/read`, `/notifications/{id}/unread` | Изменение признака прочитанности |
| POST | `/notifications/read-all` | Отметка всех прочитанными |
| DELETE | `/notifications/{id}` | Удаление уведомления |

Вход возвращает HttpOnly-cookie `taskflow_session`. OkHttp хранит её в приватных настройках в виде AES-GCM шифротекста с ключом Android Keystore, соблюдает срок действия и признаки cookie и передаёт её исходному API. При запуске сохранённую сессию подтверждает `/auth/me`. HTTP 401 для авторизованного запроса очищает сессию и возвращает пользователя на вход. Для защищённых изменений Android запрашивает `/auth/csrf` и передаёт `X-CSRF-Token`. Пароли и CSRF-токены используются в памяти. Release требует HTTPS и задаётся при сборке свойствами `taskflowReleaseApiUrl` и `taskflowReleaseOrigin`.

Задачи загружаются страницами по 10, уведомления используют серверный размер страницы. Кнопка **Load more** запрашивает следующую страницу. Счётчики Dashboard используют отдельные запросы `GET /tasks` с `limit=1` и читают `pagination.total`. Поиск следует контракту API и ищет подстроку в заголовке. Сортировки соответствуют `created_desc`, `created_asc`, `due_date_asc`. Поля формы проверяет сервер. Очистка даты отправляет `"due_date": null`. Изменяющие запросы отправляются без автоматического повтора.

## Структура проекта

- `app/src/main/java/com/taskflow/app/domain` — модели, фильтры и интерфейс репозитория.
- `data/api` — маршруты Retrofit и модели ответов.
- `data/repository` — реализация API и демонстрационные данные.
- `data/session` и `data/ConnectionSettings.kt` — хранилище сессии и настройки DataStore.
- `TaskFlowViewModel.kt` — состояния StateFlow, загрузка страниц и последовательное выполнение изменений.
- `navigation`, `ui/screens`, `ui/components` — навигация Compose, экраны и общие компоненты.
- `app/src/debug/AndroidManifest.xml` — разрешение HTTP для debug. Основной манифест отключает cleartext.
- `app/src/test` — JVM-проверки HTTP-клиента на MockWebServer.

## Appium

Пакет — `com.taskflow.app`. Стартовая Activity — `com.taskflow.app.MainActivity`. Если APK уже установлен, достаточно следующих capabilities для UiAutomator2. Значение `udid` возьмите из `adb devices`. При необходимости автоматической установки передайте `appium:app` с абсолютным путём к APK.

```json
{
  "platformName": "Android",
  "appium:automationName": "UiAutomator2",
  "appium:udid": "emulator-5554",
  "appium:appPackage": "com.taskflow.app",
  "appium:appActivity": "com.taskflow.app.MainActivity",
  "appium:noReset": true
}
```

Стабильные resource ID и пример настройки поиска по коротким идентификаторам перечислены в [TEST_LOCATORS.md](TEST_LOCATORS.md).

Следующие команды очищают приложение и возвращают Real mode с настройками по умолчанию.

```powershell
adb shell pm clear com.taskflow.app
adb shell am start -n com.taskflow.app/.MainActivity
```

Очистка удалит локальные настройки и сессию. Данные аккаунта и задач Real mode останутся на сервере. Для проверки восстановления сессии используйте `adb shell am force-stop com.taskflow.app`, затем запустите Activity.

## Диагностика подключения

- Выполните `Invoke-RestMethod http://localhost:8000/health` и `docker compose ps` на компьютере. Для эмулятора проверьте Base URL `http://10.0.2.2:8000/` и наличие сети в Android.
- При `Missing or untrusted Origin` проверьте значение поля **Allowed authentication origin** по настройкам запущенного backend.
- Если вход проходит, но сразу появляется экран входа, проверьте схему Base URL. Для сессионной cookie с атрибутом Secure требуется HTTPS.
- Если падают только уведомления, проверьте состояние контейнеров Notification Service и настройки существующей интеграции.
- В debug доступен `adb logcat -s TaskFlowHttp`. Журнал показывает метод и статус HTTP или факт сетевого сбоя. Таймаут соединения — 5 с, чтения — 12 с, всего вызова — 18 с.
- Если ответ на создание потерян, обновите список и проверьте заголовок перед повторным созданием. В API нет ключа идемпотентности.

## Проверки

```powershell
.\gradlew.bat testDebugUnitTest lintDebug assembleDebug assembleRelease
adb shell uiautomator dump /sdcard/taskflow-window.xml
adb pull /sdcard/taskflow-window.xml
```

Пять JVM-тестов проверяют Origin, передачу cookie и CSRF, явный JSON null для даты, обработку 401 и 422, ошибку десериализации, отсутствие повтора при HTTP 503 с Retry-After и чтение задач при ошибке уведомлений. Сборка debug и release прошла. Lint завершился без ошибок. Release без параметров собирается без настроенного адреса API.

На эмуляторе Pixel 6 с Android 35 проверены установка APK, регистрация, неправильный пароль, восстановление сессии после перезапуска и выход. Через живой backend прошли CRUD задач, установка и очистка даты, поиск, фильтр, сортировка, вторая страница, pull-to-refresh, свайп и long press. Проверены потеря сети и повторная загрузка после восстановления. Уведомление для проверки рабочих операций внесено штатным скриптом публикации событий Notification Service. Resource ID полей, карточек, меню и диалогов проверены через `adb shell uiautomator dump`.

В Demo mode проверены создание задачи с отключённой сетью, сохранение режима при перезапуске, счётчик и действия с уведомлениями. При повороте экрана черновик задачи сохранился. Системная кнопка «Назад» закрыла клавиатуру и при повторном нажатии вернула Dashboard.

## Ограничения

Demo использует упрощённую локальную проверку email. В Real mode применяется серверная валидация. Список уведомлений отражает события, уже обработанные сервером. Для получения свежих событий обновите список или снова откройте экран уведомлений. Firebase и системных push-уведомлений в этой версии нет.
