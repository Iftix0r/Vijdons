import 'package:flutter_test/flutter_test.dart';
import 'package:vijdon_driver/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const VijdonDriverApp());
    expect(find.text('VijdonTaxi'), findsWidgets);
  });
}
