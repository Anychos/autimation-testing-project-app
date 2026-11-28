package com.taskflow.app

import android.app.Application
import android.net.ConnectivityManager
import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.taskflow.app.data.ConnectionSettings
import com.taskflow.app.data.ConnectionStore
import com.taskflow.app.data.repository.DemoRepository
import com.taskflow.app.data.repository.RealRepository
import com.taskflow.app.data.session.KeystoreSessionCookies
import com.taskflow.app.domain.*
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*

data class AppState(
    val user: User? = null,
    val initializing: Boolean = true,
    val initializationError: RequestFailure? = null,
    val sessionExpired: Boolean = false,
    val settings: ConnectionSettings = ConnectionSettings(),
    val busy: Boolean = false,
    val error: RequestFailure? = null,
    val deletedTaskId: String? = null,
    val deletedNoticeId: String? = null
)

sealed interface UiEvent {
    data class Registered(val email: String) : UiEvent
    data object SettingsSaved : UiEvent
    data object TaskSaved : UiEvent
    data class TaskDeleted(val id: String) : UiEvent
}

data class PagedList<T>(
    val items: List<T> = emptyList(),
    val page: Int = 0,
    val hasMore: Boolean = false,
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: RequestFailure? = null
)

data class TaskDetails(
    val id: String? = null,
    val task: Task? = null,
    val error: RequestFailure? = null
)

class AuthInput {
    var password by mutableStateOf("")
    var confirmation by mutableStateOf("")

    fun clear() {
        password = ""
        confirmation = ""
    }
}

class TaskFlowViewModel(private val application: Application) : AndroidViewModel(application) {
    val loginInput = AuthInput()
    val registrationInput = AuthInput()
    private val connectionStore = ConnectionStore(application)
    private val _app = MutableStateFlow(AppState())
    val app = _app.asStateFlow()
    private val _events = Channel<UiEvent>(Channel.BUFFERED)
    val events = _events.receiveAsFlow()
    private val _query = MutableStateFlow(TaskQuery())
    val query = _query.asStateFlow()
    private val _tasks = MutableStateFlow(PagedList<Task>())
    val tasks = _tasks.asStateFlow()
    private val _counts = MutableStateFlow<TaskCounts?>(null)
    val counts = _counts.asStateFlow()
    private val _details = MutableStateFlow(TaskDetails())
    val details = _details.asStateFlow()
    private val _notices = MutableStateFlow(PagedList<Notice>())
    val notices = _notices.asStateFlow()
    private val _unread = MutableStateFlow<Int?>(null)
    val unread = _unread.asStateFlow()

    private var repository: TaskFlowRepository? = null
    private var cookies: KeystoreSessionCookies? = null
    private var restoreJob: Job? = null
    private var tasksJob: Job? = null
    private var countsJob: Job? = null
    private var detailsJob: Job? = null
    private var noticesJob: Job? = null
    private var unreadJob: Job? = null

    init {
        restore()
    }

    fun restore() {
        restoreJob?.cancel()
        _app.update { it.copy(initializing = true, initializationError = null) }
        restoreJob = viewModelScope.launch {
            try {
                val settings = connectionStore.load()
                _app.update { it.copy(settings = settings) }
                if (repository == null) configure(settings)
                val user = requireRepository().restore()
                _app.update { it.copy(user = user, initializing = false) }
                if (user != null) refreshDashboard()
            } catch (error: Exception) {
                _app.update { it.copy(initializing = false, initializationError = failure(error)) }
            }
        }
    }

    fun showLogin() {
        _app.update { it.copy(initializationError = null) }
    }

