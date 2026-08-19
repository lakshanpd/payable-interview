import { useCallback, useEffect, useState } from 'react';

import { CircleService } from '../services/circles';
import { getErrorMessage } from '../services/api';
import { CircleDetail } from '../types';

interface UseCircleDetailResult {
  detail: CircleDetail | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useCircleDetail(circleId: number): UseCircleDetailResult {
  const [detail, setDetail] = useState<CircleDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await CircleService.getDetail(circleId);
      setDetail(data);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load this circle.'));
    } finally {
      setIsLoading(false);
    }
  }, [circleId]);

  useEffect(() => {
    setIsLoading(true);
    refresh();
  }, [refresh]);

  return { detail, isLoading, error, refresh };
}
