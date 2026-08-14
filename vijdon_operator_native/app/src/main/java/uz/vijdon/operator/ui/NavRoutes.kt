package uz.vijdon.operator.ui

object Tabs {
    const val DASHBOARD = "dashboard"
    const val ORDERS = "orders"
    const val CHAT = "chat"
    const val BALANCE = "balance"
    const val DRIVERS = "drivers"
}

object SubRoutes {
    const val ORDER_CREATE = "order_create"
    const val ORDER_DETAIL = "order_detail/{orderId}"
    fun orderDetail(id: Int) = "order_detail/$id"

    const val DRIVER_DETAIL = "driver_detail/{driverId}"
    fun driverDetail(id: Int) = "driver_detail/$id"

    const val CHAT_THREAD = "chat_thread/{driverId}/{driverName}"
    fun chatThread(id: Int, name: String) = "chat_thread/$id/${java.net.URLEncoder.encode(name, "UTF-8")}"

    const val CHAT_GROUP = "chat_group"
}
