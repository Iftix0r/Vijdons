package uz.vijdon.driver.data.push

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.Ringtone
import android.media.RingtoneManager
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
    private var appContext: Context? = null
    private var sounds: Map<String, DriverSoundDto> = emptyMap()
    private var activePlayer: MediaPlayer? = null
    private var activeRingtone: Ringtone? = null

    /** `VijdonDriverApp.onCreate()`dan bir marta chaqiriladi — mahalliy
     * qo'ng'iroq ohangini (RingtoneManager) o'qish uchun Context kerak. */
    fun init(context: Context) {
        appContext = context.applicationContext
    }

    fun updateSounds(map: Map<String, DriverSoundDto>) {
        sounds = map
    }

    fun play(eventKey: String) {
        // Yangi buyurtma — operator sozlagan maxsus ovoz (server URL'idan
        // MediaPlayer.setDataSource + prepareAsync bilan) o'rniga telefonning
        // O'Z qo'ng'iroq ohangi ishlatiladi. Sabab: server ovozi tarmoqdan
        // birinchi baytlar kelguncha (sekin/beqaror aloqada bir necha soniya)
        // jim turardi — endi javob vaqti atigi 15s bo'lgani uchun bu
        // kechikish haydovchini buyurtmani eshitmay qolib ketishiga olib
        // kelishi mumkin edi. Mahalliy ringtone tarmoqqa umuman bog'liq
        // emas — DARHOL, kechikishsiz chalinadi. Admin panelidagi
        // yoqish/o'chirish sozlamasi (Ovozlar) hurmat qilinadi — faqat
        // ANIQ o'chirilgan bo'lsagina jim qolinadi.
        if (eventKey == DriverSoundEvent.NEW_ORDER) {
            if (sounds[eventKey]?.enabled == false) return
            playLocalRingtone()
            return
        }
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

    /**
     * Buyurtma boshqa sabab bilan (qabul qilindi/rad etildi/vaqti tugab
     * boshqasiga o'tkazildi/bekor qilindi) tugaganda chaqiriladi — hali
     * ijro etilib turgan mahalliy ringtone'ni DARHOL to'xtatadi.
     *
     * MUHIM: bildirishnomani yopish (`NotificationManagerCompat.cancel()`)
     * bu ovozga HECH QANDAY ta'sir qilmaydi — ular butunlay mustaqil ikkita
     * mexanizm (notification kanalining o'z ovozi va bu yerdagi qo'lda
     * ishga tushirilgan `Ringtone`). Avval faqat bildirishnoma yopilib,
     * ringtone esa hech kim to'xtatmagani uchun oxirigacha (o'zining
     * to'liq davomiyligicha) chalinaverar edi — buyurtma allaqachon
     * qabul qilingan/bekor bo'lgan bo'lsa ham.
     */
    fun stop() {
        try {
            activeRingtone?.stop()
        } catch (_: Exception) {
        }
        activeRingtone = null
    }

    private fun playLocalRingtone() {
        val context = appContext ?: return
        try {
            activeRingtone?.stop()
            val uri = RingtoneManager.getActualDefaultRingtoneUri(context, RingtoneManager.TYPE_RINGTONE)
                ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
                ?: return
            val ringtone = RingtoneManager.getRingtone(context, uri) ?: return
            ringtone.audioAttributes = AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build()
            activeRingtone = ringtone
            ringtone.play()
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
