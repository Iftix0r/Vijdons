package uz.vijdon.driver.ui.contract

import android.graphics.Bitmap
import android.graphics.Canvas as AndroidCanvas
import android.graphics.Color as AndroidColor
import android.graphics.Paint
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import java.io.File
import java.io.FileOutputStream

/** Qo'l bilan imzo chizish maydoni — chizilgan yo'llarni saqlaydi va PNG faylga eksport qila oladi. */
class SignatureState {
    val strokes = mutableStateListOf<MutableList<Offset>>()
    var canvasSize: IntSize = IntSize.Zero

    fun clear() = strokes.clear()
    val isEmpty: Boolean get() = strokes.isEmpty()

    fun exportToFile(file: File): Boolean {
        if (canvasSize.width == 0 || canvasSize.height == 0 || strokes.isEmpty()) return false
        val bitmap = Bitmap.createBitmap(canvasSize.width, canvasSize.height, Bitmap.Config.ARGB_8888)
        val canvas = AndroidCanvas(bitmap)
        canvas.drawColor(AndroidColor.WHITE)
        val paint = Paint().apply {
            color = AndroidColor.BLACK
            strokeWidth = 6f
            style = Paint.Style.STROKE
            strokeCap = Paint.Cap.ROUND
            strokeJoin = Paint.Join.ROUND
            isAntiAlias = true
        }
        strokes.forEach { stroke ->
            for (i in 0 until stroke.size - 1) {
                canvas.drawLine(stroke[i].x, stroke[i].y, stroke[i + 1].x, stroke[i + 1].y, paint)
            }
        }
        return try {
            FileOutputStream(file).use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
            true
        } catch (e: Exception) {
            false
        }
    }
}

@Composable
fun SignaturePad(state: SignatureState, modifier: Modifier = Modifier) {
    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(200.dp)
            .background(Color.White)
            .border(1.dp, MaterialTheme.colorScheme.outline)
            .onSizeChanged { state.canvasSize = it }
            .pointerInput(Unit) {
                detectDragGestures(
                    onDragStart = { offset -> state.strokes.add(mutableListOf(offset)) },
                    onDrag = { change, _ ->
                        state.strokes.lastOrNull()?.add(change.position)
                    },
                )
            },
    ) {
        state.strokes.forEach { stroke ->
            for (i in 0 until stroke.size - 1) {
                drawLine(
                    color = Color.Black, start = stroke[i], end = stroke[i + 1],
                    strokeWidth = 6f, cap = StrokeCap.Round,
                )
            }
        }
    }
}
