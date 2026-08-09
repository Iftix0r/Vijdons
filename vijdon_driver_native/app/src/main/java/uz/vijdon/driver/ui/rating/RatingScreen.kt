package uz.vijdon.driver.ui.rating

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.RatingRowDto

@Composable
fun RatingScreen(viewModel: RatingViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Scaffold { padding ->
        LazyColumn(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 12.dp)) {
            item {
                state.gapToNext?.let {
                    Text(
                        "Oldinga chiqish uchun yana $it ta buyurtma kerak",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(vertical = 8.dp),
                    )
                }
            }
            items(state.rows, key = { it.rank }) { row -> RatingRow(row) }
        }
    }
}

@Composable
private fun RatingRow(row: RatingRowDto) {
    val bg = if (row.is_me) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface
    Row(
        modifier = Modifier.fillMaxWidth().background(bg).padding(vertical = 10.dp, horizontal = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text("${row.rank}. ${row.full_name}", style = MaterialTheme.typography.bodyMedium)
        Text("${row.completed} safar · ${row.earned} so'm", style = MaterialTheme.typography.bodySmall)
    }
}
