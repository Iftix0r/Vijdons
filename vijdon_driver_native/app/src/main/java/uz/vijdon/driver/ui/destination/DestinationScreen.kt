package uz.vijdon.driver.ui.destination

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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Explore
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow

@Composable
fun DestinationScreen(onBack: () -> Unit, viewModel: DestinationViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val driver = state.driver

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Yo'nalish rejimi", onBack = onBack)
        Spacer(Modifier.height(12.dp))
        Text(
            "Uyingizga yoki ma'lum tomonga ketayotgan bo'lsangiz yoqing — faqat shu yo'nalishdagi (manzilga yaqin) buyurtmalar taklif qilinadi.",
            color = VijdonColors.TextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )
        Spacer(Modifier.height(16.dp))

        state.error?.let {
            ErrorBanner(it, modifier = Modifier.padding(bottom = 10.dp))
        }

        if (state.loading) {
            CenteredLoading()
        } else if (driver?.destination_mode == true) {
            ActiveDestinationCard(
                address = driver.destination_address,
                submitting = state.submitting,
                onClear = viewModel::clear,
            )
        } else if (state.savedAddresses.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Saqlangan manzillar yo'q — yo'nalish tanlash uchun avval manzil kerak", color = VijdonColors.TextSecondary, textAlign = TextAlign.Center)
            }
        } else {
            Text("Yo'nalishni tanlang", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.height(8.dp))
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.savedAddresses, key = { it.id }) { address ->
                    Column(Modifier.animateItem()) {
                        DestinationAddressRow(address, state.submitting) { viewModel.activate(address) }
                        Spacer(Modifier.height(8.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun ActiveDestinationCard(address: String, submitting: Boolean, onClear: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier.size(64.dp).background(VijdonColors.Green.copy(alpha = 0.15f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Rounded.Explore, contentDescription = null, tint = VijdonColors.Green, modifier = Modifier.size(30.dp))
        }
        Spacer(Modifier.height(14.dp))
        Text("Yo'nalish rejimi yoqilgan", color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
        Spacer(Modifier.height(4.dp))
        Text(address, color = VijdonColors.Green, style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center)
        Spacer(Modifier.height(20.dp))
        OutlinedButton(
            onClick = onClear,
            enabled = !submitting,
            modifier = Modifier.fillMaxWidth().height(48.dp),
        ) {
            if (submitting) {
                CircularProgressIndicator(modifier = Modifier.size(18.dp), color = VijdonColors.TextPrimary, strokeWidth = 2.dp)
            } else {
                Text("Yo'nalishni bekor qilish", color = VijdonColors.Red)
            }
        }
    }
}

@Composable
private fun DestinationAddressRow(address: AddressDto, submitting: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(enabled = !submitting, onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(36.dp).background(VijdonColors.BadgeNeutral, CircleShape), contentAlignment = Alignment.Center) {
                Icon(Icons.Rounded.LocationOn, contentDescription = null, tint = VijdonColors.Red, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(12.dp))
            Text(address.name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleSmall, maxLines = 1)
        }
        Button(
            onClick = onClick,
            enabled = !submitting,
            colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
        ) { Text("Tanlash") }
    }
}
