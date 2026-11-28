package com.taskflow.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.KeyboardType
import com.taskflow.app.AppState
import com.taskflow.app.AuthInput
import com.taskflow.app.domain.Credentials
import com.taskflow.app.ui.components.*

@Composable
fun AuthScreen(
    register: Boolean,
    state: AppState,
    input: AuthInput,
    emailHint: String,
    registered: Boolean,
    onSwitch: () -> Unit,
    onSubmit: (Credentials) -> Unit
) {
    val prefix = if (register) "registration" else "login"
    var email by rememberSaveable { mutableStateOf(emailHint) }
    var appliedHint by rememberSaveable { mutableStateOf(emailHint) }
    var mismatch by rememberSaveable { mutableStateOf(false) }
    val focus = LocalFocusManager.current
    val emailError = state.error?.fields?.get("email")

    LaunchedEffect(emailHint, registered) {
        if (!register && registered && appliedHint != emailHint) {
            email = emailHint
            input.clear()
            appliedHint = emailHint
        }
    }

    FormColumn("${prefix}_screen") {
        Heading(if (register) "Create your account" else "Sign in to TaskFlow")
        if (registered && !register) {
            Text("Account created. You can sign in now.", Modifier.testTag("registration_success_message"))
        }
        if (state.sessionExpired && !register) {
            Text("Your session expired. Sign in again.", Modifier.testTag("session_expired_message"))
        }
        OutlinedTextField(
            email, { email = it }, Modifier.fillMaxWidth().testTag("${prefix}_email_input"),
            enabled = !state.busy, singleLine = true, label = { Text("Email") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            isError = emailError != null, supportingText = emailError?.let { { Text(it) } }
        )
        PasswordInput(input.password, { input.password = it; mismatch = false }, "${prefix}_password_input",
            "${prefix}_password_visibility", "Password", !state.busy, state.error?.fields?.get("password"))
        if (register) {
            PasswordInput(input.confirmation, { input.confirmation = it; mismatch = false },
                "registration_confirm_password_input", "registration_confirm_password_visibility",
                "Confirm password", !state.busy, if (mismatch) "Passwords must match" else null)
        }
        Problem(state.error, "${prefix}_error_message")
        Button(
            onClick = {
                mismatch = register && input.password != input.confirmation
                if (!mismatch) {
                    focus.clearFocus()
                    onSubmit(Credentials(email, input.password))
                }
            },
            modifier = Modifier.fillMaxWidth().testTag("${prefix}_submit_button"),
            enabled = !state.busy
        ) { Text(if (register) "Create account" else "Sign in") }
        TextButton({ input.clear(); onSwitch() }, Modifier.testTag(if (register) "registration_login_link" else "login_register_link"),
            enabled = !state.busy) {
            Text(if (register) "Back to sign in" else "Create an account")
        }
        if (state.settings.demo) Text("Demo account\ndemo@taskflow.local · taskflow-demo")
        if (state.busy) Spinner()
    }
}
