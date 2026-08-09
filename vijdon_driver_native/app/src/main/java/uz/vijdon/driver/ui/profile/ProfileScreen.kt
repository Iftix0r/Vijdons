package uz.vijdon.driver.ui.profile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.AddCard
import androidx.compose.material.icons.rounded.CameraAlt
import androidx.compose.material.icons.rounded.DirectionsCar
import androidx.compose.material.icons.rounded.Description
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material.icons.rounded.Receipt
import androidx.compose.material.icons.rounded.Sos
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.VijdonColors
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

    // `driver` — sessiya boshida (kirishda) olingan bir martalik nusxa, shu
    // sabab bu yerda har safar ekranga kirilganda haqiqiy balans/safarlar
    // sonini serverdan qayta so'raymiz — aks holda balans hech qachon
    // yangilanmasdi (masalan buyurtma qabul qilib komissiya yechilgandan keyin).
    LaunchedEffect(Unit) { viewModel.refresh() }

    val photoLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let {
            copyUriToCacheFile(context, it, "profile_photo.jpg")?.let { file -> viewModel.uploadPhoto(file) }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(VijdonColors.Background)
            .padding(16.dp),
    ) {
        Box(
            modifier = Modifier.fillMaxWidth().background(VijdonColors.Surface, CardShape).padding(vertical = 12.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text("Profil", color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleLarge)
        }

        Spacer(Modifier.height(20.dp))
        Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Box {
                Box(
                    modifier = Modifier
                        .size(88.dp)
                        .clip(CircleShape)
                        .background(VijdonColors.Red)
                        .clickable { photoLauncher.launch("image/*") },
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        currentDriver.full_name.trim().firstOrNull()?.uppercase() ?: "?",
                        color = VijdonColors.TextPrimary,
                        style = MaterialTheme.typography.headlineMedium,
                    )
                }
                Box(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .size(28.dp)
                        .clip(CircleShape)
                        .background(VijdonColors.Blue)
                        .clickable { photoLauncher.launch("image/*") },
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Rounded.CameraAlt, contentDescription = "Rasm yuklash", tint = VijdonColors.TextPrimary, modifier = Modifier.size(16.dp))
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        Text(currentDriver.full_name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleLarge, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
        Text(currentDriver.phone_number, color = VijdonColors.TextSecondary, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
        Spacer(Modifier.height(8.dp))
        Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Pill(if (currentDriver.is_on_duty) "Onlayn" else "Oflayn", color = if (currentDriver.is_on_duty) VijdonColors.Green else VijdonColors.TextSecondary)
        }

        Spacer(Modifier.height(20.dp))
        Column(modifier = Modifier.fillMaxWidth().background(VijdonColors.Surface, CardShape).padding(16.dp)) {
            Text("JORIY BALANS", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
            Row(verticalAlignment = Alignment.Bottom) {
                Text(currentDriver.balance, color = VijdonColors.Green, style = MaterialTheme.typography.headlineMedium)
                Spacer(Modifier.width(6.dp))
                Text("so'm", color = VijdonColors.TextSecondary, modifier = Modifier.padding(bottom = 6.dp))
            }
        }

        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StatBox("Safarlar", currentDriver.trips_count.toString(), Modifier.weight(1f))
            StatBox("Reyting", currentDriver.rating, Modifier.weight(1f))
            StatBox("Daraja", currentDriver.level, Modifier.weight(1f))
        }

        Spacer(Modifier.height(20.dp))
        Text("TRANSPORT VOSITASI", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(6.dp))
        MenuRow(Icons.Rounded.DirectionsCar, currentDriver.car_model, currentDriver.car_number, showChevron = false) {}

        Spacer(Modifier.height(16.dp))
        Text("SOZLAMALAR", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(6.dp))
        MenuRow(Icons.Rounded.Receipt, "Balans tarixi", "", onClick = onOpenBalanceHistory)
        Spacer(Modifier.height(8.dp))
        MenuRow(Icons.Rounded.AddCard, "Balans to'ldirish", "", onClick = onOpenTopup)
        Spacer(Modifier.height(8.dp))
        MenuRow(Icons.Rounded.Description, "Shartnoma", "", onClick = onOpenContract)
        Spacer(Modifier.height(8.dp))
        MenuRow(Icons.Rounded.LocationOn, "Yaqin manzillar", "", onClick = onOpenAddresses)
        Spacer(Modifier.height(8.dp))
        MenuRow(Icons.Rounded.Sos, "SOS", "", tint = VijdonColors.Red, onClick = onOpenSos)
        Spacer(Modifier.height(8.dp))
        MenuRow(Icons.Rounded.Lock, "Parolni o'zgartirish", "") { showPasswordDialog = true }

        state.error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = VijdonColors.Red)
        }

        Spacer(Modifier.height(20.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(VijdonColors.Surface, CardShape)
                .clickable(onClick = onLogout)
                .padding(vertical = 16.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text("Tizimdan chiqish", color = VijdonColors.Red, style = MaterialTheme.typography.titleMedium)
        }
        Spacer(Modifier.height(24.dp))
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
private fun StatBox(label: String, value: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.background(VijdonColors.Surface, CardShape).padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(label, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(4.dp))
        Text(value, color = VijdonColors.Yellow, style = MaterialTheme.typography.titleMedium)
    }
}

@Composable
private fun MenuRow(
    icon: ImageVector,
    title: String,
    subtitle: String,
    tint: androidx.compose.ui.graphics.Color = VijdonColors.TextPrimary,
    showChevron: Boolean = true,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(12.dp))
            Text(title, color = VijdonColors.TextPrimary)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (subtitle.isNotBlank()) {
                Text(subtitle, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.width(4.dp))
            }
            if (showChevron) {
                Icon(Icons.AutoMirrored.Rounded.KeyboardArrowRight, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(18.dp))
            }
        }
    }
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
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = VijdonColors.Surface, unfocusedContainerColor = VijdonColors.Surface,
                        focusedTextColor = VijdonColors.TextPrimary, unfocusedTextColor = VijdonColors.TextPrimary,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = newPassword, onValueChange = { newPassword = it },
                    label = { Text("Yangi parol") }, visualTransformation = PasswordVisualTransformation(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = VijdonColors.Surface, unfocusedContainerColor = VijdonColors.Surface,
                        focusedTextColor = VijdonColors.TextPrimary, unfocusedTextColor = VijdonColors.TextPrimary,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
                passwordError?.let { Text(it, color = VijdonColors.Red) }
                passwordMessage?.let { Text(it, color = VijdonColors.Green) }
            }
        },
        confirmButton = {
            Button(onClick = { onSubmit(oldPassword, newPassword) }) { Text("Saqlash") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Yopish") } },
        containerColor = VijdonColors.Surface,
    )
}
