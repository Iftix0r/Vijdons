package uz.vijdon.driver.ui.addresses

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.RegionDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ChipShape
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow

/**
 * Manzillar — endi faqat "yaqin atrofdagi"lar emas, O'zbekiston bo'ylab
 * BARCHA manzillarni qidirish/hudud (viloyat→tuman) bo'yicha filtrlash
 * imkoniyati bilan. Haydovchi shu orqali boshqa hududda talab (navbat)
 * qanday ekanini oldindan ko'rib chiqishi mumkin — buyurtma esa, albatta,
 * faqat haydovchi HAQIQATDA o'sha manzil radiusiga yetib borgandagina
 * (GPS orqali) unga tegishli bo'ladi, xuddi hozirgi navbat tizimidagidek.
 */
@Composable
fun AddressesScreen(viewModel: AddressesViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Manzillar", subtitle = "Qidiring yoki hudud bo'yicha ajrating")
        Spacer(Modifier.height(12.dp))

        OutlinedTextField(
            value = state.searchQuery,
            onValueChange = viewModel::onSearchQueryChange,
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("Manzil nomi bo'yicha qidirish...") },
            leadingIcon = { Icon(Icons.Rounded.Search, contentDescription = null, tint = VijdonColors.TextSecondary) },
            trailingIcon = {
                if (state.hasActiveFilter) {
                    IconButton(onClick = viewModel::clearFilters) {
                        Icon(Icons.Rounded.Close, contentDescription = "Filtrni tozalash", tint = VijdonColors.TextSecondary)
                    }
                }
            },
            singleLine = true,
            shape = ChipShape,
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = VijdonColors.Surface, unfocusedContainerColor = VijdonColors.Surface,
                focusedTextColor = VijdonColors.TextPrimary, unfocusedTextColor = VijdonColors.TextPrimary,
            ),
        )

        if (state.regions.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            RegionChipsRow(
                regions = state.regions,
                selectedRegionId = state.selectedRegionId,
                onRegionClick = { viewModel.onRegionSelected(if (it == state.selectedRegionId) null else it) },
            )
            state.selectedRegion?.districts?.takeIf { it.isNotEmpty() }?.let { districts ->
                Spacer(Modifier.height(6.dp))
                DistrictChipsRow(
                    districts = districts,
                    selectedDistrictId = state.selectedDistrictId,
                    onDistrictClick = { viewModel.onDistrictSelected(if (it == state.selectedDistrictId) null else it) },
                )
            }
        }

        Spacer(Modifier.height(12.dp))

        state.error?.let {
            ErrorBanner(it, modifier = Modifier.padding(bottom = 10.dp))
        }

        if ((state.loading || state.detectingArea) && state.addresses.isEmpty()) {
            CenteredLoading()
        } else if (state.addresses.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(
                    if (state.hasActiveFilter) "Shu qidiruv bo'yicha manzil topilmadi" else "Boshqa manzillarni topish uchun nomini yozing yoki hudud tanlang",
                    color = VijdonColors.TextSecondary,
                    modifier = Modifier.padding(horizontal = 32.dp),
                    textAlign = TextAlign.Center,
                )
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.addresses, key = { it.id }) { address ->
                    Column(Modifier.animateItem()) { AddressRow(address) { viewModel.openQueue(address) } }
                }
            }
        }
    }

    state.selectedAddress?.let { address ->
        AlertDialog(
            onDismissRequest = viewModel::closeQueue,
            title = { Text(address.name, color = VijdonColors.TextPrimary) },
            text = {
                Column {
                    state.myPosition?.let {
                        Text("Sizning o'rningiz: $it", color = VijdonColors.Yellow, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                    } ?: Text("Siz navbatda emassiz", color = VijdonColors.TextSecondary)
                    if (state.queueDrivers.isNotEmpty()) {
                        Spacer(Modifier.height(10.dp))
                        state.queueDrivers.forEach { d ->
                            AddressQueueDriverRow(d)
                            Spacer(Modifier.height(6.dp))
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = viewModel::closeQueue) { Text("Yopish", color = VijdonColors.Yellow) } },
            containerColor = VijdonColors.Surface,
        )
    }
}

@Composable
private fun RegionChipsRow(regions: List<RegionDto>, selectedRegionId: Int?, onRegionClick: (Int) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        regions.forEach { region ->
            val selected = region.id == selectedRegionId
            Text(
                region.name,
                color = if (selected) VijdonColors.TextOnYellow else VijdonColors.TextPrimary,
                style = MaterialTheme.typography.labelMedium,
                maxLines = 1,
                modifier = Modifier
                    .background(if (selected) VijdonColors.Yellow else VijdonColors.Surface, ChipShape)
                    .clickable { onRegionClick(region.id) }
                    .padding(horizontal = 12.dp, vertical = 8.dp),
            )
        }
    }
}

@Composable
private fun DistrictChipsRow(districts: List<uz.vijdon.driver.data.api.DistrictDto>, selectedDistrictId: Int?, onDistrictClick: (Int) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        districts.forEach { district ->
            val selected = district.id == selectedDistrictId
            Text(
                district.name,
                color = if (selected) VijdonColors.TextOnYellow else VijdonColors.TextSecondary,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1,
                modifier = Modifier
                    .background(if (selected) VijdonColors.Yellow else VijdonColors.BadgeNeutral, ChipShape)
                    .clickable { onDistrictClick(district.id) }
                    .padding(horizontal = 10.dp, vertical = 6.dp),
            )
        }
    }
}

