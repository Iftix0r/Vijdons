package uz.vijdon.driver.ui.rating

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
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.RatingRowDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.VijdonColors

private val medalColors = mapOf(1 to VijdonColors.Yellow, 2 to androidx.compose.ui.graphics.Color(0xFFC0C0C0), 3 to androidx.compose.ui.graphics.Color(0xFFCD7F32))

@Composable
fun RatingScreen(viewModel: RatingViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.EmojiEvents, contentDescription = null, tint = VijdonColors.Yellow)
            Spacer(Modifier.width(8.dp))
            Text("Reyting", color = VijdonColors.TextPrimary, style = MaterialTheme.typography.headlineMedium)
        }
        Spacer(Modifier.height(4.dp))
        Text("Joriy oy — eng ko'p safar bajargan haydovchilar", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)

        state.gapToNext?.let {
            Spacer(Modifier.height(12.dp))
            Box(modifier = Modifier.fillMaxWidth().background(VijdonColors.BadgeNeutral, CardShape).padding(12.dp)) {
                Text("Oldinga chiqish uchun yana $it ta buyurtma kerak", color = VijdonColors.Yellow, style = MaterialTheme.typography.bodyMedium)
            }
        }

        Spacer(Modifier.height(12.dp))
        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(state.rows, key = { it.rank }) { row -> RatingRow(row) }
        }
    }
}

@Composable
private fun RatingRow(row: RatingRowDto) {
    val bg = if (row.is_me) VijdonColors.Yellow.copy(alpha = 0.15f) else VijdonColors.Surface
    Row(
        modifier = Modifier.fillMaxWidth().background(bg, CardShape).padding(vertical = 4.dp).padding(14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            val medal = medalColors[row.rank]
            Box(
                modifier = Modifier.size(28.dp).background(medal ?: VijdonColors.BadgeNeutral, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(row.rank.toString(), color = if (medal != null) VijdonColors.TextOnYellow else VijdonColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
            }
            Spacer(Modifier.width(12.dp))
            Text(row.full_name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.bodyLarge)
        }
        Text("${row.completed} safar · ${row.earned} so'm", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
    }
    Spacer(Modifier.height(4.dp))
}
