class OrderModel {
  final int     id;
  final String  clientName;
  final String  clientPhone;
  final String? driverName;
  final String  fromAddress;
  final String  toAddress;
  final String? price;
  final String? commission;
  final double? distanceKm;
  final String  status;
  final String  statusLabel;
  final String  createdAt;
  final String  paymentType;
  final String  note;
  final int?    secondsLeft;

  // ── Yangi maydonlar ───────────────────────────────────────────────────────
  /// Haydovchidan mijoz manziligacha masofa (km) — faqat pending
  final double? driverDistanceKm;
  /// Taxminiy yetib borish vaqti (daqiqa) — faqat pending
  final int?    driverEtaMinutes;
  /// Mijoz reytingi (1–5) — faqat pending
  final double? clientRating;
  /// Mijozning jami safarlar soni
  final int?    clientTripsCount;

  OrderModel({
    required this.id,
    required this.clientName,
    required this.clientPhone,
    this.driverName,
    required this.fromAddress,
    required this.toAddress,
    this.price,
    this.commission,
    this.distanceKm,
    required this.status,
    required this.statusLabel,
    required this.createdAt,
    this.paymentType = 'cash',
    this.note = '',
    this.secondsLeft,
    this.driverDistanceKm,
    this.driverEtaMinutes,
    this.clientRating,
    this.clientTripsCount,
  });

  factory OrderModel.fromJson(Map<String, dynamic> j) => OrderModel(
    id:               j['id'],
    clientName:       j['client_name'] ?? '',
    clientPhone:      j['client_phone'] ?? '',
    driverName:       j['driver_name'],
    fromAddress:      j['from_address'] ?? '',
    toAddress:        j['to_address'] ?? '',
    price:            j['price']?.toString(),
    commission:       j['commission']?.toString(),
    distanceKm:       j['distance_km'] != null
        ? double.tryParse(j['distance_km'].toString())
        : null,
    status:           j['status'] ?? 'pending',
    statusLabel:      j['status_label'] ?? '',
    createdAt:        j['created_at'] ?? '',
    paymentType:      j['payment_type'] ?? 'cash',
    note:             j['note'] ?? '',
    secondsLeft:      j['seconds_left'] != null
        ? int.tryParse(j['seconds_left'].toString())
        : null,
    driverDistanceKm: j['driver_distance_km'] != null
        ? double.tryParse(j['driver_distance_km'].toString())
        : null,
    driverEtaMinutes: j['driver_eta_minutes'] != null
        ? int.tryParse(j['driver_eta_minutes'].toString())
        : null,
    clientRating:     j['client_rating'] != null
        ? double.tryParse(j['client_rating'].toString())
        : null,
    clientTripsCount: j['client_trips_count'] != null
        ? int.tryParse(j['client_trips_count'].toString())
        : null,
  );

  // ── Status getters ────────────────────────────────────────────────────────
  bool get isPending   => status == 'pending';
  bool get isAccepted  => status == 'accepted';
  bool get isOnWay     => status == 'on_way';
  bool get isArrived   => status == 'arrived';
  bool get isCompleted => status == 'completed';
  bool get isCancelled => status == 'cancelled';
  bool get isActive    => isAccepted || isOnWay || isArrived;

  /// copyWith — countdown uchun
  OrderModel copyWithSecondsLeft(int? s) => OrderModel(
    id: id, clientName: clientName, clientPhone: clientPhone,
    driverName: driverName, fromAddress: fromAddress, toAddress: toAddress,
    price: price, commission: commission, distanceKm: distanceKm,
    status: status, statusLabel: statusLabel, createdAt: createdAt,
    paymentType: paymentType, note: note,
    secondsLeft: s,
    driverDistanceKm: driverDistanceKm, driverEtaMinutes: driverEtaMinutes,
    clientRating: clientRating, clientTripsCount: clientTripsCount,
  );
}
