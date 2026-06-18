import { Link } from 'react-router-dom';
import type { CompanionAction } from '../types';

export const AIContextSuggestions = ({
  actions,
  onAction,
}: {
  actions: CompanionAction[];
  onAction?: (action: CompanionAction) => void;
}) => (
  <div className="ai-companion-suggestions" aria-label="اقتراحات المرشد">
    {actions.map((action) => (
      onAction ? (
        <button key={action.id} type="button" className="ai-companion-action" onClick={() => onAction(action)}>
          <strong>{action.label}</strong>
          {action.description && <span>{action.description}</span>}
        </button>
      ) : action.targetRoute ? (
        <Link key={action.id} to={action.targetRoute} className="ai-companion-action">
          <strong>{action.label}</strong>
          {action.description && <span>{action.description}</span>}
        </Link>
      ) : (
        <button key={action.id} type="button" className="ai-companion-action" disabled>
          <strong>{action.label}</strong>
          {action.description && <span>{action.description}</span>}
        </button>
      )
    ))}
  </div>
);
