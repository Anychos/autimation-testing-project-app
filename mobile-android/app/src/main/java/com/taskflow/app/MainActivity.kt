package com.taskflow.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color
import androidx.lifecycle.viewmodel.compose.viewModel
import com.taskflow.app.navigation.TaskFlowNavigation

private val LightColors = lightColorScheme(
    primary = Color(0xFF2E64DC),
    onPrimary = Color.White,
    background = Color(0xFFF4F7FC),
    onBackground = Color(0xFF1F2A40),
    surface = Color.White,
    onSurface = Color(0xFF1F2A40),
    surfaceVariant = Color(0xFFE7EDF8),
    onSurfaceVariant = Color(0xFF475569),
    error = Color(0xFFB32636)
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFAEC6FF),
    onPrimary = Color(0xFF002B74),
    background = Color(0xFF101827),
    surface = Color(0xFF172337),
    surfaceVariant = Color(0xFF26354D),
    onSurfaceVariant = Color(0xFFCDD7EB)
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme(colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors) {
                TaskFlowNavigation(viewModel<TaskFlowViewModel>())
            }
        }
    }
}
