package uz.vijdon.driver.ui.theme

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.dp

/** Veb paneldagi "2 navbatda" / "Yakunlandi" kabi dumaloq nishonlar. */
@Composable
fun Pill(text: String, color: Color = VijdonColors.TextSecondary, background: Color = VijdonColors.BadgeNeutral, modifier: Modifier = Modifier) {
    Text(
        text,
        color = color,
        style = MaterialTheme.typography.labelMedium,
        modifier = modifier
            .background(background, CircleShape)
            .padding(horizontal = 12.dp, vertical = 6.dp),
    )
}

val CardShape = RoundedCornerShape(CardRadius)
val ChipShape = RoundedCornerShape(ChipRadius)

/** Kartalarga Yandex Taxi uslubidagi yengil "ko'tarilgan" soya beradi — tekis fon o'rniga chuqurlik hissi. */
fun Modifier.cardShadow(shape: Shape = CardShape, elevation: androidx.compose.ui.unit.Dp = 8.dp): Modifier =
    this.shadow(elevation = elevation, shape = shape, clip = false, ambientColor = Color.Black, spotColor = Color.Black)
