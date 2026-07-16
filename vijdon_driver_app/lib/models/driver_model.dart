class DriverModel {
  final int id;
  final String fullName;
  final String phoneNumber;
  final String carModel;
  final String carNumber;
  final bool isActive;
  final bool isOnDuty;
  final String approvalStatus;
  final String balance;
  final String? photoUrl;

  DriverModel({
    required this.id,
    required this.fullName,
    required this.phoneNumber,
    required this.carModel,
    required this.carNumber,
    required this.isActive,
    required this.isOnDuty,
    required this.approvalStatus,
    required this.balance,
    this.photoUrl,
  });

  factory DriverModel.fromJson(Map<String, dynamic> j) => DriverModel(
    id:             j['id'],
    fullName:       j['full_name'] ?? '',
    phoneNumber:    j['phone_number'] ?? '',
    carModel:       j['car_model'] ?? '',
    carNumber:      j['car_number'] ?? '',
    isActive:       j['is_active'] ?? false,
    isOnDuty:       j['is_on_duty'] ?? false,
    approvalStatus: j['approval_status'] ?? 'pending',
    balance:        j['balance']?.toString() ?? '0',
    photoUrl:       j['photo_url'] as String?,
  );
}
