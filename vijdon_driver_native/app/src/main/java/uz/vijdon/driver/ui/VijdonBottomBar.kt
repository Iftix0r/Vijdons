package uz.vijdon.driver.ui

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
import androidx.compose.material.icons.rounded.AccountCircle
import androidx.compose.material.icons.rounded.History
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
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import uz.vijdon.driver.ui.theme.VijdonColors

// "Asosiy" tabidagi uy ikonkasi o'rniga — "1351" belgisi (ic_launcher_foreground.xml
// bilan bir xil pathData, faqat shu yerda ImageVector sifatida qayta
// quriladi, chunki BottomTab standart Icon()/ImageVector kutadi). Tint
// (tanlangan/tanlanmagan rangi) Icon() orqali avtomatik qo'llanadi, shu
// sabab fill rangi (Black) shunchaki platsholder.
private val DispatchMarkIcon: ImageVector by lazy {
    val pathData = "M43,7 L43,7 A5,5 0 0 1 48,12 L48,35 A5,5 0 0 1 43,40 L43,40 A5,5 0 0 1 38,35 L38,12 A5,5 0 0 1 43,7 Z M43,44 L43,44 A5,5 0 0 1 48,49 L48,72 A5,5 0 0 1 43,77 L43,77 A5,5 0 0 1 38,72 L38,49 A5,5 0 0 1 43,44 Z M78,0 L98,0 A5,5 0 0 1 103,5 L103,5 A5,5 0 0 1 98,10 L78,10 A5,5 0 0 1 73,5 L73,5 A5,5 0 0 1 78,0 Z M107,7 L107,7 A5,5 0 0 1 112,12 L112,35 A5,5 0 0 1 107,40 L107,40 A5,5 0 0 1 102,35 L102,12 A5,5 0 0 1 107,7 Z M78,37 L98,37 A5,5 0 0 1 103,42 L103,42 A5,5 0 0 1 98,47 L78,47 A5,5 0 0 1 73,42 L73,42 A5,5 0 0 1 78,37 Z M107,44 L107,44 A5,5 0 0 1 112,49 L112,72 A5,5 0 0 1 107,77 L107,77 A5,5 0 0 1 102,72 L102,49 A5,5 0 0 1 107,44 Z M78,74 L98,74 A5,5 0 0 1 103,79 L103,79 A5,5 0 0 1 98,84 L78,84 A5,5 0 0 1 73,79 L73,79 A5,5 0 0 1 78,74 Z M142,0 L162,0 A5,5 0 0 1 167,5 L167,5 A5,5 0 0 1 162,10 L142,10 A5,5 0 0 1 137,5 L137,5 A5,5 0 0 1 142,0 Z M133,7 L133,7 A5,5 0 0 1 138,12 L138,35 A5,5 0 0 1 133,40 L133,40 A5,5 0 0 1 128,35 L128,12 A5,5 0 0 1 133,7 Z M142,37 L162,37 A5,5 0 0 1 167,42 L167,42 A5,5 0 0 1 162,47 L142,47 A5,5 0 0 1 137,42 L137,42 A5,5 0 0 1 142,37 Z M171,44 L171,44 A5,5 0 0 1 176,49 L176,72 A5,5 0 0 1 171,77 L171,77 A5,5 0 0 1 166,72 L166,49 A5,5 0 0 1 171,44 Z M142,74 L162,74 A5,5 0 0 1 167,79 L167,79 A5,5 0 0 1 162,84 L142,84 A5,5 0 0 1 137,79 L137,79 A5,5 0 0 1 142,74 Z M235,7 L235,7 A5,5 0 0 1 240,12 L240,35 A5,5 0 0 1 235,40 L235,40 A5,5 0 0 1 230,35 L230,12 A5,5 0 0 1 235,7 Z M235,44 L235,44 A5,5 0 0 1 240,49 L240,72 A5,5 0 0 1 235,77 L235,77 A5,5 0 0 1 230,72 L230,49 A5,5 0 0 1 235,44 Z"
    val nodes = PathParser().parsePathString(pathData).toNodes()
    ImageVector.Builder(
        name = "DispatchMark",
        defaultWidth = 27.dp,
        defaultHeight = 27.dp,
        viewportWidth = 240f,
        viewportHeight = 84f,
    ).addPath(pathData = nodes, fill = SolidColor(Color.Black)).build()
}

/**
 * Pastki navigatsiya paneli — `demo.html` maketidagi kabi: to'liq kenglikda,
 * yuqorida ajratuvchi chiziq bilan, markazda "-mt-5" uslubida biroz yuqoriga
 * chiqarilgan, soyali kvadrat "Taksimetrni boshlash" FAB tugmasi. Diqqat:
 * matn yorliqlari ATAYIN yo'q — faqat kattaroq, ma'nosi aniq ikonkalar orqali.
 */
