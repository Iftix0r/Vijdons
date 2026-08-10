package uz.vijdon.driver.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Forum
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.LocalTaxi
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
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
import uz.vijdon.driver.ui.theme.VijdonColors

/**
 * Pastki navigatsiya paneli — `demo.html` maketidagi kabi: to'liq kenglikda,
 * yuqorida ajratuvchi chiziq bilan, har bir ikonka ostida yorliq matni, va
 * markazda "-mt-5" uslubida biroz yuqoriga chiqarilgan, soyali kvadrat
 * "Buyurtma yaratish" FAB tugmasi.
 */
@Composable
fun VijdonBottomBar(
    currentRoute: String?,
    chatBadge: Int,
    onTabSelected: (String) -> Unit,
    onCreateOrder: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth().background(VijdonColors.Surface.copy(alpha = 0.96f))) {
        HorizontalDivider(color = VijdonColors.Border)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 24.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BottomTab(Icons.Rounded.LocalTaxi, "Asosiy", selected = currentRoute == Tabs.HOME) { onTabSelected(Tabs.HOME) }
            BottomTab(Icons.Rounded.History, "Tarix", selected = currentRoute == Tabs.HISTORY) { onTabSelected(Tabs.HISTORY) }
            FabButton(onClick = onCreateOrder)
            BottomTab(Icons.Rounded.Forum, "Chat", selected = currentRoute == Tabs.CHAT, badge = chatBadge) { onTabSelected(Tabs.CHAT) }
            BottomTab(Icons.Rounded.Person, "Profil", selected = currentRoute == Tabs.PROFILE) { onTabSelected(Tabs.PROFILE) }
        }
    }
}

@Composable
private fun BottomTab(icon: ImageVector, label: String, selected: Boolean, badge: Int? = null, onClick: () -> Unit) {
    val tint by animateColorAsState(
        if (selected) VijdonColors.Yellow else VijdonColors.TextSecondary,
        label = "bottomTabTint",
    )
    Column(
        modifier = Modifier.clickable(onClick = onClick).padding(horizontal = 6.dp, vertical = 2.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box {
            Icon(icon, contentDescription = label, tint = tint, modifier = Modifier.size(21.dp))
            if (badge != null && badge > 0) {
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .offset(x = 6.dp, y = (-3).dp)
                        .size(13.dp)
                        .background(VijdonColors.Red, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(badge.toString(), color = Color.White, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
        Spacer(Modifier.height(3.dp))
        Text(
            label,
            color = tint,
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium),
        )
    }
}

/**
 * Markaziy "Buyurtma yaratish" tugmasi — panel ustidan biroz chiqib turadi
 * (`-mt-5`), atrofida panel foni rangida "halqa" (`border-4 border-slate-50`)
 * bilan ajratilgan, shu sabab pastki panel ustiga "kesib qo'yilgandek" ko'rinadi.
 */
@Composable
private fun FabButton(onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .offset(y = (-14).dp)
            .shadow(elevation = 10.dp, shape = RoundedCornerShape(16.dp), ambientColor = VijdonColors.Yellow, spotColor = VijdonColors.Yellow)
            .clip(RoundedCornerShape(16.dp))
            .background(VijdonColors.Yellow)
            .border(4.dp, VijdonColors.Surface, RoundedCornerShape(16.dp))
            .clickable(onClick = onClick)
            .size(50.dp),
        contentAlignment = Alignment.Center,
    ) {
        Icon(Icons.Rounded.Add, contentDescription = "Buyurtma yaratish", tint = VijdonColors.TextOnYellow, modifier = Modifier.size(24.dp))
    }
}