/** Bosh sahifadagi manzil navbati bilan bir xil uslub — raqamlangan
 * doira belgi + "Siz" bo'lsa sariq bilan ajratilgan. */
@Composable
private fun AddressQueueDriverRow(d: uz.vijdon.driver.data.api.QueueDriverDto) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier.size(22.dp).background(if (d.is_me) VijdonColors.Yellow else VijdonColors.BadgeNeutral, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Text(d.position.toString(), color = if (d.is_me) VijdonColors.TextOnYellow else VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        }
        Spacer(Modifier.width(8.dp))
        Text(
            "${d.full_name}${if (d.is_me) " (Siz)" else ""} — ${d.car_model} (${d.car_number})",
            // Bosh sahifadagi bilan bir xil sabab: to'liq to'yingan Yellow
            // matn kartaning oq/och fonida past-kontrastli edi — YellowDark
            // ishlatiladi (uyg'unlik uchun Home ekrani bilan bir xil qoida).
            color = if (d.is_me) VijdonColors.YellowDark else VijdonColors.TextPrimary,
            style = MaterialTheme.typography.bodySmall,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun AddressRow(address: AddressDto, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 18.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(36.dp).background(VijdonColors.BadgeNeutral, CircleShape), contentAlignment = Alignment.Center) {
                Icon(Icons.Rounded.LocationOn, contentDescription = null, tint = VijdonColors.Red, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(address.name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    // Hudud ma'lum bo'lsa ko'rsatiladi (masalan "Chilonzor
                    // tumani") — yo'q bo'lsa (hali tayinlanmagan avtomatik
                    // manzil) bugungi buyurtmalar soni bilan almashtiriladi.
                    address.district_name?.let { "$it · Bugun: ${address.today_orders}" } ?: "Bugun: ${address.today_orders} buyurtma",
                    color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall,
                    maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
            }
        }
        Spacer(Modifier.width(8.dp))
        // Bosh sahifadagi manzil ro'yxati bilan bir xil qoida (uyg'unlik
        // uchun): navbat bo'sh bo'lsa "0 navbatda" emas, aniq "Bo'sh" so'zi
        // ko'rsatiladi, va band bo'lsa yorqinroq GreenBadge rangi ishlatiladi.
        if (address.queue_count > 0) {
            Pill("${address.queue_count} navbatda", color = VijdonColors.GreenBadge, background = VijdonColors.GreenBadge.copy(alpha = 0.22f))
        } else {
            Pill("Bo'sh", color = VijdonColors.TextSecondary, background = VijdonColors.TextSecondary.copy(alpha = 0.18f))
        }
    }
}
