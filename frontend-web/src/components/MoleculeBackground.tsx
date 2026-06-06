import './MoleculeBackground.css';

export const MoleculeBackground = () => {
  return (
    <div className="molecule-bg-container" aria-hidden="true">
      <svg className="molecule-bg-svg" width="100%" height="100%">
        {/* Definining glow filters */}
        <defs>
          <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="glow-violet" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Top Right: Water/Oxygen Molecule structure */}
        <g className="mol-group mol-tr">
          {/* Bonds */}
          <line x1="85%" y1="12%" x2="92%" y2="8%" className="mol-bond bond-violet" />
          <line x1="85%" y1="12%" x2="82%" y2="24%" className="mol-bond bond-violet" />
          {/* Atoms */}
          <circle cx="85%" cy="12%" r="14" className="mol-atom atom-violet" />
          <circle cx="92%" cy="8%" r="8" className="mol-atom atom-green" />
          <circle cx="82%" cy="24%" r="8" className="mol-atom atom-green" />
          <text x="85%" y="12%" className="mol-label" dy=".3em">O</text>
          <text x="92%" y="8%" className="mol-label-sm" dy=".3em">H</text>
          <text x="82%" y="24%" className="mol-label-sm" dy=".3em">H</text>
        </g>

        {/* Bottom Left: Carbon Chain Molecule */}
        <g className="mol-group mol-bl">
          {/* Bonds */}
          <line x1="8%" y1="75%" x2="16%" y2="70%" className="mol-bond bond-green" />
          <line x1="16%" y1="70%" x2="24%" y2="78%" className="mol-bond bond-green" />
          <line x1="24%" y1="78%" x2="32%" y2="73%" className="mol-bond bond-green" />
          {/* Side Bonds */}
          <line x1="16%" y1="70%" x2="16%" y2="58%" className="mol-bond bond-coral" />
          <line x1="24%" y1="78%" x2="24%" y2="90%" className="mol-bond bond-violet" />

          {/* Atoms */}
          <circle cx="8%" cy="75%" r="10" className="mol-atom atom-green" />
          <circle cx="16%" cy="70%" r="12" className="mol-atom atom-green" />
          <circle cx="24%" cy="78%" r="12" className="mol-atom atom-green" />
          <circle cx="32%" cy="73%" r="10" className="mol-atom atom-green" />
          <circle cx="16%" cy="58%" r="7" className="mol-atom atom-coral" />
          <circle cx="24%" cy="90%" r="7" className="mol-atom atom-violet" />

          <text x="16%" y="70%" className="mol-label" dy=".3em">C</text>
          <text x="24%" y="78%" className="mol-label" dy=".3em">C</text>
        </g>

        {/* Middle Right: Benzene Ring Molecule */}
        <g className="mol-group mol-mr">
          {/* Bonds */}
          <line x1="88%" y1="42%" x2="94%" y2="46%" className="mol-bond bond-green" />
          <line x1="94%" y1="46%" x2="94%" y2="54%" className="mol-bond bond-double" />
          <line x1="94%" y1="54%" x2="88%" y2="58%" className="mol-bond bond-green" />
          <line x1="88%" y1="58%" x2="82%" y2="54%" className="mol-bond bond-double" />
          <line x1="82%" y1="54%" x2="82%" y2="46%" className="mol-bond bond-green" />
          <line x1="82%" y1="46%" x2="88%" y2="42%" className="mol-bond bond-double" />

          {/* Core Atoms */}
          <circle cx="88%" cy="42%" r="9" className="mol-atom atom-violet" />
          <circle cx="94%" cy="46%" r="9" className="mol-atom atom-violet" />
          <circle cx="94%" cy="54%" r="9" className="mol-atom atom-violet" />
          <circle cx="88%" cy="58%" r="9" className="mol-atom atom-violet" />
          <circle cx="82%" cy="54%" r="9" className="mol-atom atom-violet" />
          <circle cx="82%" cy="46%" r="9" className="mol-atom atom-violet" />
        </g>

        {/* Background Grid Lines (Faint laboratory blueprint look) */}
        <path
          d="M 0,100 L 2000,100 M 0,300 L 2000,300 M 0,500 L 2000,500 M 0,700 L 2000,700 M 0,900 L 2000,900"
          stroke="rgba(13, 242, 163, 0.025)"
          strokeWidth="1"
        />
        <path
          d="M 100,0 L 100,2000 M 300,0 L 300,2000 M 500,0 L 500,2000 M 700,0 L 700,2000 M 900,0 L 900,2000"
          stroke="rgba(13, 242, 163, 0.025)"
          strokeWidth="1"
        />
      </svg>
    </div>
  );
};
