package uz.vijdon.driver.ui.sos

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Sos
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.android.gms.location.LocationServices
import uz.vijdon.driver.ui.theme.VijdonColors

@SuppressLint("MissingPermission")
@Composable
fun SosScreen(viewModel: SosViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    var lat by remember { mutableStateOf<Double?>(null) }
    var lng by remember { mutableStateOf<Double?>(null) }

    LaunchedEffect(Unit) {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (granted) {
            LocationServices.getFusedLocationProviderClient(context).lastLocation.addOnSuccessListener { location ->
                lat = location?.latitude
                lng = location?.longitude
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        Box(
            modifier = Modifier.size(72.dp).background(VijdonColors.Red.copy(alpha = 0.15f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Rounded.Sos, contentDescription = null, tint = VijdonColors.Red, modifier = Modifier.size(36.dp))
        }
        Spacer(Modifier.height(16.dp))
        Text("SOS — favqulodda yordam", style = MaterialTheme.typography.headlineSmall, color = VijdonColors.Red)
        Spacer(Modifier.height(8.dp))
        Text("Yuborilganda joriy joylashuvingiz operatorlarga darhol xabar qilinadi.", style = MaterialTheme.typography.bodyMedium, color = VijdonColors.TextSecondary)
        Spacer(Modifier.height(20.dp))
        OutlinedTextField(
            value = state.note, onValueChange = viewModel::onNoteChange,
            label = { Text("Izoh (ixtiyoriy)") },
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = VijdonColors.Surface, unfocusedContainerColor = VijdonColors.Surface,
                focusedTextColor = VijdonColors.TextPrimary, unfocusedTextColor = VijdonColors.TextPrimary,
            ),
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(20.dp))
        if (state.sent) {
            Text("Yuborildi. Operatorlar tez orada bog'lanadi.", color = VijdonColors.Green)
        } else {
            Button(
                onClick = { viewModel.send(lat, lng) },
                enabled = !state.loading,
                colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Red, contentColor = VijdonColors.TextPrimary),
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                Text("SOS Yuborish")
            }
        }
        state.error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = VijdonColors.Red)
        }
    }
}
