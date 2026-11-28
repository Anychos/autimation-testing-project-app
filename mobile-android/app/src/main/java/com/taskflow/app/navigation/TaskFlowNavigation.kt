package com.taskflow.app.navigation

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.taskflow.app.BuildConfig
import com.taskflow.app.TaskFlowViewModel
import com.taskflow.app.UiEvent
import com.taskflow.app.ui.components.*
import com.taskflow.app.ui.screens.*

private const val LOGIN = "login"
private const val REGISTER = "register"
private const val DASHBOARD = "dashboard"
private const val DETAILS = "details/{id}"
private const val EDIT = "edit/{id}"
private const val CREATE = "create"
private const val NOTIFICATIONS = "notifications"
private const val SETTINGS = "settings"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TaskFlowNavigation(model: TaskFlowViewModel) {
    val app by model.app.collectAsStateWithLifecycle()
    if (app.initializing) {
        Surface(Modifier.fillMaxSize().safeDrawingPadding().appiumRoot()) {
            FormColumn("session_loading_screen") { Spinner() }
        }
        return
    }
    key(app.user?.id, app.settings.demo) {
        val navigation = rememberNavController()
        val backStack by navigation.currentBackStackEntryAsState()
        val route = backStack?.destination?.route ?: if (app.user == null) LOGIN else DASHBOARD
        val unread by model.unread.collectAsStateWithLifecycle()
        var registeredEmail by rememberSaveable { mutableStateOf<String?>(null) }
        LaunchedEffect(navigation) {
            model.events.collect { event ->
                val entry = navigation.currentBackStackEntry
                val currentRoute = entry?.destination?.route
                when (event) {
                    is UiEvent.Registered -> if (currentRoute == REGISTER) {
                        registeredEmail = event.email
                        navigation.popBackStack()
                    }
                    UiEvent.SettingsSaved -> if (currentRoute == SETTINGS) navigation.popBackStack()
                    UiEvent.TaskSaved -> if (currentRoute == CREATE || currentRoute == EDIT) navigation.popBackStack()
                    is UiEvent.TaskDeleted -> if (currentRoute == DETAILS &&
                        entry?.arguments?.getString("id") == event.id) navigation.popBackStack()
                }
            }
        }

        fun go(destination: String) {
            if (app.busy) return
            model.clearError()
            navigation.navigate(destination) { launchSingleTop = true }
        }
        fun back() {
            if (app.busy) return
            if (route == REGISTER) model.registrationInput.clear()
            model.clearError()
            navigation.popBackStack()
        }

        Scaffold(
            modifier = Modifier.fillMaxSize().appiumRoot(),
            containerColor = MaterialTheme.colorScheme.background,
            topBar = {
                TopAppBar(
                    title = { Text(if (route == NOTIFICATIONS) "Notifications" else "TaskFlow") },
                    navigationIcon = {
                        if (route != LOGIN && route != DASHBOARD) BackButton("navigate_back", ::back)
                    },
                    actions = {
                        if (route == DASHBOARD) {
                            IconButton({ go(NOTIFICATIONS) }, Modifier.testTag("notification_bell"),
                                enabled = !app.busy) {
                                BadgedBox(badge = {
                                    unread?.let {
                                        Badge { Text(it.toString(), Modifier.testTag("notification_unread_count")) }
                                    }
                                }) {
                                    Icon(Icons.Default.Notifications, contentDescription = "Notifications")
                                }
                            }
                        }
                        if (BuildConfig.DEBUG && (route == LOGIN || route == DASHBOARD)) {
                            IconButton({ go(SETTINGS) }, Modifier.testTag("settings_button"), enabled = !app.busy) {
                                Icon(Icons.Default.Settings, contentDescription = "Connection settings")
                            }
                        }
                        if (route == DASHBOARD) {
                            TextButton(model::logout, Modifier.testTag("logout_button"), enabled = !app.busy) {
                                Text("Sign out")
                            }
                        }
                    }
                )
            },
            floatingActionButton = {
                if (route == DASHBOARD) {
                    FloatingActionButton({ go(CREATE) }, Modifier.testTag("dashboard_create_task_button")) {
                        Icon(Icons.Default.Add, contentDescription = "Create task")
                    }
                }
            }
        ) { padding ->
            Column(Modifier.padding(padding).consumeWindowInsets(padding).imePadding()) {
                if (app.settings.demo) {
                    Surface(color = MaterialTheme.colorScheme.tertiaryContainer) {
                        Text("Demo mode", Modifier.fillMaxWidth().testTag("demo_mode_indicator")
                            .padding(horizontal = 16.dp, vertical = 6.dp))
                    }
                }
                NavHost(navigation, startDestination = if (app.user == null) LOGIN else DASHBOARD,
                    modifier = Modifier.weight(1f)) {
                    if (BuildConfig.DEBUG) {
                        composable(SETTINGS) {
                            SettingsScreen(app, model::saveSettings, ::back)
                        }
                    }
                    if (app.user == null) {
                        composable(LOGIN) {
                            if (app.initializationError != null) {
                                FormColumn("session_error_screen") {
                                    Heading("Connect to TaskFlow")
                                    Problem(app.initializationError, "session_restore_error")
                                    Button(model::restore, Modifier.testTag("session_restore_retry")) { Text("Retry") }
                                    TextButton(model::showLogin, Modifier.testTag("session_continue_to_login")) {
                                        Text("Go to sign in")
                                    }
                                }
                            } else {
                                AuthScreen(false, app, model.loginInput, registeredEmail.orEmpty(), registeredEmail != null,
                                    { go(REGISTER) }, { model.login(it) })
                            }
                        }
                        composable(REGISTER) {
                            AuthScreen(true, app, model.registrationInput, "", false, ::back, model::register)
                        }
                    } else {
                        composable(DASHBOARD) {
                            val list by model.tasks.collectAsStateWithLifecycle()
                            val counts by model.counts.collectAsStateWithLifecycle()
                            val query by model.query.collectAsStateWithLifecycle()
                            DashboardScreen(app, list, counts, query, model::setQuery,
                                { model.refreshDashboard(pull = true) }, { model.loadTasks(append = true) },
                                { model.refreshDashboard() }, { go("details/$it") }, { go("edit/$it") }, model::deleteTask)
                        }
                        composable(DETAILS) { entry ->
                            val id = checkNotNull(entry.arguments?.getString("id"))
                            val details by model.details.collectAsStateWithLifecycle()
                            LaunchedEffect(id) { model.loadDetails(id) }
                            TaskDetailsScreen(id, details, app, { model.loadDetails(id) }, { go("edit/$id") },
                                { model.deleteTask(id) })
                        }
                        composable(CREATE) {
                            TaskForm(null, app, ::back) { model.saveTask(null, it) }
                        }
                        composable(EDIT) { entry ->
                            val id = checkNotNull(entry.arguments?.getString("id"))
                            val details by model.details.collectAsStateWithLifecycle()
                            LaunchedEffect(id) {
                                if (details.task?.id != id) model.loadDetails(id)
                            }
                            val task = details.task?.takeIf { it.id == id }
                            when {
                                task != null -> TaskForm(task, app, ::back) { model.saveTask(id, it) }
                                details.id == id && details.error != null -> FormColumn("task_form") {
                                    Problem(details.error, "task_form_error")
                                    Button({ model.loadDetails(id) }, Modifier.testTag("task_form_retry")) { Text("Retry") }
                                }
                                else -> FormColumn("task_form") { Spinner() }
                            }
                        }
                        composable(NOTIFICATIONS) {
                            val notices by model.notices.collectAsStateWithLifecycle()
                            LaunchedEffect(Unit) { model.loadNotices() }
                            NotificationScreen(app, notices, { model.loadNotices(pull = it) },
                                { model.loadNotices(append = true) }, model::mark, model::markAllRead, model::deleteNotice)
                        }
                    }
                }
            }
        }
        BackHandler(app.busy || (route != LOGIN && route != DASHBOARD)) { back() }
    }
}
