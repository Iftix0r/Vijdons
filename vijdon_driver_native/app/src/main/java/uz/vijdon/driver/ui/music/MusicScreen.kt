package uz.vijdon.driver.ui.music

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material.icons.rounded.MusicNote
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.SkipNext
import androidx.compose.material.icons.rounded.SkipPrevious
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.MusicTrackDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.TabHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow

@Composable
fun MusicScreen(viewModel: MusicViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        TabHeader(
            "Musiqa",
            subtitle = "Yo'lda tinglang",
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 16.dp).padding(bottom = 0.dp),
        )

        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            when {
                state.loading && state.tracks.isEmpty() -> CenteredLoading()
                state.error != null && state.tracks.isEmpty() -> Box(Modifier.padding(16.dp)) { ErrorBanner(state.error!!) }
                state.tracks.isEmpty() -> EmptyMusicState()
                else -> LazyColumn(
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(state.tracks, key = { it.id }) { track ->
                        val index = state.tracks.indexOf(track)
                        TrackRow(
                            track = track,
                            isCurrent = index == state.currentIndex,
                            isPlaying = index == state.currentIndex && state.isPlaying,
                            onClick = {
                                if (index == state.currentIndex) viewModel.togglePlayPause() else viewModel.playAt(index)
                            },
                        )
                    }
                    item { Spacer(Modifier.height(96.dp)) }
                }
            }
        }

        if (state.tracks.isNotEmpty()) {
            NowPlayingBar(
                track = state.tracks.getOrNull(state.currentIndex),
                isPlaying = state.isPlaying,
                onPlayPause = viewModel::togglePlayPause,
                onNext = viewModel::next,
                onPrevious = viewModel::previous,
            )
        }
    }
}

@Composable
private fun EmptyMusicState() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier.size(72.dp).background(VijdonColors.BadgeNeutral, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.MusicNote, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(32.dp))
            }
            Spacer(Modifier.height(12.dp))
            Text("Hali qo'shiq yo'q", color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium)
        }
    }
}

@Composable
private fun TrackRow(track: MusicTrackDto, isCurrent: Boolean, isPlaying: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(if (isCurrent) VijdonColors.Yellow.copy(alpha = 0.12f) else VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(38.dp).background(VijdonColors.Yellow.copy(alpha = 0.18f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                if (isCurrent && isPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow,
                contentDescription = null, tint = VijdonColors.YellowDark, modifier = Modifier.size(18.dp),
            )
        }
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                track.title, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = if (isCurrent) VijdonColors.YellowDark else VijdonColors.TextPrimary,
            )
            if (track.artist.isNotBlank()) {
                Text(track.artist, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
            }
        }
    }
}

@Composable
private fun NowPlayingBar(track: MusicTrackDto?, isPlaying: Boolean, onPlayPause: () -> Unit, onNext: () -> Unit, onPrevious: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(VijdonColors.Surface)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                track?.title ?: "Qo'shiq tanlang", style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = VijdonColors.TextPrimary, maxLines = 1,
            )
            if (track?.artist?.isNotBlank() == true) {
                Text(track.artist, style = MaterialTheme.typography.labelSmall, color = VijdonColors.TextSecondary, maxLines = 1)
            }
        }
        IconButton(onClick = onPrevious) {
            Icon(Icons.Rounded.SkipPrevious, contentDescription = "Oldingi", tint = VijdonColors.TextPrimary)
        }
        IconButton(
            onClick = onPlayPause,
            modifier = Modifier.size(44.dp).background(VijdonColors.Yellow, CircleShape),
        ) {
            Icon(
                if (isPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow,
                contentDescription = if (isPlaying) "Pauza" else "Ijro etish", tint = VijdonColors.TextOnYellow,
            )
        }
        IconButton(onClick = onNext) {
            Icon(Icons.Rounded.SkipNext, contentDescription = "Keyingi", tint = VijdonColors.TextPrimary)
        }
    }
}
