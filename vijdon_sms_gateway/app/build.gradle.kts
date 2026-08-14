import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("org.jetbrains.kotlin.kapt")
    id("com.google.dagger.hilt.android")
}

// Firebase (FCM) uchun google-services.json hali repo'ga qo'shilmagan —
// Firebase konsolida uz.vijdon.smsgateway uchun alohida ilova ro'yxatdan
// o'tkazilgach shu fayl app/ ichiga qo'yiladi. Fayl bo'lmasa plugin sukut
// bilan o'chiriladi. Diqqat: FCM bu ilova uchun faqat TEZKORLIK
// (bildirishnoma darhol kelishi) uchun — u ishlamasa ham, fon xizmatining
// muntazam so'rovi (polling, DEFAULT_POLL_INTERVAL_MS) baribir SMS'larni
// bir necha soniya ichida topib yuboraveradi.
val hasGoogleServices = file("google-services.json").exists()
if (hasGoogleServices) {
    apply(plugin = "com.google.gms.google-services")
    apply(plugin = "com.google.firebase.crashlytics")
}

// Release imzolash kaliti — repoga qo'shilmagan, boshqa ilovalardan
// (haydovchi/operator) MUSTAQIL, alohida keystore.
val keystorePropsFile = rootProject.file("keystore.properties")
val hasKeystore = keystorePropsFile.exists()
val keystoreProps = Properties().apply {
    if (hasKeystore) keystorePropsFile.inputStream().use { load(it) }
}

android {
    namespace = "uz.vijdon.smsgateway"
    compileSdk = 36

    defaultConfig {
        applicationId = "uz.vijdon.smsgateway"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        buildConfigField("boolean", "HAS_FCM", hasGoogleServices.toString())
        // Ishlab chiqarish serveri hosting darajasidagi Imunify360 WAF —
        // haydovchi/operator ilovalaridagi bilan bir xil muammo/yechim.
        // Diqqat: BASE_URL bu safar SAYT ILDIZI (/api/smsgatewayapp/ EMAS) —
        // chunki kirish (login) mavjud `/panel/api/operator/login/`
        // endpoint'idan (boshqa prefiks) foydalanadi, SMS navbati esa
        // `/api/smsgatewayapp/`dan. Ikkalasi ham shu BITTA Retrofit
        // xizmatida to'liq (nisbiy bo'lmagan) yo'l sifatida yozilgan.
        buildConfigField("String", "BASE_URL", "\"https://vijdontaxi.uz/\"")
        buildConfigField("String", "CHALLENGE_ORIGIN", "\"https://vijdontaxi.uz/\"")
    }

    signingConfigs {
        if (hasKeystore) {
            create("release") {
                storeFile = file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (hasKeystore) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.9.4")
    implementation("androidx.activity:activity-compose:1.11.0")

    // Compose — ataylab oddiy (bitta-ikkita ekran, og'ir UI shart emas)
    implementation(platform("androidx.compose:compose-bom:2026.06.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.9.4")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.9.4")
    debugImplementation("androidx.compose.ui:ui-tooling")

    // Hilt (DI)
    implementation("com.google.dagger:hilt-android:2.58")
    kapt("com.google.dagger:hilt-compiler:2.58")
    implementation("androidx.hilt:hilt-navigation-compose:1.3.0")

    // Tarmoq
    implementation("com.squareup.retrofit2:retrofit:3.0.0")
    implementation("com.squareup.retrofit2:converter-kotlinx-serialization:3.0.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.11.0")

    // Token saqlash
    implementation("androidx.datastore:datastore-preferences:1.2.1")

    // Push (FCM) — google-services.json qo'shilgach ishlaydi
    implementation(platform("com.google.firebase:firebase-bom:34.17.0"))
    implementation("com.google.firebase:firebase-messaging")
    implementation("com.google.firebase:firebase-crashlytics")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    androidTestImplementation(platform("androidx.compose:compose-bom:2026.06.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
