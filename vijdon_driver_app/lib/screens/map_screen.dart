import 'dart:async';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:yandex_mapkit/yandex_mapkit.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import '../models/order_model.dart';

class MapScreen extends StatefulWidget {
  final OrderModel? activeOrder;
  const MapScreen({super.key, this.activeOrder});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  YandexMapController? _mapController;
  final List<MapObject> _mapObjects = [];
  bool _trafficEnabled = false;
  bool _loading = true;
  Point? _myLocation;
  Timer? _locationTimer;

  // Placemark IDs
  static const _myPlacemarkId   = MapObjectId('my_location');
  static const _fromPlacemarkId = MapObjectId('from_location');
  static const _toPlacemarkId   = MapObjectId('to_location');
  static const _routePolylineId = MapObjectId('route');

  @override
  void initState() {
    super.initState();
    _locationTimer = Timer.periodic(const Duration(seconds: 5), (_) => _updateMyLocation());
  }

  @override
  void dispose() {
    _locationTimer?.cancel();
    _mapController?.dispose();
    super.dispose();
  }

  Future<void> _onMapCreated(YandexMapController controller) async {
    _mapController = controller;
    await _updateMyLocation();
    if (widget.activeOrder != null) {
      await _showOrderOnMap(widget.activeOrder!);
    }
    setState(() => _loading = false);
  }

