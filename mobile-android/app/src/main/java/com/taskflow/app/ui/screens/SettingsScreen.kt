package com.taskflow.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.taskflow.app.AppState
import com.taskflow.app.data.ConnectionSettings
import com.taskflow.app.ui.components.*

@Composable
fun SettingsScreen(state: AppState, onSave: (ConnectionSettings) -> Unit, onBack: () -> Unit) {
    var url by rememberSaveable { mutableStateOf(state.settings.apiUrl) }
    var origin by rememberSaveable { mutableStateOf(state.settings.origin) }
    var demo by rememberSaveable { mutableStateOf(state.settings.demo) }

    FormColumn("settings_screen") {
        Heading("Connection settings")
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Demo mode", Modifier.weight(1f))
            Switch(demo, { demo = it }, Modifier.testTag("settings_demo_switch"), enabled = !state.busy)
        }
        if (!demo) {
            OutlinedTextField(
                url, { url = it }, Modifier.fillMaxWidth().testTag("settings_api_url"),
                enabled = !state.busy, label = { Text("API base URL") }, singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri)
            )
            OutlinedTextField(
                origin, { origin = it }, Modifier.fillMaxWidth().testTag("settings_origin"),
                enabled = !state.busy, label = { Text("Allowed authentication origin") }, singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri)
            )
        }
        if (state.user != null) Text("Changing the connection signs you out of this app.")
        Problem(state.error, "settings_error_message")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button({ onSave(ConnectionSettings(url, origin, demo)) },
                Modifier.testTag("settings_save_button"), enabled = !state.busy) { Text("Save") }
            TextButton(onBack, Modifier.testTag("settings_cancel_button"), enabled = !state.busy) { Text("Cancel") }
        }
        if (state.busy) Spinner()
    }
}
