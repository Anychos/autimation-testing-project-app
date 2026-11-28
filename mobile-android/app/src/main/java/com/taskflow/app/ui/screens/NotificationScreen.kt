package com.taskflow.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.taskflow.app.AppState
import com.taskflow.app.PagedList
import com.taskflow.app.domain.Notice
import com.taskflow.app.ui.components.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationScreen(
    app: AppState, state: PagedList<Notice>, onRefresh: (Boolean) -> Unit,
    onMore: () -> Unit, onMark: (String, Boolean) -> Unit, onMarkAll: () -> Unit,
    onDelete: (String) -> Unit
) {
    var deleteId by rememberSaveable { mutableStateOf<String?>(null) }
    LaunchedEffect(app.deletedNoticeId) {
        if (app.deletedNoticeId == deleteId) deleteId = null
    }
    var retryAppend by rememberSaveable { mutableStateOf(false) }
    PullToRefreshBox(
        state.refreshing,
        { retryAppend = false; onRefresh(true) },
        Modifier.fillMaxSize().testTag("notification_screen")
    ) {
        LazyColumn(
            Modifier.fillMaxSize().testTag("notification_list"), contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(
                        onMarkAll, Modifier.testTag("notification_mark_all_read"),
                        enabled = !app.busy && !state.loading && (state.items.isNotEmpty() || state.hasMore)
                    ) { Text("Mark all read") }
                    TextButton(
                        { retryAppend = false; onRefresh(false) }, Modifier.testTag("notification_refresh"),
                        enabled = !app.busy && !state.loading && !state.refreshing
                    ) { Text("Refresh") }
                }
                if (deleteId == null) Problem(app.error, "notification_action_error")
            }
            if (state.error != null) {
                item {
                    Problem(state.error, "notification_error_state")
                    OutlinedButton(
                        { if (retryAppend) onMore() else onRefresh(false) },
                        Modifier.testTag("notification_retry")
                    ) { Text("Retry") }
                }
            }
            if (state.items.isEmpty() && state.page > 0 && state.error == null) {
                item { Text("No notifications yet.", Modifier.testTag("notification_empty_state")) }
            }
            items(state.items, key = { it.id }) { notice ->
                Card(
                    Modifier.fillMaxWidth().testTag("notification_item_${notice.id}"),
                    colors = CardDefaults.cardColors(
                        containerColor = if (notice.isRead) MaterialTheme.colorScheme.surface
                        else MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(notice.title, style = MaterialTheme.typography.titleMedium)
                        Text(notice.message)
                        Text(if (notice.isRead) "Read" else "Unread",
                            Modifier.testTag("notification_status_${notice.id}"))
                        Text(notice.createdAt.take(10), style = MaterialTheme.typography.labelMedium)
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            val action = if (notice.isRead) "unread" else "read"
                            TextButton(
                                { onMark(notice.id, !notice.isRead) },
                                Modifier.testTag("notification_mark_${action}_${notice.id}"), enabled = !app.busy
                            ) { Text("Mark $action") }
                            TextButton(
                                { deleteId = notice.id },
                                Modifier.testTag("notification_delete_button_${notice.id}"), enabled = !app.busy
                            ) { Text("Delete") }
                        }
                    }
                }
            }
            if (state.loading || app.busy) item { Spinner("notification_loading_state") }
            if (state.hasMore && !state.loading && !state.refreshing && state.error == null) {
                item {
                    OutlinedButton({ retryAppend = true; onMore() }, Modifier.testTag("notification_load_more")) {
                        Text("Load more notifications")
                    }
                }
            }
        }
    }
    deleteId?.let { id ->
        ConfirmDelete("this notification", "notification", app.busy, app.error, { deleteId = null }) {
            onDelete(id)
        }
    }
}