  Future<void> _updateMyLocation() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 5),
      );
      final point = Point(latitude: pos.latitude, longitude: pos.longitude);
      if (mounted) setState(() => _myLocation = point);

      _updatePlacemark(
        _myPlacemarkId,
        point,
        _buildPlacemarkIcon(Colors.green, Icons.navigation_rounded),
        zIndex: 2,
      );

      if (_myLocation == null) {
        _mapController?.moveCamera(
          CameraUpdate.newCameraPosition(
            CameraPosition(target: point, zoom: 15),
          ),
          animation: const MapAnimation(type: MapAnimationType.smooth, duration: 1),
        );
      }
    } catch (_) {}
  }

  Future<void> _showOrderOnMap(OrderModel order) async {
    // Buyurtma koordinatalari backend dan kelishi kerak
    // Hozircha manzil bo'yicha geocode qilamiz
    try {
      final drivers = await ApiService.getActiveDriversLocations();

      // Boshqa haydovchilarni ko'rsatish
      for (final d in drivers) {
        final lat = (d['latitude'] as num?)?.toDouble();
        final lng = (d['longitude'] as num?)?.toDouble();
        if (lat == null || lng == null) continue;
        final id = MapObjectId('driver_${d['id']}');
        _updatePlacemark(
          id,
          Point(latitude: lat, longitude: lng),
          _buildPlacemarkIcon(AppColors.info, Icons.directions_car_rounded),
          zIndex: 1,
        );
      }
    } catch (_) {}
  }

  void _updatePlacemark(MapObjectId id, Point point, PlacemarkIcon icon, {double zIndex = 0}) {
    if (!mounted) return;
    setState(() {
      _mapObjects.removeWhere((o) => o.mapId == id);
      _mapObjects.add(PlacemarkMapObject(
        mapId: id,
        point: point,
        icon: icon,
        zIndex: zIndex,
      ));
    });
  }

  PlacemarkIcon _buildPlacemarkIcon(Color color, IconData iconData) {
    return PlacemarkIcon.single(PlacemarkIconStyle(
      image: BitmapDescriptor.fromAssetImage('assets/images/marker.png'),
      scale: 2.5,
    ));
  }

  Future<void> _buildRoute(Point from, Point to) async {
    try {
      final result = YandexDriving.requestRoutes(
        points: [
          RequestPoint(point: from, requestPointType: RequestPointType.wayPoint),
          RequestPoint(point: to,   requestPointType: RequestPointType.wayPoint),
        ],
        drivingOptions: const DrivingOptions(
          initialAzimuth: 0,
          routesCount: 1,
          avoidTolls: false,
        ),
      );
      final session = await result.result;
      final routes = session.routes;
      if (routes != null && routes.isNotEmpty) {
        final geometry = routes.first.geometry;
        setState(() {
          _mapObjects.removeWhere((o) => o.mapId == _routePolylineId);
          _mapObjects.add(PolylineMapObject(
            mapId: _routePolylineId,
            polyline: Polyline(points: geometry),
            strokeColor: AppColors.primary,
            strokeWidth: 4,
          ));
        });
        _mapController?.moveCamera(
          CameraUpdate.newBounds(
            BoundingBox(
              southWest: Point(
                latitude:  [from.latitude,  to.latitude].reduce((a, b) => a < b ? a : b),
                longitude: [from.longitude, to.longitude].reduce((a, b) => a < b ? a : b),
              ),
              northEast: Point(
                latitude:  [from.latitude,  to.latitude].reduce((a, b) => a > b ? a : b),
                longitude: [from.longitude, to.longitude].reduce((a, b) => a > b ? a : b),
              ),
            ),
          ),
          animation: const MapAnimation(type: MapAnimationType.smooth, duration: 1),
        );
      }
    } catch (_) {}
  }

  void _goToMyLocation() {
    if (_myLocation == null) return;
    _mapController?.moveCamera(
      CameraUpdate.newCameraPosition(
        CameraPosition(target: _myLocation!, zoom: 16),
      ),
      animation: const MapAnimation(type: MapAnimationType.smooth, duration: 0.8),
    );
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Stack(
        children: [
          YandexMap(
            mapObjects: _mapObjects,
            onMapCreated: _onMapCreated,
            nightModeEnabled: dark,
            onMapTap: (_) {},
          ),

          // Loading
          if (_loading)
            Container(
              color: dark ? AppColors.bgDark : Colors.white,
              child: const Center(
                child: CircularProgressIndicator(color: AppColors.primary),
              ),
            ),

          // Top bar
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            left: 16, right: 16,
            child: Row(
              children: [
                GestureDetector(
                  onTap: () => Navigator.pop(context),
                  child: Container(
                    width: 44, height: 44,
                    decoration: BoxDecoration(
                      color: dark ? AppColors.cardDark : Colors.white,
                      shape: BoxShape.circle,
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.15), blurRadius: 10, offset: const Offset(0, 3))],
                    ),
                    child: const Icon(Icons.arrow_back_rounded, size: 20),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: dark ? AppColors.cardDark : Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.1), blurRadius: 8)],
                    ),
                    child: Text(
                      widget.activeOrder != null
                          ? '📍 ${widget.activeOrder!.fromAddress}'
                          : 'Xarita',
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Right controls
          Positioned(
            right: 16,
            bottom: 120,
            child: Column(
              children: [
                // Trafik toggle
                _mapBtn(
                  icon: Icons.traffic_rounded,
                  active: _trafficEnabled,
                  onTap: () => setState(() => _trafficEnabled = !_trafficEnabled),
                  tooltip: 'Trafik',
                  dark: dark,
                ),
                const SizedBox(height: 10),
                // Mening joylashuvim
                _mapBtn(
                  icon: Icons.my_location_rounded,
                  onTap: _goToMyLocation,
                  tooltip: 'Mening joylashuvim',
                  dark: dark,
                ),
                const SizedBox(height: 10),
                // Zoom +
                _mapBtn(
                  icon: Icons.add_rounded,
                  onTap: () => _mapController?.moveCamera(CameraUpdate.zoomIn()),
                  dark: dark,
                ),
                const SizedBox(height: 6),
                // Zoom -
                _mapBtn(
                  icon: Icons.remove_rounded,
                  onTap: () => _mapController?.moveCamera(CameraUpdate.zoomOut()),
                  dark: dark,
                ),
              ],
            ),
          ),

          // Active order banner
          if (widget.activeOrder != null)
            Positioned(
              bottom: 0, left: 0, right: 0,
              child: _orderBanner(widget.activeOrder!, dark),
            ),
        ],
      ),
    );
  }

  Widget _mapBtn({
    required IconData icon,
    required VoidCallback onTap,
    required bool dark,
    bool active = false,
    String? tooltip,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 46, height: 46,
        decoration: BoxDecoration(
          color: active ? AppColors.primary : (dark ? AppColors.cardDark : Colors.white),
          shape: BoxShape.circle,
          border: Border.all(
            color: active
                ? Colors.transparent
                : (dark ? AppColors.borderDark : AppColors.borderLight),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.15),
              blurRadius: 10,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Icon(icon, size: 21,
          color: active ? Colors.black : (dark ? Colors.white : AppColors.textPrimary)),
      ),
    );
  }

  Widget _orderBanner(OrderModel order, bool dark) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.15), blurRadius: 20)],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                width: 40, height: 40,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.person_rounded, color: AppColors.primary, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(order.clientName.isNotEmpty ? order.clientName : 'Mijoz',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
                    Text(order.fromAddress,
                        style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                        maxLines: 1, overflow: TextOverflow.ellipsis),
                  ],
                ),
              ),
              if (order.price != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.success.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text('${order.price} UZS',
                      style: const TextStyle(fontWeight: FontWeight.w800,
                          color: AppColors.success, fontSize: 12)),
                ),
            ],
          ),
          if (order.toAddress.isNotEmpty && _myLocation != null) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              height: 44,
              child: ElevatedButton.icon(
                onPressed: () async {
                  // Marshrut qurish (from = mening joylashuvim, to = buyurtma manzili)
                  // Manzilni geocode qilish kerak — hozircha demo koordinatalar
                  if (_myLocation != null) {
                    // to koordinatalarini backend dan olish kerak
                    // Demo uchun Toshkent markazi
                    await _buildRoute(
                      _myLocation!,
                      const Point(latitude: 41.2995, longitude: 69.2401),
                    );
                  }
                },
                icon: const Icon(Icons.directions_rounded, size: 18),
                label: const Text('Marshrut', style: TextStyle(fontWeight: FontWeight.w800)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
