# AI Chemistry Tutor — Frontend

Flutter frontend for the AI Chemistry Tutor app. Works on iOS, Android, Web, and Desktop.

## Requirements

- Flutter SDK 3.0+
- Backend running on `http://localhost:8000`

## Setup

```bash
cd frontend
flutter pub get
flutter run
```

To target a specific platform:

```bash
flutter run -d chrome       # Web
flutter run -d ios          # iOS Simulator
flutter run -d android      # Android Emulator
```

## Configuration

The backend URL is set in `lib/services/api_service.dart`. Change `_baseUrl` if your backend runs on a different host/port (e.g., use your machine's LAN IP when testing on a physical device).

## Project Structure

```
lib/
├── main.dart               # App entry point
├── models/
│   └── message.dart        # Message data model
├── providers/
│   └── chat_provider.dart  # State management
├── screens/
│   └── chat_screen.dart    # Main chat UI
├── services/
│   └── api_service.dart    # HTTP client
└── widgets/
    ├── chat_input.dart     # Message input bar
    └── message_bubble.dart # Chat bubble with Markdown support
```
