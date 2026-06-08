// lib/features/ecg_viewer/widgets/ecg_chart_widget.dart
// Custom painter untuk sinyal EKG
// Justifikasi: Goldberger et al. (2000) — standar kertas EKG: grid 1mm = 0.04s (h),
// 1mm = 0.1mV (v), warna grid merah muda pada background putih.
// Cai et al. (2022) — interaktif zoom/pan untuk analisis klinis.

import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';

class EcgChartWidget extends StatefulWidget {
  final List<double> signalData;
  final String leadName;
  final double zoomLevel;
  final bool showGrid;
  final bool showAnnotations;
  final Color lineColor;
  final double height;

  const EcgChartWidget({
    super.key,
    required this.signalData,
    required this.leadName,
    this.zoomLevel = 1.0,
    this.showGrid = true,
    this.showAnnotations = true,
    this.lineColor = AppColors.ecgLine,
    this.height = 100,
  });

  @override
  State<EcgChartWidget> createState() => _EcgChartWidgetState();
}

class _EcgChartWidgetState extends State<EcgChartWidget> {
  double _scrollOffset = 0;

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: CustomPaint(
        size: Size(double.infinity, widget.height),
        painter: _EcgPainter(
          signalData: widget.signalData,
          leadName: widget.leadName,
          zoomLevel: widget.zoomLevel,
          showGrid: widget.showGrid,
          showAnnotations: widget.showAnnotations,
          lineColor: widget.lineColor,
          scrollOffset: _scrollOffset,
        ),
      ),
    );
  }
}

class _EcgPainter extends CustomPainter {
  final List<double> signalData;
  final String leadName;
  final double zoomLevel;
  final bool showGrid;
  final bool showAnnotations;
  final Color lineColor;
  final double scrollOffset;

  _EcgPainter({
    required this.signalData,
    required this.leadName,
    required this.zoomLevel,
    required this.showGrid,
    required this.showAnnotations,
    required this.lineColor,
    required this.scrollOffset,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Background
    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..color = AppColors.ecgBackground,
    );

    if (showGrid) {
      _drawGrid(canvas, size);
    }

    _drawSignal(canvas, size);

    if (showAnnotations) {
      _drawLeadLabel(canvas, size);
    }
  }

  void _drawGrid(Canvas canvas, Size size) {
    final smallGridPaint = Paint()
      ..color = AppColors.ecgGrid
      ..strokeWidth = 0.5;

    final majorGridPaint = Paint()
      ..color = AppColors.ecgGridMajor
      ..strokeWidth = 1.0;

    final smallStep = 10.0 * zoomLevel;
    final majorStep = 50.0 * zoomLevel;

    // Vertical lines (time)
    for (double x = 0; x < size.width; x += smallStep) {
      final isMajor = (x % majorStep) < smallStep;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), isMajor ? majorGridPaint : smallGridPaint);
    }

    // Horizontal lines (voltage)
    for (double y = 0; y < size.height; y += smallStep) {
      final isMajor = (y % majorStep) < smallStep;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), isMajor ? majorGridPaint : smallGridPaint);
    }
  }

  void _drawSignal(Canvas canvas, Size size) {
    if (signalData.isEmpty) return;

    final linePaint = Paint()
      ..color = lineColor
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final path = Path();
    final midY = size.height / 2;

    // Normalize signal to fit in height
    final maxAbs = signalData.map((v) => v.abs()).reduce((a, b) => a > b ? a : b);
    final scale = maxAbs > 0 ? (size.height * 0.4) / maxAbs : 1.0;

    // Calculate how many samples fit on screen
    final samplesPerPixel = signalData.length / (size.width / zoomLevel);
    int startSample = (scrollOffset * samplesPerPixel).round().clamp(0, signalData.length - 1);

    bool first = true;
    for (double x = 0; x < size.width; x++) {
      final sampleIdx = (startSample + x * samplesPerPixel).round().clamp(0, signalData.length - 1).toInt();
      final y = midY - (signalData[sampleIdx] * scale * zoomLevel * 0.5);

      if (first) {
        path.moveTo(x, y);
        first = false;
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, linePaint);
  }

  void _drawLeadLabel(Canvas canvas, Size size) {
    final textPainter = TextPainter(
      text: TextSpan(
        text: leadName,
        style: TextStyle(
          color: Colors.white.withOpacity(0.85),
          fontSize: 11,
          fontWeight: FontWeight.w700,
          fontFamily: 'monospace',
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();

    // Background for label
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(4, 4, textPainter.width + 12, textPainter.height + 6),
        const Radius.circular(4),
      ),
      Paint()..color = Colors.black.withOpacity(0.5),
    );

    textPainter.paint(canvas, const Offset(10, 7));
  }

  @override
  bool shouldRepaint(covariant _EcgPainter oldDelegate) {
    return oldDelegate.zoomLevel != zoomLevel ||
        oldDelegate.showGrid != showGrid ||
        oldDelegate.scrollOffset != scrollOffset ||
        oldDelegate.signalData != signalData;
  }
}
