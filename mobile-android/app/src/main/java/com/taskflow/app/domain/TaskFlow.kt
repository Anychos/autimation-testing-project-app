package com.taskflow.app.domain

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class User(val id: String, val email: String)

@Serializable
data class Credentials(val email: String, val password: String)

@Serializable
enum class TaskStatus(val wire: String, val label: String) {
    @SerialName("todo") TODO("todo", "To do"),
    @SerialName("in_progress") IN_PROGRESS("in_progress", "In progress"),
    @SerialName("done") DONE("done", "Done")
}

enum class TaskSort(val wire: String, val label: String) {
    NEWEST("created_desc", "Newest first"),
    OLDEST("created_asc", "Oldest first"),
    DUE_DATE("due_date_asc", "Due date")
}

data class TaskQuery(
    val search: String = "",
    val status: TaskStatus? = null,
    val sort: TaskSort = TaskSort.NEWEST
)

@Serializable
data class TaskInput(
    val title: String,
    val description: String,
    val status: TaskStatus,
    @SerialName("due_date") val dueDate: String?
)

@Serializable
data class Task(
    val id: String,
    val title: String,
    val description: String,
    val status: TaskStatus,
    @SerialName("due_date") val dueDate: String?,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class Pagination(val page: Int, val limit: Int, val total: Int, val pages: Int)

@Serializable
data class TaskPage(val items: List<Task>, val pagination: Pagination)

data class TaskCounts(val total: Int, val inProgress: Int, val done: Int)

@Serializable
data class Notice(
    val id: String,
    val title: String,
    val message: String,
    @SerialName("is_read") val isRead: Boolean,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class NoticePage(
    val items: List<Notice>, val total: Int, val page: Int,
    @SerialName("page_size") val pageSize: Int
) {
    val hasMore get() = page.toLong() * pageSize < total
}

class RequestFailure(
    override val message: String,
    val status: Int? = null,
    val code: String? = null,
    val fields: Map<String, String> = emptyMap(),
    val connectivity: Boolean = false
) : Exception(message)

interface TaskFlowRepository {
    suspend fun restore(): User?
    suspend fun register(credentials: Credentials): User
    suspend fun login(credentials: Credentials): User
    suspend fun logout()
    suspend fun tasks(query: TaskQuery, page: Int, limit: Int): TaskPage
    suspend fun task(id: String): Task
    suspend fun create(input: TaskInput): Task
    suspend fun update(id: String, input: TaskInput): Task
    suspend fun delete(id: String)
    suspend fun notices(page: Int): NoticePage
    suspend fun unread(): Int
    suspend fun mark(id: String, read: Boolean)
    suspend fun markAllRead()
    suspend fun deleteNotice(id: String)
}
