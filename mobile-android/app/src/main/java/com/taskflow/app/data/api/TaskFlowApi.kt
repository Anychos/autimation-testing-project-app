package com.taskflow.app.data.api

import com.taskflow.app.domain.*
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonPrimitive
import retrofit2.http.*

@Serializable
data class Csrf(@SerialName("csrf_token") val token: String)

@Serializable
data class UnreadCount(val count: Int)

@Serializable
data class ErrorEnvelope(val error: ErrorBody)

@Serializable
data class ErrorBody(
    val code: String,
    val message: String,
    val details: List<ErrorDetail> = emptyList()
)

@Serializable
data class ErrorDetail(val loc: List<JsonPrimitive>, val msg: String)

interface TaskFlowApi {
    @POST("api/v1/auth/register")
    suspend fun register(@Header("Origin") origin: String, @Body body: Credentials): User

    @POST("api/v1/auth/login")
    suspend fun login(@Header("Origin") origin: String, @Body body: Credentials): User

    @GET("api/v1/auth/me")
    suspend fun me(): User

    @GET("api/v1/auth/csrf")
    suspend fun csrf(): Csrf

    @POST("api/v1/auth/logout")
    suspend fun logout(@Header("X-CSRF-Token") csrf: String)

    @GET("api/v1/tasks")
    suspend fun tasks(
        @Query("q") search: String?, @Query("status") status: String?,
        @Query("sort") sort: String, @Query("page") page: Int, @Query("limit") limit: Int
    ): TaskPage

    @GET("api/v1/tasks/{id}")
    suspend fun task(@Path("id") id: String): Task

    @POST("api/v1/tasks")
    suspend fun create(@Header("X-CSRF-Token") csrf: String, @Body body: TaskInput): Task

    @PATCH("api/v1/tasks/{id}")
    suspend fun update(
        @Path("id") id: String, @Header("X-CSRF-Token") csrf: String, @Body body: TaskInput
    ): Task

    @DELETE("api/v1/tasks/{id}")
    suspend fun delete(@Path("id") id: String, @Header("X-CSRF-Token") csrf: String)

    @GET("api/v1/notifications")
    suspend fun notices(@Query("page") page: Int): NoticePage

    @GET("api/v1/notifications/unread-count")
    suspend fun unread(): UnreadCount

    @PATCH("api/v1/notifications/{id}/read")
    suspend fun read(@Path("id") id: String, @Header("X-CSRF-Token") csrf: String): Notice

    @PATCH("api/v1/notifications/{id}/unread")
    suspend fun unread(@Path("id") id: String, @Header("X-CSRF-Token") csrf: String): Notice

    @POST("api/v1/notifications/read-all")
    suspend fun readAll(@Header("X-CSRF-Token") csrf: String)

    @DELETE("api/v1/notifications/{id}")
    suspend fun deleteNotice(@Path("id") id: String, @Header("X-CSRF-Token") csrf: String)
}