    fun saveSettings(settings: ConnectionSettings) = action { _ ->
        val previous = _app.value.settings
        if (settings != previous) {
            val normalized = if (settings.demo) settings else settings.copy(
                apiUrl = settings.parsedUrl()?.toString()
                    ?: throw RequestFailure("Enter a valid API base URL."),
                origin = settings.origin.trim().also {
                    if (!settings.validOrigin()) throw RequestFailure("Enter an allowed Origin without a path.")
                }
            )
            connectionStore.save(normalized)
            stopReads()
            withContext(Dispatchers.IO) { cookies?.clear() }
            configure(normalized)
            clearUser()
            _app.update { it.copy(settings = normalized, initializationError = null) }
        }
        _events.send(UiEvent.SettingsSaved)
    }

    fun clearError() {
        _app.update { it.copy(error = null, sessionExpired = false) }
    }

    fun login(credentials: Credentials) = action { repository ->
        val user = requireNotNull(repository).login(credentials)
        loginInput.clear()
        _app.update { it.copy(user = user, sessionExpired = false) }
        refreshDashboard()
    }

    fun register(credentials: Credentials) = action { repository ->
        val user = requireNotNull(repository).register(credentials)
        registrationInput.clear()
        _events.send(UiEvent.Registered(user.email))
    }

    fun logout() = action { repository ->
        requireNotNull(repository).logout()
        clearUser()
    }

    fun setQuery(query: TaskQuery) {
        if (_query.value == query) return
        _query.value = query
        _tasks.value = PagedList()
        loadTasks(delayRequest = true)
    }

    fun refreshDashboard(pull: Boolean = false) {
        loadTasks(pull = pull)
        refreshCounts()
        refreshUnread()
    }

    fun loadTasks(append: Boolean = false, pull: Boolean = false, delayRequest: Boolean = false) {
        val repository = repository ?: return
        if (_app.value.user == null) return
        val previous = _tasks.value
        if (append && (previous.loading || previous.refreshing || !previous.hasMore)) return
        tasksJob?.cancel()
        val currentQuery = _query.value
        val page = if (append) previous.page + 1 else 1
        _tasks.value = previous.copy(loading = !pull, refreshing = pull, error = null)
        tasksJob = viewModelScope.launch {
            try {
                if (delayRequest) delay(300)
                val response = repository.tasks(currentQuery, page, 10)
                _tasks.value = PagedList(
                    items = (if (append) previous.items + response.items else response.items).distinctBy { it.id },
                    page = response.pagination.page,
                    hasMore = response.pagination.page < response.pagination.pages
                )
            } catch (error: Exception) {
                val problem = failure(error)
                if (!expire(problem)) _tasks.value = previous.copy(loading = false, refreshing = false, error = problem)
            }
        }
    }

    private fun refreshCounts() {
        val repository = repository ?: return
        countsJob?.cancel()
        countsJob = viewModelScope.launch {
            try {
                _counts.value = coroutineScope {
                    val total = async { repository.tasks(TaskQuery(), 1, 1).pagination.total }
                    val progress = async { repository.tasks(TaskQuery(status = TaskStatus.IN_PROGRESS), 1, 1).pagination.total }
                    val done = async { repository.tasks(TaskQuery(status = TaskStatus.DONE), 1, 1).pagination.total }
                    TaskCounts(total.await(), progress.await(), done.await())
                }
            } catch (error: Exception) {
                if (!expire(failure(error))) _counts.value = null
            }
        }
    }

    fun loadDetails(id: String) {
        val repository = repository ?: return
        detailsJob?.cancel()
        _details.value = TaskDetails(id)
        detailsJob = viewModelScope.launch {
            try {
                _details.value = TaskDetails(id, repository.task(id))
            } catch (error: Exception) {
                val problem = failure(error)
                if (!expire(problem)) _details.value = TaskDetails(id, error = problem)
            }
        }
    }

    fun saveTask(id: String?, input: TaskInput) = action { repository ->
        requireNotNull(repository)
        if (id == null) repository.create(input)
        else _details.value = TaskDetails(id, repository.update(id, input))
        refreshDashboard()
        _events.send(UiEvent.TaskSaved)
    }

    fun deleteTask(id: String) = action { repository ->
        requireNotNull(repository).delete(id)
        _app.update { it.copy(deletedTaskId = id) }
        refreshDashboard()
        _events.send(UiEvent.TaskDeleted(id))
    }

