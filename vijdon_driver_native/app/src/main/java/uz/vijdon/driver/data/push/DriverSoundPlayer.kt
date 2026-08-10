package uz.vijdon.driver.data.push

import android.media.AudioAttributes
import android.media.MediaPlayer
import uz.vijdon.driver.data.api.DriverSoundDto

/**
 * Veb haydovchi panelidagi ovozli bildirishnomalar (`window.VJ_DRIVER_SOUNDS`,
 * `taxi/context_processors.py`) bilan bir xil g'oya — operator sozlagan
 * (yoki standart) ovoz fayllarini server bergan URL'dan chalib beradi.
 * Alohida Context/Hilt talab qilmaydigan oddiy singleton — shu sabab
 * ViewModel'dan ham (`HomeViewModel`), fon xizmati/Worker'dan ham
 * (`DriverLocationService`, `OrderActionWorker`) bir xilda chaqirilishi
 * mumkin. Ovoz — ixtiyoriy qo'shimcha, shu sabab har qanday xatolik jim
 * yutiladi (ilova asosiy ishini to'xtatmaydi).
 */
object DriverSoundPlayer {
    private var sounds: Map<String, DriverSoundDto> = emptyMap()
    private var activePlayer: MediaPlayer? = null

    fun updateSounds(map: Map<String, DriverSoundDto>) {
        sounds = map
    }

    fun play(eventKey: String) {
        val sound = sounds[eventKey] ?: return
        if (!sound.enabled) return
        val url = sound.url ?: return
        try {
            activePlayer?.release()
            activePlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_NOTIFICATION_EVENT)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build(),
                )
                setDataSource(url)
                setOnPreparedListener { it.start() }
                setOnCompletionListener { mp -> mp.release(); if (activePlayer === mp) activePlayer = null }
                setOnErrorListener { mp, _, _ -> mp.release(); if (activePlayer === mp) activePlayer = null; true }
                prepareAsync()
            }
        } catch (_: Exception) {
            // Ovoz ixtiyoriy — xato bo'lsa ilovaning asosiy oqimiga ta'sir qilmasin.
        }
    }
}

/** `DRIVER_SOUND_EVENTS` (taxi/constants.py) bilan bir xil kalitlar. */
object DriverSoundEvent {
    const val NEW_ORDER = "driver_new_order"
    const val ACCEPT = "driver_accept"
    const val REJECT = "driver_reject"
    const val COMPLETE = "driver_complete"
    const val LOW_BALANCE = "driver_low_balance"
}