@Composable
fun VijdonBottomBar(
    currentRoute: String?,
    chatBadge: Int,
    profilePhotoUrl: String?,
    onTabSelected: (String) -> Unit,
    onStartTrip: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth().background(VijdonColors.Surface.copy(alpha = 0.96f))) {
        HorizontalDivider(color = VijdonColors.Border)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 24.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BottomTab(DispatchMarkIcon, "Asosiy", selected = currentRoute == Tabs.HOME) { onTabSelected(Tabs.HOME) }
            BottomTab(Icons.Rounded.History, "Tarix", selected = currentRoute == Tabs.HISTORY) { onTabSelected(Tabs.HISTORY) }
            FabButton(onClick = onStartTrip)
            BottomTab(Icons.AutoMirrored.Rounded.Chat, "Chat", selected = currentRoute == Tabs.CHAT, badge = chatBadge) { onTabSelected(Tabs.CHAT) }
            ProfileBottomTab(photoUrl = profilePhotoUrl, selected = currentRoute == Tabs.PROFILE) { onTabSelected(Tabs.PROFILE) }
        }
    }
}

@Composable
private fun BottomTab(icon: ImageVector, label: String, selected: Boolean, badge: Int? = null, onClick: () -> Unit) {
    val tint by animateColorAsState(
        if (selected) VijdonColors.Yellow else VijdonColors.TextSecondary,
        label = "bottomTabTint",
    )
    Box(
        modifier = Modifier.clickable(onClick = onClick).padding(horizontal = 10.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = label, tint = tint, modifier = Modifier.size(27.dp))
        if (badge != null && badge > 0) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .offset(x = 6.dp, y = (-3).dp)
                    .size(14.dp)
                    .background(VijdonColors.Red, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(badge.toString(), color = Color.White, fontSize = 8.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

/** "Profil" tugmasi — boshqa tab'lardan farqli, ikonka o'rniga (bo'lsa)
 * haydovchining o'z profil surati dumaloq qilib ko'rsatiladi, tanlangan
 * holatda sariq halqa bilan ajratiladi. Surat yo'q/yuklanmagan bo'lsa
 * oddiy odam ikonkasiga qaytadi (boshqa tab'lar bilan bir xil uslub). */
@Composable
private fun ProfileBottomTab(photoUrl: String?, selected: Boolean, onClick: () -> Unit) {
    val tint by animateColorAsState(
        if (selected) VijdonColors.Yellow else VijdonColors.TextSecondary,
        label = "profileTabTint",
    )
    Box(
        modifier = Modifier.clickable(onClick = onClick).padding(horizontal = 10.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        if (photoUrl.isNullOrBlank()) {
            Icon(Icons.Rounded.AccountCircle, contentDescription = "Profil", tint = tint, modifier = Modifier.size(27.dp))
        } else {
            AsyncImage(
                model = photoUrl,
                contentDescription = "Profil",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(27.dp)
                    .clip(CircleShape)
                    .border(1.5.dp, if (selected) VijdonColors.Yellow else Color.Transparent, CircleShape),
            )
        }
    }
}

/**
 * Markaziy tugma — bosilsa forma so'ramasdan DARHOL taksimetrni ishga
 * tushiradi (ko'chada to'xtatib olingan yo'lovchi uchun, `StartTripScreen`).
 * Panel ustidan biroz chiqib turadi (`-mt-5`), atrofida panel foni rangida
 * "halqa" (`border-4 border-slate-50`) bilan ajratilgan, shu sabab pastki
 * panel ustiga "kesib qo'yilgandek" ko'rinadi.
 */
@Composable
private fun FabButton(onClick: () -> Unit) {
    // Diqqat: avval soya elevatsiyasi (10dp) va to'liq to'yingan sariq
    // ambient/spot rang juda "loyqa" nur berib, pastdagi "Asosiy"/"Tarix"
    // yorliqlari ustiga tushib qolardi — endi ikkalasi ham yumshatilgan.
    Box(
        modifier = Modifier
            .offset(y = (-14).dp)
            .size(50.dp)
            .shadow(
                elevation = 5.dp,
                shape = RoundedCornerShape(16.dp),
                ambientColor = VijdonColors.Yellow.copy(alpha = 0.5f),
                spotColor = VijdonColors.Yellow.copy(alpha = 0.5f),
            )
            .clip(RoundedCornerShape(16.dp))
            .background(VijdonColors.Yellow)
            .border(4.dp, VijdonColors.Surface, RoundedCornerShape(16.dp))
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(Icons.Rounded.Add, contentDescription = "Taksimetrni boshlash", tint = VijdonColors.TextOnYellow, modifier = Modifier.size(24.dp))
    }
}
