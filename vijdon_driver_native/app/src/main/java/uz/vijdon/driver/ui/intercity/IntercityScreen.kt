package uz.vijdon.driver.ui.intercity

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
import androidx.compose.material.icons.automirrored.rounded.ArrowForward
import androidx.compose.material.icons.rounded.DirectionsBus
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.IntercityPassengerDto
import uz.vijdon.driver.data.api.IntercityRouteDto
import uz.vijdon.driver.data.api.IntercityTripDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow
import uz.vijdon.driver.util.formatMoney

/**
 * Shahrlararo (viloyatlararo) yo'lovchi tashish — haydovchi bitta
 * yo'nalishga (masalan "Samarqand → Toshkent") qo'shiladi va mashina
 * to'lguncha kutadi (yo'lovchilar hozircha operator panelidan telefon
 * orqali band qilinadi — mijoz ilovasida o'z-o'zini ro'yxatga olish
 * keyingi bosqich). Bir vaqtning o'zida faqat bitta faol safar bo'lishi
 * mumkin.
 */
@Composable
fun IntercityScreen(onBack: () -> Unit, viewModel: IntercityViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Shahrlararo", subtitle = "Yo'lovchi tashish", onBack = onBack)
        Spacer(Modifier.height(12.dp))

        state.error?.let {
            ErrorBanner(it, modifier = Modifier.padding(bottom = 10.dp))
        }

        when {
            state.loading -> CenteredLoading()
            state.myTrip != null -> TripCard(trip = state.myTrip!!, onDepart = viewModel::depart, onCancel = viewModel::cancel)
            else -> RoutesList(
                routes = state.routes,
                joiningRouteId = state.joiningRouteId,
                onJoin = viewModel::join,
            )
        }
    }
}

@Composable
private fun RoutesList(routes: List<IntercityRouteDto>, joiningRouteId: Int?, onJoin: (Int) -> Unit) {
    if (routes.isEmpty()) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Hozircha shahrlararo yo'nalish sozlanmagan", color = VijdonColors.TextSecondary)
        }
        return
    }
    LazyColumn(modifier = Modifier.fillMaxSize()) {
        items(routes, key = { it.id }) { route ->
            Column {
                RouteRow(route, joining = joiningRouteId == route.id, onJoin = { onJoin(route.id) })
                Spacer(Modifier.height(10.dp))
            }
        }
    }
}

@Composable
private fun RouteRow(route: IntercityRouteDto, joining: Boolean, onJoin: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .padding(horizontal = 18.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(40.dp).background(VijdonColors.Blue.copy(alpha = 0.12f), CircleShape), contentAlignment = Alignment.Center) {
                Icon(Icons.Rounded.DirectionsBus, contentDescription = null, tint = VijdonColors.Blue, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(route.from_region, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                    Icon(Icons.AutoMirrored.Rounded.ArrowForward, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.padding(horizontal = 4.dp).size(14.dp))
                    Text(route.to_region, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                }
                Text(
                    "${formatMoney(route.seat_price)} so'm / joy · ${route.seat_capacity} o'rin",
                    color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        Spacer(Modifier.width(8.dp))
        Button(
            onClick = onJoin,
            enabled = !joining,
            colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
        ) {
            if (joining) {
                CircularProgressIndicator(modifier = Modifier.size(16.dp), color = VijdonColors.TextOnYellow, strokeWidth = 2.dp)
            } else {
                Text("Qo'shilish")
            }
        }
    }
}

@Composable
private fun TripCard(trip: IntercityTripDto, onDepart: () -> Unit, onCancel: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .padding(18.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.DirectionsBus, contentDescription = null, tint = VijdonColors.Blue, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(8.dp))
            Text(trip.from_region, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
            Icon(Icons.AutoMirrored.Rounded.ArrowForward, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.padding(horizontal = 4.dp).size(16.dp))
            Text(trip.to_region, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
        }
        Spacer(Modifier.height(4.dp))
        Text("${formatMoney(trip.seat_price)} so'm / joy", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)

        Spacer(Modifier.height(16.dp))
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(
                "${trip.seats_booked}/${trip.seat_capacity} joy band",
                color = VijdonColors.TextPrimary, style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold),
            )
            if (trip.seats_left == 0) {
                Text("To'ldi!", color = VijdonColors.Green, style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold))
            }
        }
        Spacer(Modifier.height(6.dp))
        LinearProgressIndicator(
            progress = { if (trip.seat_capacity > 0) trip.seats_booked.toFloat() / trip.seat_capacity else 0f },
            modifier = Modifier.fillMaxWidth().height(8.dp),
            color = if (trip.seats_left == 0) VijdonColors.Green else VijdonColors.Yellow,
            trackColor = VijdonColors.BadgeNeutral,
        )

        Spacer(Modifier.height(16.dp))
        if (trip.passengers.isEmpty()) {
            Text("Hali yo'lovchi yo'q — kuting yoki operatorga bog'laning", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        } else {
            Column {
                trip.passengers.forEach { p -> PassengerRow(p); Spacer(Modifier.height(6.dp)) }
            }
        }

        Spacer(Modifier.height(18.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(onClick = onCancel, modifier = Modifier.weight(1f)) {
                Text("Bekor qilish", color = VijdonColors.Red)
            }
            Button(
                onClick = onDepart,
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Green, contentColor = Color.White),
            ) {
                Text("Jo'natish")
            }
        }
    }
}

@Composable
private fun PassengerRow(p: IntercityPassengerDto) {
    Row(
        modifier = Modifier.fillMaxWidth().background(VijdonColors.BadgeNeutral, CardShape).padding(horizontal = 12.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(22.dp).background(VijdonColors.Blue.copy(alpha = 0.15f), CircleShape), contentAlignment = Alignment.Center) {
                Text(p.seats.toString(), color = VijdonColors.Blue, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold))
            }
            Spacer(Modifier.width(8.dp))
            Text(p.name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.bodySmall)
        }
        Text(p.phone, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
    }
}
