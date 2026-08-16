import java.util.Properties

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
    apply(plugin = "com.google.firebase.crashlytics")
}

// Release imzolash kaliti — repoga qo'shilmagan (`keystore.properties` va
// `release.keystore.jks`, ikkalasi ham .gitignore'da). Fayl bo'lmasa
// (masalan boshqa dasturchi mashinasida yoki CI'da) release build shunchaki
// imzosiz yig'iladi — konfiguratsiya bosqichida xato bermaydi.
val keystorePropsFile = rootProject.file("keystore.properties")
val hasKeystore = keystorePropsFile.exists()
val keystoreProps = Properties().apply {
    if (hasKeystore) keystorePropsFile.inputStream().use { load(it) }
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

    // WorkManager — bildirishnoma tugmasidan (OrderActionReceiver) kelgan
    // "Qabul qilish/Rad etish" so'rovi kafolatlangan bajarilishi uchun.
    // Oddiy BroadcastReceiver + goAsync() + korutina — tizim ilova jarayonini
    // (ayniqsa OEM'larning agressiv "battery saver"i) o'sha ondayoq
    // to'xtatib qo'yishi mumkin bo'lgan holatlarda tarmoq so'rovi hech
    // qachon yetib bormay qolishi mumkin edi; WorkManager esa buni albatta
    // (kerak bo'lsa jarayon o'lganidan keyin ham qayta urinib) bajaradi.
    // Diqqat: `androidx.hilt:hilt-work` (kapt orqali @HiltWorker generatsiya
    // qiladigan) ATAYLAB ishlatilmagan — uning kapt protsessori hozirgi
    // Kotlin (2.2.20) metadata formatini o'qiy olmasdan xato berdi ("Unable
    // to read Kotlin metadata due to unsupported metadata kind"). Shu sabab
    // `OrderActionWorker` oddiy Worker sifatida yozilgan, Hilt'dan
    // `EntryPointAccessors` orqali (kodda generatsiya shart bo'lmagan yo'l
    // bilan) foydalanadi.
    implementation("androidx.work:work-runtime-ktx:2.10.0")

    // Telefon bosh ekrani vidjeti — Compose-asosli zamonaviy widget API
    // (loyihaning qolgan qismi ham Compose bo'lgani uchun, eski
    // RemoteViews/AppWidgetProvider XML uslubidan ko'ra mos keladi).
    implementation("androidx.glance:glance-appwidget:1.1.1")

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

    // Rasm yuklash (haydovchi profil surati — pastki tab-bar/Profil ekrani)
    implementation("io.coil-kt.coil3:coil-compose:3.2.0")
    implementation("io.coil-kt.coil3:coil-network-okhttp:3.2.0")

    // Push (FCM) — google-services.json qo'shilgach ishlaydi
    implementation(platform("com.google.firebase:firebase-bom:34.17.0"))
    implementation("com.google.firebase:firebase-messaging")
    // Xatoliklarni kuzatish — real qurilmalardagi ushlanmagan
    // istisnolar (crash) haqida avtomatik hisobot beradi.
    implementation("com.google.firebase:firebase-crashlytics")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    androidTestImplementation(platform("androidx.compose:compose-bom:2026.06.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
