import type { UserPreferences, UserProfile } from '../types';

const hasItems = (values?: unknown[] | null): boolean => Array.isArray(values) && values.length > 0;

export const isOnboardingCompleteFromValues = ({
  studentInterests,
  learningModes,
  teachingLevel,
  explanationMethod,
}: {
  studentInterests?: unknown[] | null;
  learningModes?: unknown[] | null;
  teachingLevel?: string | null;
  explanationMethod?: string | null;
}): boolean => (
  hasItems(studentInterests)
  && hasItems(learningModes)
  && Boolean(teachingLevel)
  && Boolean(explanationMethod)
);

export const isUserOnboardingComplete = (user: UserProfile | null, preferences?: UserPreferences): boolean => {
  if (!user) return false;
  if (typeof user.onboarding_completed === 'boolean') return user.onboarding_completed;
  return isOnboardingCompleteFromValues({
    studentInterests: user.student_interests ?? preferences?.studentInterests,
    learningModes: user.learning_modes ?? preferences?.learningModes,
    teachingLevel: user.teaching_level ?? preferences?.teachingLevel,
    explanationMethod: user.explanation_method ?? preferences?.explanationMethod,
  });
};
