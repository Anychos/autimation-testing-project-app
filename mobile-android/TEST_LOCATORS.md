# Локаторы TaskFlow Android

Compose экспортирует `Modifier.testTag()` в Android `resource-id` через `testTagsAsResourceId`. В XML локаторы записаны короткими строками, например `login_email_input`. Для Appium UiAutomator2 выключите автодобавление package prefix, если используете стратегию ID.

[Настройки Appium UiAutomator2](https://github.com/appium/appium-uiautomator2-driver/blob/master/docs/reference/settings.md#disableidlocatorautocompletion)

```python
driver.update_settings({"disableIdLocatorAutocompletion": True})
driver.find_element(AppiumBy.ID, "login_email_input")
```

При включённом автодобавлении можно использовать `AppiumBy.ANDROID_UIAUTOMATOR` с `new UiSelector().resourceId("login_email_input")`. `content-desc` используется для доступности иконок, например **Notifications**, **Back**, **Create task** и **Task actions**.

## Общие элементы и настройки

| Resource ID | Назначение |
|---|---|
| `navigate_back` | Назад со вложенного экрана |
| `loading_indicator` | Ожидание в форме, диалоге, просмотре задачи или при восстановлении сессии |
| `network_error_message` | Ошибка сети, таймаута или подключения на текущем экране |
| `confirmation_dialog` | Диалог подтверждения удаления |
| `settings_button`, `settings_screen` | Вход в настройки подключения debug и контейнер экрана |
| `settings_api_url`, `settings_origin` | Base URL и разрешённый Origin |
| `settings_demo_switch`, `demo_mode_indicator` | Переключатель режима и постоянный баннер Demo |
| `settings_save_button`, `settings_cancel_button`, `settings_error_message` | Сохранение, отмена и ошибка настроек |
| `session_loading_screen` | Контейнер восстановления сессии |
| `session_error_screen`, `session_restore_error` | Экран и ошибка восстановления |
| `session_restore_retry`, `session_continue_to_login` | Повтор восстановления и переход к входу |
| `session_expired_message` | Сессия завершилась, требуется вход |

## Вход и регистрация

| Resource ID | Назначение |
|---|---|
| `login_screen`, `registration_screen` | Контейнеры экранов |
| `login_email_input`, `registration_email_input` | Поля Email |
| `login_password_input`, `registration_password_input` | Поля Password |
| `login_password_visibility`, `registration_password_visibility` | Показ и скрытие пароля |
| `registration_confirm_password_input`, `registration_confirm_password_visibility` | Подтверждение пароля и его видимость |
| `login_submit_button`, `registration_submit_button` | Отправка формы |
| `login_register_link`, `registration_login_link` | Переход к регистрации и возврат ко входу |
| `login_error_message`, `registration_error_message` | Ошибки входа и регистрации |
| `registration_success_message` | Подтверждение регистрации на экране входа |
| `logout_button` | Выход со страницы Dashboard |

## Dashboard

| Resource ID | Назначение |
|---|---|
| `dashboard_screen`, `dashboard_task_list` | Контейнер Dashboard и список для прокрутки и pull-to-refresh |
| `dashboard_welcome` | Приветствие с email |
| `dashboard_total_count`, `dashboard_in_progress_count`, `dashboard_completed_count` | Счётчики всех задач, в процессе и завершённых |
| `dashboard_counts_retry` | Повтор загрузки счётчиков |
| `dashboard_search_input` | Поиск по заголовку |
| `dashboard_status_filter` | Открывает фильтр статуса |
| `dashboard_status_filter_all`, `dashboard_status_filter_todo`, `dashboard_status_filter_in_progress`, `dashboard_status_filter_done` | Пункты фильтра |
| `dashboard_sort_select` | Открывает сортировку |
| `dashboard_sort_select_created_desc`, `dashboard_sort_select_created_asc`, `dashboard_sort_select_due_date_asc` | Варианты сортировки |
| `dashboard_create_task_button` | Открывает создание |
| `dashboard_empty_state`, `dashboard_loading_state`, `dashboard_error_state`, `dashboard_action_error` | Состояния списка и ошибки действий |
| `dashboard_retry_button`, `dashboard_load_more` | Повтор запроса и следующая страница |
| `task_item_{id}` | Открывает просмотр. Long press открывает меню, свайп справа налево открывает подтверждение удаления |
| `task_title_{id}`, `task_status_{id}`, `task_due_date_{id}` | Заголовок, статус и заданный срок карточки |
| `task_menu_{id}`, `task_menu_edit_{id}`, `task_menu_delete_{id}` | Меню карточки и команды |

## Задачи

| Resource ID | Назначение |
|---|---|
| `task_details_screen`, `task_details_title`, `task_details_status`, `task_details_description`, `task_details_due_date` | Контейнер просмотра и поля задачи |
| `task_details_error`, `task_details_retry` | Ошибка и повтор чтения |
| `task_edit_button`, `task_delete_button` | Редактирование и удаление из просмотра |
| `task_form`, `task_title_input`, `task_description_input` | Контейнер формы и текстовые поля |
| `task_status_select` | Открывает выбор статуса |
| `task_status_select_todo`, `task_status_select_in_progress`, `task_status_select_done` | Пункты выбора статуса |
| `task_due_date_input`, `task_clear_due_date_button` | Открывает календарь и очищает текущую дату |
| `task_date_picker`, `task_date_picker_confirm`, `task_date_picker_cancel` | Контейнер календаря и кнопки OK и Cancel |
| `task_submit_button`, `task_cancel_button` | Сохранение и отмена формы |
| `task_form_error`, `task_form_retry` | Ошибка формы и повтор загрузки редактируемой задачи |
| `task_delete_confirm_button`, `task_delete_cancel_button`, `task_delete_error` | Подтверждение, отмена и ошибка удаления |

Дата в календаре выбирается по доступному описанию дня или его тексту в сочетании с текущим месяцем. Локаторы календаря Material 3 зависят от компонента и локали устройства.

## Уведомления

| Resource ID | Назначение |
|---|---|
| `notification_bell`, `notification_unread_count` | Открывает список и показывает число непрочитанных при доступном API |
| `notification_screen`, `notification_list` | Контейнер экрана и список с pull-to-refresh |
| `notification_mark_all_read`, `notification_refresh` | Отметить все прочитанными и обновить |
| `notification_item_{id}`, `notification_status_{id}` | Карточка и состояние прочитанности |
| `notification_mark_read_{id}`, `notification_mark_unread_{id}` | Команда для текущего состояния карточки |
| `notification_delete_button_{id}` | Удаление карточки |
| `notification_delete_confirm_button`, `notification_delete_cancel_button`, `notification_delete_error` | Подтверждение, отмена и ошибка удаления |
| `notification_empty_state`, `notification_loading_state`, `notification_error_state`, `notification_action_error` | Состояния списка и ошибки действий |
| `notification_retry`, `notification_load_more` | Повтор и следующая страница |

`{id}` заменяется ID задачи или уведомления. У элементов за пределами видимой части LazyColumn узлы появляются при прокрутке. Сетевые ошибки используют общий `network_error_message`. Ожидайте нужное состояние экрана после действия, поскольку запросы асинхронны.
