package uz.vijdon.callwatcher

import android.content.ContentUris
import android.content.Context
import android.provider.MediaStore
import android.util.Log
import java.io.File

/**
 * Telefonning o'zining Dialer/Qo'ng'iroq ilovasi qo'ng'iroqni avtomatik yozib
 * olsa (ko'p qurilmalarda — Xiaomi, Vivo, Oppo va h.k. — shunday funksiya
 * bor), bu klass qo'ng'iroq tugagandan keyin MediaStore'dan eng yangi qo'shilgan
 * audio faylni qidiradi va uni ilova cache papkasiga nusxalaydi. Aniq papka
 * yo'lini bilish shart emas (har brendda boshqacha) — shunchaki vaqt bo'yicha
 * (qo'ng'iroq tugagandan keyin bir necha soniya ichida qo'shilgan) mos keladi.
 */
class NativeRecordingWatcher(private val context: Context) {

    /** [sinceEpochMs] dan keyin MediaStore'ga qo'shilgan eng yangi audio faylni
     * topib, ilova cache papkasiga nusxalaydi. Topilmasa null. */
    fun findRecentRecording(sinceEpochMs: Long): File? {
        val resolver = context.contentResolver
        val collection = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        val projection = arrayOf(
            MediaStore.Audio.Media._ID,
            MediaStore.Audio.Media.DATE_ADDED,
            MediaStore.Audio.Media.DISPLAY_NAME
        )
        val sinceSec = sinceEpochMs / 1000
        val selection = "${MediaStore.Audio.Media.DATE_ADDED} >= ?"
        val selectionArgs = arrayOf(sinceSec.toString())
        val sortOrder = "${MediaStore.Audio.Media.DATE_ADDED} DESC"

        try {
            resolver.query(collection, projection, selection, selectionArgs, sortOrder)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val idCol = cursor.getColumnIndexOrThrow(MediaStore.Audio.Media._ID)
                    val nameCol = cursor.getColumnIndexOrThrow(MediaStore.Audio.Media.DISPLAY_NAME)
                    val id = cursor.getLong(idCol)
                    val name = cursor.getString(nameCol)
                    val uri = ContentUris.withAppendedId(collection, id)
                    Log.i(TAG, "Topilgan yangi audio: $name")
                    return copyToCache(uri, name)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "MediaStore so'rovida xato", e)
        }
        return null
    }

    private fun copyToCache(uri: android.net.Uri, name: String?): File? {
        return try {
            val dir = File(context.cacheDir, "call_recordings").apply { mkdirs() }
            val ext = name?.substringAfterLast('.', "m4a") ?: "m4a"
            val out = File(dir, "native_${System.currentTimeMillis()}.$ext")
            context.contentResolver.openInputStream(uri)?.use { input ->
                out.outputStream().use { output -> input.copyTo(output) }
            }
            if (out.exists() && out.length() > 512) out else { out.delete(); null }
        } catch (e: Exception) {
            Log.e(TAG, "Faylni nusxalashda xato", e)
            null
        }
    }

    companion object {
        private const val TAG = "VijdonNativeRecWatcher"
    }
}
