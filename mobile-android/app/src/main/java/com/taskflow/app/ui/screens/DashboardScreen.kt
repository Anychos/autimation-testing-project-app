package com.taskflow.app.ui.screens

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.taskflow.app.AppState
import com.taskflow.app.PagedList
import com.taskflow.app.domain.*
import com.taskflow.app.ui.components.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    app: AppState,
    list: PagedList<Task>,
    counts: TaskCounts?,
    query: TaskQuery,
    onQuery: (TaskQuery) -> Unit,
    onRefresh: () -> Unit,
    onMore: () -> Unit,
    onRetry: () -> Unit,
    onOpen: (String) -> Unit,
    onEdit: (String) -> Unit,
    onDelete: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var deleteId by rememberSaveable { mutableStateOf<String?>(null) }
    LaunchedEffect(app.deletedTaskId) {
        if (app.deletedTaskId == deleteId) deleteId = null
    }
    var retryAppend by rememberSaveable { mutableStateOf(false) }
    PullToRefreshBox(
        isRefreshing = list.refreshing,
        onRefresh = { retryAppend = false; onRefresh() },
        modifier = modifier.fillMaxSize().testTag("dashboard_screen")
    ) {
        LazyColumn(
            Modifier.fillMaxSize().testTag("dashboard_task_list"),
            contentPadding = PaddingValues(start = 16.dp, top = 12.dp, end = 16.dp, bottom = 96.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Heading("Your tasks")
                    Text("Welcome, ${app.user?.email.orEmpty()}", Modifier.testTag("dashboard_welcome"))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Metric("Total", counts?.total, "dashboard_total_count", Modifier.weight(1f))
                        Metric("In progress", counts?.inProgress, "dashboard_in_progress_count", Modifier.weight(1f))
                        Metric("Completed", counts?.done, "dashboard_completed_count", Modifier.weight(1f))
                    }
                    if (counts == null && !list.loading && !list.refreshing && list.error == null) {
                        OutlinedButton(onRetry, Modifier.testTag("dashboard_counts_retry")) { Text("Retry counts") }
                    }
                    OutlinedTextField(
                        query.search, { retryAppend = false; onQuery(query.copy(search = it)) },
                        Modifier.fillMaxWidth().testTag("dashboard_search_input"),
                        label = { Text("Search by title") }, singleLine = true,
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search)
                    )
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Choice("Status", query.status, listOf(null) + TaskStatus.entries,
                            { it?.label ?: "All" }, { it?.wire ?: "all" }, "dashboard_status_filter") {
                            retryAppend = false
                            onQuery(query.copy(status = it))
                        }
                        Choice("Sort", query.sort, TaskSort.entries, { it.label }, { it.wire }, "dashboard_sort_select") {
                            retryAppend = false
                            onQuery(query.copy(sort = it))
                        }
                    }
                }
            }
            if (list.error != null) {
                item {
                    Problem(list.error, "dashboard_error_state")
                    OutlinedButton(if (retryAppend) onMore else onRetry, Modifier.testTag("dashboard_retry_button")) {
                        Text("Retry")
                    }
                }
            }
            if (list.items.isEmpty() && !list.loading && !list.refreshing && list.error == null) {
                item {
                    Text(
                        if (query.search.isEmpty() && query.status == null) "No tasks yet." else "No matching tasks.",
                        Modifier.testTag("dashboard_empty_state")
                    )
                }
            }
            items(list.items, key = { it.id }) { task ->
                TaskCard(task, !app.busy, { onOpen(task.id) }, { onEdit(task.id) }, { deleteId = task.id })
            }
            if (list.loading || app.busy) item { Spinner("dashboard_loading_state") }
            if (list.hasMore && !list.loading && !list.refreshing && list.error == null) {
                item {
                    OutlinedButton(
                        { retryAppend = true; onMore() }, Modifier.fillMaxWidth().testTag("dashboard_load_more")
                    ) { Text("Load more tasks") }
                }
            }
            if (deleteId == null && app.error != null) {
                item { Problem(app.error, "dashboard_action_error") }
            }
        }
    }
    deleteId?.let { id ->
        ConfirmDelete("this task", "task", app.busy, app.error, { deleteId = null }) {
            onDelete(id)
        }
    }
}

@Composable
private fun Metric(label: String, value: Int?, tag: String, modifier: Modifier) {
    Surface(modifier, shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.surface) {
        Column(Modifier.padding(10.dp)) {
            Text(value?.toString() ?: "—", Modifier.testTag(tag), style = MaterialTheme.typography.titleLarge)
            Text(label, style = MaterialTheme.typography.labelMedium)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
private fun TaskCard(task: Task, enabled: Boolean, open: () -> Unit, edit: () -> Unit, delete: () -> Unit) {
    var menu by remember { mutableStateOf(false) }
    val key = task.id
    val swipe = rememberSwipeToDismissBoxState(confirmValueChange = { direction ->
        if (enabled && direction == SwipeToDismissBoxValue.EndToStart) delete()
        false
    })
    SwipeToDismissBox(
        state = swipe,
        enableDismissFromStartToEnd = false,
        enableDismissFromEndToStart = enabled,
        backgroundContent = {
            Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.errorContainer,
                shape = MaterialTheme.shapes.medium) {
                Box(Modifier.padding(end = 16.dp), contentAlignment = Alignment.CenterEnd) {
                    Icon(Icons.Default.Delete, contentDescription = null)
                }
            }
        }
    ) {
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
            Row(
                Modifier.fillMaxWidth().testTag("task_item_$key")
                    .combinedClickable(enabled = enabled, onClick = open, onLongClick = { menu = true },
                        onLongClickLabel = "Task actions")
                    .padding(start = 14.dp, top = 10.dp, bottom = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(task.title, Modifier.testTag("task_title_$key"), style = MaterialTheme.typography.titleMedium)
                    Text(task.status.label, Modifier.testTag("task_status_$key"),
                        color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelLarge)
                    if (task.description.isNotBlank()) {
                        Text(task.description, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    }
                    task.dueDate?.let { Text("Due $it", Modifier.testTag("task_due_date_$key")) }
                }
                Box {
                    IconButton({ menu = true }, Modifier.testTag("task_menu_$key"), enabled = enabled) {
                        Icon(Icons.Default.MoreVert, contentDescription = "Task actions")
                    }
                    DropdownMenu(menu, { menu = false }, Modifier.appiumRoot()) {
                        DropdownMenuItem(text = { Text("Edit") }, onClick = { menu = false; edit() },
                            modifier = Modifier.testTag("task_menu_edit_$key"))
                        DropdownMenuItem(text = { Text("Delete") }, onClick = { menu = false; delete() },
                            modifier = Modifier.testTag("task_menu_delete_$key"))
                    }
                }
            }
        }
    }
}
