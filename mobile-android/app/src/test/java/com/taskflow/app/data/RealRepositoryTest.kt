package com.taskflow.app.data

import com.taskflow.app.data.repository.RealRepository
import com.taskflow.app.data.session.SessionCookies
import com.taskflow.app.domain.*
import kotlinx.coroutines.runBlocking
import okhttp3.Cookie
import okhttp3.HttpUrl
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Test

class RealRepositoryTest {
    private val server = MockWebServer()
    private val jar = object : SessionCookies {
        private var saved = emptyList<Cookie>()
        override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) { saved = cookies }
        override fun loadForRequest(url: HttpUrl) = saved.filter { it.matches(url) }
        override fun clear() { saved = emptyList() }
    }
    private val logs = mutableListOf<String>()
    private val repository = RealRepository(server.url("/"), "http://localhost:5173", jar, { true }, logs::add)

    @After
    fun close() = server.shutdown()

    @Test
    fun loginOriginCookieCsrfAndExplicitNullDate() = runBlocking {
        val user = """{"id":"fake-user","email":"learner@example.com"}"""
        server.enqueue(json(user).addHeader("Set-Cookie", "taskflow_session=private-cookie; Path=/; Max-Age=3600; HttpOnly"))
        server.enqueue(json(user))
        server.enqueue(json("""{"csrf_token":"private-csrf"}"""))
        server.enqueue(json("""{"id":"task-id","title":"Draft","description":"","status":"done","due_date":null,"created_at":"2025-01-01T00:00:00Z"}"""))

        repository.login(Credentials("learner@example.com", "private-password"))
        assertEquals("fake-user", repository.restore()?.id)
        val result = repository.update("task-id", TaskInput("Draft", "", TaskStatus.DONE, null))
        assertNull(result.dueDate)

        val login = server.takeRequest()
        assertEquals("/api/v1/auth/login", login.path)
        assertEquals("http://localhost:5173", login.getHeader("Origin"))
        assertTrue(login.body.readUtf8().contains("private-password"))
        assertEquals("taskflow_session=private-cookie", server.takeRequest().getHeader("Cookie"))
        assertEquals("/api/v1/auth/csrf", server.takeRequest().path)
        val patch = server.takeRequest()
        assertEquals("PATCH", patch.method)
        assertEquals("private-csrf", patch.getHeader("X-CSRF-Token"))
        assertTrue(patch.body.readUtf8().contains("\"due_date\":null"))
        assertFalse(logs.joinToString().contains("private-"))
    }

    @Test
    fun mutationWithRetryAfterIsSentOnce() = runBlocking {
        server.enqueue(json("""{"csrf_token":"token"}"""))
        server.enqueue(MockResponse().setResponseCode(503).addHeader("Retry-After", "0"))
        server.enqueue(MockResponse().setResponseCode(204))

        val error = runCatching { repository.delete("task-id") }.exceptionOrNull() as RequestFailure
        assertEquals(503, error.status)
        assertEquals(2, server.requestCount)
        server.takeRequest()
        assertEquals("DELETE", server.takeRequest().method)
    }

    @Test
    fun structuredValidationAndMalformedSuccessBecomeReadableFailures() = runBlocking {
        server.enqueue(json(
            """{"error":{"code":"VALIDATION_ERROR","message":"Invalid request data","details":[{"loc":["body","email"],"msg":"Value error, Invalid email format","type":"value_error"}]}}"""
        ).setResponseCode(422))
        val validation = runCatching {
            repository.register(Credentials("invalid", "password"))
        }.exceptionOrNull() as RequestFailure
        assertEquals("VALIDATION_ERROR", validation.code)
        assertEquals("Invalid email format", validation.fields["email"])

        server.enqueue(json("""{"items":[]}"""))
        val decoding = runCatching { repository.tasks(TaskQuery(), 1, 10) }.exceptionOrNull() as RequestFailure
        assertEquals("The server returned an unexpected response.", decoding.message)
    }

    @Test
    fun expiredSessionClearsCookie() = runBlocking {
        jar.saveFromResponse(server.url("/"), listOf(Cookie.parse(
            server.url("/"), "taskflow_session=expired-server-side; Path=/; Max-Age=3600"
        )!!))
        server.enqueue(MockResponse().setResponseCode(401))
        assertNull(repository.restore())
        assertTrue(jar.loadForRequest(server.url("/")).isEmpty())
    }

    @Test
    fun unavailableNotificationsDoNotInvalidateTaskSession() = runBlocking {
        server.enqueue(json(
            """{"error":{"code":"NOTIFICATION_SERVICE_UNAVAILABLE","message":"Notifications temporarily unavailable","details":[]}}"""
        ).setResponseCode(503))
        server.enqueue(json("""{"items":[],"pagination":{"page":2,"limit":10,"total":15,"pages":2}}"""))

        val error = runCatching { repository.notices(1) }.exceptionOrNull() as RequestFailure
        assertEquals("NOTIFICATION_SERVICE_UNAVAILABLE", error.code)
        val page = repository.tasks(TaskQuery("a+b", TaskStatus.DONE, TaskSort.DUE_DATE), 2, 10)
        assertEquals(15, page.pagination.total)
        assertEquals("/api/v1/notifications?page=1", server.takeRequest().path)
        val url = server.takeRequest().requestUrl!!
        assertEquals("a+b", url.queryParameter("q"))
        assertEquals("done", url.queryParameter("status"))
        assertEquals("due_date_asc", url.queryParameter("sort"))
        assertEquals("2", url.queryParameter("page"))
    }

    private fun json(body: String) = MockResponse().addHeader("Content-Type", "application/json").setBody(body)
}
