package uz.vijdon.driver.ui.profile

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.AccountBalanceWallet
import androidx.compose.material.icons.rounded.AddCard
import androidx.compose.material.icons.rounded.CameraAlt
import androidx.compose.material.icons.rounded.DirectionsCar
import androidx.compose.material.icons.rounded.Description
import androidx.compose.material.icons.rounded.FiberManualRecord
import androidx.compose.material.icons.rounded.Flag
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Receipt
import androidx.compose.material.icons.rounded.Star
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.BuildConfig
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.TabHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow
import uz.vijdon.driver.util.copyUriToCacheFile
import uz.vijdon.driver.util.formatMoney

@Composable
fun ProfileScreen(
    driver: DriverDto,
    onOpenBalanceHistory: () -> Unit,
    onOpenTopup: () -> Unit,
    onOpenContract: () -> Unit,
    onLogout: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    var showPasswordDialog by remember { mutableStateOf(false) }
    var showLogoutDialog by remember { mutableStateOf(false) }
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
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        TabHeader("Profil")

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
            Pill(if (currentDriver.is_on_duty) "Ish navbatida" else "Oflayn", color = if (currentDriver.is_on_duty) VijdonColors.GreenBadge else VijdonColors.TextSecondary)
        }

        Spacer(Modifier.height(20.dp))
        Column(modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.AccountBalanceWallet, contentDescription = null, tint = VijdonColors.Yellow, modifier = Modifier.size(11.dp))
                Spacer(Modifier.width(6.dp))
                Text("JORIY BALANS", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
            }
            Row(verticalAlignment = Alignment.Bottom) {
                Text(formatMoney(currentDriver.balance), color = VijdonColors.Green, style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold))
                Spacer(Modifier.width(6.dp))
                Text("so'm", color = VijdonColors.TextSecondary, modifier = Modifier.padding(bottom = 6.dp))
            }
        }

        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StatBox("Safarlar", currentDriver.trips_count.toString(), Icons.Rounded.Flag, VijdonColors.Yellow, Modifier.weight(1f), valueColor = VijdonColors.Yellow)
            StatBox("Reyting", currentDriver.rating, Icons.Rounded.Star, Color(0xFFFF9500), Modifier.weight(1f), valueColor = Color(0xFFFF9500))
            StatBox(
                "Navbat",
                if (currentDriver.is_on_duty) "Faol" else "—",
                Icons.Rounded.FiberManualRecord,
                if (currentDriver.is_on_duty) VijdonColors.Green else Color(0xFF8E8E93),
                Modifier.weight(1f),
                valueColor = if (currentDriver.is_on_duty) VijdonColors.Green else VijdonColors.TextSecondary,
            )
        }

        Spacer(Modifier.height(20.dp))
        Text("TRANSPORT VOSITASI", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(6.dp))
        MenuRow(Icons.Rounded.DirectionsCar, currentDriver.car_model, currentDriver.car_number, tint = VijdonColors.Blue, showChevron = false) {}

        Spacer(Modifier.height(16.dp))
        Text("SOZLAMALAR", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(6.dp))
        MenuRow(Icons.Rounded.Receipt, "Balans tarixi", "", tint = VijdonColors.Yellow, onClick = onOpenBalanceHistory)
        Spacer(Modifier.height(8.dp))
        MenuRow(Icons.Rounded.AddCard, "Balans to'ldirish", "", tint = VijdonColors.Green, onClick = onOpenTopup)
        Spacer(Modifier.height(8.dp))
        MenuRow(Icons.Rounded.Description, "Shartnoma", "", tint = VijdonColors.Blue, onClick = onOpenContract)
        Spacer(Modifier.height(8.dp))
        MenuRow(Icons.Rounded.Lock, "Parolni o'zgartirish", "", tint = Color(0xFF8E8E93)) { showPasswordDialog = true }

        state.error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = VijdonColors.Red)
        }

        Spacer(Modifier.height(20.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(VijdonColors.Surface, CardShape)
                .clickable { showLogoutDialog = true }
                .padding(vertical = 16.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text("Tizimdan chiqish", color = VijdonColors.Red, style = MaterialTheme.typography.titleMedium)
        }

        Spacer(Modifier.height(24.dp))
        AppFooter()
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

    // Bitta noto'g'ri bosish bilan darhol chiqib ketmasin — qayta kirish
    // uchun telefon+parol kerak bo'ladi, shu sabab tasdiqlash so'raladi.
    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = { Text("Tizimdan chiqasizmi?") },
            text = { Text("Qayta kirish uchun telefon raqami va parolingiz kerak bo'ladi.") },
            confirmButton = {
                TextButton(onClick = { showLogoutDialog = false; onLogout() }) {
                    Text("Chiqish", color = VijdonColors.Red)
                }
            },
            dismissButton = { TextButton(onClick = { showLogoutDialog = false }) { Text("Bekor qilish") } },
            containerColor = VijdonColors.Surface,
        )
    }
}

@Composable
private fun StatBox(
    label: String,
    value: String,
    icon: ImageVector,
    iconTint: androidx.compose.ui.graphics.Color,
    modifier: Modifier = Modifier,
    valueColor: androidx.compose.ui.graphics.Color = VijdonColors.Yellow,
) {
    Column(
        modifier = modifier.cardShadow().background(VijdonColors.Surface, CardShape).padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = iconTint, modifier = Modifier.size(11.dp))
            Spacer(Modifier.width(5.dp))
            Text(label, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        }
        Spacer(Modifier.height(4.dp))
        Text(value, color = valueColor, style = MaterialTheme.typography.titleMedium)
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
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier.size(40.dp).clip(RoundedCornerShape(12.dp)).background(tint.copy(alpha = 0.12f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(12.dp))
            Text(title, color = VijdonColors.TextPrimary, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Spacer(Modifier.width(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (subtitle.isNotBlank()) {
                Text(subtitle, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                Spacer(Modifier.width(4.dp))
            }
            if (showChevron) {
                Icon(Icons.AutoMirrored.Rounded.KeyboardArrowRight, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(18.dp))
            }
        }
    }
}

@Composable
private fun AppFooter() {
    val context = LocalContext.current
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .width(36.dp)
                .height(3.dp)
                .clip(RoundedCornerShape(50))
                .background(VijdonColors.TextSecondary.copy(alpha = 0.15f)),
        )
        Spacer(Modifier.height(14.dp))
        Text(
            "Versiya ${BuildConfig.VERSION_NAME}",
            color = VijdonColors.TextSecondary,
            style = MaterialTheme.typography.labelSmall,
        )
        Spacer(Modifier.height(6.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                "Powered by ",
                color = VijdonColors.TextSecondary.copy(alpha = 0.7f),
                style = MaterialTheme.typography.labelSmall,
            )
            Text(
                "ifcoder",
                color = VijdonColors.Blue,
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                modifier = Modifier.clickable {
                    // Dasturchi bilan bog'lanish uchun Telegram profili. Hech
                    // qanday brauzer/Telegram topilmasa (masalan sinov
                    // qurilmasida) `ActivityNotFoundException` ilovani
                    // qulatib qo'ymasligi uchun tutiladi.
                    try {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me/iftix0r")))
                    } catch (_: Exception) {
                    }
                },
            )
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
