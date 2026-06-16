const formulas = ['Cg = m / V', 'C = n / V', 'n = m / M', 'C1 × V1 = C2 × V2'];

export const FormulaPad = ({ onInsert }: { onInsert: (formula: string) => void }) => (
  <div className="formula-pad" aria-label="لوحة قوانين سريعة">
    <div>
      <strong>لوحة القوانين</strong>
      <span>اضغط لإدراج القانون في الإجابة.</span>
    </div>
    <div className="formula-pad-grid">
      {formulas.map((formula) => (
        <button key={formula} type="button" className="formula" onClick={() => onInsert(formula)} aria-label={`إدراج القانون ${formula}`}>
          {formula}
        </button>
      ))}
    </div>
  </div>
);
