package uz.vijdon.driver.ui.profile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.util.copyUriToCacheFile

@Composable
fun ProfileScreen(
    driver: DriverDto,
    onOpenBalanceHistory: () -> Unit,
    onOpenTopup: () -> Unit,
    onOpenContract: () -> Unit,
    onOpenAddresses: () -> Unit,
    onOpenSos: () -> Unit,
    onLogout: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    var showPasswordDialog by remember { mutableStateOf(false) }

    val currentDriver = state.driver ?: driver

    val photoLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let {
            copyUriToCacheFile(context, it, "profile_photo.jpg")?.let { file -> viewModel.uploadPhoto(file) }
        }
    }

    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            Text(currentDriver.full_name, style = MaterialTheme.typography.headlineSmall)
            Text(currentDriver.phone_number, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(4.dp))
            Text("${currentDriver.car_type_display} · ${currentDriver.car_model} · ${currentDriver.car_number}", style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(4.dp))
            Text("${currentDriver.trips_count} safar · ${currentDriver.rating} ⭐ · ${currentDriver.level}", style = MaterialTheme.typography.bodySmall)

            Spacer(Modifier.height(16.dp))
            OutlinedButton(onClick = { photoLauncher.launch("image/*") }, modifier = Modifier.fillMaxWidth()) {
                Text(if (state.uploadingPhoto) "Yuklanmoqda..." else "Rasm yuklash")
            }

            Spacer(Modifier.height(20.dp))
            Card(modifier = Modifier.fillMaxWidth()) {
                Column {
                    ProfileMenuItem("Balans tarixi", onOpenBalanceHistory)
                    ProfileMenuItem("Balans to'ldirish", onOpenTopup)
                    ProfileMenuItem("Shartnoma", onOpenContract)
                    ProfileMenuItem("Yaqin manzillar", onOpenAddresses)
                    ProfileMenuItem("SOS", onOpenSos)
                    ProfileMenuItem("Parolni o'zgartirish") { showPasswordDialog = true }
                }
            }

            state.error?.let {
                Spacer(Modifier.height(8.dp))
                Text(it, color = MaterialTheme.colorScheme.error)
            }

            Spacer(Modifier.height(20.dp))
            TextButton(onClick = onLogout) { Text("Chiqish") }
        }
    }

    if (showPasswordDialog) {
        PasswordChangeDialog(
            passwordMessage = state.passwordMessage,
            passwordError = state.passwordError,
            onDismiss = { showPasswordDialog = false },
            onSubmit = viewModel::changePassword,
        )
    }
}

@Composable
private fun ProfileMenuItem(label: String, onClick: () -> Unit) {
    androidx.compose.material3.ListItem(
        headlineContent = { Text(label) },
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    )
}

@Composable
private fun PasswordChangeDialog(
    passwordMessage: String?,
    passwordError: String?,
    onDismiss: () -> Unit,
    onSubmit: (String, String) -> Unit,
) {
    var oldPassword by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Parolni o'zgartirish") },
        text = {
            Column {
                OutlinedTextField(
                    value = oldPassword, onValueChange = { oldPassword = it },
                    label = { Text("Eski parol") }, visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = newPassword, onValueChange = { newPassword = it },
                    label = { Text("Yangi parol") }, visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                )
                passwordError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                passwordMessage?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            }
        },
        confirmButton = {
            Button(onClick = { onSubmit(oldPassword, newPassword) }) { Text("Saqlash") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Yopish") } },
    )
}
