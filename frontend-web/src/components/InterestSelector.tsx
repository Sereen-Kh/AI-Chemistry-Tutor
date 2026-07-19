import {
  Car,
  Circle,
  CookingPot,
  FlaskConical,
  Gamepad2,
  House,
  Leaf,
  Trophy,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import type { InterestCategory, StudentInterest } from '../types';

const interestIcons: Record<string, LucideIcon> = {
  football: Trophy,
  cars: Car,
  cooking: CookingPot,
  gaming: Gamepad2,
  daily_life: House,
  laboratory: FlaskConical,
  nature: Leaf,
};

interface InterestSelectorProps {
  interests: InterestCategory[];
  selected: StudentInterest[];
  onToggle: (interest: StudentInterest) => void;
  compact?: boolean;
  disabled?: boolean;
}

export const InterestSelector = ({
  interests,
  selected,
  onToggle,
  compact = false,
  disabled = false,
}: InterestSelectorProps) => (
  <div className={compact ? 'interest-grid compact' : 'interest-grid'} aria-label="اهتمامات الطالب">
    {interests.map((interest) => {
      const value = interest.key as StudentInterest;
      const Icon = interestIcons[value] ?? Circle;
      const active = selected.includes(value);
      return (
        <button
          key={interest.key}
          type="button"
          className={active ? 'interest active' : 'interest'}
          aria-pressed={active}
          onClick={() => onToggle(value)}
          disabled={disabled}
        >
          <Icon aria-hidden="true" size={compact ? 22 : 30} strokeWidth={1.8} />
          <strong>{interest.name_ar}</strong>
        </button>
      );
    })}
  </div>
);