    fun loadNotices(append: Boolean = false, pull: Boolean = false) {
        val repository = repository ?: return
        val previous = _notices.value
        if (append && (previous.loading || previous.refreshing || !previous.hasMore)) return
        noticesJob?.cancel()
        val page = if (append) previous.page + 1 else 1
        _notices.value = previous.copy(loading = !pull, refreshing = pull, error = null)
        noticesJob = viewModelScope.launch {
            try {
                val result = repository.notices(page)
                _notices.value = PagedList(
                    items = (if (append) previous.items + result.items else result.items).distinctBy { it.id },
                    page = result.page, hasMore = result.hasMore
                )
            } catch (error: Exception) {
                val problem = failure(error)
                if (!expire(problem)) _notices.value = previous.copy(loading = false, refreshing = false, error = problem)
            }
        }
        if (!append) refreshUnread()
    }

    fun mark(id: String, read: Boolean) = action {
        requireNotNull(it).mark(id, read)
        loadNotices()
    }

    fun markAllRead() = action {
        requireNotNull(it).markAllRead()
        loadNotices()
    }

    fun deleteNotice(id: String) = action {
        requireNotNull(it).deleteNotice(id)
        _app.update { state -> state.copy(deletedNoticeId = id) }
        loadNotices()
    }

    private fun refreshUnread() {
        val repository = repository ?: return
        unreadJob?.cancel()
        unreadJob = viewModelScope.launch {
            try {
                _unread.value = repository.unread()
            } catch (error: Exception) {
                if (!expire(failure(error))) _unread.value = null
            }
        }
    }

    private fun action(block: suspend (TaskFlowRepository?) -> Unit) {
        if (_app.value.busy || _app.value.initializing) return
        _app.update { it.copy(busy = true, error = null, deletedTaskId = null, deletedNoticeId = null) }
        viewModelScope.launch {
            try {
                block(repository)
            } catch (error: Exception) {
                val problem = failure(error)
                if (!expire(problem)) _app.update { it.copy(error = problem) }
            } finally {
                _app.update { it.copy(busy = false) }
            }
        }
    }

    private fun configure(settings: ConnectionSettings) {
        if (settings.demo && BuildConfig.DEBUG) {
            cookies = null
            repository = DemoRepository()
            return
        }
        val url = settings.parsedUrl()
            ?: throw RequestFailure("No valid API URL is configured for this build.")
        if (!settings.validOrigin()) throw RequestFailure("No valid authentication Origin is configured.")
        val jar = KeystoreSessionCookies(application, url)
        cookies = jar
        val connectivity = application.getSystemService(ConnectivityManager::class.java)
        repository = RealRepository(url, settings.origin.trim(), jar,
            isOnline = { connectivity.activeNetwork != null },
            reportRequest = { if (BuildConfig.DEBUG) Log.d("TaskFlowHttp", it) })
    }

    private fun requireRepository() = repository ?: throw RequestFailure("Configure the API connection first.")

    private fun failure(error: Exception): RequestFailure = when (error) {
        is CancellationException -> throw error
        is RequestFailure -> error
        else -> RequestFailure("TaskFlow could not complete the operation. Try again.")
    }

    private fun expire(error: RequestFailure): Boolean {
        if (error.status != 401 || _app.value.user == null) return false
        clearUser()
        _app.update { it.copy(sessionExpired = true) }
        return true
    }

    private fun stopReads() {
        listOf(tasksJob, countsJob, detailsJob, noticesJob, unreadJob).forEach { it?.cancel() }
    }

    private fun clearUser() {
        stopReads()
        loginInput.clear()
        registrationInput.clear()
        _query.value = TaskQuery()
        _tasks.value = PagedList()
        _counts.value = null
        _notices.value = PagedList()
        _unread.value = null
        _details.value = TaskDetails()
        _app.update { it.copy(user = null, error = null) }
    }
}
