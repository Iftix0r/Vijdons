package uz.vijdon.driver.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

// Vijdon Taxi haydovchi paneli (veb) bilan bir xil qorong'i dizayn tizimi —
// ilova hozircha faqat shu bitta (qorong'i) mavzuda ishlaydi, tizim
// yorug'/qorong'i sozlamasiga qarab o'zgarmaydi (veb panel ham shunday).
object VijdonColors {
    val Background = Color(0xFF0F1015)
    val Surface = Color(0xFF191C28)
    val SurfaceRaised = Color(0xFF20232F)
    val BottomBar = Color(0xFF0B0C11)
    val Border = Color(0xFF2A2E3D)

    val Yellow = Color(0xFFF5B400)
    val YellowDark = Color(0xFFC68F00)
    val Green = Color(0xFF34D399)
    val Red = Color(0xFFEF4444)
    val Blue = Color(0xFF60A5FA)

    val TextPrimary = Color(0xFFF5F6FA)
    val TextSecondary = Color(0xFF8B92A5)
    val TextOnYellow = Color(0xFF1A1300)

    val BadgeNeutral = Color(0xFF262A3A)
}

val CardRadius = 18.dp
val ChipRadius = 12.dp

private val AppColorScheme = darkColorScheme(
    primary = VijdonColors.Yellow,
    onPrimary = VijdonColors.TextOnYellow,
    secondary = VijdonColors.Green,
    error = VijdonColors.Red,
    background = VijdonColors.Background,
    onBackground = VijdonColors.TextPrimary,
    surface = VijdonColors.Surface,
    onSurface = VijdonColors.TextPrimary,
    surfaceVariant = VijdonColors.SurfaceRaised,
    onSurfaceVariant = VijdonColors.TextSecondary,
    outline = VijdonColors.Border,
)

@Composable
fun VijdonDriverTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = AppColorScheme, content = content)
}
