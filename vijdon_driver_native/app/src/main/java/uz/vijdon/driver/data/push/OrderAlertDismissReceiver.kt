package uz.vijdon.driver.data.push

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * "Yangi buyurtma" bildirishnomasi tugma orqali emas, shunchaki bildirishnoma
 * panelidan SURIB (swipe) yopilganda ham chaqiriladi (`setDeleteIntent`).
 * Bungacha faqat "Qabul qilish"/"Rad etish" tugmalari (`OrderActionReceiver`)
 * va ilova ichidagi tugmalar `DriverSoundPlayer.stop()`ni chaqirar edi — shu
 * sabab haydovchi bildirishnomani oddiy surib tashlasa, hali ijro etilib
 * turgan ringtone hech kim to'xtatmagani uchun davom etaverar edi.
 */
class OrderAlertDismissReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        DriverSoundPlayer.stop()
    }
}
