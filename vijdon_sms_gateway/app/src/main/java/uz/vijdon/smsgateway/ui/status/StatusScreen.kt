package uz.vijdon.smsgateway.ui.status

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.text.format.DateFormat
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Error
import androidx.compose.material.icons.rounded.Logout
import androidx.compose.material.icons.rounded.Sms
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.smsgateway.data.service.SentLogEntry
import uz.vijdon.smsgateway.data.service.SmsGatewayService
import uz.vijdon.smsgateway.ui.theme.VijdonColors
import java.util.Date

@Composable
fun StatusScreen(
    username: String,
    onLogout: () -> Unit,
    viewModel: StatusViewModel = hiltViewModel(),
) {
    val context = LocalContext.current
    val logEntries by viewModel.logEntries.collectAsState()

    var smsPermissionGranted by remember { mutableStateOf(hasSmsPermission(context)) }

    val smsPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        smsPermissionGranted = granted
        if (granted) startGatewayService(context)
    }
    val notifPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}

    LaunchedEffect(Unit) {
        viewModel.syncFcmToken()
        if (smsPermissionGranted) {
            startGatewayService(context)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            notifPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier.size(44.dp).background(VijdonColors.Green, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.Sms, contentDescription = null, tint = VijdonColors.TextOnGreen, modifier = Modifier.size(22.dp))
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text("SMS-shlyuz", style = MaterialTheme.typography.titleMedium, color = VijdonColors.TextPrimary, fontWeight = FontWeight.SemiBold)
                Text(username, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
            }
            IconButton(onClick = {
                stopGatewayService(context)
                onLogout()
            }) {
                Icon(Icons.Rounded.Logout, contentDescription = "Chiqish", tint = VijdonColors.TextSecondary)
            }
        }

        StatusCard(
            granted = smsPermissionGranted,
            onRequestPermission = { smsPermissionLauncher.launch(Manifest.permission.SEND_SMS) },
        )

        Text(
            "So'nggi faoliyat",
            style = MaterialTheme.typography.titleSmall,
            color = VijdonColors.TextPrimary,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp),
        )

        if (logEntries.isEmpty()) {
            Box(modifier = Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                Text(
                    "Hozircha SMS yuborilmagan. Yangi buyurtma/holat o'zgarganda bu yerda ko'rinadi.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = VijdonColors.TextSecondary,
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 20.dp, vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(logEntries) { entry -> LogRow(entry) }
            }
        }
    }
}

@Composable
private fun StatusCard(granted: Boolean, onRequestPermission: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 8.dp)
            .background(VijdonColors.Surface, RoundedCornerShape(16.dp))
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                if (granted) Icons.Rounded.CheckCircle else Icons.Rounded.Warning,
                contentDescription = null,
                tint = if (granted) VijdonColors.Green else VijdonColors.Yellow,
            )
            Spacer(Modifier.width(10.dp))
            Text(
                if (granted) "Ishlamoqda — SMS navbati kuzatilmoqda" else "SMS yuborish ruxsati kerak",
                style = MaterialTheme.typography.bodyMedium,
                color = VijdonColors.TextPrimary,
                fontWeight = FontWeight.Medium,
            )
        }
        if (!granted) {
            Spacer(Modifier.height(12.dp))
            Button(
                onClick = onRequestPermission,
                colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Green, contentColor = VijdonColors.TextOnGreen),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Ruxsat berish")
            }
        }
    }
}

@Composable
private fun LogRow(entry: SentLogEntry) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(VijdonColors.Surface, RoundedCornerShape(12.dp))
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            if (entry.success) Icons.Rounded.CheckCircle else Icons.Rounded.Error,
            contentDescription = null,
            tint = if (entry.success) VijdonColors.Green else VijdonColors.Red,
            modifier = Modifier.size(20.dp),
        )
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(entry.phoneNumber, style = MaterialTheme.typography.bodyMedium, color = VijdonColors.TextPrimary)
            if (!entry.success && entry.error != null) {
                Text(entry.error, style = MaterialTheme.typography.bodySmall, color = VijdonColors.Red)
            }
        }
        Text(
            DateFormat.format("HH:mm", Date(entry.atMillis)).toString(),
            style = MaterialTheme.typography.bodySmall,
            color = VijdonColors.TextSecondary,
        )
    }
}

private fun hasSmsPermission(context: Context): Boolean =
    ContextCompat.checkSelfPermission(context, Manifest.permission.SEND_SMS) == PackageManager.PERMISSION_GRANTED

private fun startGatewayService(context: Context) {
    val intent = Intent(context, SmsGatewayService::class.java)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        context.startForegroundService(intent)
    } else {
        context.startService(intent)
    }
}

private fun stopGatewayService(context: Context) {
    context.stopService(Intent(context, SmsGatewayService::class.java))
}
