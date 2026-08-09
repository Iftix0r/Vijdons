package uz.vijdon.callwatcher

import android.content.Context
import android.media.AudioManager
import android.media.MediaRecorder
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import java.io.File

/**
 * Qo'ng'iroq audiosini mahalliy faylga yozadi.
 *
 * DIQQAT: Android 10 (API 29) dan boshlab tizim uchinchi tomon ilovalarga
 * qo'ng'iroq audiosini AudioSource.VOICE_CALL orqali yozib olishni odatda
 * bloklaydi (Google maxfiylik siyosati). Muammoli tomoni: ba'zi qurilmalarda
 * bu manba xatosiz ishga tushadi, lekin haqiqatda HECH QANDAY ovoz
 * yozmaydi (butunlay jim fayl) — xato tashlamagani uchun buni faqat
 * yozib bo'lgandan keyin ovoz sathini (amplitude) tekshirib aniqlash mumkin.
 * Shu sabab: yozuv davomida ovoz sathi kuzatiladi, butunlay jim bo'lsa
 * "silent" deb belgilanadi — CallWatcherService keyingi qo'ng'iroqda
 * ro'yxatdagi keyingi manbaga o'tkazadi (Prefs.audioSourceIndex).
 */
class CallRecorder(private val context: Context) {

    private var recorder: MediaRecorder? = null
    private var outputFile: File? = null
    private var startedAt: Long = 0L
    private var sawSound = false
    private var usedSpeakerphone = false
    private var previousSpeakerphoneState = false
    private var lastResultWasSilent = false

    private val amplitudeHandler = Handler(Looper.getMainLooper())
    private val amplitudeCheck = object : Runnable {
        override fun run() {
            val mr = recorder ?: return
            try {
                if (mr.maxAmplitude > SILENCE_THRESHOLD) sawSound = true
            } catch (_: Exception) {
                // getMaxAmplitude ba'zi holatlarda ObjectNotConfiguredException tashlaydi — e'tiborsiz qoldiramiz
            }
            amplitudeHandler.postDelayed(this, 500)
        }
    }

    /** [fromIndex] — ro'yxatdagi shu indeksdan boshlab audio manbalarni sinaydi
     * (oldingi qo'ng'iroqda qaysi manba jim bo'lib chiqqan bo'lsa, shundan keyingisidan). */
    fun start(phoneNumber: String, fromIndex: Int = 0): Boolean {
        val dir = File(context.cacheDir, "call_recordings").apply { mkdirs() }
        val safeName = phoneNumber.filter { it.isDigit() || it == '+' }
        val file = File(dir, "call_${safeName}_${System.currentTimeMillis()}.m4a")

        val startIdx = fromIndex.coerceIn(0, AUDIO_SOURCES.size - 1)
        for (i in startIdx until AUDIO_SOURCES.size) {
            val source = AUDIO_SOURCES[i]
            val mr = createRecorder()
            try {
                if (source == MediaRecorder.AudioSource.MIC) enableSpeakerphone()
                mr.setAudioSource(source)
                mr.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                mr.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                mr.setAudioEncodingBitRate(32000)
                mr.setAudioSamplingRate(16000)
                mr.setOutputFile(file.absolutePath)
                mr.prepare()
                mr.start()
                recorder = mr
                outputFile = file
                startedAt = System.currentTimeMillis()
                sawSound = false
                amplitudeHandler.postDelayed(amplitudeCheck, 500)
                Log.i(TAG, "Yozuv boshlandi (source=$source, index=$i): ${file.name}")
                return true
            } catch (e: Exception) {
                Log.w(TAG, "Audio manba $source ishlamadi: ${e.message}")
                try { mr.release() } catch (_: Exception) {}
                if (source == MediaRecorder.AudioSource.MIC) restoreSpeakerphone()
            }
        }
        Log.e(TAG, "Hech qanday audio manba ishlamadi — bu qurilmada qo'ng'iroq yozib olish qo'llab-quvvatlanmaydi")
        return false
    }

    /** To'xtatadi va yozilgan faylni qaytaradi. Agar yozuv davomida hech qanday
     * ovoz sathi qayd etilmagan bo'lsa (butunlay jim), null qaytaradi va
     * [wasSilent] true bo'ladi — chaqiruvchi keyingi safar boshqa manbaga
     * o'tishi kerakligini shundan biladi. */
    fun stop(): Pair<File, Int>? {
        amplitudeHandler.removeCallbacks(amplitudeCheck)
        restoreSpeakerphone()
        lastResultWasSilent = false
        val mr = recorder ?: return null
        val file = outputFile
        val durationSec = ((System.currentTimeMillis() - startedAt) / 1000).toInt()
        recorder = null
        outputFile = null
        try {
            mr.stop()
        } catch (e: Exception) {
            Log.w(TAG, "Yozuvni to'xtatishda xato", e)
        } finally {
            try { mr.release() } catch (_: Exception) {}
        }
        if (file == null || !file.exists() || file.length() < 512) {
            Log.w(TAG, "Yozilgan fayl bo'sh yoki juda kichik — tashlab yuboriladi")
            file?.delete()
            return null
        }
        if (!sawSound) {
            Log.w(TAG, "Yozuv butunlay jim — bu manba ishlamayapti, tashlab yuboriladi")
            file.delete()
            lastResultWasSilent = true
            return null
        }
        return file to durationSec
    }

    /** Yozuv jim bo'lgani sababli tashlab yuborilganmi (stop() dan keyin chaqiring). */
    fun wasSilent(): Boolean = lastResultWasSilent

    private fun enableSpeakerphone() {
        try {
            val am = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager ?: return
            previousSpeakerphoneState = am.isSpeakerphoneOn
            am.mode = AudioManager.MODE_IN_CALL
            am.isSpeakerphoneOn = true
            usedSpeakerphone = true
        } catch (e: Exception) {
            Log.w(TAG, "Dinamikni yoqishda xato", e)
        }
    }

    private fun restoreSpeakerphone() {
        if (!usedSpeakerphone) return
        usedSpeakerphone = false
        try {
            val am = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager ?: return
            am.isSpeakerphoneOn = previousSpeakerphoneState
        } catch (e: Exception) {
            Log.w(TAG, "Dinamikni asl holatga qaytarishda xato", e)
        }
    }

    private fun createRecorder(): MediaRecorder {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) MediaRecorder(context) else @Suppress("DEPRECATION") MediaRecorder()
    }

    companion object {
        private const val TAG = "VijdonCallRecorder"
        private const val SILENCE_THRESHOLD = 300 // getMaxAmplitude() 0..32767 oralig'ida

        // VOICE_CALL — ikkala tomonni ham to'g'ridan-to'g'ri ushlaydi (eng yaxshisi,
        // lekin ko'p qurilmada bloklangan). VOICE_DOWNLINK — faqat kiruvchi ovoz.
        // MIC (dinamik rejim yoqilgan holda) — oxirgi chora, telefoniya manbasiga
        // bog'liq emas, shuning uchun ko'pchilik qurilmada ishlaydi.
        val AUDIO_SOURCES = intArrayOf(
            MediaRecorder.AudioSource.VOICE_CALL,
            MediaRecorder.AudioSource.VOICE_DOWNLINK,
            MediaRecorder.AudioSource.MIC
        )
    }
}
