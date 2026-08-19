import { NativeStackScreenProps } from '@react-navigation/native-stack';
import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { useAuth } from '../hooks/useAuth';
import { getErrorMessage } from '../services/api';
import { CircleService } from '../services/circles';
import { CircleStorage } from '../services/storage';
import { RootStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export function HomeScreen({ navigation }: Props) {
  const { user, logout } = useAuth();

  const [circleName, setCircleName] = useState('');
  const [contributionAmount, setContributionAmount] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [inviteCode, setInviteCode] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);

  // On first landing on Home after login, jump straight to whatever circle
  // was last open — but only once. `hasAutoNavigated` stops this from
  // refiring if the user taps back from Circle to Home on purpose (Home
  // stays mounted the whole time it's under Circle in the stack, so this
  // effect — which only runs on mount — won't run again).
  const hasAutoNavigated = useRef(false);
  useEffect(() => {
    if (hasAutoNavigated.current) return;
    hasAutoNavigated.current = true;
    CircleStorage.getLastCircleId().then((circleId) => {
      if (circleId != null) {
        navigation.navigate('Circle', { circleId });
      }
    });
  }, [navigation]);

  const goToCircle = async (circleId: number) => {
    await CircleStorage.setLastCircleId(circleId);
    navigation.navigate('Circle', { circleId });
  };

  const handleCreate = async () => {
    setCreateError(null);
    const amount = parseInt(contributionAmount, 10);
    if (!circleName.trim() || !Number.isFinite(amount) || amount <= 0) {
      setCreateError('Enter a circle name and a positive contribution amount.');
      return;
    }
    setIsCreating(true);
    try {
      const circle = await CircleService.create(circleName.trim(), amount);
      await goToCircle(circle.id);
    } catch (err) {
      setCreateError(getErrorMessage(err, 'Could not create the circle.'));
    } finally {
      setIsCreating(false);
    }
  };

  const handleJoin = async () => {
    setJoinError(null);
    if (!inviteCode.trim()) {
      setJoinError('Enter an invite code.');
      return;
    }
    setIsJoining(true);
    try {
      const membership = await CircleService.join(inviteCode.trim().toUpperCase());
      if (membership.circle) {
        await goToCircle(membership.circle);
      }
    } catch (err) {
      setJoinError(getErrorMessage(err, 'Could not join that circle.'));
    } finally {
      setIsJoining(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <Text style={styles.greeting}>Hi, {user?.username}</Text>
        <Pressable onPress={logout}>
          <Text style={styles.logout}>Log out</Text>
        </Pressable>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Create a circle</Text>
        <TextInput style={styles.input} placeholder="Circle name" value={circleName} onChangeText={setCircleName} />
        <TextInput
          style={styles.input}
          placeholder="Contribution amount"
          keyboardType="number-pad"
          value={contributionAmount}
          onChangeText={setContributionAmount}
        />
        {createError && <Text style={styles.error}>{createError}</Text>}
        <Pressable style={styles.button} onPress={handleCreate} disabled={isCreating}>
          {isCreating ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonLabel}>Create Circle</Text>}
        </Pressable>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Join a circle</Text>
        <TextInput
          style={styles.input}
          placeholder="Invite code"
          autoCapitalize="characters"
          value={inviteCode}
          onChangeText={setInviteCode}
        />
        {joinError && <Text style={styles.error}>{joinError}</Text>}
        <Pressable style={[styles.button, styles.buttonSecondary]} onPress={handleJoin} disabled={isJoining}>
          {isJoining ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonLabel}>Join Circle</Text>}
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, backgroundColor: '#fff', flexGrow: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  greeting: { fontSize: 22, fontWeight: '700', color: '#111827' },
  logout: { color: '#dc2626', fontSize: 14, fontWeight: '600' },
  card: {
    backgroundColor: '#f9fafb',
    borderRadius: 14,
    padding: 18,
    marginBottom: 20,
  },
  cardTitle: { fontSize: 17, fontWeight: '700', marginBottom: 12, color: '#111827' },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    marginBottom: 10,
    backgroundColor: '#fff',
  },
  error: { color: '#dc2626', marginBottom: 10, fontSize: 14 },
  button: { backgroundColor: '#2563eb', paddingVertical: 14, borderRadius: 10, alignItems: 'center' },
  buttonSecondary: { backgroundColor: '#4f46e5' },
  buttonLabel: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
