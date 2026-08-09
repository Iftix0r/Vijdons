package uz.vijdon.driver.ui.contract

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
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
import java.io.File

@Composable
fun ContractScreen(viewModel: ContractViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val signatureState = remember { SignatureState() }
    var agree by remember { mutableStateOf(false) }

    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            Text("${state.title} (v${state.version})", style = MaterialTheme.typography.headlineSmall)
            Spacer(Modifier.height(8.dp))

            if (state.signed) {
                Text("Siz ushbu versiyani allaqachon imzolagansiz.", color = MaterialTheme.colorScheme.primary)
                Spacer(Modifier.height(12.dp))
            }

            Text(
                state.content,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.weight(1f).verticalScroll(rememberScrollState()),
            )

            if (!state.signed) {
                Spacer(Modifier.height(12.dp))
                Text("Imzo:", style = MaterialTheme.typography.labelLarge)
                Spacer(Modifier.height(4.dp))
                SignaturePad(state = signatureState)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    OutlinedButton(onClick = { signatureState.clear() }) { Text("Tozalash") }
                }

                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 8.dp)) {
                    Checkbox(checked = agree, onCheckedChange = { agree = it })
                    Text("Shartlarga roziman")
                }

                state.error?.let {
                    Text(it, color = MaterialTheme.colorScheme.error)
                }

                Spacer(Modifier.height(12.dp))
                Button(
                    onClick = {
                        val file = File(context.cacheDir, "signature.png")
                        if (signatureState.exportToFile(file)) viewModel.sign(file)
                    },
                    enabled = !state.submitting && agree && !signatureState.isEmpty,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Imzolash")
                }
            }
        }
    }
}
