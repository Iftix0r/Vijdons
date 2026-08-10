package uz.vijdon.driver.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Forum
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.LocalTaxi
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.theme.VijdonColors

/**
 * Pastki navigatsiya paneli — Uzumbank ilovasidagi kabi, to'liq kenglikda,
 * ekranning pastki qismini butunlay egallagan, suzib turmaydigan oddiy
 * panel (avvalgi "dumaloq/pill" suzib turuvchi versiya bir nechta
 * qurilmada soya bilan bog'liq g'alati vizual nuqsonlarga sabab bo'lgani
 * uchun butunlay soddalashtirilgan tuzilishga o'tkazildi).
 */
@Composable
fun VijdonBottomBar(
    currentRoute: String?,
    driver: DriverDto,
    chatBadge: Int,
    onTabSelected: (String) -> Unit,
    onCreateOrder: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = VijdonColors.BottomBar,
        shadowElevation = 8.dp,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BottomIcon(Icons.Rounded.LocalTaxi, label = "Asosiy", selected = currentRoute == Tabs.HOME) { onTabSelected(Tabs.HOME) }
            BottomIcon(Icons.Rounded.History, label = "Tarix", selected = currentRoute == Tabs.HISTORY) { onTabSelected(Tabs.HISTORY) }
            FabIcon(onClick = onCreateOrder)
            BottomIcon(Icons.Rounded.Forum, label = "Chat", selected = currentRoute == Tabs.CHAT, badge = chatBadge) { onTabSelected(Tabs.CHAT) }
            ProfileIcon(driver = driver, selected = currentRoute == Tabs.PROFILE) { onTabSelected(Tabs.PROFILE) }
        }
    }
}

@Composable
private fun BottomIcon(icon: ImageVector, label: String, selected: Boolean, badge: Int? = null, onClick: () -> Unit) {
    val tint by animateColorAsState(
        if (selected) VijdonColors.Yellow else VijdonColors.TextSecondary,
        label = "bottomIconTint",
    )
    Column(
        modifier = Modifier
            .clip(CircleShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(icon, contentDescription = label, tint = tint, modifier = Modifier.size(24.dp))
            if (badge != null && badge > 0) {
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .size(14.dp)
                        .background(VijdonColors.Red, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(badge.toString(), color = VijdonColors.TextPrimary, fontSize = 9.sp)
                }
            }
        }
        Spacer(Modifier.height(2.dp))
        Text(label, color = tint, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun FabIcon(onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .clip(CircleShape)
            .background(VijdonColors.Yellow)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(Icons.Rounded.Add, contentDescription = "Buyurtma yaratish", tint = VijdonColors.TextOnYellow, modifier = Modifier.size(26.dp))
    }
}

@Composable
private fun ProfileIcon(driver: DriverDto, selected: Boolean, onClick: () -> Unit) {
    val initial = driver.full_name.trim().firstOrNull()?.uppercase() ?: "?"
    val tint by animateColorAsState(
        if (selected) VijdonColors.Yellow else VijdonColors.TextSecondary,
        label = "profileIconTint",
    )
    Column(
        modifier = Modifier
            .clip(CircleShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .size(24.dp)
                .clip(CircleShape)
                .background(if (selected) VijdonColors.Yellow else VijdonColors.Red),
            contentAlignment = Alignment.Center,
        ) {
            Text(initial, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.labelSmall)
        }
        Spacer(Modifier.height(2.dp))
        Text("Profil", color = tint, style = MaterialTheme.typography.labelSmall)
    }
}
