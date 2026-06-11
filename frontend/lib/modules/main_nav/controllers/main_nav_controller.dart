import 'package:flutter/material.dart';
import 'package:get/get.dart';

class MainNavController extends GetxController {
  final currentIndex = 0.obs;
  final scaffoldKey = GlobalKey<ScaffoldState>();

  void changeTab(int i) => currentIndex.value = i;
  void openDrawer() => scaffoldKey.currentState?.openDrawer();
}
