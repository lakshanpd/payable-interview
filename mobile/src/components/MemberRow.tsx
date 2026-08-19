import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { CircleDetailMember } from '../types';

interface Props {
  member: CircleDetailMember;
  hasContributedOverride?: boolean;
}

export function MemberRow({ member, hasContributedOverride }: Props) {
  const hasContributed = hasContributedOverride ?? member.has_contributed_current_round;

  const statusLabel = member.is_current_recipient
    ? 'Receiving this round'
    : hasContributed
    ? 'Contributed'
    : hasContributed === false
    ? 'Not contributed yet'
    : '—';

  const statusColor = member.is_current_recipient ? '#7c3aed' : hasContributed ? '#16a34a' : '#dc2626';

  return (
    <View style={styles.row}>
      <View style={styles.positionBadge}>
        <Text style={styles.positionText}>{member.position}</Text>
      </View>
      <View style={styles.info}>
        <Text style={styles.username}>
          {member.user.username}
          {member.is_admin ? ' (admin)' : ''}
        </Text>
        <Text style={[styles.status, { color: statusColor }]}>{statusLabel}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#e5e7eb',
  },
  positionBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#eef2ff',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  positionText: { color: '#4338ca', fontWeight: '700', fontSize: 13 },
  info: { flex: 1 },
  username: { fontSize: 16, fontWeight: '600', color: '#111827' },
  status: { fontSize: 13, marginTop: 2 },
});
