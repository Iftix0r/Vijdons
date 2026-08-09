package uz.vijdon.driver.ui.ordercreate

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.Edit
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.ui.theme.ChipShape
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun OrderCreateScreen(onDone: () -> Unit, onBack: () -> Unit, viewModel: OrderCreateViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(state.success) { if (state.success) onDone() }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(VijdonColors.Background)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Orqaga", tint = VijdonColors.TextPrimary)
            }
            Text("Buyurtma yaratish", color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleLarge)
        }
        Spacer(Modifier.height(20.dp))

        SectionLabel("Mijoz telefon raqami *")
        DarkTextField(state.phone, viewModel::onPhoneChange, "+998 90 123 45 67", KeyboardType.Phone)

        Spacer(Modifier.height(20.dp))
        SectionLabel("Qayerga (ixtiyoriy)")
        DarkTextField(state.toAddress, viewModel::onToAddressChange, "Manzil")

        Spacer(Modifier.height(20.dp))
        SectionLabel("Qayerdan *")
        AddressChips(state.savedAddresses, state.selectedAddressName, state.useCustomAddress, viewModel::selectAddress, viewModel::selectCustom)
        if (state.useCustomAddress) {
            Spacer(Modifier.height(8.dp))
            DarkTextField(state.customFromAddress, viewModel::onCustomFromAddressChange, "Manzilni yozing")
        }

        Spacer(Modifier.height(20.dp))
        SectionLabel("Buyurtmani kim oladi?")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            AssignToggle("O'zim olaman", state.assignToSelf) { viewModel.setAssignToSelf(true) }
            AssignToggle("Boshqa haydovchilar", !state.assignToSelf) { viewModel.setAssignToSelf(false) }
        }

        state.error?.let {
            Spacer(Modifier.height(12.dp))
            Text(it, color = VijdonColors.Red)
        }

        Spacer(Modifier.height(24.dp))
        Button(
            onClick = viewModel::submit,
            enabled = !state.loading,
            colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) {
            Text(if (state.loading) "Yuborilmoqda..." else "Buyurtma yaratish")
        }
        Spacer(Modifier.height(40.dp))
    }
}

@Composable
private fun SectionLabel(text: String) {
    Text(text, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelLarge)
    Spacer(Modifier.height(8.dp))
}

@Composable
private fun DarkTextField(value: String, onChange: (String) -> Unit, placeholder: String, keyboardType: KeyboardType = KeyboardType.Text) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        placeholder = { Text(placeholder, color = VijdonColors.TextSecondary) },
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        colors = OutlinedTextFieldDefaults.colors(
            focusedContainerColor = VijdonColors.Surface,
            unfocusedContainerColor = VijdonColors.Surface,
            focusedTextColor = VijdonColors.TextPrimary,
            unfocusedTextColor = VijdonColors.TextPrimary,
            focusedBorderColor = VijdonColors.Yellow,
            unfocusedBorderColor = VijdonColors.Border,
        ),
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun AddressChips(
    addresses: List<AddressDto>,
    selected: String?,
    useCustom: Boolean,
    onSelect: (String) -> Unit,
    onCustom: () -> Unit,
) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        addresses.forEach { addr ->
            AddressChip(Icons.Rounded.LocationOn, addr.name, selected == addr.name) { onSelect(addr.name) }
        }
        AddressChip(Icons.Rounded.Edit, "Boshqa", useCustom) { onCustom() }
    }
}

@Composable
private fun AddressChip(icon: ImageVector, text: String, selected: Boolean, onClick: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .background(if (selected) VijdonColors.SurfaceRaised else VijdonColors.Surface, ChipShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
    ) {
        Icon(icon, contentDescription = null, tint = if (selected) VijdonColors.Yellow else VijdonColors.Red, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(6.dp))
        Text(text, color = if (selected) VijdonColors.Yellow else VijdonColors.TextPrimary, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
private fun AssignToggle(text: String, selected: Boolean, onClick: () -> Unit) {
    Text(
        text,
        color = if (selected) VijdonColors.TextOnYellow else VijdonColors.TextPrimary,
        style = MaterialTheme.typography.labelLarge,
        modifier = Modifier
            .background(if (selected) VijdonColors.Yellow else VijdonColors.Surface, ChipShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp),
    )
}
