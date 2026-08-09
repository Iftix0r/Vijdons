package uz.vijdon.driver.util

import android.content.Context
import android.net.Uri
import java.io.File

/** Galereya/kameradan tanlangan `content://` Uri'ni multipart yuklash uchun vaqtinchalik faylga nusxalaydi. */
fun copyUriToCacheFile(context: Context, uri: Uri, fileName: String): File? {
    val input = context.contentResolver.openInputStream(uri) ?: return null
    val file = File(context.cacheDir, fileName)
    input.use { inStream -> file.outputStream().use { out -> inStream.copyTo(out) } }
    return file
}
