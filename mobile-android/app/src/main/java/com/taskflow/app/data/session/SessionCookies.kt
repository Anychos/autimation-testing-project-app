package com.taskflow.app.data.session

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import java.io.IOException
import java.nio.charset.StandardCharsets.UTF_8
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

interface SessionCookies : CookieJar {
    fun clear()
}

class KeystoreSessionCookies(context: Context, private val baseUrl: HttpUrl) : SessionCookies {
    private val preferences = context.getSharedPreferences("taskflow_session", Context.MODE_PRIVATE)
    private val scope = baseUrl.toString()

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        if (!sameOrigin(url)) return
        val cookie = cookies.lastOrNull { it.name == "taskflow_session" } ?: return
        if (cookie.expiresAt <= System.currentTimeMillis()) {
            clear()
            return
        }
        try {
            val cipher = cipher()
            cipher.init(Cipher.ENCRYPT_MODE, key())
            cipher.updateAAD(scope.toByteArray(UTF_8))
            val encrypted = cipher.doFinal(cookie.toString().toByteArray(UTF_8))
            check(preferences.edit().putString("cookie", encode(cipher.iv) + ":" + encode(encrypted)).commit())
        } catch (error: Exception) {
            throw SessionStorageFailure(error)
        }
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        if (!sameOrigin(url)) return emptyList()
        val stored = preferences.getString("cookie", null) ?: return emptyList()
        val cookie = try {
            val (iv, ciphertext) = stored.split(":", limit = 2)
            val cipher = cipher()
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
            cipher.updateAAD(scope.toByteArray(UTF_8))
            Cookie.parse(baseUrl, String(cipher.doFinal(Base64.decode(ciphertext, Base64.NO_WRAP)), UTF_8))
        } catch (_: Exception) {
            clear()
            return emptyList()
        }
        if (cookie == null || cookie.expiresAt <= System.currentTimeMillis()) {
            clear()
            return emptyList()
        }
        return listOf(cookie).filter { it.matches(url) }
    }

    @Synchronized
    override fun clear() {
        preferences.edit().remove("cookie").commit()
    }

    private fun sameOrigin(url: HttpUrl) =
        url.scheme == baseUrl.scheme && url.host == baseUrl.host && url.port == baseUrl.port

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val alias = "com.taskflow.app.session.v1"
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(
                KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .build()
            )
        }.generateKey()
    }

    private fun cipher() = Cipher.getInstance("AES/GCM/NoPadding")
    private fun encode(bytes: ByteArray) = Base64.encodeToString(bytes, Base64.NO_WRAP)
}

class SessionStorageFailure(cause: Throwable) : IOException("Could not store the session.", cause)
