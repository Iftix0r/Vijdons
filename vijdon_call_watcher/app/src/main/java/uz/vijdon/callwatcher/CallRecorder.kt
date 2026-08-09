package uz.vijdon.callwatcher

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import android.util.Log
import java.io.File

/**
 * Qo'ng'iroq audiosini mahalliy faylga yozadi.
 *
 * DIQQAT: Android 10 (API 29) dan boshlab tizim uchinchi tomon ilovalarga
 * qo'ng'iroq audiosini AudioSource.VOICE_CALL orqali yozib olishni odatda
 * bloklaydi (Google maxfiylik siyosati) — ba'zi qurilma ishlab
 * chiqaruvchilarida (masalan ba'zi Xiaomi/MIUI, mahalliy ROM'lar) hali ham
 * ishlashi mumkin, lekin bu kafolatlanmagan va OS yangilanishi bilan
 * to'xtab qolishi mumkin. Shu sabab bir nechta audio manba birma-bir
 * sinab ko'riladi — birinchisi ishlamasa keyingisiga o'tiladi.
 */
class CallRecorder(private val context: Context) {

    private var recorder: MediaRecorder? = null
    private var outputFile: File? = null
    private var startedAt: Long = 0L

    fun start(phoneNumber: String): Boolean {
        val dir = File(context.cacheDir, "call_recordings").apply { mkdirs() }
        val safeName = phoneNumber.filter { it.isDigit() || it == '+' }
        val file = File(dir, "call_${safeName}_${System.currentTimeMillis()}.m4a")

        for (source in AUDIO_SOURCES) {
            val mr = createRecorder()
            try {
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
                Log.i(TAG, "Yozuv boshlandi (source=$source): ${file.name}")
                return true
            } catch (e: Exception) {
                Log.w(TAG, "Audio manba $source ishlamadi: ${e.message}")
                try { mr.release() } catch (_: Exception) {}
            }
        }
        Log.e(TAG, "Hech qanday audio manba ishlamadi — bu qurilmada qo'ng'iroq yozib olish qo'llab-quvvatlanmaydi")
        return false
    }

    /** To'xtatadi va yozilgan faylni qaytaradi (agar muvaffaqiyatli va bo'sh bo'lmasa). */
    fun stop(): Pair<File, Int>? {
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
        return file to durationSec
    }

    private fun createRecorder(): MediaRecorder {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) MediaRecorder(context) else @Suppress("DEPRECATION") MediaRecorder()
    }

    companion object {
        private const val TAG = "VijdonCallRecorder"

        // Birinchi navbatda ikkala tomonni ushlaydigan manbalar, keyin faqat
        // mikrofon (faqat operator ovozi eshitiladi, dinamik rejim yoqilgan
        // bo'lsa mijoz ovozi ham qisman kirishi mumkin) — oxirgi chora sifatida.
        private val AUDIO_SOURCES = intArrayOf(
            MediaRecorder.AudioSource.VOICE_CALL,
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            MediaRecorder.AudioSource.MIC
        )
    }
}
