package uz.vijdon.driver.ui.balance

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
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ArrowDownward
import androidx.compose.material.icons.rounded.ArrowUpward
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Receipt
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.BalanceEntryDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow
import uz.vijdon.driver.util.copyUriToCacheFile

@Composable
fun BalanceHistoryScreen(viewModel: BalanceHistoryViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Balans tarixi")
        Spacer(Modifier.height(8.dp))
        Column(modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).padding(16.dp)) {
            Text("JORIY BALANS", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
            Text("${state.balance} so'm", color = VijdonColors.Green, style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold))
        }
        state.error?.let {
            Spacer(Modifier.height(10.dp))
            ErrorBanner(it)
        }
        Spacer(Modifier.height(12.dp))
        if (state.loading && state.entries.isEmpty()) {
            CenteredLoading()
        } else if (state.entries.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Tarix bo'sh", color = VijdonColors.TextSecondary)
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.entries) { entry -> BalanceEntryRow(entry) }
            }
        }
    }
}

@Composable
private fun BalanceEntryRow(entry: BalanceEntryDto) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).cardShadow().background(VijdonColors.Surface, CardShape).padding(14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            val color = if (entry.is_income) VijdonColors.Green else VijdonColors.Red
            Box(modifier = Modifier.size(32.dp).background(color.copy(alpha = 0.15f), CircleShape), contentAlignment = Alignment.Center) {
                Icon(
                    if (entry.is_income) Icons.Rounded.ArrowDownward else Icons.Rounded.ArrowUpward,
                    contentDescription = null, tint = color, modifier = Modifier.size(16.dp),
                )
            }
            Spacer(Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(entry.note, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.bodyMedium)
                Text(entry.created_at.take(16).replace("T", " "), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
            }
        }
        Spacer(Modifier.width(8.dp))
        Text(
            "${if (entry.is_income) "+" else "-"}${entry.amount}",
            color = if (entry.is_income) VijdonColors.Green else VijdonColors.Red,
            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
            maxLines = 1,
        )
    }
}

@Composable
fun TopupScreen(onDone: () -> Unit, viewModel: TopupViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    var receiptFile by remember { mutableStateOf<java.io.File?>(null) }

    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { receiptFile = copyUriToCacheFile(context, it, "receipt.jpg") }
    }

    LaunchedEffect(state.success) { if (state.success) onDone() }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Balans to'ldirish")
        Spacer(Modifier.height(16.dp))
        OutlinedTextField(
            value = state.amount, onValueChange = viewModel::onAmountChange,
            label = { Text("Summa (so'm)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = VijdonColors.Surface, unfocusedContainerColor = VijdonColors.Surface,
                focusedTextColor = VijdonColors.TextPrimary, unfocusedTextColor = VijdonColors.TextPrimary,
                focusedBorderColor = VijdonColors.Yellow,
            ),
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = { launcher.launch("image/*") },
            colors = ButtonDefaults.outlinedButtonColors(contentColor = VijdonColors.TextPrimary),
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (receiptFile != null) {
                Icon(Icons.Rounded.CheckCircle, contentDescription = null, tint = VijdonColors.Green, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(6.dp))
                Text("Chek tanlandi")
            } else {
                Icon(Icons.Rounded.Receipt, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(6.dp))
                Text("Chek rasmini tanlash")
            }
        }
        state.error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = VijdonColors.Red)
        }
        Spacer(Modifier.height(20.dp))
        Button(
            onClick = { receiptFile?.let { viewModel.submit(it) } },
            enabled = !state.loading && receiptFile != null,
            colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) {
            if (state.loading) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), color = VijdonColors.TextOnYellow, strokeWidth = 2.dp)
            } else {
                Text("Yuborish")
            }
        }
    }
}
