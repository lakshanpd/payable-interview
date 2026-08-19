import { NativeStackScreenProps } from '@react-navigation/native-stack';
import React, { useMemo, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ApproveButton } from '../components/ApproveButton';
import { ContributeButton } from '../components/ContributeButton';
import { MemberRow } from '../components/MemberRow';
import { useAuth } from '../hooks/useAuth';
import { useCircleDetail } from '../hooks/useCircleDetail';
import { RootStackParamList } from '../navigation/types';
import { Round } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'Circle'>;

const STATUS_LABELS: Record<Round['status'], string> = {
  OPEN: 'Open for contributions',
  PENDING_APPROVAL: 'Awaiting admin approval',
  COMPLETED: 'Completed',
};

function formatAmount(value: number): string {
  return value.toLocaleString('en-US');
}

export function CircleScreen({ route }: Props) {
  const { circleId } = route.params;
  const { user } = useAuth();
  const { detail, isLoading, error, refresh } = useCircleDetail(circleId);

  // Optimistic override for the current user's contribution status. `null`
  // means "defer to whatever the server last told us" (see MemberRow).
  const [optimisticContributed, setOptimisticContributed] = useState<boolean | null>(null);
  const [contributeError, setContributeError] = useState<string | null>(null);
  const [approveError, setApproveError] = useState<string | null>(null);

  const currentUserMember = useMemo(
    () => detail?.members.find((m) => m.user.id === user?.id) ?? null,
    [detail, user]
  );

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error || !detail) {
    return (
      <View style={styles.centered}>
        <Text style={styles.error}>{error ?? 'Circle not found.'}</Text>
      </View>
    );
  }

  const { circle, members, current_round: currentRound } = detail;
  const isAdmin = user?.id === circle.admin.id;

  const hasContributed = optimisticContributed ?? currentUserMember?.has_contributed_current_round ?? null;
  const canContribute = Boolean(
    currentRound &&
      currentRound.status === 'OPEN' &&
      currentUserMember &&
      !currentUserMember.is_current_recipient &&
      hasContributed === false
  );
  const canApprove = Boolean(isAdmin && currentRound && currentRound.status === 'PENDING_APPROVAL');

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={false} onRefresh={refresh} />}
    >
      <Text style={styles.circleName}>{circle.name}</Text>
      <Text style={styles.inviteCode}>Invite code: {circle.invite_code}</Text>
      <Text style={styles.contributionAmount}>Contribution: {formatAmount(circle.contribution_amount)} / round</Text>

      {currentRound ? (
        <View style={styles.roundCard}>
          <Text style={styles.roundStatus}>{STATUS_LABELS[currentRound.status]}</Text>
          <Text style={styles.roundDetail}>
            Recipient: {currentRound.payout_recipient.user.username} (position {currentRound.payout_recipient.position})
          </Text>
          <Text style={styles.roundDetail}>Deadline: {new Date(currentRound.deadline).toLocaleDateString()}</Text>
          {currentRound.payout_amount != null && (
            <Text style={styles.roundDetail}>Payout: {formatAmount(currentRound.payout_amount)}</Text>
          )}
        </View>
      ) : (
        <View style={styles.roundCard}>
          <Text style={styles.roundStatus}>All members have received their payout 🎉</Text>
        </View>
      )}

      <Text style={styles.sectionTitle}>Members</Text>
      <View style={styles.membersCard}>
        {members.map((member) => (
          <MemberRow
            key={member.id}
            member={member}
            hasContributedOverride={member.id === currentUserMember?.id ? hasContributed ?? undefined : undefined}
          />
        ))}
      </View>

      {contributeError && <Text style={styles.error}>{contributeError}</Text>}
      {currentRound && (
        <ContributeButton
          roundId={currentRound.id}
          visible={canContribute}
          onOptimisticStart={() => {
            setContributeError(null);
            setOptimisticContributed(true);
          }}
          onSuccess={() => {
            setOptimisticContributed(null);
            refresh();
          }}
          onError={(message) => {
            setOptimisticContributed(false);
            setContributeError(message);
          }}
        />
      )}

      {approveError && <Text style={styles.error}>{approveError}</Text>}
      {currentRound && (
        <ApproveButton
          roundId={currentRound.id}
          visible={canApprove}
          onSuccess={() => {
            setApproveError(null);
            refresh();
          }}
          onError={setApproveError}
        />
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, backgroundColor: '#fff', flexGrow: 1 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  circleName: { fontSize: 26, fontWeight: '800', color: '#111827' },
  inviteCode: { fontSize: 14, color: '#6b7280', marginTop: 4 },
  contributionAmount: { fontSize: 14, color: '#6b7280', marginTop: 2, marginBottom: 20 },
  roundCard: { backgroundColor: '#f9fafb', borderRadius: 14, padding: 16, marginBottom: 24 },
  roundStatus: { fontSize: 16, fontWeight: '700', color: '#111827', marginBottom: 6 },
  roundDetail: { fontSize: 14, color: '#374151', marginTop: 2 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#111827', marginBottom: 8 },
  membersCard: { backgroundColor: '#f9fafb', borderRadius: 14, paddingHorizontal: 14 },
  error: { color: '#dc2626', marginTop: 12, fontSize: 14 },
});
