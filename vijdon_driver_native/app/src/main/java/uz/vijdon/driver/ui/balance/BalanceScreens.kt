package uz.vijdon.driver.ui.balance

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.BalanceEntryDto
import uz.vijdon.driver.util.copyUriToCacheFile

@Composable
fun BalanceHistoryScreen(viewModel: BalanceHistoryViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(12.dp)) {
            Text("Balans: ${state.balance} so'm", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.entries) { entry -> BalanceEntryRow(entry) }
            }
        }
    }
}

@Composable
private fun BalanceEntryRow(entry: BalanceEntryDto) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column {
                Text(entry.note, style = MaterialTheme.typography.bodyMedium)
                Text(entry.created_at.take(16).replace("T", " "), style = MaterialTheme.typography.bodySmall)
            }
            Text(
                "${if (entry.is_income) "+" else "-"}${entry.amount}",
                color = if (entry.is_income) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
            )
        }
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

    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            Text("Balans to'ldirish", style = MaterialTheme.typography.headlineSmall)
            Spacer(Modifier.height(16.dp))
            OutlinedTextField(
                value = state.amount, onValueChange = viewModel::onAmountChange,
                label = { Text("Summa (so'm)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            OutlinedButton(onClick = { launcher.launch("image/*") }, modifier = Modifier.fillMaxWidth()) {
                Text(if (receiptFile != null) "Chek tanlandi ✓" else "Chek rasmini tanlash")
            }
            state.error?.let {
                Spacer(Modifier.height(8.dp))
                Text(it, color = MaterialTheme.colorScheme.error)
            }
            Spacer(Modifier.height(20.dp))
            Button(
                onClick = { receiptFile?.let { viewModel.submit(it) } },
                enabled = !state.loading && receiptFile != null,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Yuborish")
            }
        }
    }
}
