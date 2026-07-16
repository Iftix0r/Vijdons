import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/api_service.dart';
import '../core/theme.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  final _controller = TextEditingController();
  final _scrollCtrl = ScrollController();
  List<Map<String, dynamic>> _messages = [];
  bool  _loading = true;
  bool  _sending = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    _timer = Timer.periodic(
        const Duration(seconds: 5), (_) => _load(silent: true));
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent && mounted) setState(() => _loading = true);
    try {
      final list = await ApiService.getChatMessages();
      if (!mounted) return;
      setState(() {
        _messages = list.cast<Map<String, dynamic>>();
        _loading  = false;
      });
      _scrollToBottom();
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending) return;
    HapticFeedback.lightImpact();
    setState(() => _sending = true);
    _controller.clear();
    try {
      await ApiService.sendChatMessage(text);
      await _load(silent: true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(e.toString()),
          backgroundColor: AppColors.danger,
          behavior: SnackBarBehavior.floating,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          margin: const EdgeInsets.all(16),
        ));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final dark = Theme.of(context).brightness == Brightness.dark;

    return SafeArea(
      child: Column(
        children: [
          _header(dark),
          Expanded(
            child: _loading
                ? const Center(
                    child:
                        CircularProgressIndicator(color: AppColors.primary))
                : _messages.isEmpty
                    ? _emptyState(dark)
                    : ListView.builder(
                        controller: _scrollCtrl,
                        padding:
                            const EdgeInsets.fromLTRB(16, 16, 16, 8),
                        itemCount: _messages.length,
                        itemBuilder: (_, i) =>
                            _bubble(_messages[i], dark),
                      ),
          ),
          _inputBar(dark),
        ],
      ),
    );
  }

  // ── Header ────────────────────────────────────────────────────────────────

  Widget _header(bool dark) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 16, 14),
      decoration: BoxDecoration(
        color: dark ? AppColors.bgDark : Colors.white,
        border: Border(
          bottom: BorderSide(
            color: dark ? AppColors.borderDark : AppColors.borderLight,
            width: 0.8,
          ),
        ),
      ),
      child: Row(
        children: [
          // Operator avatar
          Container(
            width: 40, height: 40,
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(13),
            ),
            child: const Center(
              child: Text('O',
                  style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 18,
                      fontWeight: FontWeight.w900)),
            ),
          ),
          const SizedBox(width: 12),

          // Title + online status
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Operator',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.2,
                    color: dark ? Colors.white : AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Container(
                      width: 6, height: 6,
                      decoration: const BoxDecoration(
                          color: AppColors.success,
                          shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      'Onlayn',
                      style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.success.withValues(alpha: 0.8)),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Refresh button
          GestureDetector(
            onTap: _load,
            child: Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: dark ? AppColors.surfaceDark : const Color(0xFFF2F2F2),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Icons.refresh_rounded, size: 18, color: Colors.grey.shade500),
            ),
          ),
          const SizedBox(width: 8),
          // Qo'ng'iroq tugmasi — 1351
          GestureDetector(
            onTap: () async {
              HapticFeedback.mediumImpact();
              await launchUrl(
                Uri(scheme: 'tel', path: '1351'),
                mode: LaunchMode.externalApplication,
              );
            },
            child: Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: AppColors.success.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
              ),
              child: const Icon(Icons.call_rounded, size: 18, color: AppColors.success),
            ),
          ),
        ],
      ),
    );
  }

  // ── Message bubble ────────────────────────────────────────────────────────

  Widget _bubble(Map<String, dynamic> msg, bool dark) {
    final isMe = msg['sender'] == 'driver';
    final time = _formatTime(msg['created_at'] ?? '');

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        mainAxisAlignment:
            isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // Operator avatar
          if (!isMe) ...[
            Container(
              width: 28, height: 28,
              decoration: BoxDecoration(
                color: AppColors.primary,
                borderRadius: BorderRadius.circular(9),
              ),
              child: const Center(
                child: Text('O',
                    style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 12,
                        fontWeight: FontWeight.w900)),
              ),
            ),
            const SizedBox(width: 8),
          ],

          // Bubble
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                  maxWidth: MediaQuery.of(context).size.width * 0.72),
              padding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 11),
              decoration: BoxDecoration(
                // Driver = sariq; operator = kulrang
                color: isMe
                    ? AppColors.primary
                    : (dark
                        ? AppColors.surfaceDark
                        : const Color(0xFFF2F2F2)),
                borderRadius: BorderRadius.only(
                  topLeft:     const Radius.circular(18),
                  topRight:    const Radius.circular(18),
                  bottomLeft:  Radius.circular(isMe ? 18 : 4),
                  bottomRight: Radius.circular(isMe ? 4 : 18),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    msg['text'] ?? '',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      height: 1.4,
                      color: isMe
                          ? AppColors.textPrimary
                          : (dark
                              ? Colors.white
                              : AppColors.textPrimary),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    time,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: isMe
                          ? Colors.black.withValues(alpha: 0.45)
                          : Colors.grey.shade400,
                    ),
                  ),
                ],
              ),
            ),
          ),

          if (isMe) const SizedBox(width: 4),
        ],
      ),
    );
  }

  // ── Input bar ─────────────────────────────────────────────────────────────

  Widget _inputBar(bool dark) {
    return Container(
      padding: EdgeInsets.fromLTRB(
          14, 10, 14, MediaQuery.of(context).padding.bottom + 12),
      decoration: BoxDecoration(
        color: dark ? AppColors.bgDark : Colors.white,
        border: Border(
          top: BorderSide(
            color: dark ? AppColors.borderDark : AppColors.borderLight,
            width: 0.8,
          ),
        ),
      ),
      child: Row(
        children: [
          // Text field
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: dark
                    ? AppColors.surfaceDark
                    : const Color(0xFFF2F2F2),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: dark
                      ? AppColors.borderDark
                      : AppColors.borderLight,
                ),
              ),
              child: TextField(
                controller: _controller,
                textCapitalization: TextCapitalization.sentences,
                onSubmitted: (_) => _send(),
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: dark ? Colors.white : AppColors.textPrimary,
                ),
                decoration: InputDecoration(
                  hintText: 'Xabar yozing...',
                  hintStyle: TextStyle(
                    color: Colors.grey.shade500,
                    fontSize: 14,
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                      horizontal: 18, vertical: 12),
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  filled: false,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),

          // Send button
          GestureDetector(
            onTap: _sending ? null : _send,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 48, height: 48,
              decoration: BoxDecoration(
                color: _sending
                    ? Colors.grey.shade300
                    : AppColors.primary,
                shape: BoxShape.circle,
                boxShadow: _sending
                    ? []
                    : [
                        BoxShadow(
                          color: AppColors.primary
                              .withValues(alpha: 0.4),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
              ),
              child: _sending
                  ? const Center(
                      child: SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: AppColors.textPrimary),
                      ),
                    )
                  : const Icon(Icons.send_rounded,
                      color: AppColors.textPrimary, size: 20),
            ),
          ),
        ],
      ),
    );
  }

  // ── Empty state ───────────────────────────────────────────────────────────

  Widget _emptyState(bool dark) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                color: dark
                    ? AppColors.surfaceDark
                    : const Color(0xFFF2F2F2),
                borderRadius: BorderRadius.circular(24),
              ),
              child: Icon(Icons.chat_bubble_outline_rounded,
                  size: 38,
                  color: Colors.grey.shade400),
            ),
            const SizedBox(height: 20),
            Text(
              'Xabarlar yo\'q',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                letterSpacing: -0.3,
                color: dark ? Colors.white : AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Operator bilan muloqot boshlang.\nSavollaringizni yuboring.',
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: 13,
                  color: Colors.grey.shade500,
                  height: 1.6),
            ),
          ],
        ),
      ),
    );
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  String _formatTime(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      final h = dt.hour.toString().padLeft(2, '0');
      final m = dt.minute.toString().padLeft(2, '0');
      return '$h:$m';
    } catch (_) {
      return '';
    }
  }
}
