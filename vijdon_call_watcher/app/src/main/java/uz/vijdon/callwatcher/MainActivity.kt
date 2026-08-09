package uz.vijdon.callwatcher

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import uz.vijdon.callwatcher.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: Prefs
    private lateinit var siteSession: SiteSession

    private val requestPermissionsLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { results ->
            if (results.values.all { it }) {
                startWatcherService()
            } else {
                Toast.makeText(this, R.string.error_permissions_needed, Toast.LENGTH_LONG).show()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        prefs = Prefs(this)
        siteSession = SiteSession(this, binding.loginWebView)

        binding.siteUrlInput.setText(prefs.siteUrl)
        prefs.username?.let { binding.usernameInput.setText(it) }

        binding.loginButton.setOnClickListener { onLoginClicked() }
        binding.toggleButton.setOnClickListener { onToggleClicked() }
        binding.logoutButton.setOnClickListener { onLogoutClicked() }

        refreshUiState()
    }

    private fun onLoginClicked() {
        val siteUrlRaw = binding.siteUrlInput.text?.toString()?.trim().orEmpty()
        val username = binding.usernameInput.text?.toString()?.trim().orEmpty()
        val password = binding.passwordInput.text?.toString().orEmpty()

        if (siteUrlRaw.isEmpty() || username.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, R.string.error_fill_fields, Toast.LENGTH_SHORT).show()
            return
        }

        val siteUrl = SiteSession.normalizeBaseUrl(siteUrlRaw)
        binding.loginButton.isEnabled = false
        binding.statusText.setText(R.string.status_logging_in)

        siteSession.login(siteUrl, username, password) { success, message ->
            binding.loginButton.isEnabled = true
            if (success) {
                prefs.siteUrl = siteUrl
                prefs.loggedIn = true
                prefs.username = username
                binding.passwordInput.setText("")
                Toast.makeText(this, getString(R.string.logged_in_as, username), Toast.LENGTH_SHORT).show()
                refreshUiState()
            } else {
                binding.statusText.setText(R.string.status_stopped)
                Toast.makeText(this, message ?: getString(R.string.error_login_failed), Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun onToggleClicked() {
        if (prefs.serviceEnabled) {
            stopService(Intent(this, CallWatcherService::class.java))
            prefs.serviceEnabled = false
            refreshUiState()
        } else {
            ensurePermissionsThenStart()
        }
    }

    private fun onLogoutClicked() {
        stopService(Intent(this, CallWatcherService::class.java))
        prefs.clearSession()
        binding.passwordInput.setText("")
        refreshUiState()
    }

    private fun ensurePermissionsThenStart() {
        val needed = requiredPermissions().filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isEmpty()) {
            startWatcherService()
        } else {
            requestPermissionsLauncher.launch(needed.toTypedArray())
        }
    }

    private fun startWatcherService() {
        val intent = Intent(this, CallWatcherService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        prefs.serviceEnabled = true
        refreshUiState()
    }

    private fun requiredPermissions(): List<String> {
        val perms = mutableListOf(
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.READ_CALL_LOG
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
            perms.add(Manifest.permission.READ_MEDIA_AUDIO)
        } else {
            perms.add(Manifest.permission.READ_EXTERNAL_STORAGE)
        }
        return perms
    }

    private fun refreshUiState() {
        val loggedIn = prefs.loggedIn
        binding.toggleButton.isEnabled = loggedIn
        binding.logoutButton.isEnabled = loggedIn

        if (prefs.serviceEnabled && loggedIn) {
            binding.statusText.setText(R.string.status_running)
            binding.statusText.setTextColor(ContextCompat.getColor(this, R.color.status_ok))
            binding.toggleButton.setText(R.string.btn_stop)
        } else {
            binding.statusText.setText(R.string.status_stopped)
            binding.statusText.setTextColor(ContextCompat.getColor(this, R.color.status_off))
            binding.toggleButton.setText(R.string.btn_start)
        }
    }
}
