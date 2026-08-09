package uz.vijdon.driver.ui.rating

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.RatingRowDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow

private val medalEmoji = mapOf(1 to "🥇", 2 to "🥈", 3 to "🥉")

@Composable
fun RatingScreen(viewModel: RatingViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Reyting", subtitle = "Joriy oy — eng ko'p safar bajargan haydovchilar")

        Spacer(Modifier.height(14.dp))
        RankHeroCard(myRow = state.myRow, totalDrivers = state.rows.size, gapToNext = state.gapToNext)

        Spacer(Modifier.height(14.dp))
        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(state.rows, key = { it.rank }) { row -> RatingRow(row) }
        }
    }
}

/** Veb paneldagi kabi — haydovchining o'z o'rnini darhol ko'rsatadigan, rag'batlantiruvchi gradient karta. */
@Composable
private fun RankHeroCard(myRow: RatingRowDto?, totalDrivers: Int, gapToNext: Int?) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow(elevation = 10.dp)
            .background(Brush.linearGradient(listOf(VijdonColors.Yellow, androidx.compose.ui.graphics.Color(0xFFFF9500))), CardShape)
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("SIZNING O'RNINGIZ", color = androidx.compose.ui.graphics.Color(0xB3000000), style = MaterialTheme.typography.labelSmall)
        Text(
            if (myRow != null) "#${myRow.rank}" else "—",
            color = androidx.compose.ui.graphics.Color(0xFF111111),
            style = MaterialTheme.typography.displayMedium,
        )
        if (myRow != null) {
            Text(
                "$totalDrivers haydovchidan · ${myRow.completed} ta buyurtma",
                color = androidx.compose.ui.graphics.Color(0xA6000000),
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(4.dp))
            val message = when {
                myRow.rank == 1 -> "🏆 Siz bu oyning yetakchisisiz! Shu ruhda davom eting 💪"
                gapToNext != null -> "🔥 Yana $gapToNext ta buyurtma bilan oldingi o'ringa chiqasiz!"
                else -> null
            }
            message?.let {
                Text(it, color = androidx.compose.ui.graphics.Color(0xFF111111), style = MaterialTheme.typography.labelMedium, textAlign = TextAlign.Center)
            }
        } else {
            Text("Bu oy hali buyurtma yakunlanmagan", color = androidx.compose.ui.graphics.Color(0xA6000000), style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun RatingRow(row: RatingRowDto) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .cardShadow()
            .let { if (row.is_me) it.border(BorderStroke(2.dp, VijdonColors.Yellow), CardShape) else it }
            .background(VijdonColors.Surface, CardShape)
            .padding(14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            val emoji = medalEmoji[row.rank]
            Box(modifier = Modifier.size(28.dp), contentAlignment = Alignment.Center) {
                if (emoji != null) {
                    Text(emoji, style = MaterialTheme.typography.titleMedium)
                } else {
                    Text(row.rank.toString(), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
                }
            }
            Spacer(Modifier.width(12.dp))
            Column {
                Text(
                    row.full_name + if (row.is_me) " (Siz)" else "",
                    color = if (row.is_me) VijdonColors.Yellow else VijdonColors.TextPrimary,
                    style = MaterialTheme.typography.bodyLarge,
                )
                Text("${row.earned} so'm", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
            }
        }
        Text(row.completed.toString(), color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium)
    }
    Spacer(Modifier.height(4.dp))
}
