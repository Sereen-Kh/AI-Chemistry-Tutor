import { exampleProblems } from '../mockData';

export const ExampleProblemCards = ({ onSelect }: { onSelect: (problem: string) => void }) => (
  <div className="guided-example-grid" aria-label="أمثلة مسائل كيمياء">
    {exampleProblems.map((example) => (
      <button
        key={example.title}
        type="button"
        className="guided-example-card"
        onClick={() => onSelect(example.problem)}
      >
        <span>{example.title}</span>
        <strong>{example.label}</strong>
        <small>{example.problem}</small>
      </button>
    ))}
  </div>
);
