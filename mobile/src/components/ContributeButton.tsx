import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { getErrorMessage } from '../services/api';
import { RoundService } from '../services/rounds';
import { Round } from '../types';

interface Props {
  roundId: number;
  visible: boolean;
  onOptimisticStart: () => void;
  onSuccess: (round: Round) => void;
  onError: (message: string) => void;
}

/**
 * Optimistic contribute flow: mark the member as contributed the instant
 * the button is pressed (onOptimisticStart), fire the request, and only if
 * it fails do we ask the parent to roll the UI state back (onError).
 */
export function ContributeButton({ roundId, visible, onOptimisticStart, onSuccess, onError }: Props) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!visible) return null;

  const handlePress = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    onOptimisticStart();
    try {
      const round = await RoundService.contribute(roundId);
      onSuccess(round);
    } catch (err) {
      onError(getErrorMessage(err, 'Could not submit your contribution.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Pressable
      style={({ pressed }) => [styles.button, pressed && styles.buttonPressed, isSubmitting && styles.buttonDisabled]}
      onPress={handlePress}
      disabled={isSubmitting}
    >
      {isSubmitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.label}>Contribute</Text>}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#2563eb',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 16,
  },
  buttonPressed: { opacity: 0.85 },
  buttonDisabled: { opacity: 0.6 },
  label: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
