package uz.vijdon.driver.ui.nearbydrivers

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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.DirectionsCar
import androidx.compose.material.icons.rounded.Groups
import androidx.compose.material.icons.rounded.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.NearbyDriverDto
import uz.vijdon.driver.ui.home.formatDistanceM
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow

@Composable
fun NearbyDriversScreen(onBack: () -> Unit, viewModel: NearbyDriversViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Yaqin haydovchilar", subtitle = "${state.drivers.size} ta onlayn hamkasb")

        Spacer(Modifier.height(12.dp))
        state.error?.let {
            ErrorBanner(it, modifier = Modifier.padding(bottom = 10.dp))
        }

        if (state.loading && state.drivers.isEmpty()) {
            CenteredLoading()
        } else if (state.drivers.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        modifier = Modifier.size(72.dp).background(VijdonColors.BadgeNeutral, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Rounded.Groups, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(32.dp))
                    }
                    Spacer(Modifier.height(12.dp))
                    Text("Hozir yaqin atrofda boshqa onlayn haydovchi yo'q", color = VijdonColors.TextSecondary)
                }
            }
        } else {
            val sorted = remember(state.drivers, state.distancesM) {
                state.drivers.sortedBy { state.distancesM[it.id] ?: Double.MAX_VALUE }
            }
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(sorted, key = { it.id }) { driver ->
                    Column(Modifier.animateItem()) {
                        NearbyDriverRow(driver, state.distancesM[driver.id])
                        Spacer(Modifier.height(8.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun NearbyDriverRow(driver: NearbyDriverDto, distanceM: Double?) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(44.dp).background(VijdonColors.BadgeNeutral, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                driver.full_name.trim().firstOrNull()?.uppercase() ?: "?",
                color = VijdonColors.TextPrimary,
                style = MaterialTheme.typography.titleMedium,
            )
        }
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(driver.full_name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleSmall, maxLines = 1)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.DirectionsCar, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(12.dp))
                Spacer(Modifier.width(4.dp))
                Text("${driver.car_model} · ${driver.car_number}", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall, maxLines = 1)
            }
        }
        Spacer(Modifier.width(8.dp))
        Column(horizontalAlignment = Alignment.End) {
            if (distanceM != null) {
                Text(formatDistanceM(distanceM), color = VijdonColors.TextPrimary, style = MaterialTheme.typography.labelMedium)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.Star, contentDescription = null, tint = Color(0xFFFF9500), modifier = Modifier.size(11.dp))
                Spacer(Modifier.width(3.dp))
                Text(driver.rating.toString(), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}
