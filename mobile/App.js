/**
 * EpiCare native shell (iOS / Android, Expo).
 *
 * The screens are the EpiCare web app (../app), embedded offline as one HTML page by
 * scripts/build-web.js. This file only hosts it full screen and passes the safe-area
 * insets (notch, home bar) so the web layout clears them on both platforms.
 *
 * Watch demo: the page asks for the phone's accelerometer with postMessage {type: "motion", on}.
 * Readings (in g, 50 per second) are sent back in batches to window.epicareMotion([[t, x, y, z], ...]);
 * {type: "vibrate"} makes the phone vibrate when the demo detector raises an alert.
 * {type: "notify", tag, title, body} shows a phone notification (local: works in Expo Go, even
 * with the app in the background); {type: "dismiss", tag} removes it (alert cancelled).
 * {type: "sms", phone, body} opens the SMS app with the alert message ready for the caregiver
 * (expo-sms, works in Expo Go); the result goes back to window.epicareSmsResult(result).
 * expo-sensors is part of Expo Go, so this works without a development build.
 */
import { StatusBar } from 'expo-status-bar';
import * as Notifications from 'expo-notifications';
import { Accelerometer } from 'expo-sensors';
import * as SMS from 'expo-sms';
import { useCallback, useEffect, useMemo, useRef } from 'react';
import { Platform, StyleSheet, Vibration, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';

import EPICARE_HTML from './web/epicare-html';

// Show demo alerts as a banner with sound even when the app is open.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false,
  }),
});

let notifReady = null;
/** Asks once for permission (and creates the Android channel). Resolves to true if allowed. */
function ensureNotifications() {
  notifReady ??= (async () => {
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('alerts', {
        name: 'Alertes de crise', importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 500, 200, 500], lightColor: '#FF7B7B',
      });
    }
    const cur = await Notifications.getPermissionsAsync();
    const st = cur.granted ? cur : await Notifications.requestPermissionsAsync();
    return !!st.granted;
  })().catch(() => false);
  return notifReady;
}

const SAMPLE_MS = 20; // 50 Hz, close to a research watch (Empatica E4: 32 Hz)
const BATCH_MS = 100; // send to the page 10 times per second

function EpiCareScreen() {
  const insets = useSafeAreaInsets();
  const webRef = useRef(null);
  const motion = useRef({ sub: null, timer: null, batch: [] });
  const notifIds = useRef({});

  const stopMotion = useCallback(() => {
    const m = motion.current;
    m.sub?.remove();
    clearInterval(m.timer);
    Object.assign(m, { sub: null, timer: null, batch: [] });
  }, []);

  const startMotion = useCallback(async () => {
    if (motion.current.sub) return;
    ensureNotifications(); // ask now, so the permission prompt does not appear during the alert
    const send = (js) => webRef.current?.injectJavaScript(`${js};true;`);
    if (!(await Accelerometer.isAvailableAsync())) {
      send('window.epicareMotionStatus && window.epicareMotionStatus({available:false})');
      return;
    }
    Accelerometer.setUpdateInterval(SAMPLE_MS);
    const m = motion.current;
    m.sub = Accelerometer.addListener(({ x, y, z }) => {
      m.batch.push([Date.now(), +x.toFixed(4), +y.toFixed(4), +z.toFixed(4)]);
    });
    m.timer = setInterval(() => {
      if (!m.batch.length) return;
      const out = m.batch;
      m.batch = [];
      send(`window.epicareMotion && window.epicareMotion(${JSON.stringify(out)})`);
    }, BATCH_MS);
  }, []);

  useEffect(() => stopMotion, [stopMotion]);

  const onMessage = useCallback((e) => {
    let msg;
    try { msg = JSON.parse(e.nativeEvent.data); } catch { return; }
    if (msg?.type === 'motion') (msg.on ? startMotion : stopMotion)();
    if (msg?.type === 'vibrate') Vibration.vibrate(Platform.OS === 'android' ? [0, 500, 200, 500, 200, 900] : [0, 400, 400]);
    if (msg?.type === 'notify') {
      ensureNotifications().then(async (ok) => {
        if (!ok) return;
        const id = await Notifications.scheduleNotificationAsync({
          content: { title: String(msg.title || 'EpiCare'), body: String(msg.body || ''), sound: true,
            ...(Platform.OS === 'android' ? { priority: Notifications.AndroidNotificationPriority.MAX } : {}) },
          trigger: Platform.OS === 'android' ? { channelId: 'alerts' } : null,
        });
        if (msg.tag) notifIds.current[msg.tag] = id;
      }).catch(() => {});
    }
    if (msg?.type === 'sms') {
      const reply = (r) => webRef.current?.injectJavaScript(`window.epicareSmsResult && window.epicareSmsResult(${JSON.stringify(r)});true;`);
      (async () => {
        if (!(await SMS.isAvailableAsync())) return reply('unavailable');
        const { result } = await SMS.sendSMSAsync([String(msg.phone)], String(msg.body));
        reply(result);
      })().catch(() => reply('unavailable'));
    }
    if (msg?.type === 'dismiss' && notifIds.current[msg.tag]) {
      Notifications.dismissNotificationAsync(notifIds.current[msg.tag]).catch(() => {});
      delete notifIds.current[msg.tag];
    }
  }, [startMotion, stopMotion]);

  // Android WebViews report env(safe-area-inset-*) as 0: give the real values to the CSS.
  const injected = useMemo(() => `
    (function () {
      var s = document.createElement('style');
      s.textContent = ':root{--safe-top:${Math.round(insets.top)}px;--safe-bottom:${Math.round(insets.bottom)}px}';
      (document.head || document.documentElement).appendChild(s);
    })();
    true;`, [insets.top, insets.bottom]);

  return (
    <View style={[styles.root, { backgroundColor: '#0a1a3a' }]}>
      <StatusBar style="light" />
      <WebView
        ref={webRef}
        key={injected /* re-inject if the insets change (rotation) */}
        onMessage={onMessage}
        originWhitelist={['*']}
        source={{ html: EPICARE_HTML, baseUrl: 'https://epicare.app/' }}
        injectedJavaScriptBeforeContentLoaded={injected}
        style={styles.web}
        javaScriptEnabled
        domStorageEnabled
        allowFileAccess
        bounces={false}
        overScrollMode="never"
        contentInsetAdjustmentBehavior="never"
        automaticallyAdjustContentInsets={false}
        setSupportMultipleWindows={false}
        allowsBackForwardNavigationGestures={Platform.OS === 'ios'}
        decelerationRate="normal"
      />
    </View>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <EpiCareScreen />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  web: { flex: 1, backgroundColor: 'transparent' },
});
