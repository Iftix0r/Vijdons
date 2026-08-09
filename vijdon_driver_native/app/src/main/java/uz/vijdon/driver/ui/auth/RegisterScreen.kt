package uz.vijdon.driver.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.DirectionsCar
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material.icons.rounded.Phone
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.ui.theme.ChipShape
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun RegisterScreen(onRegistered: () -> Unit, viewModel: RegisterViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(state.success) {
        if (state.success) onRegistered()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(VijdonColors.Background)
            .padding(24.dp)
            .verticalScroll(rememberScrollState()),
    ) {
        Text("Ro'yxatdan o'tish", style = MaterialTheme.typography.headlineSmall, color = VijdonColors.TextPrimary)
        Text("Ma'lumotlaringizni to'ldiring, admin tasdiqlashini kuting", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(24.dp))

        AuthTextField(state.fullName, viewModel::onFullNameChange, "To'liq ism", Icons.Rounded.Person)
        Spacer(Modifier.height(12.dp))
        AuthTextField(state.phone, viewModel::onPhoneChange, "Telefon raqami", Icons.Rounded.Phone, KeyboardType.Phone)
        Spacer(Modifier.height(12.dp))
        AuthTextField(state.carModel, viewModel::onCarModelChange, "Mashina modeli", Icons.Rounded.DirectionsCar)
        Spacer(Modifier.height(12.dp))
        AuthTextField(state.carNumber, viewModel::onCarNumberChange, "Mashina raqami", Icons.Rounded.DirectionsCar)
        Spacer(Modifier.height(16.dp))

        Text("Mashina turi", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelLarge)
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            CAR_TYPES.forEach { (value, label) ->
                val selected = state.carType == value
                Text(
                    label,
                    color = if (selected) VijdonColors.TextOnYellow else VijdonColors.TextPrimary,
                    modifier = Modifier
                        .background(if (selected) VijdonColors.Yellow else VijdonColors.Surface, ChipShape)
                        .clickable { viewModel.onCarTypeChange(value) }
                        .padding(horizontal = 14.dp, vertical = 10.dp),
                )
            }
        }

        Spacer(Modifier.height(16.dp))
        AuthTextField(state.password, viewModel::onPasswordChange, "Parol (kamida 6 belgi)", Icons.Rounded.Lock, KeyboardType.Password, isPassword = true)

        state.error?.let {
            Spacer(Modifier.height(12.dp))
            Text(it, color = VijdonColors.Red)
        }

        Spacer(Modifier.height(24.dp))
        Button(
            onClick = viewModel::register,
            enabled = !state.loading,
            colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) {
            if (state.loading) {
                CircularProgressIndicator(modifier = Modifier.height(20.dp), color = VijdonColors.TextOnYellow)
            } else {
                Text("Yuborish")
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}
