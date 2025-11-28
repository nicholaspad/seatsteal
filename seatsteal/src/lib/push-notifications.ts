import { PushNotifications, Token, ActionPerformed, PushNotificationSchema } from '@capacitor/push-notifications';
import { Capacitor } from '@capacitor/core';
import { logger } from './logger';
import { fetchWithToasts } from './api';

/**
 * Push Notification Service for managing FCM push notifications
 * Handles registration, token management, and notification events
 */
export class PushNotificationService {
  private static initialized = false;

  /**
   * Check if push notifications are supported on this platform
   */
  static isSupported(): boolean {
    return Capacitor.isNativePlatform();
  }

  /**
   * Initialize push notifications
   * Should be called after user authentication
   */
  static async initialize(): Promise<void> {
    if (this.initialized) {
      logger.debug('Push notifications already initialized');
      return;
    }

    if (!this.isSupported()) {
      logger.debug('Push notifications not supported on this platform');
      return;
    }

    try {
      // Request permission
      const permissionStatus = await PushNotifications.requestPermissions();
      
      // Mark as initialized regardless of permission result to prevent repeated prompts
      this.initialized = true;
      
      if (permissionStatus.receive === 'granted') {
        logger.info('Push notification permission granted');
        
        // Register for push notifications
        await PushNotifications.register();
        
        // Set up listeners
        this.setupListeners();
        
        logger.info('Push notifications initialized successfully');
      } else {
        logger.warn('Push notification permission denied');
      }
    } catch (error) {
      logger.error('Failed to initialize push notifications', error);
      // Mark as initialized even on error to prevent repeated attempts
      this.initialized = true;
    }
  }

  /**
   * Set up event listeners for push notifications
   */
  private static setupListeners(): void {
    // Handle successful registration
    PushNotifications.addListener('registration', async (token: Token) => {
      logger.info('Push notification registration success', token.value.substring(0, 20) + '...');
      
      try {
        // Send token to backend
        await this.registerToken(token.value);
      } catch (error) {
        logger.error('Failed to register token with backend', error);
      }
    });

    // Handle registration errors
    PushNotifications.addListener('registrationError', (error) => {
      logger.error('Push notification registration error', error);
    });

    // Handle incoming push notifications (when app is in foreground)
    PushNotifications.addListener('pushNotificationReceived', (notification: PushNotificationSchema) => {
      logger.info('Push notification received', notification);
      
      // You can show a custom in-app notification here if desired
      // For now, we'll let the OS handle it
    });

    // Handle notification tap (when user taps on notification)
    PushNotifications.addListener('pushNotificationActionPerformed', (notification: ActionPerformed) => {
      logger.info('Push notification action performed', notification);
      
      // Handle notification tap - navigate to relevant screen
      const data = notification.notification.data;
      
      if (data && data.type === 'course_notification') {
        // Navigate to courses page or specific course
        // You can implement navigation logic here
        logger.info('Course notification tapped', data);
      }
    });
  }

  /**
   * Register device token with backend
   */
  private static async registerToken(token: string): Promise<void> {
    try {
      const platform = Capacitor.getPlatform(); // 'ios' or 'android'
      
      const response = await fetchWithToasts('/api/device-tokens/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          platform,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to register token with backend');
      }

      const data = await response.json();
      logger.info('Token registered with backend', data);
    } catch (error) {
      logger.error('Failed to register token', error);
      throw error;
    }
  }

  /**
   * Unregister device token from backend
   */
  static async unregister(token: string): Promise<void> {
    if (!this.isSupported()) {
      return;
    }

    try {
      const response = await fetchWithToasts(`/api/device-tokens/${encodeURIComponent(token)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to unregister token');
      }

      logger.info('Token unregistered from backend');
    } catch (error) {
      logger.error('Failed to unregister token', error);
      throw error;
    }
  }

  /**
   * Get current push notification permission status
   */
  static async checkPermissions(): Promise<boolean> {
    if (!this.isSupported()) {
      return false;
    }

    try {
      const status = await PushNotifications.checkPermissions();
      return status.receive === 'granted';
    } catch (error) {
      logger.error('Failed to check permissions', error);
      return false;
    }
  }

  /**
   * Remove all listeners (cleanup)
   */
  static async cleanup(): Promise<void> {
    if (!this.isSupported()) {
      return;
    }

    try {
      await PushNotifications.removeAllListeners();
      this.initialized = false;
      logger.info('Push notification listeners removed');
    } catch (error) {
      logger.error('Failed to cleanup push notifications', error);
    }
  }
}

