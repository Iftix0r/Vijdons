package uz.vijdon.driver.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
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
 * Pastki navigatsiya paneli — veb haydovchi panelidagi (`.ios-glass`,
 * `left-4 right-4 rounded-full`) bilan bir xil: chetlardan bo'shliq bilan
 * suzib turuvchi, to'liq dumaloq, shaffof "shisha" pill panel. Diqqat:
 * atayin SOYASIZ (`.shadow()` ishlatilmagan) — bu aynan shu uslubdagi
 * avvalgi versiyada bir nechta qurilmada g'alati vizual nuqsonlarga sabab
 * bo'lgan edi; shaffof fonning o'zi yetarlicha ajratib turadi.
 */
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
            .padding(horizontal = 16.dp, vertical = 10.dp)
            .clip(CircleShape)
            .background(VijdonColors.Glass)
            .padding(horizontal = 6.dp, vertical = 6.dp),
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

/** Veb'dagi pastki panelda ikonka ostida matn yozuvi yo'q — faqat ikonka. */
@Composable
private fun BottomIcon(icon: ImageVector, label: String, selected: Boolean, badge: Int? = null, onClick: () -> Unit) {
    val tint by animateColorAsState(
        if (selected) VijdonColors.Yellow else VijdonColors.TextSecondary,
        label = "bottomIconTint",
    )
    Box(
        modifier = Modifier
            .clip(CircleShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = label, tint = tint, modifier = Modifier.size(26.dp))
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
    Box(
        modifier = Modifier
            .clip(CircleShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .size(26.dp)
                .clip(CircleShape)
                // Diqqat: sukut rang avval QIZIL edi — pastki panelda
                // yagona qizil dumaloq bo'lgani uchun ogohlantirish/xabar
                // nishoniga o'xshab, chalkashlik keltirib chiqarardi. Qizil
                // faqat haqiqiy nishonlar (masalan chat badge'i) uchun qoladi.
                .background(if (selected) VijdonColors.Yellow else VijdonColors.Blue),
            contentAlignment = Alignment.Center,
        ) {
            Text(initial, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.labelSmall)
        }
    }
}
