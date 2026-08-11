plugins {
    id("com.android.application") version "8.11.1" apply false
    id("org.jetbrains.kotlin.android") version "2.2.20" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.20" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "2.2.20" apply false
    id("org.jetbrains.kotlin.kapt") version "2.2.20" apply false
    id("com.google.dagger.hilt.android") version "2.58" apply false
    // google-services.json fayli qo'shilmaguncha shartli qo'llaniladi (app/build.gradle.kts) —
    // aks holda plugin konfiguratsiya bosqichida xato beradi (0.3-band, FCM sozlash kerak).
    id("com.google.gms.google-services") version "4.5.0" apply false
    // Crashlytics ham xuddi shu google-services.json fayliga bog'liq — shu
    // sabab u ham shartli qo'llaniladi (app/build.gradle.kts).
    id("com.google.firebase.crashlytics") version "3.0.7" apply false
}
