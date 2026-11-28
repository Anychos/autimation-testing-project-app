package com.taskflow.app.data.repository

import com.taskflow.app.domain.*
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

class DemoRepository : TaskFlowRepository {
    private val demoEmail = "demo@taskflow.local"
    private val accounts = mutableMapOf(demoEmail to "taskflow-demo")
    private val ownerTasks = mutableMapOf(
        demoEmail to mutableListOf(
            Task("demo-plan", "Plan the release", "Review the checklist with the team.",
                TaskStatus.IN_PROGRESS, LocalDate.now().plusDays(2).toString(), "2025-01-03T09:00:00Z"),
            Task("demo-tests", "Draft mobile checks", "Cover authentication and task management.",
                TaskStatus.TODO, null, "2025-01-02T09:00:00Z"),
            Task("demo-setup", "Set up the workspace", "", TaskStatus.DONE, null, "2025-01-01T09:00:00Z")
        )
    )
    private val ownerNotices = mutableMapOf(
        demoEmail to mutableListOf(Notice("demo-welcome", "Welcome to TaskFlow",
            "Your demo workspace is ready.", false, "2025-01-01T09:00:00Z"))
    )
    private var user: User? = null

    private val tasks get() = ownerTasks.getOrPut(current().email) { mutableListOf() }
    private val notices get() = ownerNotices.getOrPut(current().email) { mutableListOf() }

    override suspend fun restore() = user

    override suspend fun register(credentials: Credentials): User {
        val email = validate(credentials)
        if (accounts.containsKey(email)) throw RequestFailure("Email is already registered", 409)
        accounts[email] = credentials.password
        return User(email, email)
    }

    override suspend fun login(credentials: Credentials): User {
        val email = validate(credentials)
        if (accounts[email] != credentials.password) throw RequestFailure("Invalid email or password", 401)
        return User(email, email).also { user = it }
    }

    override suspend fun logout() { user = null }

    override suspend fun tasks(query: TaskQuery, page: Int, limit: Int): TaskPage {
        val filtered = tasks.filter {
            (query.status == null || it.status == query.status) && it.title.contains(query.search, ignoreCase = true)
        }
        val order = when (query.sort) {
            TaskSort.NEWEST -> compareByDescending<Task> { it.createdAt }
            TaskSort.OLDEST -> compareBy<Task> { it.createdAt }
            TaskSort.DUE_DATE -> compareBy<Task> { it.dueDate == null }.thenBy { it.dueDate }
        }.thenBy { it.id }
        return TaskPage(filtered.sortedWith(order).drop((page - 1) * limit).take(limit),
            Pagination(page, limit, filtered.size, (filtered.size + limit - 1) / limit))
    }

    override suspend fun task(id: String) = tasks.firstOrNull { it.id == id } ?: missing("Task")

    override suspend fun create(input: TaskInput): Task {
        validate(input)
        return Task(UUID.randomUUID().toString(), input.title.trim(), input.description, input.status,
            input.dueDate, Instant.now().toString()).also {
            tasks.add(it)
            addNotice("Task created", it.title)
        }
    }

    override suspend fun update(id: String, input: TaskInput): Task {
        validate(input)
        val previous = task(id)
        val updated = previous.copy(title = input.title.trim(), description = input.description,
            status = input.status, dueDate = input.dueDate)
        tasks[tasks.indexOf(previous)] = updated
        if (updated != previous) addNotice(if (updated.status == TaskStatus.DONE &&
            previous.status != TaskStatus.DONE) "Task completed" else "Task updated", updated.title)
        return updated
    }

    override suspend fun delete(id: String) {
        val task = task(id)
        tasks.remove(task)
        addNotice("Task deleted", task.title)
    }

    override suspend fun notices(page: Int) = NoticePage(notices.drop((page - 1) * 20).take(20),
        notices.size, page, 20)

    override suspend fun unread() = notices.count { !it.isRead }

    override suspend fun mark(id: String, read: Boolean) {
        val index = notices.indexOfFirst { it.id == id }
        if (index < 0) missing("Notification")
        notices[index] = notices[index].copy(isRead = read)
    }

    override suspend fun markAllRead() {
        notices.indices.forEach { notices[it] = notices[it].copy(isRead = true) }
    }

    override suspend fun deleteNotice(id: String) {
        if (!notices.removeAll { it.id == id }) missing("Notification")
    }

    private fun addNotice(title: String, message: String) {
        notices.add(0, Notice(UUID.randomUUID().toString(), title, message, false, Instant.now().toString()))
    }

    private fun current() = user ?: throw RequestFailure("Authentication required", 401)
    private fun missing(kind: String): Nothing = throw RequestFailure("$kind not found", 404)

    private fun validate(credentials: Credentials): String {
        val email = credentials.email.trim().lowercase()
        val fields = buildMap {
            if (email.length > 254 || !email.matches(Regex("[^@\\s]+@[^@\\s]+\\.[^@\\s]+"))) {
                put("email", "Invalid email format")
            }
            if (credentials.password.codePointCount(0, credentials.password.length) !in 8..64) {
                put("password", "Use 8 to 64 characters")
            }
        }
        if (fields.isNotEmpty()) throw RequestFailure("Invalid request data", 422, fields = fields)
        return email
    }

    private fun validate(input: TaskInput) {
        val title = input.title.trim()
        val fields = buildMap {
            if (title.codePointCount(0, title.length) !in 3..100) put("title", "Use 3 to 100 characters")
            if (input.description.codePointCount(0, input.description.length) > 500) {
                put("description", "Use up to 500 characters")
            }
        }
        if (fields.isNotEmpty()) throw RequestFailure("Invalid request data", 422, fields = fields)
    }
}
