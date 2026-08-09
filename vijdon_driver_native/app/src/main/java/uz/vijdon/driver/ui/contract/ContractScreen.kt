package uz.vijdon.driver.ui.contract

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import java.io.File

@Composable
fun ContractScreen(viewModel: ContractViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val signatureState = remember { SignatureState() }
    var agree by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader(if (state.title.isNotBlank()) "${state.title} (v${state.version})" else "Shartnoma")
        Spacer(Modifier.height(8.dp))

        if (state.signed) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.CheckCircle, contentDescription = null, tint = VijdonColors.Green, modifier = Modifier.height(18.dp))
                Spacer(Modifier.width(6.dp))
                Text("Siz ushbu versiyani allaqachon imzolagansiz.", color = VijdonColors.Green)
            }
            Spacer(Modifier.height(12.dp))
        }

        Text(
            state.content,
            style = MaterialTheme.typography.bodySmall,
            color = VijdonColors.TextSecondary,
            modifier = Modifier.weight(1f).verticalScroll(rememberScrollState())
                .background(VijdonColors.Surface, CardShape).padding(14.dp),
        )

        if (!state.signed) {
            Spacer(Modifier.height(12.dp))
            Text("Imzo:", style = MaterialTheme.typography.labelLarge, color = VijdonColors.TextSecondary)
            Spacer(Modifier.height(4.dp))
            SignaturePad(state = signatureState)
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                OutlinedButton(
                    onClick = { signatureState.clear() },
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = VijdonColors.TextPrimary),
                ) { Text("Tozalash") }
            }

            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 8.dp)) {
                Checkbox(
                    checked = agree, onCheckedChange = { agree = it },
                    colors = CheckboxDefaults.colors(checkedColor = VijdonColors.Yellow, checkmarkColor = VijdonColors.TextOnYellow),
                )
                Text("Shartlarga roziman", color = VijdonColors.TextPrimary)
            }

            state.error?.let {
                Text(it, color = VijdonColors.Red)
            }

            Spacer(Modifier.height(12.dp))
            Button(
                onClick = {
                    val file = File(context.cacheDir, "signature.png")
                    if (signatureState.exportToFile(file)) viewModel.sign(file)
                },
                enabled = !state.submitting && agree && !signatureState.isEmpty,
                colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                Text("Imzolash")
            }
        }
    }
}
