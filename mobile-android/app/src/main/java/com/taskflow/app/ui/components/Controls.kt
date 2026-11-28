package com.taskflow.app.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.taskflow.app.domain.RequestFailure

@OptIn(androidx.compose.ui.ExperimentalComposeUiApi::class)
fun Modifier.appiumRoot(): Modifier = semantics { testTagsAsResourceId = true }

@Composable
fun Heading(title: String) {
    Text(title, style = MaterialTheme.typography.headlineSmall)
}

@Composable
fun FormColumn(tag: String, content: @Composable ColumnScope.() -> Unit) {
    Box(Modifier.fillMaxSize().testTag(tag), contentAlignment = Alignment.TopCenter) {
        Column(
            Modifier.widthIn(max = 560.dp).fillMaxWidth().verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            content = content
        )
    }
}

@Composable
fun Problem(error: RequestFailure?, tag: String) {
    if (error == null) return
    val color = MaterialTheme.colorScheme.error
    val style = MaterialTheme.typography.bodyMedium
    if (error.connectivity) {
        Box(Modifier.testTag(tag)) {
            Text(error.message, Modifier.testTag("network_error_message"), color = color, style = style)
        }
    } else {
        Text(error.message, Modifier.testTag(tag), color = color, style = style)
    }
}

@Composable
fun Spinner(tag: String = "loading_indicator") {
    Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(Modifier.size(32.dp).testTag(tag))
    }
}

@Composable
fun BackButton(tag: String, onClick: () -> Unit) {
    IconButton(onClick = onClick, modifier = Modifier.testTag(tag)) {
        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
    }
}

@Composable
fun PasswordInput(value: String, onChange: (String) -> Unit, tag: String, toggleTag: String,
                  label: String, enabled: Boolean, error: String? = null) {
    var visible by rememberSaveable { mutableStateOf(false) }
    OutlinedTextField(
        value, onChange, Modifier.fillMaxWidth().testTag(tag),
        enabled = enabled, singleLine = true, label = { Text(label) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(),
        isError = error != null, supportingText = error?.let { { Text(it) } },
        trailingIcon = {
            TextButton({ visible = !visible }, Modifier.testTag(toggleTag), enabled = enabled) {
                Text(if (visible) "Hide" else "Show")
            }
        }
    )
}

@Composable
fun <T> Choice(
    label: String, selected: T, options: List<T>, text: (T) -> String, key: (T) -> String,
    tag: String, enabled: Boolean = true, onSelect: (T) -> Unit
) {
    var open by remember { mutableStateOf(false) }
    Box {
        OutlinedButton({ open = true }, Modifier.testTag(tag), enabled = enabled) {
            Text("$label · ${text(selected)}")
        }
        DropdownMenu(open, { open = false }, Modifier.appiumRoot()) {
            for (option in options) {
                DropdownMenuItem(
                    text = { Text(text(option)) },
                    onClick = { open = false; onSelect(option) },
                    modifier = Modifier.testTag("${tag}_${key(option)}")
                )
            }
        }
    }
}

@Composable
fun ConfirmDelete(
    name: String, prefix: String, busy: Boolean, error: RequestFailure?,
    onDismiss: () -> Unit, onConfirm: () -> Unit
) {
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        modifier = Modifier.appiumRoot().testTag("confirmation_dialog"),
        title = { Text("Delete $name?") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("This action is permanent.")
                Problem(error, "${prefix}_delete_error")
                if (busy) Spinner()
            }
        },
        confirmButton = {
            TextButton(onConfirm, Modifier.testTag("${prefix}_delete_confirm_button"), enabled = !busy) {
                Text("Delete", color = MaterialTheme.colorScheme.error)
            }
        },
        dismissButton = {
            TextButton(onDismiss, Modifier.testTag("${prefix}_delete_cancel_button"), enabled = !busy) {
                Text("Cancel")
            }
        }
    )
}
