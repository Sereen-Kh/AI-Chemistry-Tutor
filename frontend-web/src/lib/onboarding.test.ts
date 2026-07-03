import { describe, expect, it } from 'vitest';

import { isOnboardingCompleteFromValues, isUserOnboardingComplete } from './onboarding';
import type { UserProfile } from '../types';

describe('onboarding completion helpers', () => {
  it('requires interests, learning modes, teaching level, and explanation method', () => {
    expect(isOnboardingCompleteFromValues({
      studentInterests: ['cars'],
      learningModes: ['text'],
      teachingLevel: 'standard',
      explanationMethod: 'direct',
    })).toBe(true);

    expect(isOnboardingCompleteFromValues({
      studentInterests: [],
      learningModes: ['text'],
      teachingLevel: 'standard',
      explanationMethod: 'direct',
    })).toBe(false);
  });

  it('uses backend onboarding_completed when present', () => {
    const incompleteUser = {
      id: 1,
      name: 'طالب',
      email: 'student@example.com',
      grade: 'grade_9',
      subject: 'chemistry',
      teaching_style: 'real_life_examples',
      answer_format: 'text',
      language: 'ar',
      xp: 0,
      level: 1,
      streak_days: 0,
      onboarding_completed: false,
      student_interests: ['cars'],
      learning_modes: ['text'],
      teaching_level: 'standard',
      explanation_method: 'direct',
    } satisfies UserProfile;

    expect(isUserOnboardingComplete(incompleteUser)).toBe(false);
    expect(isUserOnboardingComplete({ ...incompleteUser, onboarding_completed: true })).toBe(true);
  });
});
