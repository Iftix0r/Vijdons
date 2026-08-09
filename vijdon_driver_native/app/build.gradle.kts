plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("org.jetbrains.kotlin.kapt")
    id("com.google.dagger.hilt.android")
}

// Firebase (FCM) uchun google-services.json hali repo'ga qo'shilmagan
// (0.3-band — Firebase loyihasi yaratilgach, shu faylni app/ ichiga qo'yish
// kerak). Fayl bo'lmasa plugin sukut bilan o'chiriladi, aks holda build
// konfiguratsiya bosqichidayoq xato berardi.
val hasGoogleServices = file("google-services.json").exists()
if (hasGoogleServices) {
    apply(plugin = "com.google.gms.google-services")
}

android {
    namespace = "uz.vijdon.driver"
    compileSdk = 36

    defaultConfig {
        applicationId = "uz.vijdon.driver"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        buildConfigField("boolean", "HAS_FCM", hasGoogleServices.toString())
        // Ishlab chiqarish serveri hosting darajasidagi Imunify360 WAF
        // JS-bot-tekshiruvi ostida — bu WHM/server administratori darajasida
        // qulflangan (cPanel hisobidan o'zgartirib bo'lmaydi), shu sabab
        // ChallengeInterceptor (data/challenge/) uni ilova ichida ko'rinmas
        // WebView orqali avtomatik "yechadi". Lokal sinov uchun vaqtincha
        // "http://127.0.0.1:8000/api/driverapp/" ga o'zgartirib, qurilmada
        // `adb reverse tcp:8000 tcp:8000` ishga tushiring (bu holda
        // ChallengeInterceptor hech narsa qilmaydi, chunki host boshqacha).
        buildConfigField("String", "BASE_URL", "\"https://vijdontaxi.uz/api/driverapp/\"")
        buildConfigField("String", "CHALLENGE_ORIGIN", "\"https://vijdontaxi.uz/\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
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

    // Compose
    implementation(platform("androidx.compose:compose-bom:2026.06.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.9.4")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.9.4")
    implementation("androidx.navigation:navigation-compose:2.9.8")
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

    // Joylashuv (foreground service)
    implementation("com.google.android.gms:play-services-location:21.4.0")

    // Push (FCM) — google-services.json qo'shilgach ishlaydi
    implementation(platform("com.google.firebase:firebase-bom:34.17.0"))
    implementation("com.google.firebase:firebase-messaging")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    androidTestImplementation(platform("androidx.compose:compose-bom:2026.06.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
