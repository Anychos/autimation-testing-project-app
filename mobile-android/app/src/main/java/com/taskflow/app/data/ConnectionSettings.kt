package com.taskflow.app.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.taskflow.app.BuildConfig
import kotlinx.coroutines.flow.first
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

private val Context.connectionStore by preferencesDataStore("taskflow_connection")

data class ConnectionSettings(
    val apiUrl: String = BuildConfig.API_URL,
    val origin: String = BuildConfig.API_ORIGIN,
    val demo: Boolean = false
) {
    fun parsedUrl(): HttpUrl? {
        val url = apiUrl.trim().toHttpUrlOrNull() ?: return null
        if (url.username.isNotEmpty() || url.password.isNotEmpty() || url.query != null ||
            url.fragment != null || (!BuildConfig.DEBUG && !url.isHttps)) return null
        return url.newBuilder().encodedPath(url.encodedPath.trimEnd('/') + "/").build()
    }

    fun validOrigin(): Boolean {
        val value = origin.trim()
        val url = value.toHttpUrlOrNull() ?: return false
        if (!BuildConfig.DEBUG && !url.isHttps) return false
        return url.username.isEmpty() && url.password.isEmpty() && url.encodedPath == "/" &&
            url.query == null && url.fragment == null &&
            value == url.toString().removeSuffix("/")
    }
}

class ConnectionStore(private val context: Context) {
    private val url = stringPreferencesKey("base_url")
    private val origin = stringPreferencesKey("origin")
    private val demo = booleanPreferencesKey("demo")

    suspend fun load(): ConnectionSettings {
        if (!BuildConfig.DEBUG) return ConnectionSettings()
        val values = context.connectionStore.data.first()
        return ConnectionSettings(values[url] ?: BuildConfig.API_URL,
            values[origin] ?: BuildConfig.API_ORIGIN, values[demo] ?: false)
    }

    suspend fun save(settings: ConnectionSettings) {
        check(BuildConfig.DEBUG)
        context.connectionStore.edit {
            it[url] = settings.apiUrl
            it[origin] = settings.origin
            it[demo] = settings.demo
        }
    }
}
