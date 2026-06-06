import { mockBalanceEquation } from './mockData';
import type { BalanceResult } from '../types';

export const labApi = {
  async balanceEquation(input: string): Promise<BalanceResult> {
    return mockBalanceEquation(input);
  },
};
