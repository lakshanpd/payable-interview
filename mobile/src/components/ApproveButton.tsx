import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { getErrorMessage } from '../services/api';
import { RoundService } from '../services/rounds';
import { Round } from '../types';

interface Props {
  roundId: number;
  visible: boolean;
  onSuccess: (round: Round) => void;
  onError: (message: string) => void;
}

export function ApproveButton({ roundId, visible, onSuccess, onError }: Props) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!visible) return null;

  const handlePress = async () => {
    // `isSubmitting` (plus the `disabled` prop below) is what stops a
    // second tap from firing a second approve request while the first is
    // still in flight.
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      const round = await RoundService.approve(roundId);
      onSuccess(round);
    } catch (err) {
      onError(getErrorMessage(err, 'Could not approve this round.'));
      setIsSubmitting(false);
    }
  };

  return (
    <Pressable
      style={({ pressed }) => [styles.button, pressed && styles.buttonPressed, isSubmitting && styles.buttonDisabled]}
      onPress={handlePress}
      disabled={isSubmitting}
    >
      {isSubmitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.label}>Approve Payout</Text>}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#16a34a',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 12,
  },
  buttonPressed: { opacity: 0.85 },
  buttonDisabled: { opacity: 0.6 },
  label: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
