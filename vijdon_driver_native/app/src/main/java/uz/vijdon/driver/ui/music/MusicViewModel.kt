package uz.vijdon.driver.ui.music

import android.media.AudioAttributes
import android.media.MediaPlayer
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.MusicTrackDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class MusicUiState(
    val tracks: List<MusicTrackDto> = emptyList(),
    val currentIndex: Int = -1,
    val isPlaying: Boolean = false,
    val loading: Boolean = true,
    val error: String? = null,
)

/**
 * Operator panelida qo'shilgan pleylistni (`taxi/views.py: music_list`)
 * ijro etadi — haydovchi ilovasi Asosiy'dan o'ngga surilganda ochiladigan
 * "Musiqa" bo'limi. Diqqat: bu YOZUV (in-app) pleylist — `DriverSoundPlayer`
 * (yangi buyurtma/qabul qilish kabi qisqa signal ovozlari) bilan aralashtirib
 * yubormaslik uchun ataylab alohida `MediaPlayer` ishlatiladi. Ilova
 * fondan chiqarilsa yoki ekran yopilsa ijro to'xtaydi (fon xizmati emas,
 * shu sabab faqat ilova ochiq turgan payt eshitiladi).
 */
@HiltViewModel
class MusicViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(MusicUiState())
    val uiState: StateFlow<MusicUiState> = _uiState.asStateFlow()

    private var player: MediaPlayer? = null

    init { load() }

    private fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            when (val result = repository.musicTracks()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(tracks = result.data, loading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }

    fun refresh() = load()

    fun togglePlayPause() {
        val state = _uiState.value
        if (state.tracks.isEmpty()) return
        if (state.currentIndex == -1) {
            playAt(0)
            return
        }
        val active = player ?: return
        try {
            if (state.isPlaying) {
                active.pause()
                _uiState.value = state.copy(isPlaying = false)
            } else {
                active.start()
                _uiState.value = state.copy(isPlaying = true)
            }
        } catch (_: Exception) {
        }
    }

    fun playAt(index: Int) {
        val tracks = _uiState.value.tracks
        if (index !in tracks.indices) return
        releasePlayer()
        val track = tracks[index]
        try {
            player = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build(),
                )
                setDataSource(track.url)
                setOnPreparedListener { it.start() }
                setOnCompletionListener { next() }
                setOnErrorListener { _, _, _ -> next(); true }
                prepareAsync()
            }
            _uiState.value = _uiState.value.copy(currentIndex = index, isPlaying = true, error = null)
        } catch (_: Exception) {
            _uiState.value = _uiState.value.copy(error = "Musiqani ijro etib bo'lmadi")
        }
    }

    fun next() {
        val s = _uiState.value
        if (s.tracks.isEmpty()) return
        playAt((s.currentIndex + 1).mod(s.tracks.size))
    }

    fun previous() {
        val s = _uiState.value
        if (s.tracks.isEmpty()) return
        playAt((s.currentIndex - 1).mod(s.tracks.size))
    }

    private fun releasePlayer() {
        player?.apply {
            try { stop() } catch (_: Exception) { }
            release()
        }
        player = null
    }

    override fun onCleared() {
        releasePlayer()
        super.onCleared()
    }
}
