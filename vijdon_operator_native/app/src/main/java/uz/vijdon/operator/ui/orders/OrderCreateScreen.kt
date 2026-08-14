package uz.vijdon.operator.ui.orders

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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.ScreenHeader
import uz.vijdon.operator.ui.theme.VijdonColors

private val carTypes = listOf("light" to "🚗 Yengil", "cargo" to "🚚 Yuk mashinasi", "minivan" to "🚐 Minivan")
private val paymentTypes = listOf("cash" to "Naqd", "card" to "Karta")

@Composable
fun OrderCreateScreen(onDone: () -> Unit, onBack: () -> Unit, viewModel: OrderCreateViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(state.created) {
        if (state.created) onDone()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(VijdonColors.Background)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        ScreenHeader(title = "Buyurtma yaratish", onBack = onBack)
        Spacer(Modifier.height(16.dp))

        Field("Mijoz telefon raqami *", state.phone) { viewModel.update { s -> s.copy(phone = it, error = null) } }
        Spacer(Modifier.height(10.dp))
        Field("Mijoz ismi", state.customerName) { viewModel.update { s -> s.copy(customerName = it) } }
        Spacer(Modifier.height(10.dp))
        Field("Qayerdan (manzil) *", state.fromAddress) { viewModel.update { s -> s.copy(fromAddress = it) } }
        Spacer(Modifier.height(10.dp))
        Field("Qayerga (ixtiyoriy)", state.toAddress) { viewModel.update { s -> s.copy(toAddress = it) } }
        Spacer(Modifier.height(10.dp))
        Field("Izoh", state.note) { viewModel.update { s -> s.copy(note = it) } }

        Spacer(Modifier.height(14.dp))
        Text("Mashina turi", color = VijdonColors.TextSecondary)
        Spacer(Modifier.height(6.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            carTypes.forEach { (value, label) ->
                ChoiceChip(label, selected = state.carType == value) { viewModel.update { s -> s.copy(carType = value) } }
            }
        }

        Spacer(Modifier.height(14.dp))
        Text("To'lov turi", color = VijdonColors.TextSecondary)
        Spacer(Modifier.height(6.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            paymentTypes.forEach { (value, label) ->
                ChoiceChip(label, selected = state.paymentType == value) { viewModel.update { s -> s.copy(paymentType = value) } }
            }
        }

        Spacer(Modifier.height(14.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = state.isDelivery, onCheckedChange = { viewModel.update { s -> s.copy(isDelivery = it) } })
            Text("Yetkazib berish (dastavka)", color = VijdonColors.TextPrimary)
        }

        Spacer(Modifier.height(14.dp))
        Text("Haydovchi (ixtiyoriy — bo'sh qoldirilsa avtomatik taqsimlanadi)", color = VijdonColors.TextSecondary)
        Spacer(Modifier.height(6.dp))
        DriverDropdown(
            drivers = state.drivers,
            selectedId = state.driverId,
            onSelect = { viewModel.update { s -> s.copy(driverId = it) } },
        )

        state.error?.let {
            Spacer(Modifier.height(14.dp))
            ErrorBanner(it)
        }

        Spacer(Modifier.height(20.dp))
        Button(
            onClick = viewModel::submit,
            enabled = !state.loading,
            colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Blue, contentColor = VijdonColors.TextOnBlue),
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) {
            if (state.loading) {
                CircularProgressIndicator(modifier = Modifier.height(20.dp), color = VijdonColors.TextOnBlue)
            } else {
                Text("Buyurtma yaratish")
            }
        }
        Spacer(Modifier.height(40.dp))
    }
}

@Composable
private fun Field(label: String, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        colors = OutlinedTextFieldDefaults.colors(
            focusedContainerColor = VijdonColors.Surface,
            unfocusedContainerColor = VijdonColors.Surface,
            focusedBorderColor = VijdonColors.Blue,
            unfocusedBorderColor = VijdonColors.Border,
        ),
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun ChoiceChip(label: String, selected: Boolean, onClick: () -> Unit) {
    Text(
        label,
        color = if (selected) VijdonColors.TextOnBlue else VijdonColors.TextSecondary,
        modifier = Modifier
            .background(if (selected) VijdonColors.Blue else VijdonColors.BadgeNeutral, androidx.compose.foundation.shape.RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 8.dp),
    )
}

@Composable
private fun DriverDropdown(drivers: List<uz.vijdon.operator.data.api.DriverDto>, selectedId: Int?, onSelect: (Int?) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val selectedName = drivers.find { it.id == selectedId }?.full_name ?: "Avtomatik taqsimlash"
    Box {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Text(selectedName)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            DropdownMenuItem(text = { Text("Avtomatik taqsimlash") }, onClick = { expanded = false; onSelect(null) })
            drivers.forEach { d ->
                DropdownMenuItem(text = { Text("${d.full_name} (${d.car_number})") }, onClick = { expanded = false; onSelect(d.id) })
            }
        }
    }
}
