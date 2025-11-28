# Push Notifications Setup Guide

This guide covers the manual steps required to complete the push notification setup for the SeatSteal iOS app.

## Overview

The code for push notifications has been implemented. The following manual configuration steps are required:

1. Firebase Console setup
2. iOS App configuration in Xcode
3. Apple Developer account configuration
4. Environment variables setup

---

## 1. Firebase Console Setup

### Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.com)
2. Click "Add project" or select an existing project
3. Follow the wizard to create/configure your project

### Add iOS App to Firebase

1. In your Firebase project, click the iOS icon to add an iOS app
2. Enter your iOS bundle ID: `com.seatsteal.frontend`
   - This must match the bundle ID in your Xcode project
3. Enter an app nickname (optional): "SeatSteal iOS"
4. Click "Register app"

### Download Configuration File

1. Download the `GoogleService-Info.plist` file
2. Place it in: `seatsteal/ios/App/App/GoogleService-Info.plist`
3. In Xcode, add this file to your project:
   - Right-click on the "App" folder in Xcode
   - Select "Add Files to App"
   - Choose the `GoogleService-Info.plist` file
   - Make sure "Copy items if needed" is checked
   - Click "Add"

### Enable Cloud Messaging

1. In Firebase Console, go to "Build" → "Cloud Messaging"
2. The service should be automatically enabled

### Upload APNs Authentication Key

To send push notifications to iOS devices, Firebase needs your Apple Push Notification service (APNs) authentication key:

1. **Generate APNs Key in Apple Developer Portal:**
   - Go to [Apple Developer Account](https://developer.apple.com/account)
   - Navigate to "Certificates, Identifiers & Profiles"
   - Click "Keys" in the sidebar
   - Click the "+" button to create a new key
   - Give it a name like "SeatSteal Push Notifications"
   - Check "Apple Push Notifications service (APNs)"
   - Click "Continue" then "Register"
   - Download the `.p8` key file (you can only download this once!)
   - Note your **Key ID** and **Team ID**

2. **Upload to Firebase:**
   - In Firebase Console, go to Project Settings (gear icon) → "Cloud Messaging"
   - Scroll to "Apple app configuration"
   - Under "APNs Authentication Key", click "Upload"
   - Upload your `.p8` file
   - Enter the Key ID and Team ID
   - Click "Upload"

### Download Service Account for Backend

1. In Firebase Console, go to Project Settings (gear icon)
2. Navigate to "Service accounts" tab
3. Click "Generate new private key"
4. Download the JSON file
5. Save it as `firebase-credentials.json` in the `webapp/` directory
6. **IMPORTANT**: Add this file to `.gitignore` (it should already be there)

---

## 2. iOS App Configuration in Xcode

### Enable Push Notifications Capability

1. Open the iOS project in Xcode:
   ```bash
   cd seatsteal/ios
   open App.xcworkspace
   ```

2. Select the "App" target in the project navigator
3. Go to the "Signing & Capabilities" tab
4. Click the "+" button (Capability)
5. Search for and add "Push Notifications"
6. The capability should now appear in the list

### Enable Background Modes (Optional but Recommended)

For better notification handling when app is in background:

1. In the same "Signing & Capabilities" tab
2. Click "+" and add "Background Modes"
3. Check "Remote notifications"

### Verify Bundle ID

1. In the "General" tab, verify the Bundle Identifier is: `com.seatsteal.frontend`
2. Make sure this matches what you entered in Firebase

---

## 3. Environment Variables Setup

### Backend Environment Variables

Add the following to your `.env` file in the project root:

```bash
# Firebase Push Notifications
FIREBASE_CREDENTIALS_PATH=/path/to/seatsteal/webapp/firebase-credentials.json
```

Replace `/path/to/` with the actual absolute path to your project.

### Example .env entry:
```bash
FIREBASE_CREDENTIALS_PATH=/Users/yourname/projects/seatsteal/webapp/firebase-credentials.json
```

---

## 4. Install Dependencies

### Frontend Dependencies

```bash
cd seatsteal
npm install
npx cap sync ios
```

### Backend Dependencies

```bash
cd webapp
pip install -r requirements.txt
```

---

## 5. Database Migration

Run the database migration to create the `device_tokens` table:

```bash
cd webapp
alembic upgrade head
```

---

## 6. Testing

### Test on Real Device

**Note**: Push notifications do NOT work in the iOS Simulator. You must test on a real device.

1. Connect your iOS device
2. Select your device in Xcode
3. Build and run the app (⌘R)
4. Sign in to the app
5. Accept the push notification permission prompt
6. Check the backend logs to verify the device token was registered

### Test Notification Sending

1. Trigger a course notification (or use dry-run mode):
   ```bash
   cd webapp
   python notifications/send_notifs.py --dry-run
   ```

2. Check logs for push notification activity

### Manual Test via Firebase Console

1. In Firebase Console, go to "Cloud Messaging"
2. Click "Send your first message"
3. Enter a notification title and text
4. Click "Send test message"
5. Enter the FCM token from your device
6. Click "Test"

---

## 7. Production Checklist

Before deploying to production:

- [ ] `GoogleService-Info.plist` added to iOS project
- [ ] APNs authentication key uploaded to Firebase
- [ ] `firebase-credentials.json` secured and not in version control
- [ ] Environment variable `FIREBASE_CREDENTIALS_PATH` set on production server
- [ ] Push Notifications capability enabled in Xcode
- [ ] Database migration run on production database
- [ ] Tested on real iOS device
- [ ] Verified notifications work when app is in foreground, background, and closed

---

## Troubleshooting

### Token Not Registering

- Check that Push Notifications capability is enabled in Xcode
- Verify APNs key is uploaded to Firebase
- Check device logs in Xcode for registration errors
- Ensure you're testing on a real device, not simulator

### Notifications Not Appearing

- Verify APNs key is correctly configured in Firebase
- Check notification permissions in iOS Settings → SeatSteal
- Check backend logs for FCM errors
- Ensure device token is active in database

### Firebase Initialization Fails

- Check that `FIREBASE_CREDENTIALS_PATH` points to the correct file
- Verify the credentials JSON file has correct permissions
- Check backend logs for initialization errors

---

## Security Notes

- **Never commit** `firebase-credentials.json` to version control
- **Never commit** `GoogleService-Info.plist` with sensitive data to public repos
- Store Firebase credentials securely in production (use environment variables or secret management)
- Rotate Firebase service account keys periodically
- Use different Firebase projects for development and production

---

## Additional Resources

- [Firebase Cloud Messaging Documentation](https://firebase.google.com/docs/cloud-messaging)
- [Capacitor Push Notifications Plugin](https://capacitorjs.com/docs/apis/push-notifications)
- [Apple Push Notifications Service](https://developer.apple.com/documentation/usernotifications)
- [Firebase Admin SDK for Python](https://firebase.google.com/docs/admin/setup)

