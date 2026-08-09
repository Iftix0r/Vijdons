package uz.vijdon.driver.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun VijdonBottomBar(
    currentRoute: String?,
    driver: DriverDto,
    chatBadge: Int,
    onTabSelected: (String) -> Unit,
    onCreateOrder: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(VijdonColors.BottomBar)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        BottomIcon(Icons.Rounded.LocalTaxi, selected = currentRoute == Tabs.HOME) { onTabSelected(Tabs.HOME) }
        BottomIcon(Icons.Rounded.History, selected = currentRoute == Tabs.HISTORY) { onTabSelected(Tabs.HISTORY) }
        FabIcon(onClick = onCreateOrder)
        BottomIcon(Icons.Rounded.Forum, selected = currentRoute == Tabs.CHAT, badge = chatBadge) { onTabSelected(Tabs.CHAT) }
        ProfileIcon(driver = driver, selected = currentRoute == Tabs.PROFILE) { onTabSelected(Tabs.PROFILE) }
    }
}

@Composable
private fun BottomIcon(icon: ImageVector, selected: Boolean, badge: Int? = null, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(44.dp)
            .clip(CircleShape)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            icon,
            contentDescription = null,
            tint = if (selected) VijdonColors.Yellow else VijdonColors.TextSecondary,
            modifier = Modifier.size(24.dp),
        )
        if (badge != null && badge > 0) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .size(16.dp)
                    .background(VijdonColors.Red, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(badge.toString(), color = VijdonColors.TextPrimary, fontSize = 10.sp)
            }
        }
    }
}

@Composable
private fun FabIcon(onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(52.dp)
            .clip(CircleShape)
            .background(VijdonColors.Yellow)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(Icons.Rounded.Add, contentDescription = "Buyurtma yaratish", tint = VijdonColors.TextOnYellow, modifier = Modifier.size(28.dp))
    }
}

@Composable
private fun ProfileIcon(driver: DriverDto, selected: Boolean, onClick: () -> Unit) {
    val initial = driver.full_name.trim().firstOrNull()?.uppercase() ?: "?"
    Box(
        modifier = Modifier
            .size(36.dp)
            .clip(CircleShape)
            .background(if (selected) VijdonColors.Yellow else VijdonColors.Red)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(initial, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.labelLarge)
    }
}
