package uz.vijdon.operator.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Chat
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.AccountBalanceWallet
import androidx.compose.material.icons.rounded.DirectionsCar
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.ListAlt
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import uz.vijdon.operator.ui.theme.VijdonColors

/** Pastki navigatsiya paneli — 5 bo'lim + markazda "Buyurtma yaratish" FAB
 * (haydovchi ilovasidagi VijdonBottomBar bilan bir xil vizual naqsh). */
@Composable
fun VijdonBottomBar(
    currentTab: String,
    ordersBadge: Int,
    chatBadge: Int,
    balanceBadge: Int,
    onTabSelected: (String) -> Unit,
    onCreateOrder: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth().background(VijdonColors.Surface.copy(alpha = 0.96f))) {
        HorizontalDivider(color = VijdonColors.Border)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 16.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BottomTab(Icons.Rounded.Home, "Bosh sahifa", selected = currentTab == Tabs.DASHBOARD) { onTabSelected(Tabs.DASHBOARD) }
            BottomTab(Icons.Rounded.ListAlt, "Buyurtmalar", selected = currentTab == Tabs.ORDERS, badge = ordersBadge) { onTabSelected(Tabs.ORDERS) }
            FabButton(onClick = onCreateOrder)
            BottomTab(Icons.AutoMirrored.Rounded.Chat, "Chat", selected = currentTab == Tabs.CHAT, badge = chatBadge) { onTabSelected(Tabs.CHAT) }
            BottomTab(Icons.Rounded.AccountBalanceWallet, "Balans", selected = currentTab == Tabs.BALANCE, badge = balanceBadge) { onTabSelected(Tabs.BALANCE) }
            BottomTab(Icons.Rounded.DirectionsCar, "Haydovchilar", selected = currentTab == Tabs.DRIVERS) { onTabSelected(Tabs.DRIVERS) }
        }
    }
}

@Composable
private fun BottomTab(icon: ImageVector, label: String, selected: Boolean, badge: Int? = null, onClick: () -> Unit) {
    val tint by animateColorAsState(
        if (selected) VijdonColors.Blue else VijdonColors.TextSecondary,
        label = "bottomTabTint",
    )
    Box(
        modifier = Modifier.clickable(onClick = onClick).padding(horizontal = 8.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = label, tint = tint, modifier = Modifier.size(25.dp))
        if (badge != null && badge > 0) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .offset(x = 6.dp, y = (-3).dp)
                    .size(14.dp)
                    .background(VijdonColors.Red, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(if (badge > 99) "99+" else badge.toString(), color = Color.White, fontSize = 8.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun FabButton(onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .offset(y = (-14).dp)
            .size(50.dp)
            .shadow(
                elevation = 5.dp,
                shape = RoundedCornerShape(16.dp),
                ambientColor = VijdonColors.Blue.copy(alpha = 0.5f),
                spotColor = VijdonColors.Blue.copy(alpha = 0.5f),
            )
            .clip(RoundedCornerShape(16.dp))
            .background(VijdonColors.Blue)
            .border(4.dp, VijdonColors.Surface, RoundedCornerShape(16.dp))
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(Icons.Rounded.Add, contentDescription = "Buyurtma yaratish", tint = VijdonColors.TextOnBlue, modifier = Modifier.size(24.dp))
    }
}
