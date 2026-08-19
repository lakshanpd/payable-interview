import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { useAuth } from '../hooks/useAuth';
import { CircleScreen } from '../screens/CircleScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { LoginScreen } from '../screens/LoginScreen';
import { RegisterScreen } from '../screens/RegisterScreen';
import { CircleStorage } from '../services/storage';
import { RootStackParamList } from './types';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  const { user, isBootstrapping } = useAuth();
  const [lastCircleId, setLastCircleId] = useState<number | null>(null);
  const [isResolvingLastCircle, setIsResolvingLastCircle] = useState(true);

  useEffect(() => {
    if (!user) {
      setIsResolvingLastCircle(false);
      return;
    }
    CircleStorage.getLastCircleId().then((id) => {
      setLastCircleId(id);
      setIsResolvingLastCircle(false);
    });
  }, [user]);

  if (isBootstrapping || (user && isResolvingLastCircle)) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{ headerTitleAlign: 'center' }}
        // Must match a screen actually registered in the branch below:
        // 'Circle'/'Home' only exist when logged in, 'Login' only when not.
        initialRouteName={user ? (lastCircleId ? 'Circle' : 'Home') : 'Login'}
      >
        {user ? (
          <>
            <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'CircleFund' }} />
            <Stack.Screen
              name="Circle"
              component={CircleScreen}
              initialParams={lastCircleId ? { circleId: lastCircleId } : undefined}
              options={{ title: 'Circle' }}
            />
          </>
        ) : (
          <>
            <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Register" component={RegisterScreen} options={{ headerShown: false }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
