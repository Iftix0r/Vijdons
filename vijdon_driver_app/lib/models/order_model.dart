class OrderModel {
  final int id;
  final String clientName;
  final String clientPhone;
  final String? driverName;
  final String fromAddress;
  final String toAddress;
  final String? price;
  final String? commission;
  final double? distanceKm;
  final String status;
  final String statusLabel;
  final String createdAt;
  final String paymentType;
  final String note;

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
  });

  factory OrderModel.fromJson(Map<String, dynamic> j) => OrderModel(
    id:          j['id'],
    clientName:  j['client_name'] ?? '',
    clientPhone: j['client_phone'] ?? '',
    driverName:  j['driver_name'],
    fromAddress: j['from_address'] ?? '',
    toAddress:   j['to_address'] ?? '',
    price:       j['price']?.toString(),
    commission:  j['commission']?.toString(),
    distanceKm:  j['distance_km'] != null ? double.tryParse(j['distance_km'].toString()) : null,
    status:      j['status'] ?? 'pending',
    statusLabel: j['status_label'] ?? '',
    createdAt:   j['created_at'] ?? '',
    paymentType: j['payment_type'] ?? 'cash',
    note:        j['note'] ?? '',
  );

  bool get isPending   => status == 'pending';
  bool get isAccepted  => status == 'accepted';
  bool get isOnWay     => status == 'on_way';
  bool get isArrived   => status == 'arrived';
  bool get isCompleted => status == 'completed';
  bool get isCancelled => status == 'cancelled';
  bool get isActive    => isAccepted || isOnWay || isArrived;
}
