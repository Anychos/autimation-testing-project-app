package com.taskflow.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.taskflow.app.AppState
import com.taskflow.app.TaskDetails
import com.taskflow.app.domain.*
import com.taskflow.app.ui.components.*
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset

@Composable
fun TaskDetailsScreen(
    id: String, details: TaskDetails, app: AppState, onRetry: () -> Unit,
    onEdit: () -> Unit, onDelete: () -> Unit
) {
    var delete by rememberSaveable { mutableStateOf(false) }
    FormColumn("task_details_screen") {
        val task = details.task?.takeIf { it.id == id }
        when {
            details.id == id && details.error != null -> {
                Problem(details.error, "task_details_error")
                Button(onRetry, Modifier.testTag("task_details_retry")) { Text("Retry") }
            }
            task == null -> Spinner()
            else -> {
                Text(task.title, Modifier.testTag("task_details_title"), style = MaterialTheme.typography.headlineSmall)
                Text(task.status.label, Modifier.testTag("task_details_status"), color = MaterialTheme.colorScheme.primary)
                Text(task.description.ifBlank { "No description" }, Modifier.testTag("task_details_description"))
                Text(task.dueDate?.let { "Due $it" } ?: "No due date", Modifier.testTag("task_details_due_date"))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onEdit, Modifier.testTag("task_edit_button"), enabled = !app.busy) { Text("Edit") }
                    OutlinedButton({ delete = true }, Modifier.testTag("task_delete_button"),
                        enabled = !app.busy) { Text("Delete") }
                }
                Problem(app.error, "task_details_error")
                if (app.busy) Spinner()
            }
        }
    }
    if (delete) ConfirmDelete("this task", "task", app.busy, app.error, { delete = false }) {
        onDelete()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TaskForm(
    task: Task?, app: AppState, onCancel: () -> Unit, onSave: (TaskInput) -> Unit
) {
    var title by rememberSaveable { mutableStateOf(task?.title.orEmpty()) }
    var description by rememberSaveable { mutableStateOf(task?.description.orEmpty()) }
    var status by rememberSaveable { mutableStateOf(task?.status ?: TaskStatus.TODO) }
    var dueDate by rememberSaveable { mutableStateOf(task?.dueDate) }
    var selectingDate by rememberSaveable { mutableStateOf(false) }
    val focus = LocalFocusManager.current
    val fields = app.error?.fields.orEmpty()
    FormColumn("task_form") {
        Heading(if (task == null) "New task" else "Edit task")
        OutlinedTextField(
            title, { title = it }, Modifier.fillMaxWidth().testTag("task_title_input"),
            enabled = !app.busy, label = { Text("Title") }, singleLine = true,
            supportingText = { Text(fields["title"] ?: "3–100 characters") },
            isError = fields.containsKey("title")
        )
        OutlinedTextField(
            description, { description = it }, Modifier.fillMaxWidth().testTag("task_description_input"),
            enabled = !app.busy, label = { Text("Description") }, minLines = 3, maxLines = 5,
            supportingText = { Text(fields["description"] ?: "Up to 500 characters") },
            isError = fields.containsKey("description")
        )
        Choice("Status", status, TaskStatus.entries, { it.label }, { it.wire }, "task_status_select",
            enabled = !app.busy) { status = it }
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                { focus.clearFocus(); selectingDate = true },
                Modifier.testTag("task_due_date_input"), enabled = !app.busy
            ) { Text(dueDate?.let { "Due $it" } ?: "Choose due date") }
            if (dueDate != null) {
                TextButton({ dueDate = null }, Modifier.testTag("task_clear_due_date_button"),
                    enabled = !app.busy) { Text("Clear date") }
            }
        }
        fields["due_date"]?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Problem(app.error, "task_form_error")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                { focus.clearFocus(); onSave(TaskInput(title, description, status, dueDate)) },
                Modifier.testTag("task_submit_button"), enabled = !app.busy
            ) { Text("Save task") }
            TextButton(onCancel, Modifier.testTag("task_cancel_button"), enabled = !app.busy) { Text("Cancel") }
        }
        if (app.busy) Spinner()
    }
    if (selectingDate) {
        val picker = rememberDatePickerState(
            initialSelectedDateMillis = dueDate?.let {
                LocalDate.parse(it).atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli()
            },
            yearRange = 1..9999
        )
        DatePickerDialog(
            onDismissRequest = { selectingDate = false },
            modifier = Modifier.appiumRoot().testTag("task_date_picker"),
            confirmButton = {
                TextButton(
                    {
                        dueDate = picker.selectedDateMillis?.let {
                            Instant.ofEpochMilli(it).atOffset(ZoneOffset.UTC).toLocalDate().toString()
                        }
                        selectingDate = false
                    },
                    Modifier.testTag("task_date_picker_confirm"), enabled = picker.selectedDateMillis != null
                ) { Text("OK") }
            },
            dismissButton = {
                TextButton({ selectingDate = false }, Modifier.testTag("task_date_picker_cancel")) { Text("Cancel") }
            }
        ) { DatePicker(picker, Modifier.weight(1f, fill = false)) }
    }
}
