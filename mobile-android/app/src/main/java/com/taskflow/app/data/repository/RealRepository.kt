package com.taskflow.app.data.repository

import com.taskflow.app.data.api.*
import com.taskflow.app.data.session.SessionCookies
import com.taskflow.app.data.session.SessionStorageFailure
import com.taskflow.app.domain.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import okhttp3.ConnectionPool
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.BufferedSink
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.io.IOException
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

class RealRepository(
    private val baseUrl: HttpUrl,
    private val origin: String,
    private val cookies: SessionCookies,
    private val isOnline: () -> Boolean,
    reportRequest: (String) -> Unit = {}
) : TaskFlowRepository {
    private val json = Json { ignoreUnknownKeys = true }
    private val client = OkHttpClient.Builder()
        .cookieJar(cookies)
        // Retire idle connections before TaskFlow's Uvicorn keep-alive timeout.
        .connectionPool(ConnectionPool(5, 3, TimeUnit.SECONDS))
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(12, TimeUnit.SECONDS)
        .callTimeout(18, TimeUnit.SECONDS)
        .retryOnConnectionFailure(false)
        .followRedirects(false)
        .followSslRedirects(false)
        .addInterceptor { chain ->
            val request = chain.request()
            val method = request.method
            val outgoing = if (method == "GET") request else {
                val body = request.body ?: ByteArray(0).toRequestBody()
                val oneShot = object : RequestBody() {
                    override fun isOneShot() = true
                    override fun contentType() = body.contentType()
                    override fun contentLength() = body.contentLength()
                    override fun writeTo(sink: BufferedSink) = body.writeTo(sink)
                }
                request.newBuilder().method(method, oneShot).build()
            }
            try {
                chain.proceed(outgoing).also { reportRequest("$method HTTP ${it.code}") }
            } catch (error: IOException) {
                reportRequest("$method connection failed (${error.javaClass.simpleName})")
                throw error
            }
        }.build()
    private val api = Retrofit.Builder().baseUrl(baseUrl).client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build().create(TaskFlowApi::class.java)

    override suspend fun restore(): User? = try {
        val hasSession = withContext(Dispatchers.IO) { cookies.loadForRequest(baseUrl).isNotEmpty() }
        if (hasSession) request { api.me() } else null
    } catch (error: RequestFailure) {
        if (error.status == 401) null else throw error
    }

    override suspend fun register(credentials: Credentials) = request(authenticated = false) {
        api.register(origin, credentials)
    }

    override suspend fun login(credentials: Credentials) = request(authenticated = false) {
        api.login(origin, credentials)
    }

    override suspend fun logout() = mutate { api.logout(it) }.also { clearCookies() }

    override suspend fun tasks(query: TaskQuery, page: Int, limit: Int) = request {
        api.tasks(query.search.takeUnless(String::isEmpty), query.status?.wire, query.sort.wire, page, limit)
    }

    override suspend fun task(id: String) = request { api.task(id) }
    override suspend fun create(input: TaskInput) = mutate { api.create(it, input) }
    override suspend fun update(id: String, input: TaskInput) = mutate { api.update(id, it, input) }
    override suspend fun delete(id: String) = mutate { api.delete(id, it) }
    override suspend fun notices(page: Int) = request { api.notices(page) }
    override suspend fun unread() = request { api.unread().count }

    override suspend fun mark(id: String, read: Boolean) {
        mutate { if (read) api.read(id, it) else api.unread(id, it) }
    }

    override suspend fun markAllRead() = mutate { api.readAll(it) }
    override suspend fun deleteNotice(id: String) = mutate { api.deleteNotice(id, it) }

    private suspend fun <T> mutate(call: suspend (String) -> T): T = request {
        call(api.csrf().token)
    }

    private suspend fun <T> request(authenticated: Boolean = true, call: suspend () -> T): T {
        try {
            return call()
        } catch (error: CancellationException) {
            throw error
        } catch (error: HttpException) {
            val status = error.code()
            if (authenticated && status == 401) clearCookies()
            val body = runCatching {
                error.response()?.errorBody()?.use { json.decodeFromString<ErrorEnvelope>(it.string()).error }
            }.getOrNull()
            val fields = body?.details.orEmpty().mapNotNull { detail ->
                val field = detail.loc.getOrNull(1)?.content
                if (detail.loc.firstOrNull()?.content == "body" && field != null) {
                    field to detail.msg.removePrefix("Value error, ")
                } else null
            }.toMap()
            throw RequestFailure(body?.message ?: "Request failed (HTTP $status).", status, body?.code, fields)
        } catch (_: SerializationException) {
            throw RequestFailure("The server returned an unexpected response.")
        } catch (_: NullPointerException) {
            throw RequestFailure("The server returned an empty response.")
        } catch (_: SessionStorageFailure) {
            throw RequestFailure("Could not save the sign-in session on this device.")
        } catch (_: SocketTimeoutException) {
            throw RequestFailure("The server took too long to respond.", connectivity = true)
        } catch (_: IOException) {
            val message = if (isOnline()) "Cannot reach TaskFlow. Check the server address and try again."
            else "No network connection. Reconnect and try again."
            throw RequestFailure(message, connectivity = true)
        }
    }

    private suspend fun clearCookies() = withContext(Dispatchers.IO) { cookies.clear() }
}
