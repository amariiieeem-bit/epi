# EpiCare native app (Expo)

iOS and Android app built with Expo. Its screens are the EpiCare web app (`../app`), embedded
offline by `scripts/build-web.js` and shown full screen in a WebView (`App.js`). Edit the
screens in `../app`; this folder only packages them.

## Try it on a phone with Expo Go

```bash
cd mobile
npm install
npm start              # rebuilds the embedded page, then starts Expo
```

Scan the QR code with the iPhone camera (or the Expo Go app on Android). Phone and PC must be on
the same Wi-Fi. If the network blocks devices from seeing each other (university or office
Wi-Fi), use `npm run tunnel` instead.

## Live demo: the phone stands in for the watch

Détection tab → **Lancer la démo**. `App.js` reads the phone's accelerometer (`expo-sensors`,
50 Hz, included in Expo Go) and streams it to the page; the demo detector (`renderDemo` in
`../app/app.js`) raises an alert after ~8 s of strong (RMS ≥ 0.45 g) rhythmic (2.5–9 Hz, measured on the axis that moves most)
shaking, tuned by the branch 1 prior shift. Walking does not trigger it. On a PC with no sensor,
use the simulation buttons. Nothing is sent automatically.

On alert, the phone shows a local notification (`expo-notifications`, works in Expo Go); if the
patient does not tap « Je vais bien » within 10 s, a second notification shows what the
caregiver would receive, and a button opens the SMS app (`expo-sms`) with the alert message ready for the caregiver from the profile. Sending a push to the caregiver's own phone needs push notifications and a
development build (remote push is not available in Expo Go on Android).

## Update the results shown

`npm start` re-embeds `../app/data/app_data.json` (and `../app/data/branch2.json` if present).
After `python -m epicare_b1 export-app`, restart `npm start` and reload the app.

## Publish on the App Store and Google Play

Builds run in the cloud with EAS, no Mac needed:

```bash
npx eas-cli@latest login
npx eas-cli@latest build -p android --profile preview   # .apk to share by link
npx eas-cli@latest build -p ios                         # needs an Apple Developer account (99 $/year)
npx eas-cli@latest submit -p ios                        # or -p android (Google Play: 25 $ once)
```

App id: `com.epicare.app` (in `app.json`; change it before the first store upload if needed).
Health apps are reviewed closely: present EpiCare as a research / information tool, not a
medical device, and provide a privacy policy.
