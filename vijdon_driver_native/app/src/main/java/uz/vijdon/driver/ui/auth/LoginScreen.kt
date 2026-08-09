package uz.vijdon.driver.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.LocalTaxi
import androidx.compose.material.icons.rounded.Phone
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun LoginScreen(
    onLoggedIn: (DriverDto) -> Unit,
    onGoToRegister: () -> Unit,
    viewModel: LoginViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(VijdonColors.Background)
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier
                .size(72.dp)
                .background(VijdonColors.Yellow, CircleShape)
                .align(Alignment.CenterHorizontally),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Rounded.LocalTaxi, contentDescription = null, tint = VijdonColors.TextOnYellow, modifier = Modifier.size(36.dp))
        }
        Spacer(Modifier.height(16.dp))
        Text(
            "Vijdon Taxi",
            style = MaterialTheme.typography.headlineMedium,
            color = VijdonColors.TextPrimary,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
        )
        Text(
            "Haydovchi ilovasi",
            style = MaterialTheme.typography.bodyMedium,
            color = VijdonColors.TextSecondary,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(36.dp))

        AuthTextField(
            value = state.phone,
            onChange = viewModel::onPhoneChange,
            label = "Telefon raqami",
            icon = Icons.Rounded.Phone,
            keyboardType = KeyboardType.Phone,
        )
        Spacer(Modifier.height(12.dp))
        AuthTextField(
            value = state.password,
            onChange = viewModel::onPasswordChange,
            label = "Parol",
            icon = Icons.Rounded.Lock,
            keyboardType = KeyboardType.Password,
            isPassword = true,
        )

        state.error?.let {
            Spacer(Modifier.height(12.dp))
            Text(it, color = VijdonColors.Red)
        }

        Spacer(Modifier.height(24.dp))
        Button(
            onClick = { viewModel.login(onLoggedIn) },
            enabled = !state.loading,
            colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) {
            if (state.loading) {
                CircularProgressIndicator(modifier = Modifier.height(20.dp), color = VijdonColors.TextOnYellow)
            } else {
                Text("Kirish")
            }
        }

        TextButton(onClick = onGoToRegister, modifier = Modifier.fillMaxWidth()) {
            Text("Ro'yxatdan o'tish", color = VijdonColors.Yellow)
        }
    }
}

@Composable
fun AuthTextField(
    value: String,
    onChange: (String) -> Unit,
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    keyboardType: KeyboardType = KeyboardType.Text,
    isPassword: Boolean = false,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        leadingIcon = { Icon(icon, contentDescription = null, tint = VijdonColors.TextSecondary) },
        visualTransformation = if (isPassword) PasswordVisualTransformation() else androidx.compose.ui.text.input.VisualTransformation.None,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        colors = OutlinedTextFieldDefaults.colors(
            focusedContainerColor = VijdonColors.Surface,
            unfocusedContainerColor = VijdonColors.Surface,
            focusedTextColor = VijdonColors.TextPrimary,
            unfocusedTextColor = VijdonColors.TextPrimary,
            focusedBorderColor = VijdonColors.Yellow,
            unfocusedBorderColor = VijdonColors.Border,
            focusedLabelColor = VijdonColors.Yellow,
            unfocusedLabelColor = VijdonColors.TextSecondary,
            cursorColor = VijdonColors.Yellow,
        ),
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
}
