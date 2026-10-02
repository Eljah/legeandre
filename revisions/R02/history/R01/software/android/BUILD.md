# Android (Java only)
Android Studio / JDK 17, Android SDK 35, Gradle 8.9, Android Gradle Plugin 8.7.3.
Open this folder in Android Studio, install SDK 35 and let Gradle sync.
Alternatively, with Gradle 8.9 installed: `gradle :app:assembleDebug`.
The Gradle wrapper and SDK binaries are not bundled. No APK was built in the generation environment (no Android SDK or network).

Connect: hold physical ARM on a healthy controller for 2 seconds, scan, tap its address, enter the prototype's 6-digit PIN shown in the USB console / printed label. An ARM press only grants a 60-second start window; it does not heat. Work session is at most 30 minutes. BLE commands do not implement remote ARM/reset.
Foreground app sends PING every second. OnStop sends STOP and stops heartbeats; the MCU independently times out after 5 seconds. This is intentional for R01, not a background heating service.
